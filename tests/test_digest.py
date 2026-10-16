# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A1-A4, A7, A28: what changed since the last review, unclear first, one summary."""
from contextlib import closing, redirect_stderr, redirect_stdout
import http.client
from io import StringIO
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import ScanSession, scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN, WORK = "owner@example.invalid", "work@example.invalid"


def mail(sender, subject="Your account has been created", recipient=OWN, **options):
    return synthetic_mail(sender, subject, "", recipient=recipient, **options)


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN, WORK])

    def changes(self):
        return self.store.snapshot()["changes"]

    def groups(self):
        return [(g["kind"], g["account_id"] or g["domain"], g["attention"]) for g in self.changes()["groups"]]

    def test_new_clues_are_shown_once_and_identical_reimports_stay_quiet(self):
        messages = [mail("noreply@github.com"), mail("no-reply@dropbox.com")]
        scan_messages(self.store, messages)
        changes = self.changes()
        self.assertEqual((changes["new"], changes["changed"], changes["since"]), (2, 0, None))
        self.assertEqual({g["account_id"] for g in changes["groups"]}, {"github", "dropbox"})
        self.store.acknowledge_changes(changes["revision"])
        self.assertEqual((self.changes()["new"], self.changes()["groups"]), (0, []))
        self.assertIsNotNone(self.changes()["since"])
        # A2: the same messages again are duplicates and bring nothing back.
        self.assertEqual(scan_messages(self.store, messages)["duplicates"], 2)
        self.assertEqual(self.changes()["groups"], [])
        scan_messages(self.store, [mail("noreply@spotify.com")])
        self.assertEqual([g["account_id"] for g in self.changes()["groups"]], ["spotify"])

    def test_a_changed_rating_counts_as_changed_not_new(self):
        raw = mail("noreply@github.com")
        scan_messages(self.store, [raw])
        self.store.acknowledge_changes(self.changes()["revision"])
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE evidence SET signal='welcome_account', score=70")
        scan_messages(self.store, [raw])
        changes = self.changes()
        self.assertEqual((changes["new"], changes["changed"]), (0, 1))
        self.assertEqual(changes["groups"][0]["signals"], ["account_created"])

    def test_unclear_groups_come_first_and_other_clues_are_only_counted(self):
        scan_messages(self.store, [
            mail("noreply@github.com"),
            mail("hello@new-service.example"),
            mail("noreply@dropbox.com", recipient=f"{OWN}, {WORK}"),
            mail("news@spotify.com", "Our spring sale", newsletter=True),
            mail("orders@zalando.de", "Deine Bestellung"),
            mail("noreply@netflix.com", "Reset your password"),
        ])
        self.assertEqual(self.groups(), [("unassigned", "dropbox", "unassigned"),
                                         ("domain", "new-service.example", "domain"),
                                         ("account", "github", None)])
        changes = self.changes()
        self.assertEqual(changes["other"], {"marketing": 1, "order": 1, "reset": 1})
        self.assertEqual(changes["attention"], 2)

    def test_reviewing_changes_never_touches_decisions_and_can_be_undone(self):
        scan_messages(self.store, [mail("noreply@github.com")])
        self.store.decide("github", "confirmed")
        history = len(self.store.recent_changes())
        revision = self.changes()["revision"]
        self.store.acknowledge_changes(revision)
        account = next(a for a in self.store.snapshot()["accounts"] if a["id"] == "github")
        self.assertEqual((account["decision"], len(self.store.recent_changes())), ("confirmed", history))
        for stale in (revision + 1, 0, -1, "1", None, True):
            with self.subTest(revision=stale), self.assertRaises(UserFacingError):
                self.store.acknowledge_changes(stale)
        self.store.undo_acknowledge_changes()
        self.assertEqual((self.changes()["new"], self.changes()["since"]), (1, None))
        with self.assertRaises(UserFacingError):
            self.store.undo_acknowledge_changes()

    def test_clues_arriving_after_the_page_was_loaded_stay_new(self):
        scan_messages(self.store, [mail("noreply@github.com")])
        seen = self.changes()["revision"]
        scan_messages(self.store, [mail("noreply@dropbox.com")])
        self.store.acknowledge_changes(seen)
        self.assertEqual([g["account_id"] for g in self.changes()["groups"]], ["dropbox"])

    def test_import_gaps_stay_visible_until_reviewed(self):
        session = ScanSession(self.store, "eml")
        session.skip(2)
        session.finish()
        changes = self.changes()
        self.assertEqual((changes["new"], changes["gaps"]["result"], changes["gaps"]["skipped"]),
                         (0, "completed_with_gaps", 2))
        summary = self.store.snapshot()["return_summary"]
        self.assertEqual(summary["items"][0]["kind"], "scan_gaps")
        # Gaps alone can be marked as reviewed; the import result keeps them.
        self.store.acknowledge_changes(changes["revision"])
        self.assertIsNone(self.changes()["gaps"])
        self.assertEqual(self.store.snapshot()["result"]["gaps"]["skipped"], 2)

    def test_return_summary_puts_problems_first(self):
        scan_messages(self.store, [mail("noreply@github.com"), mail("hello@new-service.example")])
        kinds = [item["kind"] for item in self.store.snapshot()["return_summary"]["items"]]
        self.assertEqual(kinds, ["decide_first", "changes"])
        self.store.acknowledge_changes(self.changes()["revision"])
        self.assertEqual(self.store.snapshot()["return_summary"]["items"], [])

    def test_profiles_from_before_revisions_start_without_old_changes(self):
        scan_messages(self.store, [mail("noreply@github.com")])
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE evidence SET created_rev=0, changed_rev=0")
            db.execute("DELETE FROM meta WHERE key IN ('revision','changes_seen')")
        self.assertEqual(self.changes()["groups"], [])

    def test_cli_shows_and_marks_changes(self):
        scan_messages(self.store, [mail("noreply@github.com")])
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            base = ["--language", "de", "--data-dir", str(self.profile), "whats-new"]
            self.assertEqual(main([*base, "--mark-reviewed"]), 0)
        self.assertEqual(json.loads(out.getvalue())["changes"]["groups"][0]["account_id"], "github")
        self.assertIn("Als gesehen markiert", err.getvalue())
        self.assertEqual(self.changes()["groups"], [])

    def test_api_routes_are_strictly_shaped(self):
        scan_messages(self.store, [mail("noreply@github.com")])
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

        revision = self.changes()["revision"]
        self.assertEqual(post("/api/digest/seen", {"revision": revision, "extra": 1})[0], 400)
        self.assertEqual(post("/api/digest/seen", {"revision": revision})[0], 200)
        self.assertEqual(post("/api/digest/seen/undo", {"x": 1})[0], 400)
        self.assertEqual(post("/api/digest/seen/undo", {})[0], 200)
        status, body = post("/api/digest/seen", {"revision": revision + 5})
        self.assertEqual((status, body["error"]), (400, "These changes are no longer current; reload the page"))


if __name__ == "__main__":
    unittest.main()
