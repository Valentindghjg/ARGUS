# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan B1, B3 and A19: three equal ways into Bitwarden, a journal over all of them, readiness first."""
from contextlib import redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
import unittest

from argus_security import handoffs
from argus_security.bitwarden import download_export, export_file, readiness
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


def created(sender, recipient=OWN):
    return synthetic_mail(sender, "Your account has been created", "", recipient=recipient)


class BitwardenPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN, "work@example.invalid"])
        scan_messages(self.store, [created("noreply@github.com"), created("noreply@spotify.com"),
                                   created("noreply@dropbox.com", f"{OWN}, work@example.invalid")])
        self.store.decide("github", "confirmed")

    def account(self, account_id):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == account_id)

    def journal(self):
        return {entry["account_id"]: entry for entry in self.store.snapshot()["bitwarden_handoffs"]}

    def test_readiness_names_what_is_missing_and_blocks_only_real_obstacles(self):
        self.assertEqual(self.account("github")["bitwarden_readiness"], {"status": "ready", "issues": []})
        self.assertEqual(self.account("spotify")["bitwarden_readiness"], {"status": "check", "issues": ["not_confirmed"]})
        # Two own recipients leave the sign-in address open; weak evidence alone is no hand-off.
        self.assertIn("unknown", self.account("dropbox")["bitwarden_readiness"]["issues"])
        self.store.decide("dropbox", "confirmed")
        self.assertEqual(self.account("dropbox")["bitwarden_readiness"], {"status": "check", "issues": ["no_address"]})
        github = self.account("github")
        for state, issue in (("uncertain", "transfer_unclear"), ("exported", "downloaded"), ("created", "in_vault")):
            with self.subTest(state=state):
                self.assertEqual(readiness(github, state)["status"], "blocked")
                self.assertIn(issue, readiness(github, state)["issues"])
        self.store.decide("spotify", "rejected", "not_mine")
        self.assertIn("rejected", self.account("spotify")["bitwarden_readiness"]["issues"])

    def test_a_download_is_journaled_and_blocks_a_second_one_until_resolved(self):
        result = download_export(self.store, ["github"])
        self.assertEqual(len(result["items"]), 1)
        entry = self.journal()["github"]
        self.assertEqual((entry["state"], entry["can_resolve"]), ("exported", True))
        self.assertEqual(self.account("github")["bitwarden_readiness"]["status"], "blocked")
        with self.assertRaises(handoffs.HandoffError):
            download_export(self.store, ["github"])
        with self.assertRaises(handoffs.HandoffError):
            handoffs.reserve(self.store, "github", OWN)
        handoffs.resolve(self.store, {"id": entry["id"], "created": False, "confirmed": True})
        self.assertEqual(len(download_export(self.store, ["github"])["items"]), 1)
        entry = self.journal()["github"]
        handoffs.resolve(self.store, {"id": entry["id"], "created": True, "confirmed": True})
        # A confirmed import is a password-free entry: prepared, never done.
        self.assertEqual(self.account("github")["steps"]["vault"]["state"], "prepared")
        with self.assertRaises(UserFacingError):
            handoffs.resolve(self.store, {"id": entry["id"], "created": True, "confirmed": True})

    def test_the_cli_file_is_journaled_and_an_existing_file_is_reported_first(self):
        path = self.root / "export.json"
        export_file(self.store, path, ["github"])
        self.assertEqual(self.journal()["github"]["state"], "exported")
        with self.assertRaises(FileExistsError):
            export_file(self.store, path, ["github"])
        with self.assertRaises(handoffs.HandoffError):
            export_file(self.store, self.root / "second.json", ["github"])

    def test_marking_accounts_found_in_the_vault_reads_nothing_and_can_be_undone(self):
        result = self.store.mark_in_vault(["github", "spotify"])
        self.assertEqual({self.account(i)["steps"]["vault"]["state"] for i in ("github", "spotify")}, {"done"})
        self.store.undo(result["batch"])
        self.assertEqual({self.account(i)["steps"]["vault"]["state"] for i in ("github", "spotify")}, {"open"})
        for ids in ([], "github", ["missing"], [1]):
            with self.subTest(ids=ids), self.assertRaises(UserFacingError):
                self.store.mark_in_vault(ids)
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            code = main(["--language", "en", "--data-dir", str(self.profile), "bitwarden-assign", "--id", "github"])
        self.assertEqual(code, 0)
        self.assertIn("did not read your vault", out.getvalue())

    def test_api_routes(self):
        server = DashboardServer(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def post(path, body):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request("POST", path, json.dumps(body), {"Authorization": "Bearer " + server.token,
                                                                "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())

        self.assertEqual(post("/api/bitwarden/assign", {"ids": ["github"], "x": 1})[0], 400)
        self.assertEqual(post("/api/bitwarden", {"ids": ["github"]})[0], 200)
        status, body = post("/api/bitwarden", {"ids": ["github"]})
        self.assertEqual(status, 400)
        self.assertIn("downloaded for Bitwarden", body["error"])
        self.assertEqual(post("/api/bitwarden/assign", {"ids": ["spotify"]})[0], 200)


if __name__ == "__main__":
    unittest.main()
