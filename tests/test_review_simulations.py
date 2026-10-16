# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""End-to-end simulations added by the 2026-10 security review.

Everything is synthetic: a real local Store, the in-memory FakeIMAP server from
the IMAP tests, a fake keyring and a controllable clock. No socket to a mail
server, keyring backend or Bitwarden CLI is ever opened.
"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security.background import (BackgroundScanService, KeyringCredentialStore,
                                       LEASE_RENEW_SECONDS, RUN_LEASE_SECONDS)
from argus_security.i18n import catalog
from argus_security.imap_client import IMAPConfig, imap_messages
from argus_security.registry import Registry
from argus_security.scan import file_messages, scan_messages, synthetic_mail
from argus_security.server import DashboardServer, startup_notice
from argus_security.store import Store
from tests.test_background import FakeKeyring
from tests.test_imap_discovery import FakeIMAP

SECRET = "SYNTHETIC-APP-PASSWORD-NEVER-STORED"
OWN = "demo@example.invalid"


def account_mail(index):
    return synthetic_mail("notify@github.com", "Your account has been created", f"Message {index}", recipient=OWN)


def poison_mail():
    # Deeply nested multiparts exhaust the MIME parser's recursion budget.
    header = (b"From: noreply@github.com\r\nTo: " + OWN.encode() +
              b"\r\nSubject: Your account has been created\r\n")
    return header + b"".join(b"Content-Type: multipart/mixed; boundary=b%d\r\n\r\n--b%d\r\n" % (i, i)
                             for i in range(2000))


class HookedIMAP(FakeIMAP):
    """FakeIMAP that runs a callback whenever a message size is requested."""

    def __init__(self, messages, on_fetch):
        super().__init__(messages)
        self.on_fetch = on_fetch

    def uid(self, operation, *args):
        if operation == "FETCH" and args[1] == "(RFC822.SIZE)":
            self.on_fetch(int(args[0]))
        return super().uid(operation, *args)


class ScheduledScanSimulation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "profile", Registry())
        self.store.configure([OWN])
        self.keyring = FakeKeyring()
        self.credentials = KeyringCredentialStore(self.keyring)
        self.now = [1_700_000_000.0]
        self.config = IMAPConfig("imap.example.invalid", OWN)
        no_sleep = patch("argus_security.imap_client.time.sleep", lambda seconds: None)
        no_sleep.start()
        self.addCleanup(no_sleep.stop)

    def service(self):
        # The default runner is used: real imap_messages + scan_messages.
        return BackgroundScanService(self.store, self.credentials, config_loader=lambda: self.config,
                                     clock=lambda: self.now[0])

    def run_with(self, client, service):
        factory = lambda host, port, ssl_context, timeout: client
        with patch("argus_security.imap_client.BoundedIMAP4SSL", factory):
            return service.run_due(allow_network=True)

    def test_long_scan_renews_its_lease_so_a_second_process_cannot_open_the_mailbox(self):
        selector = self.credentials.save(SECRET)
        first, second = self.service(), self.service()
        first.configure(credential_id=selector, interval_seconds=900, limit=50)
        competing = []

        def slow_server(uid):
            # Each message takes 100 simulated seconds: 6 messages exceed one lease.
            self.now[0] += 100
            competing.append(second.run_due(allow_network=True)["status"])

        messages = {uid: account_mail(uid) for uid in range(1, 7)}
        result = self.run_with(HookedIMAP(messages, slow_server), first)
        self.assertGreater(6 * 100, RUN_LEASE_SECONDS)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processed"], 6)
        self.assertEqual(set(competing), {"running"})
        self.assertFalse(first.snapshot()["running"])

    def test_disable_during_scan_stops_before_the_next_fetch_and_keeps_evidence(self):
        selector = self.credentials.save(SECRET)
        service = self.service()
        service.configure(credential_id=selector, interval_seconds=900, limit=50)
        fetched = []

        def disable_after_first(uid):
            fetched.append(uid)
            if uid == 1:
                service.disable()
            self.now[0] += LEASE_RENEW_SECONDS + 1

        client = HookedIMAP({uid: account_mail(uid) for uid in range(1, 6)}, disable_after_first)
        result = self.run_with(client, service)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(fetched, [1])
        self.assertEqual(client.calls[-1][0], "LOGOUT")
        self.assertFalse(service.snapshot()["enabled"])
        self.assertEqual(self.store.snapshot()["summary"]["found"], 1)
        self.assertEqual(self.store.meta("last_scan")["result"], "partial")

    def test_revoke_during_scan_removes_keyring_entry_and_cancels(self):
        selector = self.credentials.save(SECRET)
        service = self.service()
        service.configure(credential_id=selector, interval_seconds=900, limit=50)

        def revoke_on_second(uid):
            if uid == 2:
                service.revoke()
            self.now[0] += LEASE_RENEW_SECONDS + 1

        client = HookedIMAP({uid: account_mail(uid) for uid in range(1, 5)}, revoke_on_second)
        result = self.run_with(client, service)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(self.keyring.entries, {})
        self.assertFalse(service.snapshot()["authorized"])
        self.assertLessEqual(len([call for call in client.calls if call[0] == "FETCH" and "BODY" in call[2]]), 2)

    def test_secret_never_reaches_profile_files_after_a_scheduled_run(self):
        selector = self.credentials.save(SECRET)
        service = self.service()
        service.configure(credential_id=selector, interval_seconds=900, limit=50)
        result = self.run_with(HookedIMAP({1: account_mail(1)}, lambda uid: None), service)
        self.assertEqual(result["status"], "completed")
        for path in Path(self.store.data_dir).rglob("*"):
            if path.is_file():
                self.assertNotIn(SECRET.encode(), path.read_bytes(), path.name)


class PoisonMessageSimulation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "profile", Registry())
        self.store.configure([OWN])
        self.config = IMAPConfig("imap.example.invalid", OWN)

    def scan(self, client):
        factory = lambda host, port, ssl_context, timeout: client
        messages = imap_messages(self.store, self.config, SECRET, allow_network=True, factory=factory, delay=0)
        return scan_messages(self.store, messages, "imap")

    def test_malformed_message_is_counted_and_never_blocks_later_incremental_scans(self):
        messages = {1: account_mail(1), 2: poison_mail(), 3: account_mail(3)}
        first = self.scan(FakeIMAP(messages))
        self.assertEqual((first["processed"], first["errors"], first["evidence"]), (3, 1, 2))
        self.assertEqual(first["result"], "completed_with_gaps")
        second = self.scan(FakeIMAP(messages))
        self.assertEqual(second["processed"], 0)


class ReadOnlyImportSimulation(unittest.TestCase):
    def test_mbox_import_leaves_the_original_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = Store(root / "profile", Registry())
            store.configure([OWN])
            mbox = root / "export.mbox"
            mbox.write_bytes(b"".join(b"From sender@example.invalid Mon Oct  5 10:00:00 2026\n" +
                                      account_mail(index).replace(b"\r\n", b"\n") + b"\n"
                                      for index in range(1, 3)))
            mbox.chmod(0o444)
            before = (mbox.read_bytes(), mbox.stat().st_mtime_ns, mbox.stat().st_mode)
            result = scan_messages(store, file_messages(mbox, "mbox"), "mbox")
            self.assertEqual(result["processed"], 2)
            self.assertEqual(before, (mbox.read_bytes(), mbox.stat().st_mtime_ns, mbox.stat().st_mode))
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["export.mbox", "profile"])


class OAuthScheduleNoticeSimulation(unittest.TestCase):
    def test_enabling_an_oauth2_schedule_warns_about_token_expiry_without_echoing_it(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from argus_security.cli import main
        from argus_security.imap_client import save_config
        for language, expected in (("en", "expire within hours"), ("de", "nach wenigen Stunden ab")):
            with self.subTest(language=language), tempfile.TemporaryDirectory() as temporary:
                data_dir = Path(temporary) / "profile"
                Store(data_dir, Registry()).configure([OWN])
                save_config(data_dir / "imap.json", IMAPConfig("imap.example.invalid", OWN, auth="oauth2"))
                credentials = KeyringCredentialStore(FakeKeyring())
                output = StringIO()
                with patch("argus_security.cli.KeyringCredentialStore", return_value=credentials), \
                     patch("argus_security.cli.sys.stdin.isatty", return_value=True), \
                     patch("argus_security.cli.getpass.getpass", return_value=SECRET), redirect_stdout(output):
                    self.assertEqual(main(["--language", language, "--data-dir", str(data_dir),
                                           "background-imap", "enable"]), 0)
                self.assertIn(expected, output.getvalue())
                self.assertNotIn(SECRET, output.getvalue())
                self.assertNotIn(SECRET.encode(), (data_dir / "accounts.sqlite3").read_bytes())


class PublisherKeySimulation(unittest.TestCase):
    def test_key_generator_refuses_private_key_inside_the_repository(self):
        import subprocess
        import sys
        repository = Path(__file__).resolve().parents[1]
        private = repository / ".local" / "review-simulation-private.pem"
        self.assertFalse(private.exists())
        with tempfile.TemporaryDirectory() as temporary:
            public = Path(temporary) / "public.pem"
            result = subprocess.run([sys.executable, str(repository / "scripts" / "generate_license_keys.py"),
                                     "--private-key", str(private), "--public-key", str(public)],
                                    capture_output=True, text=True, timeout=60)
            self.addCleanup(lambda: private.unlink(missing_ok=True))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(private.exists())
            self.assertFalse(public.exists())
            self.assertNotIn("PRIVATE KEY", result.stdout + result.stderr)
            outside = Path(temporary) / "offline" / "private.pem"
            created = subprocess.run([sys.executable, str(repository / "scripts" / "generate_license_keys.py"),
                                      "--private-key", str(outside), "--public-key", str(public)],
                                     capture_output=True, text=True, timeout=60)
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(outside.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("PRIVATE KEY", created.stdout)


class DashboardSchedulerSimulation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "profile", Registry())
        self.store.configure([OWN])
        self.server = DashboardServer(self.store, 0)
        self.addCleanup(self.server.server_close)

    def test_scheduler_pass_survives_unexpected_errors(self):
        calls = []

        class Flaky:
            def run_due(self, *, allow_network):
                calls.append(allow_network)
                if len(calls) == 1:
                    raise RuntimeError("database is locked")
                return {"status": "not_due"}

        self.server.background_service = Flaky()
        self.server._background_pass()
        self.server._background_pass()
        self.assertEqual(calls, [True, True])

    def test_scheduler_pass_waits_for_a_running_browser_import(self):
        calls = []

        class Recorder:
            def run_due(self, *, allow_network):
                calls.append(allow_network)

        from argus_security.scan import ScanSession
        self.server.background_service = Recorder()
        self.server.import_job = ScanSession(self.store, "eml", expected=2)
        self.server._background_pass()
        self.assertEqual(calls, [])
        self.server.import_job.finish("partial")
        self.server._background_pass()
        self.assertEqual(calls, [True])

    def test_startup_notice_discloses_enabled_mailbox_schedule_in_both_languages(self):
        enabled = {"enabled": True}
        for language in ("en", "de"):
            self.assertIn("background-imap disable", startup_notice(enabled, language))
            self.assertNotIn("No mailbox connection", startup_notice(enabled, language))
        english = startup_notice(enabled, "en")
        self.assertIn(english, catalog()["de"])
        self.assertIn("No mailbox connection is active", startup_notice({"enabled": False}, "en"))


if __name__ == "__main__":
    unittest.main()
