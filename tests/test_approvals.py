# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A23, A26 and D5: a visible standing approval, revocation and an offline preview."""
from contextlib import redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
import unittest

from argus_security.background import BackgroundScanService, KeyringCredentialStore
from argus_security.cli import main
from argus_security.imap_client import IMAPConfig, cursor_identity, save_config
from argus_security.registry import Registry
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


class FakeKeyring:
    def __init__(self):
        self.entries = {}

    def set_password(self, service, account, secret):
        self.entries[(service, account)] = secret

    def get_password(self, service, account):
        return self.entries.get((service, account))

    def delete_password(self, service, account):
        del self.entries[(service, account)]


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        self.config = IMAPConfig("imap.example.invalid", OWN, folders=("INBOX",))
        save_config(self.profile / "imap.json", self.config)
        self.keyring = FakeKeyring()
        self.calls = []
        self.service = self.make_service()

    def make_service(self):
        def runner(*args, **kwargs):
            self.calls.append(1)
            return {"result": "completed"}
        return BackgroundScanService(self.store, KeyringCredentialStore(self.keyring),
                                     config_loader=lambda: self.config, scan_runner=runner)

    def events(self):
        return [entry["event"] for entry in self.store.control_overview()["activity"]]

    def test_an_approval_is_recorded_shown_without_the_username_and_checked_before_each_run(self):
        self.assertIsNone(self.service.approval())
        selector = self.service.credentials.save("not-a-real-secret")
        self.service.configure(credential_id=selector, target=self.config.target_fingerprint(), limit=50)
        approval = self.service.approval()
        self.assertEqual((approval["state"], approval["host"], approval["folders"], approval["limit"]),
                         ("active", "imap.example.invalid", ["INBOX"], 50))
        self.assertIsNotNone(approval["approved_at"])
        self.assertNotIn(OWN, json.dumps(approval))
        self.assertEqual(self.events()[0], "approval_granted")
        # A changed folder selection is a new target: the run is refused before any keyring use.
        self.config = IMAPConfig("imap.example.invalid", OWN, folders=("INBOX", "Archive"))
        self.assertEqual(self.service.approval()["state"], "needs_approval")
        self.assertEqual(self.service.run_due(allow_network=True)["status"], "reauthorization_required")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.events()[0], "approval_refused")

    def test_revoking_ends_the_approval_and_removes_the_authorization(self):
        selector = self.service.credentials.save("not-a-real-secret")
        self.service.configure(credential_id=selector, target=self.config.target_fingerprint())
        self.service.revoke()
        self.assertIsNone(self.service.approval())
        self.assertEqual(self.keyring.entries, {})
        self.assertEqual(self.events()[0], "approval_revoked")

    def test_the_preview_reads_only_local_checkpoints(self):
        preview = self.service.preview(self.config, interval_seconds=3600, limit=20)
        self.assertEqual((preview["checkpoints"], preview["folders"]), (0, ["INBOX"]))
        self.store.set_imap_cursor(cursor_identity(self.config, [OWN]) + ":folder", {"validity": "1", "uid": 9})
        self.store.set_imap_cursor("other-settings:folder", {"validity": "1", "uid": 3})
        self.assertEqual(self.service.preview(self.config, interval_seconds=3600, limit=20)["checkpoints"], 1)
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--language", "en", "--data-dir", str(self.profile), "background-imap", "preview",
                         "--interval-minutes", "60", "--limit", "20"])
        self.assertEqual(code, 0)
        printed = out.getvalue()
        self.assertIn("Saved checkpoints: 1 folder(s)", printed)
        self.assertEqual(json.loads(printed[printed.index("{"):])["limit"], 20)

    def test_the_control_api_shows_and_revokes_the_approval(self):
        server = DashboardServer(self.store, 0)
        server.background_service = self.service
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def call(method, path, body=None):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request(method, path, json.dumps(body) if body is not None else None,
                               {"Authorization": "Bearer " + server.token, "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())

        self.assertIsNone(call("GET", "/api/control")[1]["approval"])
        selector = self.service.credentials.save("not-a-real-secret")
        self.service.configure(credential_id=selector, target=self.config.target_fingerprint())
        self.assertEqual(call("GET", "/api/control")[1]["approval"]["state"], "active")
        self.assertEqual(call("POST", "/api/approvals/revoke", {"kind": "manual_scan"})[0], 400)
        self.assertEqual(call("POST", "/api/approvals/revoke", {"kind": "scheduled_scan"})[0], 200)
        self.assertIsNone(call("GET", "/api/control")[1]["approval"])


if __name__ == "__main__":
    unittest.main()
