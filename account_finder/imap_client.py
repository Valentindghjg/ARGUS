"""TLS-only IMAP ingestion. All selected mailboxes are opened read-only."""
from dataclasses import dataclass, asdict
import base64
import imaplib
import json
from pathlib import Path
import re
import ssl
import time
from hashlib import sha256

from .analysis import ANALYSIS_VERSION, MAX_MESSAGE_BYTES
from .registry import normalize_domain
from .store import Store, write_private

MAX_HEADER_BYTES = 64 * 1024


class MailboxError(Exception):
    """Only fixed, non-sensitive user messages are used for this exception."""


@dataclass(frozen=True)
class IMAPConfig:
    host: str
    username: str
    port: int = 993
    auth: str = "app_password"
    folders: tuple[str, ...] = ("*",)

    def validate(self):
        if not isinstance(self.host, str):
            raise ValueError("Invalid IMAP host")
        normalize_domain(self.host)
        if not isinstance(self.username, str) or not 1 <= len(self.username) <= 254 or any(ord(c) < 32 for c in self.username):
            raise ValueError("Invalid IMAP username")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError("Invalid TLS port")
        if self.auth not in {"app_password", "oauth2"}:
            raise ValueError("Only app-password or OAuth2 authentication is supported")
        if not self.folders or len(self.folders) > 1000 or any(not isinstance(f, str) or not f or len(f) > 512 or any(ord(c) < 32 for c in f) for f in self.folders):
            raise ValueError("Invalid folder selection")
        if "*" in self.folders and self.folders != ("*",):
            raise ValueError("Choose all folders or explicit folder names")
        return self


def load_config(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) - {"host", "username", "port", "auth", "folders"}:
        raise ValueError("IMAP settings contain unknown fields; do not store credentials")
    try:
        if not isinstance(data.get("folders", ["*"]), list):
            raise ValueError("Folders must be specified as a list")
        config = IMAPConfig(data["host"], data["username"], data.get("port", 993),
                            data.get("auth", "app_password"), tuple(data.get("folders", ["*"])))
        return config.validate()
    except (KeyError, TypeError):
        raise ValueError("Incomplete IMAP configuration") from None


def save_config(path: Path, config: IMAPConfig):
    config.validate()
    write_private(path, json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n")


def encode_folder(name: str) -> bytes:
    """RFC3501 modified UTF-7 for international mailbox names."""
    result, pending = [], []
    def flush():
        if pending:
            encoded = base64.b64encode("".join(pending).encode("utf-16-be")).rstrip(b"=").replace(b"/", b",")
            result.append(b"&" + encoded + b"-")
            pending.clear()
    for char in name:
        if " " <= char <= "~":
            flush()
            result.append(b"&-" if char == "&" else char.encode("ascii"))
        else:
            pending.append(char)
    flush()
    return b"".join(result)


def decode_folder(raw: bytes) -> str:
    def replace(match):
        value = match.group(1)
        if not value:
            return "&"
        encoded = value.replace(b",", b"/")
        encoded += b"=" * (-len(encoded) % 4)
        return base64.b64decode(encoded, validate=True).decode("utf-16-be")
    result, start = [], 0
    for match in re.finditer(rb"&([^-]*)-", raw):
        result.append(raw[start:match.start()].decode("ascii"))
        result.append(replace(match))
        start = match.end()
    result.append(raw[start:].decode("ascii"))
    return "".join(result)


def _quoted(raw: bytes):
    if len(raw) > 2048 or any(c in raw for c in (b"\r", b"\n", b"\x00")):
        raise MailboxError("The IMAP server returned an invalid folder name")
    return b'"' + raw.replace(b"\\", b"\\\\").replace(b'"', b'\\"') + b'"'


def _folders(client):
    status, rows = client.list()
    if status != "OK":
        raise MailboxError("Could not read the IMAP folder list")
    result = []
    for row in rows or []:
        if not row:
            continue
        literal = None
        if isinstance(row, tuple):
            row, literal = row
        match = re.match(rb'^\(([^)]*)\)\s+(?:NIL|"(?:[^"\\]|\\.)*")\s+(.+)$', row)
        if not match or b"\\noselect" in match.group(1).lower():
            continue
        raw = literal if literal is not None else match.group(2)
        if literal is None and raw.startswith(b'"') and raw.endswith(b'"'):
            raw = re.sub(rb"\\(.)", rb"\1", raw[1:-1])
        _quoted(raw)
        result.append((decode_folder(raw), raw))
    return result


class BoundedIMAP4SSL(imaplib.IMAP4_SSL):
    def read(self, size):
        if size > MAX_MESSAGE_BYTES + MAX_HEADER_BYTES:
            raise imaplib.IMAP4.error("IMAP literal exceeds local limit")
        return super().read(size)


class IMAPStream:
    def __init__(self, iterator, scan_info, scan_emails):
        self.iterator = iterator
        self.scan_info = scan_info
        self.scan_emails = tuple(scan_emails)

    def __iter__(self):
        return self.iterator


def imap_messages(store: Store, config: IMAPConfig, secret: str, *, allow_network=False,
                  full_scan=False, limit=None, list_only=False, factory=None, delay=0.15):
    info = {}
    emails = store.meta("emails", [])
    return IMAPStream(_imap_messages(store, config, secret, allow_network=allow_network,
                     full_scan=full_scan, limit=limit, list_only=list_only, factory=factory,
                     delay=delay, info=info, emails=emails), info, emails)


def _imap_messages(store: Store, config: IMAPConfig, secret: str, *, allow_network,
                   full_scan, limit, list_only, factory, delay, info, emails):
    """Yield at most 2 MiB per mail; checkpoints commit AFTER evidence persistence."""
    if not allow_network:
        raise MailboxError("IMAP access is not authorized: --allow-imap is required")
    config.validate()
    if not secret or any(c in secret for c in ("\r", "\n", "\x00", "\x01")):
        raise MailboxError("App password / OAuth2 token is missing or invalid")
    if limit is not None and limit < 1:
        raise ValueError("The scan limit must be positive")
    factory = factory or BoundedIMAP4SSL
    client = None
    # Config identity includes credentials selectors, but never the secret.
    identity = sha256(json.dumps({"config": asdict(config), "emails": emails,
                                 "analysis_version": ANALYSIS_VERSION}, sort_keys=True).encode()).hexdigest()
    cursors = store.meta("imap_cursors", {})
    sent = 0
    try:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        client = factory(config.host, config.port, ssl_context=context, timeout=30)
        client.debug = 0
        if config.auth == "oauth2":
            auth = f"user={config.username}\x01auth=Bearer {secret}\x01\x01".encode("utf-8")
            status, _ = client.authenticate("XOAUTH2", lambda _: auth)
        else:
            status, _ = client.login(config.username, secret)
        if status != "OK":
            raise MailboxError("IMAP authentication failed; check app password / OAuth2 and provider settings")
        available = _folders(client)
        if list_only:
            for display, _ in available:
                yield display
            return
        chosen = available if config.folders == ("*",) else [(f, encode_folder(f)) for f in config.folders]
        if not chosen:
            raise MailboxError("No readable, selectable IMAP folders were found")
        info.update(folders_total=len(chosen), folders_processed=0, available_messages=0)
        for display, raw_name in chosen:
            status, _ = client.select(_quoted(raw_name), readonly=True)
            if status != "OK":
                raise MailboxError("A selected IMAP folder could not be opened read-only")
            _, validity_data = client.response("UIDVALIDITY")
            value = validity_data[0] if validity_data else None
            validity = value.decode("ascii") if value and value.isdigit() else None
            cursor_key = identity + ":" + sha256(raw_name).hexdigest()
            previous = cursors.get(cursor_key, {})
            start = 1 if full_scan or not validity or previous.get("validity") != validity else int(previous.get("uid", 0)) + 1
            status, data = client.uid("SEARCH", None, "UID", f"{start}:*")
            if status != "OK":
                raise MailboxError("Could not read the IMAP message list")
            uids = sorted({int(x) for item in data or [] if isinstance(item, bytes) for x in item.split() if x.isdigit() and int(x) >= start})
            info["available_messages"] += len(uids)
            for uid in uids:
                if limit is not None and sent >= limit:
                    info["limit_reached"] = True
                    return
                status, size_data = client.uid("FETCH", str(uid), "(RFC822.SIZE)")
                if status != "OK":
                    raise MailboxError("Could not read IMAP message sizes; scanning can resume")
                size = None
                for row in size_data or []:
                    header = row[0] if isinstance(row, tuple) else row
                    if isinstance(header, bytes):
                        match = re.search(rb"RFC822\.SIZE\s+(\d+)", header, re.I)
                        if match:
                            size = int(match.group(1))
                # Missing size also uses a bounded PEEK; never request an unbounded literal.
                header_only = size is not None and size > MAX_MESSAGE_BYTES
                section = "HEADER" if header_only else ""
                maximum = MAX_HEADER_BYTES if header_only else MAX_MESSAGE_BYTES
                status, parts = client.uid("FETCH", str(uid), f"(BODY.PEEK[{section}]<0.{maximum}>)")
                if status != "OK":
                    raise MailboxError("Could not read an IMAP message; scanning can resume")
                raw = next((part[1] for part in parts or [] if isinstance(part, tuple) and isinstance(part[1], bytes)), None)
                if raw and len(raw) <= maximum:
                    if header_only:
                        # Retain headers with an explicit local processing marker, not a fetched URL.
                        raw = b"X-Account-Finder-Headers-Only: yes\r\n" + raw
                    yield raw
                else:
                    yield None
                sent += 1
                if validity:
                    cursors[cursor_key] = {"validity": validity, "uid": uid}
                    store.set_imap_cursor(cursor_key, cursors[cursor_key])
                if delay:
                    time.sleep(delay)
            info["folders_processed"] += 1
    except (imaplib.IMAP4.error, OSError, UnicodeError, ValueError) as exc:
        # Never forward server text, exception details, usernames, passwords or tokens.
        raise MailboxError("IMAP connection / authentication failed. Check TLS, host, authorization and app password or OAuth2 with your provider. Saved progress is preserved.") from None
    finally:
        secret = ""  # best effort; Python strings cannot be reliably zeroed
        if client:
            try:
                client.logout()  # no CLOSE/EXPUNGE, even on failure
            except (imaplib.IMAP4.error, OSError):
                pass
