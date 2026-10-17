# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan P1, P2 and P5: separate profiles, a minimal history of counts and data-minimal reports."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
import http.client
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from argus_security import history
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.profiles import profile_dir
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class ProfileHistoryReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        redirect = patch("argus_security.cli.data_root", return_value=self.root)
        redirect.start()
        self.addCleanup(redirect.stop)

    def cli(self, *arguments):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--language", "en", *arguments])
        return code, out.getvalue(), err.getvalue()

    def test_named_profiles_are_separate_folders_and_never_read_each_other(self):
        self.assertEqual(self.cli("--profile", "work", "init", "--email", OWN)[0], 0)
        self.assertEqual(self.cli("init", "--email", "private@example.invalid")[0], 0)
        work = Store(profile_dir(self.root, "work"), Registry())
        scan_messages(work, [created("noreply@github.com")])
        self.assertEqual(work.snapshot()["profile_name"], "work")
        default = Store(self.root / "argus", Registry())
        self.assertEqual((default.snapshot()["summary"]["clues"], default.snapshot()["profile_name"]), (0, None))
        self.assertEqual(json.loads(self.cli("profiles")[1]), ["default", "work"])
        for name in ("Work", "../work", "", "-work", "a" * 41):
            with self.subTest(name=name), self.assertRaises(UserFacingError):
                profile_dir(self.root, name)
        code, _, err = self.cli("--profile", "work", "--data-dir", str(self.root / "x"), "report")
        self.assertEqual(code, 2)
        self.assertIn("Choose either --profile or --data-dir", err)

    def test_history_keeps_daily_counts_and_compares_them(self):
        store = Store(self.root / "profile", Registry())
        store.configure([OWN])
        scan_messages(store, [created("noreply@github.com"), created("noreply@dropbox.com")])
        today = date.today()
        with store.connect() as db:
            old = dict(store.snapshot()["history"]["today"], clues=0, found=0)
            db.execute("INSERT INTO history(day,counts) VALUES (?,?)", ((today - timedelta(days=31)).isoformat(), json.dumps(old)))
            db.execute("INSERT INTO history(day,counts) VALUES (?,?)", ((today - timedelta(days=500)).isoformat(), json.dumps(old)))
        snapshot = store.snapshot()
        self.assertEqual(snapshot["history"]["today"]["clues"], 2)
        month = next(c for c in snapshot["history"]["comparisons"] if c["days"] == 30)
        self.assertEqual((month["delta"]["clues"], month["delta"]["found"]), (2, 2))
        with store.connect() as db:
            history.record(db, snapshot["history"]["today"], today + timedelta(days=1))
            days = [row[0] for row in db.execute("SELECT day FROM history ORDER BY day")]
            columns = [row["name"] for row in db.execute("PRAGMA table_info(history)")]
        self.assertNotIn((today - timedelta(days=500)).isoformat(), days)
        self.assertEqual(columns, ["day", "counts"])

    def test_reports_leave_out_sensitive_fields_unless_asked(self):
        profile = self.root / "profile"
        store = Store(profile, Registry())
        store.configure([OWN])
        scan_messages(store, [created("noreply@github.com")])
        numbers = store.report_text("numbers", language="de")
        self.assertIn("ARGUS-Fortschrittsbericht", numbers)
        self.assertNotIn("GitHub", numbers)
        tasks = store.report_text("tasks")
        github = next(line for line in tasks.splitlines() if line.startswith("- GitHub: "))
        self.assertIn("Not decided; Not started; next: Decide whether this account is yours", github)
        self.assertNotIn("@", tasks)
        self.assertIn(OWN, store.report_text("tasks", include_addresses=True))
        for level, addresses in (("all", False), ("numbers", True), ("tasks", "yes")):
            with self.subTest(level=level), self.assertRaises(UserFacingError):
                store.report_text(level, addresses)
        path = self.root / "report.txt"
        code, _, err = self.cli("--data-dir", str(profile), "report", "--level", "tasks", "--export", str(path))
        self.assertEqual(code, 0)
        self.assertIn("GitHub", path.read_text(encoding="utf-8"))
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.cli("--data-dir", str(profile), "report", "--export", str(path))[0], 2)
        server = DashboardServer(store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def get(path):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request("GET", path, headers={"Authorization": "Bearer " + server.token})
            response = connection.getresponse()
            return response.status, json.loads(response.read())

        status, body = get("/api/report?level=tasks&addresses=1&language=en")
        self.assertEqual(status, 200)
        self.assertIn(OWN, body["text"])
        self.assertEqual(get("/api/report?level=numbers&addresses=1")[0], 400)


if __name__ == "__main__":
    unittest.main()
