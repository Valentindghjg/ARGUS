# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: imports, budgets, the folder watch, job states and the scheduler."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from argus_security import watch
from argus_security.cli import main
from argus_security.imports import budget
from argus_security.registry import Registry
from argus_security.scan import ScanSession, file_items, scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN = "owner@example.invalid"
BROKEN = b"From: spam@spam.example\r\nTo: ,\t:\r\nSubject: hi\r\n\r\nx\r\n"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class ReviewImportTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        self.mails = self.root / "mails"
        self.mails.mkdir()

    def clues(self):
        return self.store.snapshot()["summary"]["clues"]

    def test_a_message_the_parser_cannot_read_is_one_error_not_a_failed_import(self):
        (self.mails / "1.eml").write_bytes(BROKEN)
        (self.mails / "2.eml").write_bytes(created("noreply@github.com"))
        session = ScanSession(self.store, "eml")
        result = scan_messages(self.store, file_items(self.mails, "eml"), "eml", session=session, keyed=True)
        self.assertEqual((result["result"], result["errors"], self.clues()), ("completed_with_gaps", 1, 1))
        self.assertEqual(session.failed_items, ["1.eml"])

    def test_an_unreadable_file_is_listed_for_retry_and_the_rest_is_read(self):
        (self.mails / "a.eml").write_bytes(created("noreply@github.com"))
        (self.mails / "b.eml").write_bytes(created("support@discord.com"))
        original = Path.open

        def guarded(path, *args, **kwargs):
            if path.name == "a.eml":
                raise PermissionError("denied")
            return original(path, *args, **kwargs)
        session = ScanSession(self.store, "eml")
        with patch.object(Path, "open", guarded):
            scan_messages(self.store, file_items(self.mails, "eml"), "eml", session=session, keyed=True)
        self.assertEqual((session.failed_items, self.clues()), (["a.eml"], 1))

    def test_upper_case_eml_files_are_imported(self):
        (self.mails / "A.EML").write_bytes(created("noreply@github.com"))
        self.assertEqual([key for key, _ in file_items(self.mails, "eml")], ["A.EML"])

    def test_a_budget_counts_only_new_work_and_an_exact_fit_completes(self):
        messages = [b"", b""] + [created(s) for s in ("noreply@github.com", "support@discord.com", "hello@spotify.com")]
        runs = [scan_messages(self.store, messages, budget=budget(max_messages=2)) for _ in range(2)]
        self.assertEqual([run["result"] for run in runs], ["limited", "completed_with_gaps"])
        self.assertEqual(self.clues(), 3)
        exact = scan_messages(self.store, [created("noreply@epicgames.com")], budget=budget(max_messages=1))
        self.assertEqual(exact["result"], "completed")

    def test_a_full_scan_with_a_limit_is_refused_before_any_connection(self):
        error = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(error):
            code = main(["--data-dir", str(self.profile), "scan-imap", "--allow-imap", "--full-scan", "--limit", "5"])
        self.assertEqual(code, 2)
        self.assertIn("without --limit", error.getvalue())

    def test_coverage_counts_messages_read_again_only_once(self):
        messages = [created("noreply@github.com"), created("support@discord.com")]
        scan_messages(self.store, messages)
        scan_messages(self.store, messages)
        source = self.store.snapshot()["coverage"]["sources"][0]
        self.assertEqual((source["runs"], source["messages"]), (2, 2))

    def test_the_scheduler_starts_with_the_dashboard_even_before_anything_is_enabled(self):
        server = DashboardServer(self.store, 0)
        try:
            server.start_background_scans()
            self.assertIsNotNone(server.background_thread)
        finally:
            server.server_close()


class ReviewWatchTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.store = Store(self.root / "profile", Registry())
        self.store.configure([OWN])
        self.folder = self.root / "exports"
        self.folder.mkdir()
        for name, sender in (("a.eml", "noreply@github.com"), ("b.eml", "support@discord.com"),
                             ("c.eml", "hello@spotify.com")):
            (self.folder / name).write_bytes(created(sender))
        watch.enable(self.store, self.folder, 60)
        self.clock = time.time()

    def run_now(self):
        self.clock += 24 * 60 * 60
        return watch.run_due(self.store, now=self.clock)

    def test_a_failing_pass_is_recorded_and_waits_for_the_interval(self):
        with patch("argus_security.scan.scan_messages", side_effect=OSError("disk")):
            self.assertEqual(self.run_now(), {"status": "failed"})
        status = watch.status(self.store)
        self.assertEqual(status["last_result"], "failed")
        self.assertGreater(status["next_run_at"], self.clock)
        self.assertEqual(watch.run_due(self.store, now=self.clock + 1), {"status": "not_due"})

    def test_disabling_during_a_pass_stays_disabled(self):
        original = watch._read

        def read_and_disable(folder, name):
            if name == "b.eml":
                watch.disable(self.store)
            return original(folder, name)
        with patch.object(watch, "_read", read_and_disable):
            self.run_now()
        self.assertFalse(watch.status(self.store)["enabled"])
        self.assertEqual(self.run_now(), {"status": "disabled"})

    def test_files_after_a_scope_change_are_read_again(self):
        original = watch._read

        def read_and_add_address(folder, name):
            if name == "b.eml":
                self.store.add_emails(["second@example.invalid"])
            return original(folder, name)
        with patch.object(watch, "_read", read_and_add_address):
            self.run_now()
        self.assertEqual(set(self.store.meta(watch.STATE)), {"a.eml"})
        self.run_now()
        self.assertEqual(self.store.snapshot()["summary"]["clues"], 3)

    def test_a_folder_too_large_to_track_is_reported_instead_of_rereading_forever(self):
        with patch.object(watch, "MAX_TRACKED_FILES", 2):
            self.assertEqual(self.run_now(), {"status": "too_many_files"})
        self.assertEqual(watch.status(self.store)["last_result"], "too_many_files")


if __name__ == "__main__":
    unittest.main()
