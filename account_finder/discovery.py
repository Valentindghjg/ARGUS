"""Explicit opt-in DNS MX discovery. Never sends the mailbox's local part."""
import ipaddress
from pathlib import Path
import secrets
import socket
import struct

from .registry import is_subdomain, normalize_domain

PROFILES = [
    {"id": "google", "name": "Google / Google Workspace", "mx": ["google.com", "googlemail.com"],
     "host": "imap.gmail.com", "port": 993, "auth": "app_password",
     "note": "Use an app password only if supported by your account; otherwise use OAuth2. Follow your administrator’s IMAP policy.",
     "source": "https://support.google.com/mail/answer/185833"},
    {"id": "microsoft", "name": "Microsoft 365 / Exchange Online", "mx": ["mail.protection.outlook.com"],
     "host": "outlook.office365.com", "port": 993, "auth": "oauth2",
     "note": "Exchange Online requires OAuth2 for IMAP; an app password does not restore disabled Basic Authentication.",
     "source": "https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth"},
    {"id": "fastmail", "name": "Fastmail", "mx": ["messagingengine.com"],
     "host": "imap.fastmail.com", "port": 993, "auth": "app_password",
     "note": "Use a separate app password; your account plan must support IMAP.",
     "source": "https://www.fastmail.help/hc/en-us/articles/1500000278342-Server-names-and-ports"},
    {"id": "icloud", "name": "Apple iCloud Mail", "mx": ["icloud.com"],
     "host": "imap.mail.me.com", "port": 993, "auth": "app_password",
     "note": "Use an app-specific password; verify the username with your provider.",
     "source": "https://support.apple.com/en-us/102525"},
    {"id": "proton", "name": "Proton Mail", "mx": ["protonmail.ch", "protonmail.com"],
     "host": None, "port": None, "auth": None,
     "note": "No direct standard IMAP access. Export EML/mbox with official Proton tools. This TLS-only scanner does not automatically configure a local Bridge.",
     "source": "https://proton.me/support/protonmail-bridge-clients"},
    {"id": "mailbox", "name": "mailbox.org", "mx": ["mailbox.org"],
     "host": "imap.mailbox.org", "port": 993, "auth": "app_password",
     "note": "Verify IMAP settings and app-password requirements in current provider documentation.",
     "source": "https://kb.mailbox.org/"},
    {"id": "infomaniak", "name": "Infomaniak", "mx": ["infomaniak.ch", "infomaniak.com"],
     "host": "mail.infomaniak.com", "port": 993, "auth": "app_password",
     "note": "Receiving service identified; verify the actual mail host and login in your provider account.",
     "source": "https://www.infomaniak.com/en/support/faq"},
]


class DNSError(Exception):
    pass


def _name(packet: bytes, offset: int):
    labels, seen, end = [], set(), None
    for _ in range(128):
        if offset >= len(packet) or offset in seen:
            raise DNSError("Invalid DNS response")
        seen.add(offset)
        size = packet[offset]
        if size & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise DNSError("Invalid DNS response")
            if end is None:
                end = offset + 2
            offset = ((size & 0x3F) << 8) | packet[offset + 1]
        elif size == 0:
            return ".".join(labels).lower(), end if end is not None else offset + 1
        elif size > 63 or offset + 1 + size > len(packet):
            raise DNSError("Invalid DNS response")
        else:
            try:
                labels.append(packet[offset + 1:offset + 1 + size].decode("ascii"))
            except UnicodeError:
                raise DNSError("Invalid DNS response") from None
            offset += 1 + size
    raise DNSError("The DNS response contains too many pointers")


def parse_mx(packet: bytes, txid: int, domain: str):
    if len(packet) < 12:
        raise DNSError("Incomplete DNS response")
    ident, flags, questions, answers, _, _ = struct.unpack("!6H", packet[:12])
    if ident != txid or not flags & 0x8000 or flags & 0x7800 or questions != 1:
        raise DNSError("Invalid DNS response")
    if flags & 0xF:
        raise DNSError("Domain or MX lookup unavailable at the resolver")
    if flags & 0x200:
        raise DNSError("Truncated DNS response")
    question, offset = _name(packet, 12)
    if question != domain or offset + 4 > len(packet) or struct.unpack("!HH", packet[offset:offset + 4]) != (15, 1):
        raise DNSError("The DNS response does not match the query")
    offset += 4
    records = []
    for _ in range(answers):
        _, offset = _name(packet, offset)
        if offset + 10 > len(packet):
            raise DNSError("Incomplete DNS response")
        kind, cls, ttl, length = struct.unpack("!HHIH", packet[offset:offset + 10])
        offset += 10
        end = offset + length
        if end > len(packet):
            raise DNSError("Incomplete DNS response")
        if kind == 15 and cls == 1:
            if length < 3:
                raise DNSError("Invalid MX record")
            preference = struct.unpack("!H", packet[offset:offset + 2])[0]
            host, consumed = _name(packet, offset + 2)
            if consumed > end:
                raise DNSError("Invalid MX record")
            records.append({"preference": preference, "host": normalize_domain(host) if host else "."})
        offset = end
    return sorted(records, key=lambda item: (item["preference"], item["host"]))


def system_resolvers():
    path = Path("/etc/resolv.conf")
    result = []
    if path.exists():
        for line in path.read_text(encoding="ascii", errors="ignore").splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0] == "nameserver":
                try:
                    result.append(str(ipaddress.ip_address(fields[1])))
                except ValueError:
                    continue
    return result


def _read_exact(sock, length):
    result = bytearray()
    while len(result) < length:
        part = sock.recv(length - len(result))
        if not part:
            raise DNSError("Incomplete DNS response")
        result.extend(part)
    return bytes(result)


def lookup_mx(domain: str, *, allow_network=False, resolver=None):
    domain = normalize_domain(domain)
    if not allow_network:
        raise DNSError("MX lookup requires explicit --allow-dns authorization")
    resolvers = [str(ipaddress.ip_address(resolver))] if resolver else system_resolvers()
    if not resolvers:
        raise DNSError("No system resolver available; specify an explicitly selected IP with --resolver or configure offline")
    txid = secrets.randbelow(65536)
    question = b"".join(bytes([len(label)]) + label.encode("ascii") for label in domain.split(".")) + b"\0" + struct.pack("!HH", 15, 1)
    query = struct.pack("!6H", txid, 0x0100, 1, 0, 0, 0) + question
    for resolver_ip in resolvers[:2]:
        family = socket.AF_INET6 if ":" in resolver_ip else socket.AF_INET
        try:
            with socket.socket(family, socket.SOCK_DGRAM) as sock:
                sock.settimeout(4)
                sock.connect((resolver_ip, 53))
                sock.send(query)
                response = sock.recv(65535)
            if len(response) >= 4 and struct.unpack("!H", response[2:4])[0] & 0x0200:
                with socket.socket(family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(4)
                    sock.connect((resolver_ip, 53))
                    sock.sendall(struct.pack("!H", len(query)) + query)
                    length = struct.unpack("!H", _read_exact(sock, 2))[0]
                    response = _read_exact(sock, length)
            return parse_mx(response, txid, domain)
        except (OSError, DNSError, ValueError):
            continue
    raise DNSError("MX lookup failed. Identify the provider using your email client / hosting account; do not automatically try guessed IMAP hosts.")


def provider_hints(records):
    return [profile for profile in PROFILES if any(any(is_subdomain(row["host"], root) for root in profile["mx"]) for row in records)]


def discover(domain, *, allow_network=False, resolver=None):
    domain = normalize_domain(domain)
    if not allow_network:
        return {"domain": domain, "network": False, "mx": [], "candidates": [],
                "note": "Offline. For a custom domain, check your email client or hosting account. --allow-dns authorizes only the MX lookup, not an IMAP connection."}
    records = lookup_mx(domain, allow_network=True, resolver=resolver)
    return {"domain": domain, "network": True, "mx": records, "candidates": provider_hints(records),
            "note": "MX describes the receiving route; an upstream spam filter may hide the actual mail provider. Verify the IMAP host separately in official documentation."}
