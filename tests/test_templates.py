# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A22 and P4: declarative task templates with a preview and one undoable change."""
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

OWN = "owner@example.invalid"
VALID = {"name": "Streaming check", "categories": ["Streaming"], "min_priority": "normal", "confirmed_only": False,
         "worklist": True, "review_steps": ["password", "mfa_recovery"], "review_days": 30}


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [created(sender) for sender in
                                   ("noreply@paypal.com", "noreply@spotify.com", "noreply@netflix.com", "noreply@github.com")])
        self.store.decide("paypal", "confirmed")

    def account(self, account_id):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == account_id)

    def test_a_builtin_template_previews_then_applies_as_one_undoable_change(self):
        templates = {t["id"]: t for t in self.store.snapshot()["templates"]}
        self.assertTrue(templates["finance-recovery"]["builtin"])
        self.assertEqual(templates["finance-recovery"]["matches"], 1)
        _, plan = self.store.template_plan("finance-recovery")
        self.assertEqual((plan["accounts"], plan["worklist_additions"], plan["review_steps"]),
                         (["paypal"], ["paypal"], ["mfa_recovery"]))
        result = self.store.apply_template("finance-recovery")
        self.assertEqual(result["accounts"], 1)
        self.assertEqual(self.account("paypal")["steps"]["mfa_recovery"]["review_after"], plan["review_date"])
        self.assertEqual([item["id"] for item in self.store.snapshot()["workflow"]["items"]], ["paypal"])
        self.store.undo(result["batch"])
        self.assertIsNone(self.account("paypal")["steps"]["mfa_recovery"]["review_after"])
        self.assertEqual(self.store.snapshot()["workflow"]["items"], [])
        self.store.decide("paypal", "rejected", "not_mine")
        with self.assertRaises(UserFacingError):
            self.store.apply_template("finance-recovery")

    def test_own_templates_are_validated_saved_and_skip_steps_that_do_not_apply(self):
        cases = {"fields": {**VALID, "script": "x"}, "name": {**VALID, "name": " "}, "category": {**VALID, "categories": ["Spyware"]},
                 "priority": {**VALID, "min_priority": "urgent"}, "step": {**VALID, "review_steps": ["format_disk"]},
                 "days": {**VALID, "review_days": 3}, "nothing": {**VALID, "worklist": False, "review_steps": [], "review_days": None}}
        for case, data in cases.items():
            with self.subTest(case=case), self.assertRaises(UserFacingError):
                self.store.save_template(data)
        ident = self.store.save_template(dict(VALID))["id"]
        self.assertEqual(ident, "mine-streaming-check")
        self.store.update_account("spotify", {"login_method": "sso"})
        self.store.apply_template(ident)
        spotify, netflix = self.account("spotify"), self.account("netflix")
        self.assertIsNone(spotify["steps"]["password"]["review_after"])
        self.assertIsNotNone(spotify["steps"]["mfa_recovery"]["review_after"])
        self.assertIsNotNone(netflix["steps"]["password"]["review_after"])
        with self.assertRaises(UserFacingError):
            self.store.delete_template("yearly-important")
        self.store.delete_template(ident)
        self.assertNotIn(ident, {t["id"] for t in self.store.snapshot()["templates"]})

    def test_cli_and_api(self):
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            base = ["--language", "en", "--data-dir", str(self.profile), "template"]
            self.assertEqual(main([*base, "preview", "finance-recovery"]), 0)
            self.assertEqual(main([*base, "apply"]), 2)
        self.assertEqual(json.loads(out.getvalue())["accounts"], ["paypal"])
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

        self.assertEqual(post("/api/templates", VALID)[0], 200)
        self.assertEqual(post("/api/templates/preview", {"id": "missing"})[0], 400)
        self.assertEqual(post("/api/templates/apply", {"id": "finance-recovery", "x": 1})[0], 400)
        status, body = post("/api/templates/apply", {"id": "finance-recovery"})
        self.assertEqual((status, body["accounts"]), (200, 1))


if __name__ == "__main__":
    unittest.main()
