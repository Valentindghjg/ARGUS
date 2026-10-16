# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Simulations for the follow-up fixes R-14 to R-16 of the 2026-10 review.

Synthetic only: a real local Store, FakeIMAP, a fake keyring, a controllable
clock and fake Bitwarden runners. Nothing connects to a real service.
"""
from contextlib import closing, redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from argus_security.background import BackgroundScanService, KeyringCredentialStore
from argus_security.cli import main
from argus_security.imap_client import IMAPConfig, save_config
from argus_security.mailbox_lease import LEASE_KEY, LEASE_SECONDS, LeaseLost, MailboxBusy, MailboxLease, RENEW_SECONDS
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store
from tests.test_background import FakeKeyring
from tests.test_imap_discovery import FakeIMAP
from tests.test_review_simulations import HookedIMAP, OWN, SECRET, account_mail


class Profile(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "profile"
        self.store = Store(self.data_dir, Registry())
        self.store.configure([OWN])
        self.config = IMAPConfig("imap.example.invalid", OWN)
        save_config(self.data_dir / "imap.json", self.config)
        self.now = [1_700_000_000.0]
        self.keyring = FakeKeyring()
        self.credentials = KeyringCredentialStore(self.keyring)
        no_sleep = patch("argus_security.imap_client.time.sleep", lambda seconds: None)
        no_sleep.start()
        self.addCleanup(no_sleep.stop)

    def manual_scan(self, client, getpass_calls=None):
        """Run `argus scan-imap --allow-imap` against a fake mailbox."""
        calls = getpass_calls if getpass_calls is not None else []
        factory = lambda host, port, ssl_context, timeout: client
        output, errors = StringIO(), StringIO()
        with patch("argus_security.imap_client.BoundedIMAP4SSL", factory), \
             patch("argus_security.cli.sys.stdin.isatty", return_value=True), \
             patch("argus_security.cli.getpass.getpass", side_effect=lambda prompt: calls.append(prompt) or SECRET), \
             redirect_stdout(output), redirect_stderr(errors):
            code = main(["--language", "en", "--data-dir", str(self.data_dir), "scan-imap", "--allow-imap"])
        return code, output.getvalue(), errors.getvalue()


class MailboxLeaseSimulation(Profile):
    def scheduled(self):
        return BackgroundScanService(self.store, self.credentials, config_loader=lambda: self.config,
                                     clock=lambda: self.now[0])

    def test_manual_scan_completes_and_releases_the_mailbox(self):
        code, output, errors = self.manual_scan(FakeIMAP({1: account_mail(1), 2: account_mail(2)}))
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output.strip().splitlines()[-1])["processed"], 2)
        self.assertIsNone(self.store.meta(LEASE_KEY))
        self.assertNotIn(SECRET, output + errors)

    def test_scheduled_run_gives_its_claim_back_while_a_manual_scan_holds_the_mailbox(self):
        selector = self.credentials.save(SECRET)
        service = self.scheduled()
        service.configure(credential_id=selector, interval_seconds=900)
        due = service.schedule().next_run_at
        manual = MailboxLease(self.store, kind="manual", clock=lambda: self.now[0]).acquire()
        self.keyring.calls.clear()
        self.assertEqual(service.run_due(allow_network=True), {"status": "busy"})
        self.assertEqual(self.keyring.calls, [])
        self.assertFalse(service.snapshot()["running"])
        self.assertEqual(service.schedule().next_run_at, due)
        manual.release()
        with patch("argus_security.imap_client.BoundedIMAP4SSL", lambda *a, **k: FakeIMAP()):
            self.assertEqual(service.run_due(allow_network=True)["status"], "completed")

    def test_manual_scan_is_refused_before_the_password_prompt_while_a_scheduled_scan_runs(self):
        selector = self.credentials.save(SECRET)
        # Both "processes" use the real clock here, as they would in production.
        service = BackgroundScanService(self.store, self.credentials, config_loader=lambda: self.config)
        service.configure(credential_id=selector, interval_seconds=900)
        attempts = []

        def try_manual(uid):
            if uid == 1:
                prompts = []
                attempts.append((self.manual_scan(FakeIMAP(), prompts), prompts))

        client = HookedIMAP({1: account_mail(1)}, try_manual)
        with patch("argus_security.imap_client.BoundedIMAP4SSL", lambda *a, **k: client):
            self.assertEqual(service.run_due(allow_network=True)["status"], "completed")
        (code, _, errors), prompts = attempts[0]
        self.assertEqual(code, 2)
        self.assertIn("Another ARGUS mailbox scan for this profile is running", errors)
        self.assertEqual(prompts, [])
        self.assertIsNone(self.store.meta(LEASE_KEY))

    def test_expired_or_malformed_records_never_block_a_new_session(self):
        clock = lambda: self.now[0]
        for stale in ({"token": "x", "kind": "manual", "lease_until": self.now[0] - 1},
                      {"token": 3, "kind": "manual", "lease_until": self.now[0] + 99},
                      {"kind": "unknown"}, "garbage", None):
            with self.subTest(stale=stale):
                self.store.set_meta(LEASE_KEY, stale)
                MailboxLease(self.store, kind="manual", clock=clock).acquire().release()
        holder = MailboxLease(self.store, kind="scheduled", clock=clock).acquire()
        with self.assertRaises(MailboxBusy):
            MailboxLease(self.store, kind="manual", clock=clock).acquire()
        holder.release()

    def test_a_taken_over_lease_stops_the_manual_scan_between_messages(self):
        fetched = []

        def steal_after_first(uid):
            fetched.append(uid)
            if uid == 1:
                # Simulate a stale lease replaced by another process.
                self.store.set_meta(LEASE_KEY, {"token": "other", "kind": "scheduled",
                                                "lease_until": 9_999_999_999})

        clock = patch("argus_security.mailbox_lease.time.time",
                      side_effect=lambda: self.now.__setitem__(0, self.now[0] + RENEW_SECONDS + 1) or self.now[0])
        with clock:
            code, output, errors = self.manual_scan(HookedIMAP({1: account_mail(1), 2: account_mail(2)}, steal_after_first))
        self.assertEqual(code, 2)
        self.assertIn("took over this mailbox", errors)
        self.assertEqual(fetched, [1])
        self.assertEqual(self.store.snapshot()["summary"]["found"], 1)
        self.assertEqual(self.store.meta(LEASE_KEY)["token"], "other")

    def test_lease_renewal_keeps_long_manual_scans_exclusive(self):
        lease = MailboxLease(self.store, kind="manual", clock=lambda: self.now[0]).acquire()
        for _ in range(4):
            self.now[0] += LEASE_SECONDS - 1
            lease.keep_alive()
        with self.assertRaises(MailboxBusy):
            MailboxLease(self.store, kind="scheduled", clock=lambda: self.now[0]).acquire()
        lease.release()
        with self.assertRaises(LeaseLost):
            lease.keep_alive()


class UserFacingErrorSimulation(Profile):
    def setUp(self):
        super().setUp()
        self.server = DashboardServer(self.store, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        scan_messages(self.store, [synthetic_mail("notify@github.com", "Your account has been created", "")])

    def request(self, method, path, payload):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        with closing(http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)) as connection:
            connection.request(method, path, body=body, headers={"Authorization": "Bearer " + self.server.token,
                                                                 "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read()).get("error")

    def test_account_rules_reach_the_dashboard_verbatim(self):
        self.store.add_emails(["second@example.invalid"])
        status, message = self.request("PATCH", "/api/accounts/github", {"registered_email": "second@example.invalid"})
        self.assertEqual(status, 400)
        self.assertEqual(message, "An existing account's sign-in address cannot be reassigned; add a separate account")
        status, message = self.request("PATCH", "/api/accounts/github", {"registered_email": "stranger@example.invalid"})
        self.assertEqual(message, "Use only explicitly configured own addresses")
        self.assertNotIn("stranger", message)

    def test_worklist_rules_reach_the_dashboard_verbatim(self):
        self.request("POST", "/api/workflow", {"action": "add", "ids": ["github"]})
        status, message = self.request("POST", "/api/workflow", {"action": "snooze_until", "id": "github", "date": "1999-01-01"})
        self.assertEqual((status, message), (400, "Choose a future local date"))

    def test_malformed_requests_stay_generic(self):
        status, message = self.request("PATCH", "/api/accounts/github", "{not json")
        self.assertEqual(status, 400)
        self.assertEqual(message, "Invalid update; check required steps before marking the account done")
        status, message = self.request("POST", "/api/workflow", {"action": "add", "ids": "github", "extra": 1})
        self.assertEqual(message, "Invalid worklist action")


if __name__ == "__main__":
    unittest.main()
