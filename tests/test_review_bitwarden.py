# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: Bitwarden hand-offs, the CLI journal, profiles and move plans."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security import bitwarden, handoffs
from argus_security.bitwarden import BitwardenCliError, bw_executable, download_export, export_file
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.profiles import profile_dir
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN, WORK = "owner@example.invalid", "work@example.invalid"


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "", recipient=OWN)


class ReviewBitwardenTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN, WORK])
        scan_messages(self.store, [created("noreply@github.com"), created("support@discord.com")])

    def journal(self):
        return {entry["account_id"]: entry for entry in self.store.snapshot()["bitwarden_handoffs"]}

    def cli(self, *arguments):
        output, error = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = main(["--data-dir", str(self.profile), *arguments])
        return code, output.getvalue(), error.getvalue()

    def test_two_downloads_at_once_never_both_get_a_file(self):
        original = bitwarden.make_export
        handed_out, raced = [], []

        def racing(store, ids, language="en"):
            result = original(store, ids, language)
            if not raced:
                # A second download runs completely between planning and recording the first.
                raced.append(True)
                handed_out.append(download_export(store, ids, language))
            return result
        with patch.object(bitwarden, "make_export", racing):
            with self.assertRaises(handoffs.HandoffError):
                download_export(self.store, ["github"])
        self.assertEqual(len(handed_out), 1)
        self.assertEqual(self.journal()["github"]["state"], "exported")

    def test_a_file_that_cannot_be_written_leaves_no_journal_entry(self):
        with patch.object(bitwarden, "write_private", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                export_file(self.store, self.root / "vault.json", ["github"])
        self.assertNotIn("github", self.journal())
        export_file(self.store, self.root / "vault.json", ["github"])
        self.assertEqual(self.journal()["github"]["state"], "exported")

    def test_only_found_accounts_can_be_marked_as_in_the_vault(self):
        with self.assertRaisesRegex(UserFacingError, "discovered accounts"):
            self.store.mark_in_vault(["amazon"])
        self.store.decide("discord", "rejected", "not_mine")
        with self.assertRaisesRegex(UserFacingError, "discovered accounts"):
            self.store.mark_in_vault(["discord"])
        with self.store.connect() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM account_instances WHERE id='amazon'").fetchone())

    def test_marking_a_downloaded_account_as_in_the_vault_closes_its_journal_entry(self):
        download_export(self.store, ["github"])
        self.store.mark_in_vault(["github"])
        self.assertEqual(self.journal()["github"]["state"], "created")

    def test_the_journal_can_be_listed_and_resolved_in_a_terminal(self):
        download_export(self.store, ["github"])
        code, output, _ = self.cli("bitwarden-journal", "list")
        entries = json.loads(output)
        self.assertEqual((code, [entry["account_id"] for entry in entries]), (0, ["github"]))
        code, _, error = self.cli("bitwarden-journal", "resolve", entries[0]["id"])
        self.assertEqual(code, 2)
        code, _, _ = self.cli("bitwarden-journal", "resolve", entries[0]["id"], "--not-found")
        self.assertEqual((code, self.journal()["github"]["state"]), (0, "not_created"))
        # A second export is possible again.
        download_export(self.store, ["github"])

    def test_only_bw_exe_from_a_path_folder_runs_on_windows(self):
        folder = self.root / "bin"
        folder.mkdir()
        (folder / "bw.exe").write_bytes(b"")
        with patch("argus_security.bitwarden.shutil.which", return_value=str(folder / "bw.cmd")):
            with self.assertRaises(BitwardenCliError):
                bw_executable(windows=True)
        with patch("argus_security.bitwarden.shutil.which", return_value=str(folder / "bw.exe")):
            with patch.dict(os.environ, {"PATH": str(folder)}):
                self.assertEqual(Path(bw_executable(windows=True)), (folder / "bw.exe").resolve())
            with patch.dict(os.environ, {"PATH": str(self.root / "elsewhere")}):
                self.assertIsNone(bw_executable(windows=True))

    def test_a_move_plan_keeps_an_address_note_the_person_wrote(self):
        scan_messages(self.store, [synthetic_mail("noreply@dropbox.com", "Your account has been created", "",
                                                  recipient=OWN)])
        self.store.relate_addresses(OWN, WORK, "same_mailbox")
        self.store.create_move_plan(OWN, WORK)
        kinds = [entry["kind"] for entry in self.store.snapshot()["relations"]]
        self.assertEqual(kinds, ["same_mailbox"])


class ReviewProfileTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def run_cli(self, *arguments):
        output, error = StringIO(), StringIO()
        with patch("argus_security.cli.data_root", return_value=self.root), redirect_stdout(output), redirect_stderr(error):
            code = main(list(arguments))
        return code, output.getvalue(), error.getvalue()

    def test_reserved_profile_names_are_refused(self):
        for name in ("default", "con", "nul", "com1", "lpt9"):
            with self.subTest(name=name), self.assertRaises(UserFacingError):
                profile_dir(self.root, name)

    def test_a_mistyped_profile_is_never_created(self):
        code, _, error = self.run_cli("--profile", "wrok", "report")
        self.assertEqual(code, 2)
        self.assertIn("does not exist yet", error)
        self.assertFalse((self.root / "argus-profiles" / "wrok").exists())

    def test_about_and_profiles_never_move_an_old_profile_folder(self):
        legacy = self.root / "account-finder"
        Store(legacy, Registry()).configure([OWN])
        for command in ("about", "profiles"):
            code, output, error = self.run_cli(command)
            self.assertEqual((code, error), (0, ""))
            self.assertNotIn(str(self.root), output)
        self.assertTrue(legacy.is_dir())
        self.assertFalse((self.root / "argus").exists())
        self.assertEqual(json.loads(self.run_cli("about")[1])["profile_data"], "counts")


if __name__ == "__main__":
    unittest.main()
