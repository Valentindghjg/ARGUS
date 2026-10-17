# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A24, A25, A27 and D5: one job model, a global pause and a minimal activity log."""
from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import http.client
from io import StringIO
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from argus_security import jobs
from argus_security.background import BackgroundScanService, KeyringCredentialStore
from argus_security.bitwarden import add_to_unlocked_cli
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.imap_client import IMAPConfig
from argus_security.registry import Registry
from argus_security.scan import ScanSession, scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class FakeKeyring:
    def __init__(self):
        self.entries = {}

    def set_password(self, service, account, secret):
        self.entries[(service, account)] = secret

    def get_password(self, service, account):
        return self.entries.get((service, account))

    def delete_password(self, service, account):
        del self.entries[(service, account)]


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])

    def control(self):
        return self.store.control_overview()

    def test_every_scan_is_a_job_with_counts_and_one_activity_entry(self):
        scan_messages(self.store, [created("noreply@github.com"), b""])
        job = self.control()["jobs"][0]
        self.assertEqual((job["kind"], job["source"], job["state"]), ("import", "eml", "completed_with_gaps"))
        self.assertEqual((job["counts"]["processed"], job["counts"]["evidence"], job["counts"]["skipped"]), (2, 1, 1))
        entry = self.control()["activity"][0]
        self.assertEqual((entry["event"], entry["kind"], entry["outcome"]), ("job_finished", "import", "completed_with_gaps"))
        # Only codes and integer counts are kept.
        self.assertTrue(all(type(value) is int for value in entry["counts"].values()))

    def test_failures_and_interruptions_have_their_own_state(self):
        def broken():
            yield created("noreply@github.com")
            raise OSError("disk gone")
        with self.assertRaises(OSError):
            scan_messages(self.store, broken())
        self.assertEqual(self.control()["jobs"][0]["state"], "failed")

        def stopped():
            yield created("noreply@github.com")
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            scan_messages(self.store, stopped())
        self.assertEqual(self.control()["jobs"][0]["state"], "cancelled")
        session = ScanSession(self.store, "imap")
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE jobs SET updated_at=? WHERE id=?",
                       ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(), session.stats["id"]))
        self.assertEqual((self.control()["jobs"][0]["kind"], self.control()["jobs"][0]["state"]), ("imap_scan", "interrupted"))

    def test_the_pause_blocks_new_jobs_and_stops_running_ones_between_messages(self):
        self.store.set_automation_paused(True)
        self.assertIsNotNone(self.store.snapshot()["automation_paused"])
        self.assertEqual(self.store.snapshot()["return_summary"]["items"][0]["kind"], "paused")
        with self.assertRaises(UserFacingError):
            scan_messages(self.store, [created("noreply@github.com")])
        self.store.set_automation_paused(False)

        def messages():
            for index, sender in enumerate(("noreply@github.com", "noreply@dropbox.com")):
                if index == 1:
                    self.store.set_automation_paused(True)
                yield created(sender)
        with patch("argus_security.scan.PAUSE_CHECK_SECONDS", 0), self.assertRaises(jobs.JobPaused):
            scan_messages(self.store, messages())
        self.assertEqual(self.control()["jobs"][0]["state"], "paused")
        # The clue saved before the pause stays.
        self.assertEqual(self.store.snapshot()["summary"]["clues"], 1)
        events = [entry["event"] for entry in self.control()["activity"]]
        self.assertEqual(events[:2], ["job_finished", "automation_paused"])
        self.assertIn("automation_resumed", events)
        with self.assertRaises(UserFacingError):
            self.store.set_automation_paused("yes")

    def test_scheduled_scans_wait_while_paused_and_a_paused_run_keeps_its_schedule(self):
        credentials = KeyringCredentialStore(FakeKeyring())
        config = IMAPConfig("imap.example.invalid", OWN)
        calls = []

        def runner(store, config, secret, *, limit, keep_alive):
            calls.append(1)
            raise jobs.JobPaused("Automation was paused; the job stopped between two messages. Saved clues stay.")
        service = BackgroundScanService(self.store, credentials, config_loader=lambda: config, scan_runner=runner)
        service.configure(credential_id=credentials.save("not-a-real-secret"), target=config.target_fingerprint())
        self.store.set_automation_paused(True)
        self.assertEqual(service.run_due(allow_network=True), {"status": "paused"})
        self.assertEqual(calls, [])
        self.store.set_automation_paused(False)
        self.assertEqual(service.run_due(allow_network=True), {"status": "paused"})
        schedule = service.snapshot()
        self.assertEqual((schedule["enabled"], schedule["last_result"], schedule["last_error"]), (True, "paused", None))
        waiting = self.store.control_overview(schedule)["waiting"]
        self.assertEqual(waiting[0]["kind"], "scheduled_scan")

    def test_bitwarden_transfers_are_jobs_and_wait_for_the_pause(self):
        scan_messages(self.store, [created("noreply@github.com")])

        def runner(arguments, **kwargs):
            if arguments[1:] == ["status"]:
                return SimpleNamespace(returncode=0, stdout='{"status":"unlocked"}')
            return SimpleNamespace(returncode=0, stdout='{"id":"46caf902-0e99-4bc1-bb92-6075b813233c"}')
        self.store.set_automation_paused(True)
        with patch("argus_security.bitwarden.shutil.which", return_value="/usr/bin/bw"):
            with self.assertRaises(UserFacingError):
                add_to_unlocked_cli(self.store, ["github"], runner=runner, environment={"BW_SESSION": "x"})
            self.store.set_automation_paused(False)
            add_to_unlocked_cli(self.store, ["github"], runner=runner, environment={"BW_SESSION": "x"})
        job = self.control()["jobs"][0]
        self.assertEqual((job["kind"], job["state"], job["counts"]), ("bitwarden_write", "completed", {"items": 1}))

    def test_retention_keeps_the_log_short(self):
        with self.store.connect() as db:
            old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
            db.execute("INSERT INTO activity(at,event,counts) VALUES (?,'automation_resumed','{}')", (old,))
            for _ in range(jobs.KEEP_ACTIVITY + 5):
                jobs.record(db, "automation_paused")
            for index in range(jobs.KEEP_JOBS + 3):
                jobs.start(db, f"job-{index:03}", "import", "eml")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM activity").fetchone()[0], jobs.KEEP_ACTIVITY)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM activity WHERE event='automation_resumed'").fetchone()[0], 0)
            self.assertLessEqual(db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], jobs.KEEP_JOBS)
            with self.assertRaises(ValueError):
                jobs.record(db, "message_text_seen")

    def test_cli_and_api(self):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            base = ["--language", "de", "--data-dir", str(self.profile), "automation"]
            self.assertEqual(main([*base, "pause"]), 0)
        self.assertIsNotNone(json.loads(out.getvalue())["paused"])
        self.assertIn("Die gesamte Automatik ist pausiert", err.getvalue())
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

        self.assertIsNotNone(call("GET", "/api/control")[1]["paused"])
        self.assertEqual(call("POST", "/api/control", {"action": "stop"})[0], 400)
        self.assertEqual(call("POST", "/api/control", {"action": "resume"})[0], 200)
        self.assertIsNone(call("GET", "/api/control")[1]["paused"])


if __name__ == "__main__":
    unittest.main()
