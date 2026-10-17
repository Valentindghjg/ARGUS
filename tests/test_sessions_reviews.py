# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A8, A10, A18 and A20: short sessions, a review rule and confirmed export details."""
from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
import http.client
from io import StringIO
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from argus_security.bitwarden import preview_export
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.reviews import add_months
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store
from argus_security.workflow import change_worklist

OWN = "owner@example.invalid"
STEPS = ("identity", "vault", "password", "signin_test", "mfa_recovery")


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class SessionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [created(sender) for sender in
                                   ("noreply@github.com", "noreply@paypal.com", "noreply@spotify.com", "noreply@notion.so")])

    def account(self, account_id):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == account_id)

    def complete(self, account_id):
        self.store.decide(account_id, "confirmed")
        for step in STEPS:
            self.store.set_step(account_id, step, state="done")

    def test_review_rule_only_proposes_and_applying_is_one_undoable_change(self):
        self.complete("paypal")
        self.complete("spotify")
        self.assertIsNone(self.account("paypal")["review_proposal"])
        for months, scope in ((3, "all"), (12, "everything"), (True, "all"), (12.0, "all")):
            with self.subTest(months=months, scope=scope), self.assertRaises(UserFacingError):
                self.store.set_review_rule(months, scope)
        self.store.set_review_rule(12, "important")
        paypal, spotify = self.account("paypal"), self.account("spotify")
        expected = add_months(datetime.fromisoformat(paypal["completed_at"]).date(), 12).isoformat()
        self.assertEqual(paypal["review_proposal"], expected)
        self.assertEqual(paypal["steps"]["identity"]["review_after"], None)
        # Spotify has normal priority, so the "important" scope leaves it out.
        self.assertEqual((spotify["priority"], spotify["review_proposal"]), ("normal", None))
        result = self.store.apply_review_proposals(["paypal"])
        self.assertEqual((self.account("paypal")["steps"]["identity"]["review_after"],
                          self.account("paypal")["review_proposal"]), (expected, None))
        with self.assertRaises(UserFacingError):
            self.store.apply_review_proposals(["paypal"])
        self.store.undo(result["batch"])
        self.assertEqual(self.account("paypal")["review_proposal"], expected)
        self.store.set_review_rule(None)
        self.assertIsNone(self.account("paypal")["review_proposal"])

    def test_a_long_completed_account_gets_tomorrow_never_a_past_date(self):
        self.complete("paypal")
        old = (datetime.now(timezone.utc) - timedelta(days=800)).isoformat()
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE account_steps SET done_at=? WHERE account_id='paypal'", (old,))
        self.store.set_review_rule(6, "all")
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        self.assertEqual(self.account("paypal")["review_proposal"], tomorrow)
        self.assertEqual(add_months(date(2026, 8, 31), 6), date(2027, 2, 28))

    def test_a_session_takes_ready_tasks_and_reports_only_what_was_recorded(self):
        with self.assertRaises(UserFacingError):
            self.store.start_session(3)
        change_worklist(self.store, {"action": "add", "ids": ["github", "paypal", "spotify", "notion"]})
        change_worklist(self.store, {"action": "defer", "id": "paypal"})
        for size in (2, 0, "3", True):
            with self.subTest(size=size), self.assertRaises(UserFacingError):
                self.store.start_session(size)
        session = self.store.start_session(3)["session"]
        self.assertEqual(session["accounts"], ["github", "spotify", "notion"])
        self.store.decide("github", "confirmed")
        self.store.set_step("github", "identity", state="done")
        report = self.store.snapshot()["session"]
        github = report["accounts"][0]
        self.assertEqual((github["decided"], github["done"], report["steps_done"], report["finished"]),
                         (True, ["identity"], 1, 0))
        text = self.store.session_report_text("de")
        self.assertIn("ARGUS-Sitzungsbericht", text)
        self.assertIn("GitHub: erledigt: Von dir bestätigt, Anmeldung geprüft", text)
        self.assertNotIn("@", text)
        self.store.end_session()
        self.assertIsNone(self.store.snapshot()["session"])
        with self.assertRaises(UserFacingError):
            self.store.end_session()

    def test_export_notes_add_only_confirmed_details(self):
        self.store.decide("github", "confirmed")
        self.store.update_account("notion", {"login_method": "sso"})
        self.store.link_sign_in("notion", "github")
        self.store.decide("notion", "confirmed")
        items = {item["account_id"]: item for item in preview_export(self.store, ["notion", "spotify"], "en")["items"]}
        self.assertIn("Sign-in method: Single sign-on\nSigns in with: GitHub", items["notion"]["notes"])
        self.assertNotIn("Sign-in method", items["spotify"]["notes"])
        self.assertNotIn("Signs in with", items["spotify"]["notes"])

    def test_cli_and_api(self):
        self.complete("paypal")
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            base = ["--language", "en", "--data-dir", str(self.profile)]
            self.assertEqual(main([*base, "review-rule", "--months", "6", "--scope", "all", "--apply"]), 0)
        self.assertTrue(json.loads(out.getvalue())["applied"])
        self.assertIsNotNone(self.account("paypal")["steps"]["identity"]["review_after"])
        change_worklist(self.store, {"action": "add", "ids": ["github"]})
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            self.assertEqual(main([*base, "session", "start", "--size", "1"]), 0)
            self.assertEqual(main([*base, "session", "end"]), 0)
        self.assertIn("Finished accounts: 0 of 1", out.getvalue())
        server = DashboardServer(self.store, 0)
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

        self.assertEqual(call("GET", "/api/session/report")[0], 400)
        self.assertEqual(call("POST", "/api/session", {"action": "start", "size": 1})[0], 200)
        status, body = call("GET", "/api/session/report?language=de")
        self.assertEqual((status, body["text"].splitlines()[0]), (200, "ARGUS-Sitzungsbericht"))
        self.assertEqual(call("GET", "/api/session/report?language=fr")[0], 400)
        self.assertEqual(call("POST", "/api/session", {"action": "end", "x": 1})[0], 400)
        self.assertEqual(call("POST", "/api/session", {"action": "end"})[0], 200)
        self.assertEqual(call("POST", "/api/review-rule", {"months": 12})[0], 400)
        self.assertEqual(call("POST", "/api/review-rule", {"months": None, "scope": None})[0], 200)
        self.assertEqual(call("POST", "/api/review-rule/apply", {"ids": ["github"]})[0], 400)


if __name__ == "__main__":
    unittest.main()
