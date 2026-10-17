# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: the local API behind the dashboard."""
from contextlib import closing
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


class ReviewDashboardTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / "profile", Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                   for sender in ("noreply@github.com", "support@discord.com")])
        self.server = DashboardServer(self.store, 0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, method="GET", body=None):
        headers = {"Authorization": "Bearer " + self.server.token, "Content-Type": "application/json"}
        with closing(http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)) as connection:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read() or b"null")

    def test_apply_refuses_when_the_template_covers_other_accounts_than_its_preview(self):
        self.store.save_template({"name": "All found", "categories": [], "min_priority": "normal",
                                  "confirmed_only": False, "worklist": True, "review_steps": [], "review_days": None})
        ident = next(t["id"] for t in self.store.snapshot()["templates"] if not t["builtin"])
        _, plan = self.request("/api/templates/preview", "POST", json.dumps({"id": ident}))
        self.store.decide("discord", "rejected", "not_mine")
        status, body = self.request("/api/templates/apply", "POST", json.dumps({"id": ident, "accounts": plan["accounts"]}))
        self.assertEqual((status, body["error"]), (400, "This template now covers other accounts; preview it again"))
        status, _ = self.request("/api/templates/apply", "POST", json.dumps({"id": ident, "accounts": ["github"]}))
        self.assertEqual(status, 200)

    def test_marking_the_same_changes_twice_keeps_the_undo_point(self):
        revision = self.store.snapshot()["changes"]["revision"]
        for _ in range(2):
            self.assertEqual(self.request("/api/digest/seen", "POST", json.dumps({"revision": revision}))[0], 200)
        self.request("/api/digest/seen/undo", "POST", "{}")
        self.assertEqual(self.store.snapshot()["changes"]["new"], 2)

    def test_a_busy_database_and_deeply_nested_json_get_clean_answers(self):
        with patch.object(Store, "snapshot", side_effect=sqlite3.OperationalError("database is locked")):
            status, body = self.request("/api/accounts")
        self.assertEqual((status, body["error"]), (503, "The local database is temporarily unavailable"))
        status, _ = self.request("/api/undo", "POST", "[" * 20000)
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
