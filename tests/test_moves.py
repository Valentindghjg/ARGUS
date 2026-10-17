# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A21 and P4: an ordered, manual plan for moving accounts to another own address."""
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

OLD, NEW = "old@example.invalid", "new@example.invalid"


def created(sender, recipient=OLD):
    return synthetic_mail(sender, "Your account has been created", "", recipient=recipient)


class MovePlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OLD, NEW])
        scan_messages(self.store, [created("noreply@spotify.com"), created("noreply@google.com"),
                                   created("noreply@paypal.com"), created("noreply@github.com", NEW)])
        self.store.decide("google", "confirmed")
        self.store.set_mailbox(OLD, "google")

    def plan(self):
        return self.store.snapshot()["move_plans"][0]

    def test_a_plan_orders_the_accounts_of_the_old_address_and_notes_the_relation(self):
        # The same address, a foreign address, or an address without accounts cannot be planned.
        for old, new in ((OLD, OLD), (OLD, "stranger@example.invalid"), ("stranger@example.invalid", NEW)):
            with self.subTest(old=old, new=new), self.assertRaises(UserFacingError):
                self.store.create_move_plan(old, new)
        self.store.create_move_plan(OLD, NEW)
        plan = self.plan()
        order = [item["account_id"] for item in plan["items"]]
        # The mailbox account comes first; the account at the new address is not part of the plan.
        self.assertEqual(order[0], "google")
        self.assertEqual(set(order), {"google", "spotify", "paypal"})
        self.assertEqual(self.store.snapshot()["relations"][0]["kind"], "replaced_by")
        with self.assertRaises(UserFacingError):
            self.store.create_move_plan(OLD, NEW)

    def test_marking_items_never_changes_an_account(self):
        self.store.create_move_plan(OLD, NEW)
        plan_id = self.plan()["id"]
        self.store.mark_move(plan_id, "google", "changed")
        self.store.mark_move(plan_id, "spotify", "skipped")
        self.assertEqual(self.plan()["done"], 2)
        self.store.mark_move(plan_id, "spotify", "open")
        self.assertEqual(self.plan()["done"], 1)
        google = next(a for a in self.store.snapshot()["accounts"] if a["id"] == "google")
        self.assertEqual(google["identity_email"], OLD)
        for account_id, state in (("github", "changed"), ("google", "done")):
            with self.subTest(account_id=account_id), self.assertRaises(UserFacingError):
                self.store.mark_move(plan_id, account_id, state)
        self.store.close_move_plan(plan_id)
        with self.assertRaises(UserFacingError):
            self.store.mark_move(plan_id, "google", "open")
        # A closed plan allows a new one for the same address.
        self.store.create_move_plan(OLD, NEW)

    def test_cli_and_api(self):
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            base = ["--language", "en", "--data-dir", str(self.profile), "move-address"]
            self.assertEqual(main([*base, "create", OLD]), 2)
            self.assertEqual(main([*base, "create", OLD, NEW]), 0)
        plan = json.loads(out.getvalue())[0]
        self.assertEqual(plan["items"][0]["account_id"], "google")
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

        self.assertEqual(post("/api/moves/item", {"plan_id": plan["id"], "account_id": "google"})[0], 400)
        self.assertEqual(post("/api/moves/item", {"plan_id": plan["id"], "account_id": "google", "state": "changed"})[0], 200)
        self.assertEqual(post("/api/moves/close", {"plan_id": plan["id"]})[0], 200)
        self.assertEqual(post("/api/moves/close", {"plan_id": plan["id"]})[0], 400)


if __name__ == "__main__":
    unittest.main()
