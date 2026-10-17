# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plans G4 and G6: data-minimal bug reports and releases that name every connection."""
from contextlib import redirect_stdout
from hashlib import sha256
import importlib.util
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from argus_security.about import about
from argus_security.cli import main
from argus_security.registry import Registry
from argus_security.scan import DEMO_EMAILS, load_demo
from argus_security.store import Store

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("argus_release_check", ROOT / "scripts" / "release_check.py")
release_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_check)


class ReleaseCheckTests(unittest.TestCase):
    def test_versions_connections_and_permissions_are_declared(self):
        self.assertEqual(release_check.problems(), [])
        self.assertEqual(set(release_check.reaching_modules()), set(release_check.DECLARED))

    def test_release_notes_template_names_the_declared_connections(self):
        template = (ROOT / "docs" / "RELEASE_NOTES_TEMPLATE.md").read_text(encoding="utf-8")
        self.assertIn("## New connections and permissions", template)
        for module in release_check.DECLARED:
            self.assertIn(module, template)

    def test_checksums_cover_every_built_file(self):
        with tempfile.TemporaryDirectory() as folder:
            dist = Path(folder)
            (dist / "argus-2.6.0.tar.gz").write_bytes(b"synthetic")
            (dist / "argus-2.6.0-py3-none-any.whl").write_bytes(b"also synthetic")
            with redirect_stdout(StringIO()):
                self.assertEqual(release_check.main(["checksums", str(dist)]), 0)
            lines = (dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines, [f"{sha256(b'also synthetic').hexdigest()}  argus-2.6.0-py3-none-any.whl",
                                 f"{sha256(b'synthetic').hexdigest()}  argus-2.6.0.tar.gz"])

    def test_release_workflow_only_reads_and_publishes_nothing(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertNotIn(": write", workflow)
        self.assertNotIn("gh release", workflow)
        self.assertIn("scripts/release_check.py", workflow)


class AboutTests(unittest.TestCase):
    def test_about_reports_counts_but_no_address_path_or_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            data_dir = Path(folder) / "profile"
            load_demo(Store(data_dir, Registry()))
            database = data_dir / "accounts.sqlite3"
            before = database.read_bytes()
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--data-dir", str(data_dir), "about"]), 0)
            self.assertEqual(database.read_bytes(), before)
        text = output.getvalue()
        facts = json.loads(text)
        self.assertEqual((facts["profile"], facts["profile_data"], facts["own_addresses"], facts["demo"]),
                         ("custom", "counts", 2, True))
        self.assertGreater(facts["clues"], 0)
        for private in [*DEMO_EMAILS, folder, "github", "paypal", "example.invalid"]:
            self.assertNotIn(private, text)

    def test_about_never_creates_a_missing_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing"
            self.assertEqual(about(missing, "default")["profile_data"], "none")
            self.assertFalse(missing.exists())

    def test_bug_report_asks_for_about_and_never_for_private_data(self):
        form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text(encoding="utf-8")
        self.assertIn("argus about", form)
        self.assertIn("type: checkboxes", form)
        self.assertIn("We never need your", form)
        # The data check is mandatory, so no report is sent without confirming it.
        self.assertIn("contains no real email", form.split("type: checkboxes")[1])
        self.assertIn("required: true", form.split("type: checkboxes")[1])


if __name__ == "__main__":
    unittest.main()
