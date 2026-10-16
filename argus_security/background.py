# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Opt-in local scheduling for incremental, read-only IMAP scans.

This module deliberately has no daemon or import-time side effects.  A caller
must explicitly enable a schedule, provide OS-keyring-backed authorization and
call :meth:`BackgroundScanService.run_due` with network permission.  The local
dashboard process (``server.py``) is the only host that calls it; no scan is
started merely because this module is installed.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
import time
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from .imap_client import IMAPConfig, imap_messages, load_config, with_keep_alive
from .mailbox_lease import MailboxBusy, MailboxLease
from .store import UNCHANGED, atomic_meta_update
from .scan import scan_messages


SCHEDULE_META_KEY = "background_imap_schedule"
SCHEDULE_VERSION = 1
MIN_INTERVAL_SECONDS = 15 * 60
MAX_INTERVAL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
DEFAULT_LIMIT = 500
MAX_LIMIT = 10_000
RUN_LEASE_SECONDS = 5 * 60
TARGET_CHANGED_ERROR = ("IMAP settings differ from the authorized target; scheduled scans stopped. "
                        "Run background-imap enable to approve the current settings.")
# A running scan renews its lease well before expiry and notices a disable,
# revoke or replacement lease within this interval.
LEASE_RENEW_SECONDS = 15


class MetaStore(Protocol):
    """The small persistence interface needed by the scheduler."""

    def meta(self, key: str, default: Any = None) -> Any: ...

    def set_meta(self, key: str, value: Any) -> None: ...


class CredentialError(Exception):
    """A fixed, non-sensitive credential-storage error."""


class ScanCancelled(Exception):
    """The scheduled run no longer owns its lease (disabled, revoked or replaced)."""


def _valid_credential_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return True


def _validate_secret(secret: object) -> str:
    if not isinstance(secret, str) or not secret or any(char in secret for char in "\r\n\x00\x01"):
        raise CredentialError("The IMAP authorization is missing or invalid")
    return secret


class KeyringCredentialStore:
    """Stores an IMAP app password/token only in the operating-system keyring.

    ``keyring`` is optional so that importing ARGUS does not add a dependency.
    There is intentionally no plaintext file fallback.  The opaque UUID stored
    in the local ARGUS database is only a selector for the keyring entry.
    """

    def __init__(self, keyring: object | None = None, service_name: str = "ARGUS IMAP authorization"):
        if not isinstance(service_name, str) or not service_name or len(service_name) > 128:
            raise ValueError("Invalid keyring service name")
        self._keyring = keyring
        self._service_name = service_name

    def _backend(self):
        if self._keyring is not None:
            return self._keyring
        try:
            import keyring  # type: ignore[import-not-found]
        except ImportError:
            raise CredentialError("The OS keyring is unavailable; background scans cannot safely store IMAP authorization") from None
        backend = keyring.get_keyring()
        identity = (type(backend).__module__ + "." + type(backend).__name__).lower()
        # The optional keyring ecosystem can be configured with file-backed
        # fallbacks. ARGUS requires an OS-managed secret store and refuses
        # these known plaintext alternatives instead of treating them as one.
        if "plaintext" in identity or "keyrings.alt" in identity or "chainer" in identity:
            raise CredentialError("The selected keyring is not an OS-protected secret store; background scans cannot safely store IMAP authorization")
        return keyring

    def save(self, secret: str, credential_id: str | None = None) -> str:
        secret = _validate_secret(secret)
        credential_id = credential_id or str(uuid4())
        if not _valid_credential_id(credential_id):
            raise ValueError("Invalid credential selector")
        try:
            self._backend().set_password(self._service_name, credential_id, secret)
        except Exception:
            raise CredentialError("The OS keyring is unavailable; background scans cannot safely store IMAP authorization") from None
        return credential_id

    def load(self, credential_id: str) -> str:
        if not _valid_credential_id(credential_id):
            raise CredentialError("The IMAP authorization is missing or invalid")
        try:
            secret = self._backend().get_password(self._service_name, credential_id)
        except Exception:
            raise CredentialError("The OS keyring is unavailable; background scans cannot safely load IMAP authorization") from None
        return _validate_secret(secret)

    def delete(self, credential_id: str) -> None:
        if not _valid_credential_id(credential_id):
            return
        try:
            self._backend().delete_password(self._service_name, credential_id)
        except Exception:
            # A failed cleanup must not disclose backend details or change the
            # scheduler state.  The selector remains harmless without a secret.
            raise CredentialError("The OS keyring could not remove IMAP authorization") from None


@dataclass(frozen=True)
class BackgroundSchedule:
    enabled: bool = False
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    limit: int = DEFAULT_LIMIT
    credential_id: str | None = None
    next_run_at: float | None = None
    last_started_at: float | None = None
    last_finished_at: float | None = None
    last_result: str | None = None
    last_error: str | None = None
    run_id: str | None = None
    lease_until: float | None = None
    # Fingerprint of the IMAP settings the user approved (see
    # IMAPConfig.target_fingerprint). None for schedules from before 2.0.
    target: str | None = None

    @classmethod
    def from_data(cls, data: Any) -> "BackgroundSchedule":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("Invalid background IMAP schedule")
        allowed = {"version", "enabled", "interval_seconds", "limit", "credential_id", "next_run_at",
                   "last_started_at", "last_finished_at", "last_result", "last_error",
                   "run_id", "lease_until", "target"}
        if set(data) - allowed or data.get("version", SCHEDULE_VERSION) != SCHEDULE_VERSION:
            raise ValueError("Invalid background IMAP schedule")
        enabled = data.get("enabled", False)
        interval = data.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)
        limit = data.get("limit", DEFAULT_LIMIT)
        credential_id = data.get("credential_id")
        timestamps = {name: data.get(name) for name in ("next_run_at", "last_started_at", "last_finished_at", "lease_until")}
        if type(enabled) is not bool or type(interval) is not int or not MIN_INTERVAL_SECONDS <= interval <= MAX_INTERVAL_SECONDS:
            raise ValueError("Invalid background IMAP schedule")
        if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
            raise ValueError("Invalid background IMAP schedule")
        if credential_id is not None and not _valid_credential_id(credential_id):
            raise ValueError("Invalid background IMAP schedule")
        run_id = data.get("run_id")
        if run_id is not None and not _valid_credential_id(run_id):
            raise ValueError("Invalid background IMAP schedule")
        if (run_id is None) != (data.get("lease_until") is None):
            raise ValueError("Invalid background IMAP schedule")
        if enabled and credential_id is None:
            raise ValueError("Background IMAP scans require OS-keyring authorization")
        target = data.get("target")
        if target is not None and (not isinstance(target, str) or not re.fullmatch(r"[0-9a-f]{64}", target)):
            raise ValueError("Invalid background IMAP schedule")
        if any(value is not None and (type(value) not in {int, float} or value < 0) for value in timestamps.values()):
            raise ValueError("Invalid background IMAP schedule")
        for name in ("last_result", "last_error"):
            value = data.get(name)
            if value is not None and (not isinstance(value, str) or len(value) > 200):
                raise ValueError("Invalid background IMAP schedule")
        return cls(enabled, interval, limit, credential_id,
                   next_run_at=data.get("next_run_at"), last_started_at=data.get("last_started_at"),
                   last_finished_at=data.get("last_finished_at"), last_result=data.get("last_result"),
                   last_error=data.get("last_error"), run_id=run_id, lease_until=data.get("lease_until"),
                   target=target)

    def public_data(self) -> dict[str, Any]:
        """Stable metadata safe to persist locally; it contains no secret."""
        return {"version": SCHEDULE_VERSION, "enabled": self.enabled, "interval_seconds": self.interval_seconds,
                "limit": self.limit, "credential_id": self.credential_id, "next_run_at": self.next_run_at,
                "last_started_at": self.last_started_at, "last_finished_at": self.last_finished_at,
                "last_result": self.last_result, "last_error": self.last_error,
                "run_id": self.run_id, "lease_until": self.lease_until, "target": self.target}


def _default_runner(store: MetaStore, config: IMAPConfig, secret: str, *, limit: int,
                    keep_alive: Callable[[], None]) -> dict[str, Any]:
    """The only network path, reached after explicit schedule + runtime consent."""
    messages = imap_messages(store, config, secret, allow_network=True, full_scan=False, limit=limit)
    return scan_messages(store, with_keep_alive(messages, keep_alive), "imap")


class BackgroundScanService:
    """Runs at most one *due* incremental scan when the host app calls it.

    The service itself does not spawn a thread, discover hosts or retain
    credentials; the dashboard owns the scheduling loop.
    It reads the normal credential-free ``imap.json`` immediately before a run,
    so host changes are always made through the existing explicit IMAP setup.
    """

    def __init__(self, store: MetaStore, credentials: KeyringCredentialStore, *,
                 config_path: Path | None = None, config_loader: Callable[[], IMAPConfig] | None = None,
                 scan_runner: Callable[..., dict[str, Any]] = _default_runner,
                 clock: Callable[[], float] = time.time):
        if config_path is not None and config_loader is not None:
            raise ValueError("Choose an IMAP configuration path or loader")
        self.store = store
        self.credentials = credentials
        self.config_path = Path(config_path) if config_path is not None else None
        self.config_loader = config_loader or self._load_store_config
        self.scan_runner = scan_runner
        self.clock = clock

    def _load_store_config(self) -> IMAPConfig:
        if self.config_path is not None:
            return load_config(self.config_path)
        data_dir = getattr(self.store, "data_dir", None)
        if data_dir is None:
            raise ValueError("IMAP configuration is unavailable")
        return load_config(data_dir / "imap.json")

    def schedule(self) -> BackgroundSchedule:
        return BackgroundSchedule.from_data(self.store.meta(SCHEDULE_META_KEY))

    def _save(self, schedule: BackgroundSchedule) -> BackgroundSchedule:
        self.store.set_meta(SCHEDULE_META_KEY, schedule.public_data())
        return schedule

    def _atomic_update(self, change):
        """Apply a schedule transition under SQLite's cross-process write lock.

        ``change`` receives the validated schedule and returns ``(updated or
        None, result)``; mailbox work is claimed before any keyring or network use.
        """
        def apply(value):
            updated, result = change(BackgroundSchedule.from_data(value))
            return (UNCHANGED if updated is None else updated.public_data()), result
        return atomic_meta_update(self.store, SCHEDULE_META_KEY, apply)

    def configure(self, *, credential_id: str, target: str | None = None,
                  interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
                  limit: int = DEFAULT_LIMIT, enabled: bool = True) -> BackgroundSchedule:
        """Persist an explicit opt-in for exactly one IMAP target.

        Call ``credentials.save`` first; ``target`` is the approved
        ``IMAPConfig.target_fingerprint()``.
        """
        if enabled and target is None:
            raise ValueError("Background IMAP scans require an approved IMAP target")
        now = self.clock()
        schedule = BackgroundSchedule(enabled=enabled, interval_seconds=interval_seconds, limit=limit,
                                      credential_id=credential_id, next_run_at=now if enabled else None,
                                      target=target)
        # Reuse strict validation rather than silently accepting unsafe values.
        schedule = BackgroundSchedule.from_data(schedule.public_data())
        return self._save(schedule)

    def disable(self) -> BackgroundSchedule:
        def disable(schedule):
            stopped = replace(schedule, enabled=False, next_run_at=None, run_id=None, lease_until=None)
            return stopped, stopped
        return self._atomic_update(disable)

    def revoke(self) -> BackgroundSchedule:
        """Disable scheduling and remove the stored OS-keyring authorization.

        The schedule is disabled before keyring cleanup, so an unavailable
        keyring can never leave automatic scans active.  If cleanup fails the
        caller receives a fixed error and can retry; the saved selector remains
        visible only through the safe ``authorized`` boolean in ``snapshot``.
        """
        current = self.disable()
        if current.credential_id:
            self.credentials.delete(current.credential_id)
        revoked = replace(current, enabled=False, credential_id=None, next_run_at=None,
                          run_id=None, lease_until=None, target=None)
        return self._save(revoked)

    def snapshot(self) -> dict[str, Any]:
        """Return schedule state suitable for the local dashboard/API.

        The opaque credential selector is not needed by the UI and is omitted
        to make accidental exposure through future server responses less likely.
        """
        schedule = self.schedule()
        return {"enabled": schedule.enabled, "authorized": schedule.credential_id is not None,
                "target_confirmed": self._target_confirmed(schedule),
                "interval_seconds": schedule.interval_seconds, "limit": schedule.limit,
                "next_run_at": schedule.next_run_at, "last_started_at": schedule.last_started_at,
                "last_finished_at": schedule.last_finished_at, "last_result": schedule.last_result,
                "last_error": schedule.last_error, "running": schedule.run_id is not None and
                schedule.lease_until is not None and schedule.lease_until > self.clock()}

    def _target_confirmed(self, schedule: BackgroundSchedule) -> bool:
        """Whether the current IMAP settings are the ones the user approved."""
        if schedule.target is None:
            return False
        try:
            config = self.config_loader()
            return isinstance(config, IMAPConfig) and config.target_fingerprint() == schedule.target
        except Exception:
            return False

    def _require_reauthorization(self, run_id) -> bool:
        """Stop scheduling until the user approves the current target again.

        The keyring entry stays (``revoke`` removes it); no secret was loaded.
        """
        moment = self.clock()

        def stop(schedule):
            if schedule.run_id != run_id:
                return None, False
            stopped = replace(schedule, enabled=False, next_run_at=None, run_id=None, lease_until=None,
                              last_finished_at=moment, last_result="reauthorization_required",
                              last_error=TARGET_CHANGED_ERROR)
            return stopped, True

        return self._atomic_update(stop)

    def _fail(self, run_id) -> dict[str, Any]:
        # Do not retain implementation/server/keyring exception text.  A
        # failure backs off for the selected interval instead of retrying.
        # A lost lease (ScanCancelled) ends as "cancelled" because the
        # schedule no longer carries this run ID.
        error = "Background IMAP scan could not complete; check local setup and authorization"
        committed = self._finish_claim(run_id, outcome="failed", error=error)
        return {"status": "failed" if committed else "cancelled", "error": error}

    def _claim_due(self):
        moment = self.clock()

        def claim(schedule):
            if not schedule.enabled:
                return None, {"status": "disabled"}
            if schedule.run_id is not None and schedule.lease_until is not None and schedule.lease_until > moment:
                return None, {"status": "running"}
            if schedule.next_run_at is not None and moment < schedule.next_run_at:
                return None, {"status": "not_due", "next_run_at": schedule.next_run_at}
            run_id = str(uuid4())
            started = replace(schedule, run_id=run_id, lease_until=moment + RUN_LEASE_SECONDS,
                              last_started_at=moment, last_error=None)
            return started, {"status": "claimed", "run_id": run_id, "schedule": started}

        return self._atomic_update(claim)

    def _finish_claim(self, run_id, *, outcome, error=None):
        moment = self.clock()

        def finish(schedule):
            # A later disable/revoke or replacement lease wins over an old
            # worker. It must never reactivate scheduling on completion.
            if schedule.run_id != run_id or not schedule.enabled:
                return None, False
            completed = replace(schedule, run_id=None, lease_until=None,
                                next_run_at=moment + schedule.interval_seconds,
                                last_finished_at=moment, last_result=outcome,
                                last_error=error)
            return completed, True

        return self._atomic_update(finish)

    def _release_claim(self, run_id) -> None:
        """Give a claimed run back unchanged when the mailbox is busy elsewhere."""
        def release(schedule):
            if schedule.run_id != run_id:
                return None, None
            return replace(schedule, run_id=None, lease_until=None), None

        self._atomic_update(release)

    def _renew_claim(self, run_id) -> bool:
        moment = self.clock()

        def renew(schedule):
            if schedule.run_id != run_id or not schedule.enabled:
                return None, False
            return replace(schedule, lease_until=moment + RUN_LEASE_SECONDS), True

        return self._atomic_update(renew)

    def _keep_alive(self, run_id, mailbox: MailboxLease) -> Callable[[], None]:
        """Return the runner's heartbeat: renew both leases or stop the run.

        Without renewal a long scan (up to ``MAX_LIMIT`` messages) outlives
        ``RUN_LEASE_SECONDS``; a disable, revoke or replacement stops it.
        """
        renewed = [self.clock()]

        def keep_alive():
            moment = self.clock()
            if moment - renewed[0] >= LEASE_RENEW_SECONDS:
                if not self._renew_claim(run_id):
                    raise ScanCancelled()
                renewed[0] = moment
            mailbox.keep_alive()

        return keep_alive

    def run_due(self, *, allow_network: bool = False) -> dict[str, Any]:
        """Run a due scan only after the caller grants runtime network access.

        Return values deliberately contain status/counts, never IMAP server
        messages, credentials, configured host names or raw email content.
        """
        if not allow_network:
            return {"status": "authorization_required"}
        claimed = self._claim_due()
        if claimed["status"] != "claimed":
            return claimed
        schedule = claimed["schedule"]
        run_id = claimed["run_id"]
        # The approved target is checked before any keyring or network use:
        # a changed host, account or folder selection is a new approval.
        try:
            config = self.config_loader()
            if not isinstance(config, IMAPConfig):
                raise ValueError("Invalid IMAP configuration")
            approved = schedule.target is not None and config.target_fingerprint() == schedule.target
        except Exception:
            return self._fail(run_id)
        if not approved:
            committed = self._require_reauthorization(run_id)
            return {"status": "reauthorization_required" if committed else "cancelled",
                    "error": TARGET_CHANGED_ERROR}
        # A manual scan-imap of the same profile may hold the mailbox. Give the
        # claim back unchanged; the dashboard's next pass retries.
        mailbox = MailboxLease(self.store, kind="scheduled", clock=self.clock)
        try:
            mailbox.acquire()
        except MailboxBusy:
            self._release_claim(run_id)
            return {"status": "busy"}
        try:
            secret = self.credentials.load(schedule.credential_id or "")
            result = self.scan_runner(self.store, config, secret, limit=schedule.limit,
                                      keep_alive=self._keep_alive(run_id, mailbox))
            if not isinstance(result, dict):
                raise ValueError("Invalid scan result")
            outcome = result.get("result", "completed")
            if not isinstance(outcome, str) or len(outcome) > 80:
                outcome = "completed_with_gaps"
            committed = self._finish_claim(run_id, outcome=outcome)
            safe = {key: result[key] for key in ("processed", "evidence", "duplicates", "updated_evidence",
                                                  "removed_evidence", "ignored", "skipped", "errors", "headers_only")
                    if type(result.get(key)) is int and result[key] >= 0}
            return {"status": "completed" if committed else "cancelled", "result": outcome, **safe}
        except Exception:
            return self._fail(run_id)
        finally:
            mailbox.release()
