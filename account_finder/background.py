"""Opt-in local scheduling for incremental, read-only IMAP scans.

This module deliberately has no daemon or import-time side effects.  A caller
must explicitly enable a schedule, provide OS-keyring-backed authorization and
call :meth:`BackgroundScanService.run_due` with network permission.  It is a
foundation for a future dashboard/CLI integration; no scan is started merely
because this module is installed.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import UUID, uuid4

from .imap_client import IMAPConfig, imap_messages, load_config
from .scan import scan_messages


SCHEDULE_META_KEY = "background_imap_schedule"
SCHEDULE_VERSION = 1
MIN_INTERVAL_SECONDS = 15 * 60
MAX_INTERVAL_SECONDS = 7 * 24 * 60 * 60
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60
DEFAULT_LIMIT = 500
MAX_LIMIT = 10_000


class MetaStore(Protocol):
    """The small persistence interface needed by the scheduler."""

    def meta(self, key: str, default: Any = None) -> Any: ...

    def set_meta(self, key: str, value: Any) -> None: ...


class CredentialError(Exception):
    """A fixed, non-sensitive credential-storage error."""


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

    @classmethod
    def from_data(cls, data: Any) -> "BackgroundSchedule":
        if data is None:
            return cls()
        if not isinstance(data, dict):
            raise ValueError("Invalid background IMAP schedule")
        allowed = {"version", "enabled", "interval_seconds", "limit", "credential_id", "next_run_at",
                   "last_started_at", "last_finished_at", "last_result", "last_error"}
        if set(data) - allowed or data.get("version", SCHEDULE_VERSION) != SCHEDULE_VERSION:
            raise ValueError("Invalid background IMAP schedule")
        enabled = data.get("enabled", False)
        interval = data.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)
        limit = data.get("limit", DEFAULT_LIMIT)
        credential_id = data.get("credential_id")
        timestamps = {name: data.get(name) for name in ("next_run_at", "last_started_at", "last_finished_at")}
        if type(enabled) is not bool or type(interval) is not int or not MIN_INTERVAL_SECONDS <= interval <= MAX_INTERVAL_SECONDS:
            raise ValueError("Invalid background IMAP schedule")
        if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
            raise ValueError("Invalid background IMAP schedule")
        if credential_id is not None and not _valid_credential_id(credential_id):
            raise ValueError("Invalid background IMAP schedule")
        if enabled and credential_id is None:
            raise ValueError("Background IMAP scans require OS-keyring authorization")
        if any(value is not None and (type(value) not in {int, float} or value < 0) for value in timestamps.values()):
            raise ValueError("Invalid background IMAP schedule")
        for name in ("last_result", "last_error"):
            value = data.get(name)
            if value is not None and (not isinstance(value, str) or len(value) > 200):
                raise ValueError("Invalid background IMAP schedule")
        return cls(enabled, interval, limit, credential_id, **timestamps,
                   last_result=data.get("last_result"), last_error=data.get("last_error"))

    def public_data(self) -> dict[str, Any]:
        """Stable metadata safe to persist locally; it contains no secret."""
        return {"version": SCHEDULE_VERSION, "enabled": self.enabled, "interval_seconds": self.interval_seconds,
                "limit": self.limit, "credential_id": self.credential_id, "next_run_at": self.next_run_at,
                "last_started_at": self.last_started_at, "last_finished_at": self.last_finished_at,
                "last_result": self.last_result, "last_error": self.last_error}


def _default_runner(store: MetaStore, config: IMAPConfig, secret: str, *, limit: int) -> dict[str, Any]:
    """The only network path, reached after explicit schedule + runtime consent."""
    messages = imap_messages(store, config, secret, allow_network=True, full_scan=False, limit=limit)
    return scan_messages(store, messages, "imap")


class BackgroundScanService:
    """Runs at most one *due* incremental scan when the host app calls it.

    The service does not spawn a thread, discover hosts or retain credentials.
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

    def configure(self, *, credential_id: str, interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
                  limit: int = DEFAULT_LIMIT, enabled: bool = True) -> BackgroundSchedule:
        """Persist an explicit opt-in.  Call ``credentials.save`` first."""
        now = self.clock()
        schedule = BackgroundSchedule(enabled=enabled, interval_seconds=interval_seconds, limit=limit,
                                      credential_id=credential_id,
                                      next_run_at=now if enabled else None)
        # Reuse strict validation rather than silently accepting unsafe values.
        schedule = BackgroundSchedule.from_data(schedule.public_data())
        return self._save(schedule)

    # These names are deliberately compact for a local server controller.
    # ``start`` does not connect; it merely saves an explicit opt-in schedule.
    def start(self, *, credential_id: str, interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
              limit: int = DEFAULT_LIMIT) -> BackgroundSchedule:
        return self.configure(credential_id=credential_id, interval_seconds=interval_seconds,
                              limit=limit, enabled=True)

    def disable(self) -> BackgroundSchedule:
        current = self.schedule()
        return self._save(BackgroundSchedule(False, current.interval_seconds, current.limit,
                                             current.credential_id, None, current.last_started_at,
                                             current.last_finished_at, current.last_result, current.last_error))

    def stop(self) -> BackgroundSchedule:
        return self.disable()

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
        revoked = BackgroundSchedule(False, current.interval_seconds, current.limit,
                                     None, None, current.last_started_at,
                                     current.last_finished_at, current.last_result,
                                     current.last_error)
        return self._save(revoked)

    def snapshot(self) -> dict[str, Any]:
        """Return schedule state suitable for the local dashboard/API.

        The opaque credential selector is not needed by the UI and is omitted
        to make accidental exposure through future server responses less likely.
        """
        schedule = self.schedule()
        return {"enabled": schedule.enabled, "authorized": schedule.credential_id is not None,
                "interval_seconds": schedule.interval_seconds, "limit": schedule.limit,
                "next_run_at": schedule.next_run_at, "last_started_at": schedule.last_started_at,
                "last_finished_at": schedule.last_finished_at, "last_result": schedule.last_result,
                "last_error": schedule.last_error}

    def run_due(self, *, allow_network: bool = False) -> dict[str, Any]:
        """Run a due scan only after the caller grants runtime network access.

        Return values deliberately contain status/counts, never IMAP server
        messages, credentials, configured host names or raw email content.
        """
        schedule = self.schedule()
        now = self.clock()
        if not schedule.enabled:
            return {"status": "disabled"}
        if not allow_network:
            return {"status": "authorization_required"}
        if schedule.next_run_at is not None and now < schedule.next_run_at:
            return {"status": "not_due", "next_run_at": schedule.next_run_at}

        started = BackgroundSchedule(True, schedule.interval_seconds, schedule.limit, schedule.credential_id,
                                     schedule.next_run_at, now, schedule.last_finished_at,
                                     schedule.last_result, None)
        self._save(started)
        try:
            secret = self.credentials.load(schedule.credential_id or "")
            config = self.config_loader()
            if not isinstance(config, IMAPConfig):
                raise ValueError("Invalid IMAP configuration")
            result = self.scan_runner(self.store, config, secret, limit=schedule.limit)
            if not isinstance(result, dict):
                raise ValueError("Invalid scan result")
            outcome = result.get("result", "completed")
            if not isinstance(outcome, str) or len(outcome) > 80:
                outcome = "completed_with_gaps"
            finished = BackgroundSchedule(True, schedule.interval_seconds, schedule.limit, schedule.credential_id,
                                          now + schedule.interval_seconds, now, now, outcome, None)
            self._save(finished)
            safe = {key: result[key] for key in ("processed", "evidence", "duplicates", "updated_evidence",
                                                  "removed_evidence", "ignored", "skipped", "errors", "headers_only")
                    if type(result.get(key)) is int and result[key] >= 0}
            return {"status": "completed", "result": outcome, **safe}
        except Exception:
            # Do not retain implementation/server/keyring exception text.  A
            # failure backs off for the selected interval instead of retrying.
            failed = BackgroundSchedule(True, schedule.interval_seconds, schedule.limit, schedule.credential_id,
                                        now + schedule.interval_seconds, now, now, "failed",
                                        "Background IMAP scan could not complete; check local setup and authorization")
            self._save(failed)
            return {"status": "failed", "error": failed.last_error}
        finally:
            # Best effort only: Python cannot zero immutable string storage.
            secret = "" if "secret" in locals() else ""
