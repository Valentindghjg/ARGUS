# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: command-line edge cases."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security.cli import main
from argus_security.registry import Registry
from argus_security.scan import synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"


class ReviewCliTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.profile = self.root / "profile"
        Store(self.profile, Registry()).configure([OWN])
        self.mails = self.root / "mails"
        self.mails.mkdir()

    def cli(self, *arguments, language="en"):
        output, error = StringIO(), StringIO()
        with patch("argus_security.cli.data_root", return_value=self.root), redirect_stdout(output), redirect_stderr(error):
            code = main(["--language", language, "--data-dir", str(self.profile), *arguments])
        return code, output.getvalue(), error.getvalue()

    def test_import_output_is_json_and_progress_goes_to_stderr(self):
        (self.mails / "a.eml").write_bytes(synthetic_mail("noreply@github.com", "Your account has been created", "",
                                                          recipient=OWN))
        code, output, error = self.cli("import", str(self.mails))
        self.assertEqual(code, 0)
        json.loads(output)
        self.assertIn("Processed locally", error)

    def test_a_mistyped_source_never_replaces_the_remembered_one(self):
        (self.mails / "a.eml").write_bytes(b"")
        self.cli("import", str(self.mails))
        code, _, error = self.cli("import", str(self.root / "malis"))
        self.assertEqual(code, 2)
        self.assertEqual(self.cli("import", "--again")[0], 0)
        code, _, _ = self.cli("import", str(self.mails), "--format", "mbox")
        self.assertEqual(code, 2)
        self.assertEqual(self.cli("import", "--again")[0], 0)

    def test_a_retry_stopped_by_its_limit_keeps_the_items_it_did_not_reach(self):
        for name in ("a.eml", "b.eml", "c.eml"):
            (self.mails / name).write_bytes(b"")
        self.cli("import", str(self.mails))
        for index, name in enumerate(("a.eml", "b.eml", "c.eml")):
            (self.mails / name).write_bytes(synthetic_mail(f"noreply@{('github.com', 'dropbox.com', 'spotify.com')[index]}",
                                                           "Your account has been created", "", recipient=OWN))
        code, _, _ = self.cli("import", "--retry-failed", "--max-messages", "1")
        self.assertEqual(code, 0)
        code, _, error = self.cli("import", "--retry-failed")
        self.assertEqual(code, 0, error)
        self.assertEqual(Store(self.profile, Registry()).snapshot()["summary"]["clues"], 3)

    def test_the_demo_never_goes_into_the_default_profile(self):
        output, error = StringIO(), StringIO()
        with patch("argus_security.cli.data_root", return_value=self.root), redirect_stdout(output), redirect_stderr(error):
            code = main(["demo"])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "argus").exists())

    def test_ports_outside_the_valid_range_get_a_message(self):
        code, _, error = self.cli("serve", "--port", "70000")
        self.assertEqual(code, 2)
        self.assertIn("between 1 and 65535", error)

    def test_missing_files_get_constant_translated_messages_without_paths(self):
        code, _, error = self.cli("background-imap", "preview", language="de")
        self.assertEqual(code, 2)
        self.assertIn("setup-imap", error)
        self.assertNotIn(str(self.profile), error)
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(["--language", "de", "--providers", str(self.root / "missing.json"),
                         "--data-dir", str(self.profile), "report"])
        self.assertEqual(code, 2)
        self.assertNotIn("missing.json", error.getvalue())
        self.assertIn("nicht gefunden", error.getvalue())

    def test_setup_imap_without_a_terminal_or_with_existing_settings(self):
        with patch("builtins.input", side_effect=EOFError):
            code, _, error = self.cli("setup-imap")
        self.assertEqual(code, 2)
        self.assertIn("--host", error)
        self.assertEqual(self.cli("setup-imap", "--host", "imap.example.invalid", "--username", OWN)[0], 0)
        code, _, error = self.cli("setup-imap", "--host", "imap2.example.invalid", "--username", OWN)
        self.assertEqual(code, 2)
        self.assertIn("imap.json", error)

    def test_the_review_rule_keeps_the_part_you_did_not_change(self):
        self.cli("review-rule", "--months", "12", "--scope", "all")
        rule = json.loads(self.cli("review-rule", "--months", "24")[1])["rule"]
        self.assertEqual(rule, {"months": 24, "scope": "all"})
        rule = json.loads(self.cli("review-rule", "--scope", "important")[1])["rule"]
        self.assertEqual(rule, {"months": 24, "scope": "important"})

    def test_json_texts_follow_the_language(self):
        code, output, _ = self.cli("template", "list", language="de")
        names = [template["name"] for template in json.loads(output)]
        self.assertIn("Jährliche Prüfung wichtiger Accounts", names)


if __name__ == "__main__":
    unittest.main()
