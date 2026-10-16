"""Streaming local file imports and synthetic examples."""
from email.message import EmailMessage
from hashlib import sha256
import mailbox
from pathlib import Path
import time
import uuid

from .analysis import ANALYSIS_VERSION, HEADERS_ONLY_MARKER, analyze, MAX_MESSAGE_BYTES
from .store import Store, now


class ScanSession:
    """One durable scan, including multi-file imports; no message contents retained."""

    def __init__(self, store: Store, source="eml", expected=None, progress=None, info=None, emails=None):
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
                      "analysis_version": ANALYSIS_VERSION}
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
        if self.progress:
            self.progress(dict(self.stats))
        return dict(self.stats)

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

    def process(self, raw):
        self._ensure_capacity()
        self.stats["processed"] += 1
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_MESSAGE_BYTES:
            self.stats["skipped"] += 1
        else:
            if raw.startswith(HEADERS_ONLY_MARKER + b": yes"):
                self.stats["headers_only"] += 1
            try:
                evidence = analyze(raw, self.store.registry, self.emails, self.stats["source"])
                outcome = self.store.record_analysis(sha256(raw).hexdigest(), evidence, expected_emails=self.emails)
                if outcome == "scope_changed":
                    self.info["scope_changed"] = True
                key = {"new": "evidence", "updated": "updated_evidence", "removed": "removed_evidence",
                       "duplicate": "duplicates", "ignored": "ignored", "scope_changed": "ignored"}[outcome]
                self.stats[key] += 1
            except (ValueError, TypeError, UnicodeError, RecursionError):
                self.stats["errors"] += 1
        if self.stats["processed"] == 1 or self.stats["processed"] % 50 == 0:
            self.publish()
        return dict(self.stats)

    def finish(self, result=None):
        if not self.stats["running"]:
            return dict(self.stats)
        if result not in {None, "partial"}:
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
        return self.publish()


def scan_messages(store: Store, messages, source="eml", progress=None, *, session=None):
    session = session or ScanSession(store, source, progress=progress, info=getattr(messages, "scan_info", None),
                                    emails=getattr(messages, "scan_emails", None))
    iterator = None
    try:
        iterator = iter(messages)
        for raw in iterator:
            session.process(raw)
            if session.info.get("scope_changed"):
                break
    except BaseException:
        session.finish("partial")
        raise
    finally:
        close = getattr(iterator, "close", None)
        if close:
            close()
    return session.finish()


def file_messages(path: Path, kind: str):
    if kind == "mbox":
        if not path.is_file():
            raise ValueError("mbox file not found")
        # mailbox.mbox opens the file itself (read/write when permitted, otherwise
        # read-only). ARGUS only reads: it never adds, removes, locks or flushes
        # changes, so the original stays unchanged. create=False never creates it.
        box = mailbox.mbox(path, create=False)
        try:
            for key in box.iterkeys():
                with box.get_file(key, from_=False) as message_file:
                    raw = message_file.read(MAX_MESSAGE_BYTES + 1)
                yield raw if len(raw) <= MAX_MESSAGE_BYTES else None
        finally:
            box.close()
    elif kind == "maildir":
        if not path.is_dir() or not (path / "cur").is_dir() or not (path / "new").is_dir():
            raise ValueError("Maildir requires cur/ and new/")
        for folder in (path / "cur", path / "new"):
            for file in sorted(folder.iterdir()):
                if file.is_file() and not file.is_symlink():
                    with file.open("rb") as handle:
                        yield handle.read(MAX_MESSAGE_BYTES + 1)
    elif kind == "eml":
        if not path.exists():
            raise ValueError("EML path not found")
        files = [path] if path.is_file() else sorted(path.rglob("*.eml"))
        for file in files:
            if file.is_symlink():
                continue
            with file.open("rb") as handle:
                yield handle.read(MAX_MESSAGE_BYTES + 1)
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


def load_demo(store: Store):
    if not store.meta("demo", False) and store.meta("emails"):
        raise ValueError("The demo requires a separate data directory")
    store.configure(["demo@example.invalid"], demo=True)
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
    ]
    stats = scan_messages(store, (synthetic_mail(*row) for row in rows), "demo")
    store.update_account("github", {"checklist": {key: True for key in ("reviewed", "saved_in_bitwarden", "password_changed", "login_tested", "mfa_checked")}, "status": "done"})
    store.update_account("paypal", {"checklist": {"reviewed": True}})
    return stats
