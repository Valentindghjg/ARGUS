# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Master plan priority 10: an approval never silently covers a new target.

Synthetic only: a real Store, a fake keyring and FakeIMAP. A scheduled scan
must stop before reading the keyring or opening a socket whenever imap.json no
longer matches the settings the user approved.
"""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security.background import (SCHEDULE_META_KEY, TARGET_CHANGED_ERROR, BackgroundScanService,
                                       KeyringCredentialStore)
from argus_security.cli import main
from argus_security.imap_client import IMAPConfig, save_config
from argus_security.registry import Registry
from argus_security.store import Store
from tests.test_background import FakeKeyring
from tests.test_imap_discovery import FakeIMAP
from tests.test_review_simulations import OWN, SECRET, account_mail


class TargetBindingSimulation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "profile"
        self.store = Store(self.data_dir, Registry())
        self.store.configure([OWN])
        self.approved = IMAPConfig("imap.example.invalid", OWN, folders=("INBOX",))
        self.write_config(self.approved)
        self.keyring = FakeKeyring()
        self.credentials = KeyringCredentialStore(self.keyring)
        self.connections = []
        no_sleep = patch("argus_security.imap_client.time.sleep", lambda seconds: None)
        no_sleep.start()
        self.addCleanup(no_sleep.stop)

    def write_config(self, config):
        path = self.data_dir / "imap.json"
        path.unlink(missing_ok=True)
        save_config(path, config)

    def service(self):
        return BackgroundScanService(self.store, self.credentials)

    def enable(self, service):
        selector = self.credentials.save(SECRET)
        service.configure(credential_id=selector, target=self.approved.target_fingerprint(), interval_seconds=900)
        self.keyring.calls.clear()

    def run_due(self, service):
        def factory(host, port, ssl_context, timeout):
            self.connections.append((host, port))
            return FakeIMAP({1: account_mail(1)})
        with patch("argus_security.imap_client.BoundedIMAP4SSL", factory):
            return service.run_due(allow_network=True)

    def assert_blocked_without_secret_or_network(self, service, result):
        self.assertEqual(result["status"], "reauthorization_required")
        self.assertEqual(result["error"], TARGET_CHANGED_ERROR)
        self.assertFalse(any(call[0] == "get" for call in self.keyring.calls))
        self.assertEqual(self.connections, [])
        snapshot = service.snapshot()
        self.assertFalse(snapshot["enabled"])
        self.assertFalse(snapshot["target_confirmed"])
        self.assertTrue(snapshot["authorized"])
        self.assertEqual(snapshot["last_error"], TARGET_CHANGED_ERROR)
        # A stopped schedule stays stopped; nothing retries on its own.
        self.assertEqual(service.run_due(allow_network=True), {"status": "disabled"})

    def test_unchanged_target_runs_normally(self):
        service = self.service()
        self.enable(service)
        self.assertTrue(service.snapshot()["target_confirmed"])
        self.assertEqual(self.run_due(service)["status"], "completed")
        self.assertEqual(self.connections, [("imap.example.invalid", 993)])

    def test_any_changed_field_stops_before_keyring_or_network(self):
        changes = {"host": replace(self.approved, host="imap.attacker.example"),
                   "port": replace(self.approved, port=1993),
                   "username": replace(self.approved, username="someone@example.invalid"),
                   "auth": replace(self.approved, auth="oauth2"),
                   "folders": replace(self.approved, folders=("*",))}
        for field, changed in changes.items():
            with self.subTest(field=field):
                self.write_config(self.approved)
                service = self.service()
                self.enable(service)
                self.connections.clear()
                self.write_config(changed)
                self.assert_blocked_without_secret_or_network(service, self.run_due(service))

    def test_schedule_from_before_target_binding_needs_new_approval(self):
        selector = self.credentials.save(SECRET)
        self.store.set_meta(SCHEDULE_META_KEY, {"version": 1, "enabled": True, "interval_seconds": 900,
                                                "limit": 500, "credential_id": selector, "next_run_at": 0})
        self.keyring.calls.clear()
        service = self.service()
        self.assertFalse(service.snapshot()["target_confirmed"])
        self.assert_blocked_without_secret_or_network(service, self.run_due(service))

    def test_enable_shows_the_target_and_reapproval_resumes_scans(self):
        service = self.service()
        self.enable(service)
        self.write_config(replace(self.approved, host="imap.new-provider.example"))
        self.assertEqual(self.run_due(service)["status"], "reauthorization_required")
        output = StringIO()
        with patch("argus_security.cli.KeyringCredentialStore", return_value=self.credentials), \
             patch("argus_security.cli.sys.stdin.isatty", return_value=True), \
             patch("argus_security.cli.getpass.getpass", return_value=SECRET), \
             redirect_stdout(output), redirect_stderr(StringIO()):
            self.assertEqual(main(["--language", "en", "--data-dir", str(self.data_dir),
                                   "background-imap", "enable", "--interval-minutes", "15"]), 0)
        self.assertIn("imap.new-provider.example:993", output.getvalue())
        self.assertIn("INBOX", output.getvalue())
        self.assertNotIn(SECRET, output.getvalue())
        self.assertTrue(service.snapshot()["target_confirmed"])
        self.assertEqual(self.run_due(service)["status"], "completed")
        self.assertEqual(self.connections, [("imap.new-provider.example", 993)])

    def test_revoke_forgets_the_approved_target(self):
        service = self.service()
        self.enable(service)
        service.revoke()
        self.assertIsNone(service.schedule().target)
        self.assertFalse(service.snapshot()["target_confirmed"])

    def test_fingerprint_is_stable_validated_and_secret_free(self):
        first, second = self.approved.target_fingerprint(), IMAPConfig("imap.example.invalid", OWN,
                                                                      folders=("INBOX",)).target_fingerprint()
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")
        self.assertNotIn(SECRET, repr(self.store.meta(SCHEDULE_META_KEY)))
        with self.assertRaises(ValueError):
            IMAPConfig("not a host", OWN).target_fingerprint()
        with self.assertRaises(ValueError):
            BackgroundScanService(self.store, self.credentials).configure(credential_id=self.credentials.save(SECRET))


if __name__ == "__main__":
    unittest.main()
