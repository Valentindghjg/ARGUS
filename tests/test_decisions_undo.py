# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""ADR-0001 actions: confirm or reject with a reason, dated steps, review dates and undo."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from argus_security import handoffs
from argus_security.bitwarden import make_export
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store
from argus_security.workflow import change_worklist

OWN = "owner@example.invalid"


class DecisionAndUndoTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                   for sender in ("noreply@github.com", "support@discord.com")])

    def account(self, ident="github"):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == ident)

    def test_rejecting_hides_the_account_everywhere_and_one_undo_restores_it(self):
        change_worklist(self.store, {"action": "add", "ids": ["github", "discord"]})
        result = self.store.decide("github", "rejected", "not_mine")
        account = self.account()
        self.assertEqual((account["decision"], account["decision_reason"]), ("rejected", "not_mine"))
        self.assertEqual(account["classification"], "unknown")
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["summary"]["rejected"], 1)
        self.assertEqual(snapshot["summary"]["found"], 1)
        self.assertNotIn("github", [item["id"] for item in snapshot["workflow"]["items"]])
        self.assertNotIn("github", snapshot["workflow"]["priority_preview"])
        # Evidence is never touched by a decision.
        self.assertEqual(account["evidence_count"], 1)
        self.store.undo(result["batch"])
        snapshot = self.store.snapshot()
        self.assertEqual(self.account()["decision"], "undecided")
        self.assertEqual([item["id"] for item in snapshot["workflow"]["items"]], ["github", "discord"])

    def test_decisions_are_validated(self):
        for decision, reason in [("rejected", None), ("rejected", "spam"), ("confirmed", "not_mine"), ("maybe", None)]:
            with self.subTest(decision=decision, reason=reason), self.assertRaises(UserFacingError):
                self.store.decide("github", decision, reason)
        with self.assertRaises(UserFacingError):
            self.store.decide("not-a-provider", "confirmed")
        self.assertEqual(self.store.decide("github", "undecided"), {"ok": True, "batch": None})

    def test_new_strong_evidence_after_a_rejection_only_raises_a_hint(self):
        self.store.decide("github", "rejected", "not_an_account")
        self.assertFalse(self.account()["reconsider"])
        scan_messages(self.store, [synthetic_mail("security@github.com", "New sign-in to your account", "", recipient=OWN)])
        account = self.account()
        self.assertTrue(account["reconsider"])
        self.assertEqual(account["decision"], "rejected")

    def test_steps_are_dated_and_validated(self):
        self.store.decide("github", "confirmed")
        self.store.set_step("github", "identity", state="done")
        self.assertTrue(self.account()["steps"]["identity"]["done_at"])
        for step, state in [("vault", "prepared"), ("vault", "not_applicable"), ("identity", "not_applicable"),
                            ("password", "not_applicable"), ("nonsense", "done"), ("vault", "finished")]:
            with self.subTest(step=step, state=state), self.assertRaises(UserFacingError):
                self.store.set_step("github", step, state=state)
        self.store.update_account("github", {"login_method": "sso"})
        with self.assertRaises(UserFacingError):
            self.store.set_step("github", "password", state="open")
        for step in ("vault", "signin_test"):
            self.store.set_step("github", step, state="done")
        self.store.set_step("github", "mfa_recovery", state="not_applicable")
        account = self.account()
        self.assertEqual(account["progress"], "complete")
        self.assertEqual(account["status"], "done")

    def test_review_dates_become_due_locally(self):
        today = datetime.now(timezone.utc).date()
        for value in ["2020-01-01", today.isoformat(), (today + timedelta(days=6 * 366)).isoformat(), "soon", 5]:
            with self.subTest(value=value), self.assertRaises(UserFacingError):
                self.store.set_step("github", "mfa_recovery", review_after=value)
        due = (today + timedelta(days=30)).isoformat()
        self.store.set_step("github", "mfa_recovery", review_after=due)
        self.assertEqual(self.account()["steps"]["mfa_recovery"]["review_after"], due)
        self.assertEqual(self.account()["reviews_due"], [])
        later = datetime.now(timezone.utc) + timedelta(days=31)
        with patch("argus_security.workflow.utcnow", return_value=later):
            self.assertEqual(self.account()["reviews_due"], ["mfa_recovery"])
        self.store.set_step("github", "mfa_recovery", review_after=None)
        self.assertIsNone(self.account()["steps"]["mfa_recovery"]["review_after"])

    def test_undo_walks_back_in_order_and_never_overwrites_a_later_change(self):
        first = self.store.decide("github", "confirmed")["batch"]
        self.store.set_step("github", "identity", state="done")
        self.store.set_step("github", "vault", state="done")
        self.store.undo()
        self.assertEqual(self.account()["steps"]["vault"]["state"], "open")
        self.store.undo()
        self.assertEqual(self.account()["steps"]["identity"]["state"], "open")
        # The decision changed again later: undoing the first batch would hide that.
        self.store.decide("github", "rejected", "closed")
        with self.assertRaises(UserFacingError):
            self.store.undo(first)
        undone = self.store.undo()
        self.assertEqual(self.account()["decision"], "confirmed")
        # Undoing the undo restores the change again.
        self.store.undo(undone["batch"])
        self.assertEqual(self.account()["decision"], "rejected")

    def test_worklist_planning_is_undoable(self):
        change_worklist(self.store, {"action": "add", "ids": ["github"]})
        change_worklist(self.store, {"action": "snooze", "id": "github", "days": 7})
        self.assertTrue(self.store.snapshot()["workflow"]["items"][0]["deferred"])
        self.store.undo()
        self.assertFalse(self.store.snapshot()["workflow"]["items"][0]["deferred"])
        self.store.undo()
        self.assertEqual(self.store.snapshot()["workflow"]["items"], [])
        with self.assertRaises(UserFacingError):
            self.store.undo()

    def test_undo_never_reverses_an_external_effect(self):
        attempt = handoffs.reserve(self.store, "github", OWN)
        handoffs.finish(self.store, attempt, "created", "33333333-3333-4333-8333-333333333333")
        self.assertEqual(self.account()["steps"]["vault"]["state"], "prepared")
        self.store.undo()
        self.assertEqual(self.account()["steps"]["vault"]["state"], "open")
        # The journal still knows the item exists: no second item is offered.
        self.assertEqual(handoffs.handoff_snapshot(self.store)[0]["state"], "created")
        exported = make_export(self.store, ["github", "discord"])
        self.assertEqual([item["fields"][0]["value"] for item in exported["items"]], ["discord"])

    def test_history_lists_batches_without_message_content(self):
        self.store.decide("github", "confirmed")
        self.store.set_step("github", "identity", state="done")
        history = self.store.recent_changes()
        self.assertEqual([entry["changes"][0]["field"] for entry in history], ["step:identity", "decision"])
        self.assertNotIn("Your account has been created", json.dumps(history))
        with self.assertRaises(UserFacingError):
            self.store.recent_changes(0)

    def test_cli_changes_and_undo(self):
        self.store.decide("github", "confirmed")
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            self.assertEqual(main(["--language", "en", "--data-dir", str(self.profile), "changes"]), 0)
            self.assertEqual(main(["--language", "en", "--data-dir", str(self.profile), "undo"]), 0)
        self.assertEqual(json.loads(out.getvalue().split("\n]\n")[0] + "\n]")[0]["changes"][0]["field"], "decision")
        self.assertIn("Undid one local change", out.getvalue())
        self.assertEqual(self.account()["decision"], "undecided")


class DecisionApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(Path(self.temporary.name) / "profile", Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail("noreply@github.com", "Your account has been created", "", recipient=OWN)])
        self.server = DashboardServer(self.store, 0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, body=None, method="POST"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.addCleanup(connection.close)
        headers = {"Authorization": "Bearer " + self.server.token, "Content-Type": "application/json"}
        connection.request(method, path, body=None if body is None else json.dumps(body), headers=headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())

    def test_decision_step_undo_and_history_routes(self):
        status, result = self.request("/api/accounts/github/decision", {"decision": "rejected", "reason": "not_mine"})
        self.assertEqual(status, 200)
        self.assertTrue(result["batch"])
        status, body = self.request("/api/changes", method="GET")
        self.assertEqual((status, body["changes"][0]["changes"][0]["field"]), (200, "decision"))
        self.assertEqual(self.request("/api/undo", {"batch": None})[0], 200)
        self.assertEqual(self.request("/api/accounts/github/steps", {"step": "identity", "state": "done"})[0], 200)
        for path, body in [("/api/accounts/github/decision", {"decision": "rejected"}),
                           ("/api/accounts/github/decision", {"decision": "confirmed", "extra": 1}),
                           ("/api/accounts/github/steps", {"step": "vault"}),
                           ("/api/accounts/github/steps", {"step": "vault", "state": "prepared"}),
                           ("/api/accounts/github/steps", {"step": "vault", "secret": "x", "state": "done"}),
                           ("/api/undo", {"batch": 5}), ("/api/undo", {})]:
            with self.subTest(path=path, body=body):
                self.assertEqual(self.request(path, body)[0], 400)
        status, body = self.request("/api/undo", {"batch": "unknown-batch"})
        self.assertEqual((status, body["error"]), (400, "There is no local change to undo"))


if __name__ == "__main__":
    unittest.main()
