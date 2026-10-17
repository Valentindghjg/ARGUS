# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Streaming local file imports and synthetic examples."""
from email.message import EmailMessage
from hashlib import sha256
import mailbox
from pathlib import Path
import time
import uuid

from .analysis import ANALYSIS_VERSION, HEADERS_ONLY_MARKER, analyze, MAX_MESSAGE_BYTES
from .guidance import scan_next_steps
from . import imports, jobs
from .errors import UserFacingError
from .store import Store, now

# Plan A24/A27: a running job looks at the global pause between two messages,
# at most once per this many seconds, so a pause takes effect within about a second.
PAUSE_CHECK_SECONDS = 1.0
# How a finished scan maps to the shared job states (ADR-0001, section 3.4).
JOB_STATES = {"completed": "completed", "completed_with_gaps": "completed_with_gaps", "limited": "completed_with_gaps"}


class ScanSession:
    """One durable scan, including multi-file imports; no message contents retained."""

    def __init__(self, store: Store, source="eml", expected=None, progress=None, info=None, emails=None,
                 trigger="manual", budget=None, recheck=False):
        self.store = store
        self.emails = list(emails) if emails is not None else store.meta("emails", [])
        if not self.emails:
            raise ValueError("Configure your own email addresses with init first")
        if expected is not None and (type(expected) is not int or not 0 <= expected <= 100_000):
            raise ValueError("Invalid message count")
        self.info = info if info is not None else {}
        self.progress = progress
        self.last_activity = time.monotonic()
        self.stats = {"id": str(uuid.uuid4()), "source": source, "processed": 0, "evidence": 0,
                      "duplicates": 0, "updated_evidence": 0, "removed_evidence": 0,
                      "ignored": 0, "skipped": 0, "errors": 0, "headers_only": 0,
                      "expected": expected, "running": True, "started": now(),
                      "analysis_version": ANALYSIS_VERSION, "rule_changes": [], "rule_changes_count": 0,
                      "unchanged": 0}
        # Plan A13/A14: skip what was analyzed under the same conditions; limit new work per run.
        self.scope = imports.scope_key(self.emails, store.registry, ANALYSIS_VERSION)
        if recheck and budget:
            # A recheck starts at the first message every time, so a limit would never move on.
            raise UserFacingError("Recheck everything without a message or size limit")
        self.recheck = recheck
        self.budget = budget
        self.pause_checked = None
        # Plan A16: keys of local items that were skipped or failed, for a targeted retry.
        self.failed_items = []
        self.new_work = {"messages": 0, "bytes": 0}
        self.kind = {"scheduled": "scheduled_scan", "watch": "folder_watch"}.get(
            trigger, "imap_scan" if source == "imap" else "import")
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            jobs.require_running(db)
            jobs.start(db, self.stats["id"], self.kind, source)
            imports.forget_other_scopes(db, self.scope)
        self.publish()

    def publish(self):
        for key in ("folders_total", "folders_processed", "available_messages"):
            value = self.info.get(key)
            if type(value) is int and value >= 0:
                self.stats[key] = value
        if self.info.get("scope_changed"):
            self.stats["scope_changed"] = True
        self.stats["updated_at"] = now()
        self.last_activity = time.monotonic()
        self.store.set_meta("last_scan", self.stats)
        with self.store.connect() as db:
            jobs.update(db, self.stats["id"], self.stats)
        if self.progress:
            self.progress(dict(self.stats))
        # Derived, never stored: the advice follows the current rules.
        return {**self.stats, "next_steps": scan_next_steps(self.stats)}

    def _ensure_capacity(self, count=1):
        if not self.stats["running"] or (self.stats["expected"] is not None and
                self.stats["processed"] + count > self.stats["expected"]):
            raise ValueError("The scan has ended or the declared file count was exceeded")

    def skip(self, count=1):
        if type(count) is not int or not 1 <= count <= 100_000:
            raise ValueError("Invalid skipped-file count")
        self._ensure_capacity(count)
        self.stats["processed"] += count
        self.stats["skipped"] += count
        return self.publish()

    def _check_pause(self):
        moment = time.monotonic()
        if self.pause_checked is None or moment - self.pause_checked >= PAUSE_CHECK_SECONDS:
            self.pause_checked = moment
            with self.store.connect() as db:
                if jobs.paused(db):
                    raise jobs.JobPaused("Automation was paused; the job stopped between two messages. Saved clues stay.")

    def _budget_spent(self):
        return bool(self.budget) and (
            (self.budget["messages"] and self.new_work["messages"] >= self.budget["messages"])
            or (self.budget["bytes"] and self.new_work["bytes"] >= self.budget["bytes"]))

    def process(self, raw, key=None):
        self._ensure_capacity()
        self._check_pause()
        fingerprint = sha256(raw).hexdigest() if isinstance(raw, bytes) and raw and len(raw) <= MAX_MESSAGE_BYTES else None
        known = False
        if fingerprint and not self.recheck:
            with self.store.connect() as db:
                known = imports.known(db, fingerprint, self.scope)
        if fingerprint and not known and self._budget_spent():
            # A13/A14: more new work waits than this run may do. It stops before this
            # message and ends as "limited"; a source that fits the limit completes.
            self.info["limit_reached"] = True
            return dict(self.stats)
        self.stats["processed"] += 1
        if known:
            self.stats["unchanged"] += 1
            return self._progress()
        if fingerprint is None:
            # Empty or oversized items cost nothing and do not use up the limit.
            self.stats["skipped"] += 1
            self._failed(key)
        else:
            if raw.startswith(HEADERS_ONLY_MARKER + b": yes"):
                self.stats["headers_only"] += 1
            try:
                try:
                    evidence = analyze(raw, self.store.registry, self.emails, self.stats["source"])
                except Exception as exc:
                    # Hostile headers can break the standard parser in unexpected ways;
                    # one such message must never stop a whole import or a scheduled scan.
                    raise ValueError("The message could not be analyzed") from exc
                self.new_work["messages"] += 1
                self.new_work["bytes"] += len(raw)
                changes = []
                outcome = self.store.record_analysis(fingerprint, evidence, expected_emails=self.emails,
                                                     changes=changes)
                # Plan E6: show what current rules changed; your decisions stay as they were.
                if changes:
                    self.stats["rule_changes_count"] += len(changes)
                    self.stats["rule_changes"] = (self.stats["rule_changes"] + changes)[:20]
                if outcome == "scope_changed":
                    self.info["scope_changed"] = True
                key = {"new": "evidence", "updated": "updated_evidence", "removed": "removed_evidence",
                       "duplicate": "duplicates", "ignored": "ignored", "scope_changed": "ignored"}[outcome]
                self.stats[key] += 1
                if outcome != "scope_changed":
                    with self.store.connect() as db:
                        imports.remember(db, fingerprint, self.scope)
            except (ValueError, TypeError, UnicodeError, RecursionError):
                self.stats["errors"] += 1
                self._failed(key)
        return self._progress()

    def _failed(self, key):
        if key is not None and len(self.failed_items) < imports.MAX_FAILED_ITEMS:
            self.failed_items.append(key)

    def _progress(self):
        if self.stats["processed"] == 1 or self.stats["processed"] % 50 == 0:
            self.publish()
        return dict(self.stats)

    def finish(self, result=None, job_state=None):
        """End the scan. ``job_state`` names why a partial scan stopped (paused, failed, cancelled)."""
        if not self.stats["running"]:
            return dict(self.stats)
        if result not in {None, "partial"} or job_state not in {None, "paused", "failed", "cancelled"}:
            raise ValueError("Invalid completion status")
        if result is None:
            if self.info.get("scope_changed"):
                result = "partial"
            elif self.info.get("limit_reached"):
                result = "limited"
            elif self.stats["expected"] is not None and self.stats["processed"] < self.stats["expected"]:
                result = "partial"
            elif self.stats["errors"] or self.stats["skipped"] or self.stats["headers_only"]:
                result = "completed_with_gaps"
            else:
                result = "completed"
        self.stats.update(result=result, running=False, finished=now())
        published = self.publish()
        with self.store.connect() as db:
            jobs.finish(db, self.stats["id"], JOB_STATES.get(result, job_state or "cancelled"), self.stats)
        return published


def scan_messages(store: Store, messages, source="eml", progress=None, *, session=None, trigger="manual",
                  budget=None, recheck=False, keyed=False):
    """Analyze messages; with ``keyed`` each item is a (key, raw) pair from ``file_items``."""
    session = session or ScanSession(store, source, progress=progress, info=getattr(messages, "scan_info", None),
                                    emails=getattr(messages, "scan_emails", None), trigger=trigger,
                                    budget=budget, recheck=recheck)
    iterator = None
    try:
        iterator = iter(messages)
        for item in iterator:
            if keyed:
                session.process(item[1], key=item[0])
            else:
                session.process(item)
            if session.info.get("scope_changed") or (session.budget and session.info.get("limit_reached")):
                break
    except jobs.JobPaused:
        session.finish("partial", "paused")
        raise
    except (KeyboardInterrupt, GeneratorExit, jobs.JobCancelled):
        session.finish("partial", "cancelled")
        raise
    except BaseException:
        session.finish("partial", "failed")
        raise
    finally:
        close = getattr(iterator, "close", None)
        if close:
            close()
    return session.finish()


def _read_item(file: Path):
    """One message file, or None if it cannot be read; it is then listed for --retry-failed."""
    try:
        with file.open("rb") as handle:
            return handle.read(MAX_MESSAGE_BYTES + 1)
    except OSError:
        return None


def file_messages(path: Path, kind: str):
    for _, raw in file_items(path, kind):
        yield raw


def file_items(path: Path, kind: str, only=None):
    """Messages of a local source with a stable key each (plan A16).

    The key is the file's path relative to the source, or the message number in
    an mbox. ``only`` restricts reading to these keys, for retrying failures.
    """
    only = set(only) if only is not None else None
    if kind == "mbox":
        if not path.is_file():
            raise ValueError("mbox file not found")
        # mailbox.mbox opens the file itself (read/write when permitted, otherwise
        # read-only). ARGUS only reads: it never adds, removes, locks or flushes
        # changes, so the original stays unchanged. create=False never creates it.
        box = mailbox.mbox(path, create=False)
        try:
            for number, key in enumerate(box.iterkeys()):
                item = f"#{number}"
                if only is not None and item not in only:
                    continue
                with box.get_file(key, from_=False) as message_file:
                    raw = message_file.read(MAX_MESSAGE_BYTES + 1)
                yield item, raw if len(raw) <= MAX_MESSAGE_BYTES else None
        finally:
            box.close()
    elif kind == "maildir":
        if not path.is_dir() or not (path / "cur").is_dir() or not (path / "new").is_dir():
            raise ValueError("Maildir requires cur/ and new/")
        for folder in (path / "cur", path / "new"):
            for file in sorted(folder.iterdir()):
                item = file.relative_to(path).as_posix()
                if file.is_file() and not file.is_symlink() and (only is None or item in only):
                    yield item, _read_item(file)
    elif kind == "eml":
        if not path.exists():
            raise ValueError("EML path not found")
        # Exported files are named .eml or .EML depending on the program.
        files = [path] if path.is_file() else sorted(file for file in path.rglob("*")
                                                     if file.suffix.lower() == ".eml" and file.is_file())
        for file in files:
            item = file.name if file == path else file.relative_to(path).as_posix()
            if file.is_symlink() or (only is not None and item not in only):
                continue
            yield item, _read_item(file)
    else:
        raise ValueError("Unknown import format")


def synthetic_mail(sender, subject, body, recipient="demo@example.invalid", newsletter=False, html=False):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message["Date"] = "Mon, 05 Oct 2026 10:00:00 +0000"
    if newsletter:
        message["List-Unsubscribe"] = "<https://example.invalid/unsubscribe>"
    if html:
        message.set_content("<p>" + body + "</p>", subtype="html")
    else:
        message.set_content(body)
    return message.as_bytes()


DEMO_EMAILS = ["demo@example.invalid", "demo.work@example.invalid"]


def load_demo(store: Store):
    """Load invented messages that also explain the hard cases (plan F6).

    Zalando (newsletter), Amazon (guest order) and eBay (password reset) stay
    clues without an account; GitHub has two accounts, one per own address;
    Notion uses single sign-on; a look-alike sender domain is not matched.
    """
    if not store.meta("demo", False) and store.meta("emails"):
        raise ValueError("The demo requires a separate data directory")
    store.configure(DEMO_EMAILS, demo=True)
    rows = [
        ("security@google.com", "New sign-in to your account", "A new device signed in to your account."),
        ("noreply@github.com", "Your account has been created", "Your account has been created. Welcome!"),
        ("service@paypal.com", "Your password has been changed", "Your password has been changed successfully."),
        ("noreply@steampowered.com", "Verify your email", "Please verify your email address to complete registration."),
        ("support@discord.com", "Your account has been created", "Your account has been created."),
        ("noreply@netflix.com", "New login to your account", "New login to your account from another device."),
        ("hello@spotify.com", "Welcome to Spotify", "Welcome! You can manage your new account in settings."),
        ("security@apple.com", "Your password has been changed", "Your password has been changed."),
        ("hello@notion.so", "Confirm your email", "Confirm your email address."),
        ("noreply@epicgames.com", "Your account has been created", "Your account has been created."),
        ("support@klarna.com", "Your registration is complete", "Your registration is complete."),
        ("notify@instagram.com", "New sign-in to your account", "New sign-in to your account."),
        ("hello@new-service.example", "Your account has been created", "Your account has been created."),
        ("newsletter@zalando.de", "Welcome to the newsletter", "Newsletter: special offers and discounts. Unsubscribe."),
        ("orders@amazon.de", "Order confirmation", "Your order has shipped. Guest checkout is possible."),
        ("security@github.com.attacker.example", "Your password has been changed", "Your password has been changed."),
        ("noreply@ebay.de", "Reset your password", "Here is your password reset link."),
        ("noreply@github.com", "Your account has been created", "Your account has been created. Welcome!",
         "demo.work@example.invalid"),
    ]
    stats = scan_messages(store, (synthetic_mail(*row) for row in rows), "demo")
    store.update_account("github", {"checklist": {key: True for key in ("reviewed", "saved_in_bitwarden", "password_changed", "login_tested", "mfa_checked")}, "status": "done"})
    store.update_account("paypal", {"checklist": {"reviewed": True}})
    store.update_account("notion", {"login_method": "sso"})
    return stats
