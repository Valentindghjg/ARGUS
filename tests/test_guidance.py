# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Master plan F4 and G1: errors with a next step, and a precise product promise."""
import ast
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest

from argus_security.cli import main
from argus_security.guidance import HINTS, SCAN_STEPS, hint_for, scan_next_steps
from argus_security.i18n import catalog
from argus_security.scan import synthetic_mail

ROOT = Path(__file__).resolve().parents[1]


def code_literals():
    literals = set()
    for path in (ROOT / "argus_security").glob("*.py"):
        if path.name == "guidance.py":
            continue
        literals |= {node.value for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    return literals


class GuidanceCatalogTests(unittest.TestCase):
    def test_every_hint_belongs_to_a_real_message_and_is_translated(self):
        literals = code_literals()
        for message, hint in HINTS.items():
            with self.subTest(message=message):
                self.assertIn(message, literals, "hint for a message that is never raised")
                self.assertIn(hint, catalog()["de"])
                self.assertNotRegex(hint, r"\{[^}]*\}", "hints are constant; they never carry data")
        for step in SCAN_STEPS.values():
            self.assertIn(step, catalog()["de"])

    def test_unknown_or_non_text_messages_have_no_hint(self):
        self.assertIsNone(hint_for("Not found"))
        self.assertIsNone(hint_for(None))
        self.assertIsNone(hint_for(["EML path not found"]))

    def test_scan_next_steps_follow_each_gap(self):
        self.assertEqual(scan_next_steps({"running": True, "skipped": 3}), [])
        self.assertEqual(scan_next_steps({"result": "completed", "skipped": 0, "errors": 0, "headers_only": 0}), [])
        self.assertEqual(scan_next_steps({"result": "completed_with_gaps", "skipped": 2, "errors": 1, "headers_only": 1}),
                         [SCAN_STEPS["skipped"], SCAN_STEPS["errors"], SCAN_STEPS["headers_only"]])
        self.assertEqual(scan_next_steps({"result": "limited"}), [SCAN_STEPS["limited"]])
        self.assertEqual(scan_next_steps({"result": "partial"}), [SCAN_STEPS["partial"]])
        # A changed address scope needs a restart, not a mere continuation.
        self.assertEqual(scan_next_steps({"result": "partial", "scope_changed": True}), [SCAN_STEPS["scope_changed"]])
        self.assertEqual(scan_next_steps({"result": "completed", "skipped": "3"}), [])
        self.assertEqual(scan_next_steps(None), [])


class CommandLineGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"

    def run_cli(self, *arguments, language="en"):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--language", language, "--data-dir", str(self.profile), *arguments])
        return code, out.getvalue(), err.getvalue()

    def test_missing_profile_and_missing_source_explain_the_next_step(self):
        code, _, err = self.run_cli("import", str(self.root / "missing"), "--format", "eml")
        self.assertEqual(code, 2)
        self.assertIn("Next step: Start with argus init --email", err)
        self.assertEqual(self.run_cli("init", "--email", "owner@example.invalid")[0], 0)
        missing = self.root / "private-folder-name"
        code, _, err = self.run_cli("import", str(missing), "--format", "eml", language="de")
        self.assertEqual(code, 2)
        self.assertIn("Fehler: ", err)
        self.assertIn("Nächster Schritt: Prüfe den Pfad.", err)
        # The hint is constant; it does not repeat the path the user typed.
        self.assertEqual(err.count("private-folder-name"), 0)

    def test_import_reports_json_and_translated_next_steps_separately(self):
        self.run_cli("init", "--email", "owner@example.invalid")
        folder = self.root / "mail"
        folder.mkdir()
        (folder / "large.eml").write_bytes(b"X" * (2 * 1024 * 1024 + 1))
        (folder / "ok.eml").write_bytes(synthetic_mail("noreply@github.com", "Your account has been created", "",
                                                       recipient="owner@example.invalid"))
        code, out, err = self.run_cli("import", str(folder), "--format", "eml", language="de")
        self.assertEqual(code, 0)
        result = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((result["skipped"], result["result"]), (1, "completed_with_gaps"))
        self.assertEqual(result["next_steps"], [SCAN_STEPS["skipped"]])
        self.assertIn("Nächster Schritt: Übersprungene Nachrichten", err)

    def test_existing_export_is_never_overwritten_and_explains_why(self):
        self.run_cli("demo")
        target = self.root / "export.json"
        target.write_text("{}", encoding="utf-8")
        code, _, err = self.run_cli("bitwarden-export", str(target), "--id", "discord")
        self.assertEqual(code, 2)
        self.assertIn("Next step: Choose a new file name.", err)
        self.assertEqual(target.read_text(encoding="utf-8"), "{}")


class ProductPromiseTests(unittest.TestCase):
    """G1: no completeness or protection guarantee in the interface or the guides."""

    FORBIDDEN = [r"for every account", r"closer to completion", r"\bAlready secured\b", r"all your accounts",
                 r"fully secure", r"100\s?% secure", r"complete inventory", r"Inventur vollständiger",
                 r"Bereits abgesichert", r"alle deine Accounts", r"vollständig geschützt", r"garantiert sicher"]

    def texts(self):
        catalog_texts = [text for pair in catalog()["de"].items() for text in pair]
        pages = [(ROOT / name).read_text(encoding="utf-8") for name in ("README.md", "README_DE.md")]
        web = [(ROOT / "argus_security" / "web" / name).read_text(encoding="utf-8") for name in ("app.js", "index.html")]
        return catalog_texts + pages + web

    def test_no_absolute_promises(self):
        for text in self.texts():
            for pattern in self.FORBIDDEN:
                self.assertIsNone(re.search(pattern, text, re.IGNORECASE), pattern)

    def test_both_guides_state_the_precise_promise(self):
        self.assertIn("It cannot\nfind every account", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("Es kann weder alle Accounts finden", (ROOT / "README_DE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
