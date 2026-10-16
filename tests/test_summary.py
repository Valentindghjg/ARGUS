# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan F3 and D1: an honest result summary and one reasoned next task."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security import handoffs
from argus_security.cli import main
from argus_security.registry import Registry
from argus_security.scan import ScanSession, load_demo, scan_messages, synthetic_mail
from argus_security.store import Store
from argus_security.workflow import change_worklist

OWN = "owner@example.invalid"


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root / "profile", Registry())
        self.store.configure([OWN])

    def scan(self, *senders):
        return scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                          for sender in senders])

    def task(self):
        return self.store.snapshot()["next_task"]

    def test_empty_profile_starts_with_a_local_import(self):
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["next_task"], {"kind": "import", "count": None, "account_id": None})
        self.assertEqual(snapshot["result"]["clues"], 0)

    def test_tasks_follow_the_documented_order(self):
        self.scan("noreply@github.com", "support@discord.com")
        task = self.task()
        self.assertEqual((task["kind"], task["count"]), ("decide", 2))
        self.assertEqual(task["account_id"], "github")  # higher priority first
        for account in ("github", "discord"):
            self.store.decide(account, "confirmed")
        self.assertEqual(self.task(), {"kind": "secure", "count": None, "account_id": "github"})
        change_worklist(self.store, {"action": "add", "ids": ["discord"]})
        self.assertEqual(self.task()["kind"], "continue")
        self.assertEqual(self.task()["account_id"], "discord")
        due = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
        self.store.set_step("github", "mfa_recovery", review_after=due)
        with patch("argus_security.workflow.utcnow", return_value=datetime.now(timezone.utc) + timedelta(days=11)):
            self.assertEqual(self.task()["kind"], "review_due")
        attempt = handoffs.reserve(self.store, "discord", OWN)
        handoffs.finish(self.store, attempt, "uncertain")
        self.assertEqual(self.task()["kind"], "handoff")
        session = ScanSession(self.store, "eml", expected=5)
        session.process(synthetic_mail("noreply@steampowered.com", "Your account has been created", "", recipient=OWN))
        session.finish("partial")
        self.assertEqual(self.task()["kind"], "scan_gaps")

    def test_everything_decided_and_complete_has_no_task(self):
        self.scan("noreply@github.com")
        self.store.decide("github", "confirmed")
        for step in ("identity", "vault", "password", "signin_test", "mfa_recovery"):
            self.store.set_step("github", step, state="done")
        self.assertEqual(self.task()["kind"], "done")
        self.store.set_step("github", "vault", state="open")
        self.assertEqual(self.task()["kind"], "secure")
        # A rejected account never becomes a task.
        self.store.decide("github", "rejected", "closed")
        self.assertEqual(self.task()["kind"], "done")

    def test_summary_counts_unclear_items_and_gaps_honestly(self):
        load_demo_store = Store(self.root / "demo", Registry())
        load_demo(load_demo_store)
        result = load_demo_store.snapshot()["result"]
        self.assertEqual(result["clues"], 18)
        self.assertEqual(result["confirmed"], 2)
        self.assertEqual(result["to_decide"], 11)
        self.assertEqual(result["unclear"]["unknown_domains"], 2)
        self.assertEqual(result["unclear"]["unassigned_clues"], 3)
        self.assertFalse(result["gaps"]["unfinished"])
        self.assertEqual(result["messages_processed"], 18)

    def test_report_includes_summary_and_next_task(self):
        self.scan("noreply@github.com")
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            self.assertEqual(main(["--language", "en", "--data-dir", str(self.root / "profile"), "report"]), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["next_task"]["kind"], "decide")
        self.assertEqual(report["result"]["clues"], 1)
        self.assertIn("found", report)


if __name__ == "__main__":
    unittest.main()
