# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from argus_security.background import (BackgroundScanService, CredentialError, KeyringCredentialStore,
                                       RUN_LEASE_SECONDS, SCHEDULE_META_KEY)
from argus_security.cli import main
from argus_security.imap_client import IMAPConfig, save_config
from argus_security.registry import Registry
from argus_security.store import Store


class MemoryStore:
    def __init__(self):
        self.values = {}

    def meta(self, key, default=None):
        return self.values.get(key, default)

    def set_meta(self, key, value):
        self.values[key] = value


class FakeKeyring:
    def __init__(self):
        self.entries = {}
        self.calls = []

    def set_password(self, service, account, secret):
        self.calls.append(("set", service, account))
        self.entries[(service, account)] = secret

    def get_password(self, service, account):
        self.calls.append(("get", service, account))
        return self.entries.get((service, account))

    def delete_password(self, service, account):
        self.calls.append(("delete", service, account))
        del self.entries[(service, account)]


class BackgroundScanTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.keyring = FakeKeyring()
        self.credentials = KeyringCredentialStore(self.keyring)
        self.now = [1_700_000_000.0]
        self.config = IMAPConfig("imap.example.invalid", "person@example.invalid")

    def service(self, runner=None):
        return BackgroundScanService(self.store, self.credentials, config_loader=lambda: self.config,
                                     scan_runner=runner or (lambda *args, **kwargs: {"result": "completed"}),
                                     clock=lambda: self.now[0])

    def test_disabled_by_default_never_touches_keyring_or_runner(self):
        calls = []
        service = self.service(lambda *args, **kwargs: calls.append(True))
        self.assertEqual(service.run_due(allow_network=True), {"status": "disabled"})
        self.assertEqual(self.keyring.calls, [])
        self.assertEqual(calls, [])

    def test_metadata_never_contains_secret_and_requires_runtime_network_consent(self):
        secret = "APP-PASSWORD-DO-NOT-STORE"
        selector = self.credentials.save(secret)
        service = self.service()
        service.configure(credential_id=selector)
        saved = self.store.values[SCHEDULE_META_KEY]
        self.assertNotIn(secret, repr(saved))
        self.assertEqual(service.run_due(), {"status": "authorization_required"})
        self.assertFalse(any(call[0] == "get" for call in self.keyring.calls))

    def test_due_run_is_incremental_and_uses_only_injected_runner(self):
        selector = self.credentials.save("APP-PASSWORD-DO-NOT-STORE")
        received = []
        def runner(store, config, secret, *, limit, keep_alive):
            keep_alive()
            received.append((store, config, secret, limit))
            return {"result": "completed", "processed": 3, "evidence": 1}
        service = self.service(runner)
        service.configure(credential_id=selector, interval_seconds=900, limit=10)
        self.assertEqual(service.run_due(allow_network=True),
                         {"status": "completed", "result": "completed", "processed": 3, "evidence": 1})
        self.assertEqual(received, [(self.store, self.config, "APP-PASSWORD-DO-NOT-STORE", 10)])
        self.assertEqual(service.run_due(allow_network=True)["status"], "not_due")

    def test_failures_are_safe_and_back_off_without_secret_leak(self):
        secret = "APP-PASSWORD-DO-NOT-LEAK"
        selector = self.credentials.save(secret)
        def broken(*args, **kwargs):
            raise OSError("server rejected " + secret)
        service = self.service(broken)
        service.configure(credential_id=selector, interval_seconds=900)
        result = service.run_due(allow_network=True)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn(secret, result["error"])
        persisted = self.store.values[SCHEDULE_META_KEY]
        self.assertNotIn(secret, repr(persisted))
        self.assertEqual(persisted["next_run_at"], self.now[0] + 900)

    def test_keyring_has_no_plaintext_fallback(self):
        unavailable = KeyringCredentialStore(keyring=object())
        with self.assertRaises(CredentialError) as raised:
            unavailable.save("APP-PASSWORD")
        self.assertNotIn("APP-PASSWORD", str(raised.exception))

    def test_disable_preserves_selector_but_stops_runs(self):
        selector = self.credentials.save("APP-PASSWORD")
        service = self.service()
        service.configure(credential_id=selector)
        service.disable()
        self.assertEqual(service.schedule().credential_id, selector)
        self.assertEqual(service.run_due(allow_network=True), {"status": "disabled"})

    def test_revoke_stops_scans_and_removes_the_keyring_secret(self):
        selector = self.credentials.save("APP-PASSWORD")
        service = self.service()
        service.configure(credential_id=selector)
        result = service.revoke()
        self.assertFalse(result.enabled)
        self.assertIsNone(result.credential_id)
        self.assertNotIn(("ARGUS IMAP authorization", selector), self.keyring.entries)
        self.assertFalse(service.snapshot()["authorized"])

    def test_expired_lease_replaces_stale_worker_without_old_completion_winning(self):
        selector = self.credentials.save("APP-PASSWORD")
        service = self.service()
        service.configure(credential_id=selector)
        first = service._claim_due()
        self.assertEqual(first["status"], "claimed")
        self.assertEqual(service._claim_due(), {"status": "running"})
        self.now[0] += RUN_LEASE_SECONDS + 1
        second = service._claim_due()
        self.assertEqual(second["status"], "claimed")
        self.assertFalse(service._finish_claim(first["run_id"], outcome="completed"))
        self.assertTrue(service._finish_claim(second["run_id"], outcome="completed"))

    def test_real_store_allows_only_one_concurrent_scheduled_runner(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "data", Registry())
            store.configure(["person@example.invalid"])
            selector = self.credentials.save("APP-PASSWORD")
            began, release, calls = threading.Event(), threading.Event(), []
            def runner(*args, **kwargs):
                calls.append(True)
                began.set()
                release.wait(2)
                return {"result": "completed"}
            first = BackgroundScanService(store, self.credentials,
                                          config_loader=lambda: self.config, scan_runner=runner)
            second = BackgroundScanService(store, self.credentials,
                                           config_loader=lambda: self.config, scan_runner=runner)
            first.configure(credential_id=selector)
            result = []
            worker = threading.Thread(target=lambda: result.append(first.run_due(allow_network=True)))
            worker.start()
            self.assertTrue(began.wait(1))
            self.assertEqual(second.run_due(allow_network=True), {"status": "running"})
            release.set()
            worker.join(2)
            self.assertEqual(result[0]["status"], "completed")
            self.assertEqual(calls, [True])

    def test_disable_while_running_prevents_late_completion_from_reenabling(self):
        selector = self.credentials.save("APP-PASSWORD")
        service = self.service()
        service.configure(credential_id=selector)
        claim = service._claim_due()
        service.disable()
        self.assertFalse(service._finish_claim(claim["run_id"], outcome="completed"))
        self.assertFalse(service.snapshot()["enabled"])


class BackgroundCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.data_dir = Path(self.temporary.name) / "profile"
        store = Store(self.data_dir, Registry())
        store.configure(["person@example.invalid"])
        save_config(self.data_dir / "imap.json", IMAPConfig("imap.example.invalid", "person@example.invalid"))
        self.keyring = FakeKeyring()

    def test_enable_status_disable_and_revoke_never_store_the_secret(self):
        credentials = KeyringCredentialStore(self.keyring)
        secret = "APP-PASSWORD-NOT-IN-ARGUS"
        argv = ["--data-dir", str(self.data_dir), "background-imap", "enable", "--interval-minutes", "15", "--limit", "11"]
        output = StringIO()
        with patch("argus_security.cli.KeyringCredentialStore", return_value=credentials), \
             patch("argus_security.cli.sys.stdin.isatty", return_value=True), \
             patch("argus_security.cli.getpass.getpass", return_value=secret), redirect_stdout(output):
            self.assertEqual(main(argv), 0)
        saved = Store(self.data_dir, Registry()).meta(SCHEDULE_META_KEY)
        self.assertTrue(saved["enabled"])
        self.assertEqual(saved["interval_seconds"], 900)
        self.assertNotIn(secret, repr(saved))
        self.assertNotIn(secret, output.getvalue())
        with patch("argus_security.cli.KeyringCredentialStore", return_value=credentials), redirect_stdout(output):
            self.assertEqual(main(["--data-dir", str(self.data_dir), "background-imap", "revoke"]), 0)
        saved = Store(self.data_dir, Registry()).meta(SCHEDULE_META_KEY)
        self.assertFalse(saved["enabled"])
        self.assertIsNone(saved["credential_id"])
        self.assertNotIn(secret, repr(saved))

    def test_server_shape_hides_credential_selector(self):
        credentials = KeyringCredentialStore(self.keyring)
        selector = credentials.save("APP-PASSWORD")
        service = BackgroundScanService(Store(self.data_dir, Registry()), credentials)
        service.configure(credential_id=selector)
        snapshot = service.snapshot()
        self.assertTrue(snapshot["enabled"])
        self.assertTrue(snapshot["authorized"])
        self.assertNotIn("credential_id", snapshot)
        service.disable()
        self.assertFalse(service.snapshot()["enabled"])


if __name__ == "__main__":
    unittest.main()
