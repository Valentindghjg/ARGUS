# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan D3, A6, A17 and B6: explained priorities, confirmed identity relations, worklist order."""
from contextlib import redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
import unittest

from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store
from argus_security.workflow import change_worklist

OWN = "owner@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class IdentityPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [created(sender) for sender in
                                   ("noreply@google.com", "noreply@notion.so", "noreply@spotify.com", "noreply@github.com")])

    def account(self, account_id):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == account_id)

    def codes(self, account_id):
        return [reason["code"] for reason in self.account(account_id)["priority_reasons"]]

    def test_catalog_priority_is_explained_and_the_persons_choice_wins(self):
        spotify = self.account("spotify")
        self.assertEqual(spotify["priority_reasons"], [{"code": "catalog", "level": spotify["catalog_priority"]}])
        self.store.update_account("spotify", {"priority": "critical"})
        self.assertEqual((self.account("spotify")["priority"], self.codes("spotify")[-1]), ("critical", "override"))
        self.store.update_account("spotify", {"priority": None})
        self.assertEqual(self.account("spotify")["priority"], spotify["catalog_priority"])

    def test_a_confirmed_mailbox_account_becomes_critical_with_its_reason(self):
        with self.assertRaises(UserFacingError):
            self.store.set_mailbox(OWN, "google")  # not confirmed yet
        self.store.decide("google", "confirmed")
        with self.assertRaises(UserFacingError):
            self.store.set_mailbox("stranger@example.invalid", "google")
        self.store.set_mailbox(OWN, "google")
        google = self.account("google")
        self.assertEqual(google["priority"], "critical")
        mailbox = next(r for r in google["priority_reasons"] if r["code"] == "mailbox")
        self.assertEqual((mailbox["addresses"], mailbox["count"]), ([OWN], 3))
        # A later rejection makes the relation inactive instead of deleting it.
        self.store.decide("google", "rejected", "not_mine")
        snapshot = self.store.snapshot()
        self.assertFalse(snapshot["identity_links"]["mailboxes"][0]["active"])
        self.assertNotIn("mailbox", self.codes("google"))
        self.store.set_mailbox(OWN, None)
        self.assertEqual(self.store.snapshot()["identity_links"]["mailboxes"], [])

    def test_single_sign_on_needs_the_method_a_confirmed_provider_and_no_cycle(self):
        self.store.decide("google", "confirmed")
        with self.assertRaises(UserFacingError):
            self.store.link_sign_in("notion", "google")  # notion still uses a password
        self.store.update_account("notion", {"login_method": "sso"})
        for provider in ("spotify", "notion", "missing"):
            with self.subTest(provider=provider), self.assertRaises(UserFacingError):
                self.store.link_sign_in("notion", provider)
        self.store.link_sign_in("notion", "google")
        self.assertEqual(self.account("notion")["signs_in_with"], "google")
        self.assertEqual((self.account("google")["priority"], self.account("google")["dependents"]), ("critical", 1))
        self.assertIn("signs_in_with", self.codes("notion"))
        # Google cannot sign in with Notion while Notion signs in with Google.
        self.store.decide("notion", "confirmed")
        self.store.update_account("google", {"login_method": "sso"})
        with self.assertRaises(UserFacingError):
            self.store.link_sign_in("google", "notion")
        self.store.link_sign_in("notion", None)
        self.assertIsNone(self.account("notion")["signs_in_with"])

    def test_identity_accounts_lead_the_suggestions_with_reasons(self):
        self.store.decide("github", "confirmed")
        self.store.update_account("spotify", {"login_method": "sso"})
        self.store.link_sign_in("spotify", "github")
        workflow = self.store.snapshot()["workflow"]
        self.assertEqual(workflow["priority_preview"][0], "github")
        self.assertEqual(workflow["suggestion_reasons"]["github"][:2], ["sso_provider", "confirmed"])
        self.assertIn("probable", workflow["suggestion_reasons"]["spotify"])

    def test_moving_a_worklist_task_swaps_two_places_and_can_be_undone(self):
        change_worklist(self.store, {"action": "add", "ids": ["google", "notion", "spotify"]})
        result = change_worklist(self.store, {"action": "move", "id": "spotify", "direction": "up"})
        order = [item["id"] for item in self.store.snapshot()["workflow"]["items"]]
        self.assertEqual(order, ["google", "spotify", "notion"])
        self.assertEqual(change_worklist(self.store, {"action": "move", "id": "google", "direction": "up"})["batch"], None)
        self.store.undo(result["batch"])
        self.assertEqual([item["id"] for item in self.store.snapshot()["workflow"]["items"]], ["google", "notion", "spotify"])
        for bad in ({"action": "move", "id": "spotify", "direction": "sideways"},
                    {"action": "move", "id": "github", "direction": "up"},
                    {"action": "move", "id": "spotify"}):
            with self.subTest(bad=bad), self.assertRaises(UserFacingError):
                change_worklist(self.store, bad)

    def test_cli_and_api_are_strictly_shaped(self):
        self.store.decide("google", "confirmed")
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            base = ["--language", "en", "--data-dir", str(self.profile)]
            self.assertEqual(main([*base, "mailbox", OWN, "google"]), 0)
            self.assertEqual(main([*base, "mailbox", OWN, "--remove"]), 0)
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

        self.assertEqual(post("/api/profile/mailboxes", {"address": OWN, "account_id": "google"})[0], 200)
        self.assertEqual(post("/api/profile/mailboxes", {"address": OWN})[0], 400)
        self.store.update_account("notion", {"login_method": "sso"})
        self.assertEqual(post("/api/accounts/notion/sign-in-with", {"account_id": "google"})[0], 200)
        self.assertEqual(post("/api/accounts/notion/sign-in-with", {"account_id": "google", "x": 1})[0], 400)
        self.assertEqual(post("/api/accounts/notion/sign-in-with", {"account_id": None})[0], 200)


if __name__ == "__main__":
    unittest.main()
