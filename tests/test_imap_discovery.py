# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
import imaplib
import json
from pathlib import Path
import ssl
import struct
import tempfile
import unittest
from unittest.mock import patch

from argus_security.discovery import discover, lookup_mx, parse_mx, provider_hints, DNSError
from argus_security.imap_client import IMAPConfig, imap_messages, MailboxError, encode_folder, decode_folder, load_config, save_config
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store


class FakeIMAP:
    def __init__(self, messages=None, failure=None, validity=b"1"):
        self.messages = messages or {1: synthetic_mail("notify@github.com", "Your account has been created", "")}
        self.failure = failure
        self.validity = validity
        self.calls = []
        self.debug = 4

    def login(self, username, password):
        self.calls.append(("LOGIN",))
        if self.failure == "login":
            raise imaplib.IMAP4.error("SECRET-TOKEN: synthetic server rejection")
        return "OK", []

    def authenticate(self, mechanism, callback):
        self.calls.append((mechanism,))
        self.assertion = callback(None).startswith(b"user=")
        return "OK", []

    def list(self):
        self.calls.append(("LIST",))
        return "OK", [b'(\\Noselect) "/" "Parent"', b'(\\HasNoChildren) "/" "INBOX"']

    def select(self, folder, readonly=False):
        self.calls.append(("SELECT", folder, readonly))
        return "OK", [b"1"]

    def response(self, name):
        return name, [self.validity]

    def uid(self, operation, *args):
        self.calls.append((operation, *args))
        if operation == "SEARCH":
            return "OK", [b" ".join(str(uid).encode() for uid in self.messages)]
        uid = int(args[0])
        if self.failure == "fetch":
            return "NO", [b"SECRET-TOKEN"]
        raw = self.messages[uid]
        if args[1] == "(RFC822.SIZE)":
            return "OK", [f"1 (UID {uid} RFC822.SIZE {len(raw)})".encode()]
        if "[HEADER]" in args[1]:
            raw = raw.split(b"\n\n", 1)[0] + b"\n\n"
        return "OK", [(b"1 (BODY[] {10}", raw), b")"]

    def logout(self):
        self.calls.append(("LOGOUT",))
        return "BYE", []


class IMAPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "data", Registry())
        self.store.configure(["demo@example.invalid"])
        self.config = IMAPConfig("imap.example.invalid", "demo@example.invalid")

    def tearDown(self):
        self.temp.cleanup()

    def run_scan(self, client, **kwargs):
        def factory(host, port, ssl_context, timeout):
            self.assertEqual(host, self.config.host)
            self.assertEqual(ssl_context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(ssl_context.check_hostname)
            self.assertGreaterEqual(ssl_context.minimum_version, ssl.TLSVersion.TLSv1_2)
            return client
        messages = imap_messages(self.store, self.config, "SECRET-TOKEN", allow_network=True, factory=factory, delay=0, **kwargs)
        return scan_messages(self.store, messages, "imap")

    def test_readonly_peek_no_mutations(self):
        client = FakeIMAP()
        self.assertEqual(self.run_scan(client)["evidence"], 1)
        selects = [c for c in client.calls if c[0] == "SELECT"]
        self.assertEqual(len(selects), 1)
        self.assertTrue(selects[0][2])
        body_fetches = [c for c in client.calls if c[0] == "FETCH" and "BODY" in c[2]]
        self.assertTrue(all("BODY.PEEK" in c[2] and "<0." in c[2] for c in body_fetches))
        self.assertFalse(any(c[0] in {"STORE", "EXPUNGE", "DELETE", "CLOSE", "APPEND"} for c in client.calls))
        self.assertEqual(client.debug, 0)
        self.assertEqual(client.calls[-1][0], "LOGOUT")

    def test_permission_required_before_socket(self):
        with patch("argus_security.imap_client.BoundedIMAP4SSL") as factory:
            with self.assertRaises(MailboxError):
                list(imap_messages(self.store, self.config, "SECRET-TOKEN"))
            factory.assert_not_called()

    def test_incremental_uid_and_full_rescan(self):
        self.run_scan(FakeIMAP())
        second = FakeIMAP()
        result = self.run_scan(second)
        self.assertEqual(result["processed"], 0)
        self.assertIn(("SEARCH", None, "UID", "2:*"), second.calls)
        result = self.run_scan(FakeIMAP(), full_scan=True)
        self.assertEqual(result["duplicates"], 1)

    def test_changed_uidvalidity_rescans(self):
        self.run_scan(FakeIMAP())
        changed = FakeIMAP(validity=b"2")
        self.run_scan(changed)
        self.assertIn(("SEARCH", None, "UID", "1:*"), changed.calls)

    def test_failures_do_not_leak_and_logout(self):
        for failure in ["login", "fetch"]:
            client = FakeIMAP(failure=failure)
            with self.assertRaises(MailboxError) as raised:
                self.run_scan(client)
            self.assertNotIn("SECRET-TOKEN", str(raised.exception))
            self.assertEqual(client.calls[-1][0], "LOGOUT")
            self.assertNotIn(b"SECRET-TOKEN", self.store.path.read_bytes())
            self.assertEqual(self.store.meta("last_scan")["result"], "partial")
        self.assertFalse(self.store.meta("imap_cursors", {}))

    def test_limit_checkpoint_and_resume(self):
        messages = {uid: synthetic_mail("notify@github.com", "Your account has been created", f"Message {uid}") for uid in range(1,4)}
        self.assertEqual(self.run_scan(FakeIMAP(messages), limit=1)["processed"], 1)
        self.assertEqual(self.run_scan(FakeIMAP(messages))["processed"], 2)

    def test_large_message_header_only(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "x" * (3 * 1024 * 1024))
        client = FakeIMAP({1:raw})
        result = self.run_scan(client)
        self.assertEqual(result["evidence"], 1)
        account = next(a for a in self.store.snapshot()["accounts"] if a["id"] == "github")
        self.assertEqual(account["score"], 70)
        self.assertTrue(any(c[0] == "FETCH" and "BODY.PEEK[HEADER]" in c[2] for c in client.calls))

    def test_oauth2_and_folder_listing(self):
        self.config = IMAPConfig("imap.example.invalid", "demo@example.invalid", auth="oauth2")
        client = FakeIMAP()
        self.run_scan(client)
        self.assertIn(("XOAUTH2",), client.calls)
        self.assertTrue(client.assertion)
        listing = FakeIMAP()
        self.assertEqual(list(imap_messages(self.store, self.config, "SECRET-TOKEN", allow_network=True, list_only=True, factory=lambda *a, **kw:listing, delay=0)), ["INBOX"])
        self.assertFalse(any(c[0] == "SELECT" for c in listing.calls))

    def test_non_ascii_folder_roundtrip(self):
        for name in ["INBOX", "Archiv/Österreich", "Gelöscht & Sonstiges", "收件箱"]:
            self.assertEqual(decode_folder(encode_folder(name)), name)

    def test_config_contains_no_secret_and_rejects_secret_fields(self):
        path = self.root / "data" / "imap.json"
        save_config(path, self.config)
        self.assertEqual(load_config(path), self.config)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["password"] = "SECRET-TOKEN"
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            load_config(path)


def wire_name(domain):
    return b"".join(bytes([len(p)]) + p.encode() for p in domain.split(".")) + b"\0"


class DiscoveryTests(unittest.TestCase):
    def test_offline_discovery_never_connects(self):
        with patch("socket.socket") as sock:
            result = discover("example.org")
            self.assertFalse(result["network"])
            with self.assertRaises(DNSError):
                lookup_mx("example.org")
            sock.assert_not_called()

    def test_mx_packet_and_provider_hint(self):
        domain = "example.org"
        question = wire_name(domain) + struct.pack("!HH",15,1)
        payload = struct.pack("!H",10) + wire_name("in1-smtp.messagingengine.com")
        answer = b"\xc0\x0c" + struct.pack("!HHIH",15,1,60,len(payload)) + payload
        packet = struct.pack("!6H",123,0x8180,1,1,0,0) + question + answer
        records = parse_mx(packet,123,domain)
        self.assertEqual(records[0]["preference"],10)
        self.assertEqual(provider_hints(records)[0]["id"],"fastmail")
        with self.assertRaises(DNSError):
            parse_mx(packet,124,domain)
        with self.assertRaises(DNSError):
            parse_mx(packet,123,"someone.org")

    def test_dns_pointer_cycle_and_truncation_rejected(self):
        packet = struct.pack("!6H",123,0x8180,1,0,0,0) + b"\xc0\x0c"
        with self.assertRaises(DNSError):
            parse_mx(packet,123,"example.org")
        with self.assertRaises(DNSError):
            parse_mx(b"\0"*5,123,"example.org")

    def test_provider_suffix_not_spoofable(self):
        self.assertEqual(provider_hints([{"host":"messagingengine.com.attacker.example"}]), [])

    def test_domain_rejects_email_and_control_characters(self):
        for value in ["person@example.org", "example.org\ninjected", "localhost"]:
            with self.assertRaises(ValueError):
                discover(value)
