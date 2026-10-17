# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan A11, A16 and P3: repeat the last local import, retry only failures, check before importing."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import mailbox
from pathlib import Path
import shutil
import tempfile
import unittest

from argus_security.cli import main
from argus_security.registry import Registry
from argus_security.scan import file_items, synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class ImportPresetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        Store(self.profile, Registry()).configure([OWN])
        self.folder = self.root / "mail"
        (self.folder / "sub").mkdir(parents=True)
        (self.folder / "a.eml").write_bytes(created("noreply@github.com"))
        (self.folder / "sub" / "b.eml").write_bytes(created("no-reply@dropbox.com"))
        (self.folder / "empty.eml").write_bytes(b"")

    def run_cli(self, *arguments):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--language", "en", "--data-dir", str(self.profile), "import", *arguments])
        return code, out.getvalue(), err.getvalue()

    def store(self):
        return Store(self.profile, Registry())

    def test_the_last_source_is_remembered_and_repeated(self):
        self.assertEqual(self.run_cli("--again")[0], 2)
        code, _, err = self.run_cli(str(self.folder))
        self.assertEqual(code, 0)
        last = self.store().snapshot()["last_local_import"]
        self.assertEqual((last["path"], last["format"], last["failed"]), (str(self.folder.resolve()), "eml", 1))
        code, _, err = self.run_cli("--again")
        self.assertIn("2 unchanged message(s)", err)
        self.assertEqual(self.run_cli(str(self.folder), "--again")[0], 2)
        shutil.rmtree(self.folder)
        code, _, err = self.run_cli("--again")
        self.assertEqual(code, 2)
        self.assertIn("The last import source no longer exists", err)

    def test_retry_reads_only_the_failed_items(self):
        self.run_cli(str(self.folder))
        self.assertEqual([key for key, _ in file_items(self.folder, "eml", ["empty.eml"])], ["empty.eml"])
        (self.folder / "empty.eml").write_bytes(created("noreply@spotify.com"))
        code, out, err = self.run_cli("--retry-failed")
        self.assertEqual(code, 0)
        result = json.loads(out[out.index("{"):out.rindex("}") + 1])
        self.assertEqual((result["processed"], result["evidence"]), (1, 1))
        self.assertEqual(self.store().snapshot()["last_local_import"]["failed"], 0)
        code, _, err = self.run_cli("--retry-failed")
        self.assertEqual(code, 2)
        self.assertIn("no failed items to retry", err)
        # The failed keys stay local; the dashboard only sees their number.
        self.assertNotIn("items", self.store().snapshot()["last_local_import"])

    def test_mbox_items_are_numbered(self):
        path = self.root / "box.mbox"
        box = mailbox.mbox(path)
        for sender in ("noreply@github.com", "noreply@paypal.com"):
            box.add(created(sender))
        box.flush()
        box.close()
        self.assertEqual([key for key, _ in file_items(path, "mbox")], ["#0", "#1"])
        self.assertEqual([key for key, _ in file_items(path, "mbox", ["#1"])], ["#1"])

    def test_check_counts_without_importing(self):
        code, out, err = self.run_cli(str(self.folder), "--check")
        self.assertEqual(code, 0)
        summary = json.loads(out)
        self.assertEqual((summary["messages"], summary["new"], summary["unchanged"], summary["too_large"]), (3, 2, 0, 1))
        self.assertIn("Nothing was imported", err)
        store = self.store()
        self.assertEqual((store.snapshot()["summary"]["clues"], store.control_overview()["jobs"]), (0, []))
        self.run_cli(str(self.folder))
        summary = json.loads(self.run_cli(str(self.folder), "--check")[1])
        self.assertEqual((summary["new"], summary["unchanged"]), (0, 2))


if __name__ == "__main__":
    unittest.main()
