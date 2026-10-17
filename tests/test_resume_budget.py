# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A13, A14 and A15: skip what is unchanged, limit new work and continue safely."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security import scan
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.imports import budget
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN, ALIAS = "owner@example.invalid", "alias@example.invalid"
SENDERS = ("noreply@github.com", "no-reply@dropbox.com", "noreply@spotify.com", "noreply@notion.so", "noreply@paypal.com")


def created(sender, recipient=OWN):
    return synthetic_mail(sender, "Your account has been created", "", recipient=recipient)


class ResumeBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        self.messages = [created(sender) for sender in SENDERS]

    def analyses(self, messages, **options):
        calls = []
        original = scan.analyze

        def counting(*args, **kwargs):
            calls.append(1)
            return original(*args, **kwargs)
        with patch("argus_security.scan.analyze", counting):
            result = scan_messages(self.store, messages, **options)
        return result, len(calls)

    def test_unchanged_messages_are_recognized_by_content_not_analyzed_again(self):
        first, analyzed = self.analyses(self.messages)
        self.assertEqual((first["evidence"], analyzed), (5, 5))
        again, analyzed = self.analyses(self.messages)
        self.assertEqual((again["unchanged"], again["duplicates"], analyzed, again["result"]), (5, 0, 0, "completed"))
        rechecked, analyzed = self.analyses(self.messages, recheck=True)
        self.assertEqual((rechecked["duplicates"], analyzed), (5, 5))
        # The index holds fingerprints and a scope digest, nothing else.
        with self.store.connect() as db:
            columns = [row["name"] for row in db.execute("PRAGMA table_info(processed_messages)")]
        self.assertEqual(columns, ["fingerprint", "scope"])

    def test_new_own_addresses_or_catalog_entries_analyze_everything_again(self):
        self.analyses(self.messages)
        self.store.add_emails([ALIAS])
        result, analyzed = self.analyses(self.messages)
        self.assertEqual((result["unchanged"], analyzed), (0, 5))
        self.store.add_provider({"name": "New Service", "website": "https://new-service.example/",
                                 "category": "Productivity", "domains": ["new-service.example"], "priority": "normal"})
        result, analyzed = self.analyses(self.messages)
        self.assertEqual((result["unchanged"], analyzed), (0, 5))
        # Fingerprints of earlier conditions are dropped.
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(DISTINCT scope) FROM processed_messages").fetchone()[0], 1)

    def test_a_budget_limits_new_work_and_the_next_run_continues(self):
        limits = budget(max_messages=2)
        first = scan_messages(self.store, self.messages, budget=limits)
        self.assertEqual((first["processed"], first["evidence"], first["result"]), (2, 2, "limited"))
        self.assertIn("not a complete result", " ".join(first["next_steps"]))
        second = scan_messages(self.store, self.messages, budget=limits)
        self.assertEqual((second["unchanged"], second["evidence"], second["result"]), (2, 2, "limited"))
        third = scan_messages(self.store, self.messages, budget=limits)
        self.assertEqual((third["unchanged"], third["evidence"], third["result"]), (4, 1, "completed"))
        self.assertEqual(self.store.snapshot()["summary"]["clues"], 5)
        byte_limited = scan_messages(self.store, [created("noreply@netflix.com"), created("noreply@ebay.de")],
                                     budget=budget(max_megabytes=1), recheck=True)
        self.assertEqual(byte_limited["result"], "completed")
        for bad in ({"max_messages": 0}, {"max_messages": "5"}, {"max_megabytes": 10**6}):
            with self.subTest(bad=bad), self.assertRaises(UserFacingError):
                budget(**bad)

    def test_an_interrupted_import_continues_without_repeating_work(self):
        def interrupted():
            yield from self.messages[:3]
            raise OSError("disk gone")
        with self.assertRaises(OSError):
            scan_messages(self.store, interrupted())
        result, analyzed = self.analyses(self.messages)
        self.assertEqual((result["unchanged"], analyzed, result["result"]), (3, 2, "completed"))

    def test_cli_budget_and_recheck(self):
        folder = self.root / "mail"
        folder.mkdir()
        for index, raw in enumerate(self.messages):
            (folder / f"{index}.eml").write_bytes(raw)
        base = ["--language", "en", "--data-dir", str(self.profile), "import", str(folder)]
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(main([*base, "--max-messages", "3"]), 0)
            self.assertEqual(main(base), 0)
            self.assertEqual(main([*base, "--max-megabytes", "0"]), 2)
        self.assertIn("not a complete result", err.getvalue())
        self.assertIn("3 unchanged message(s) were recognized", err.getvalue())
        self.assertIn("The size budget must be between 1 and 100000 MB", err.getvalue())


if __name__ == "__main__":
    unittest.main()
