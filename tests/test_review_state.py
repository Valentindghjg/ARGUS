# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: change log, undo, evidence marks, backups and migrations."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from argus_security import changes
from argus_security.analysis import Evidence
from argus_security.backup import BackupError, create_backup, restore_backup
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"


class ReviewStateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.store = Store(self.root / "profile", Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                   for sender in ("noreply@github.com", "support@discord.com")])

    def account(self, ident):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == ident)

    def test_a_batch_larger_than_the_retention_limit_stays_undoable(self):
        self.store.decide("github", "confirmed")
        with patch.object(changes, "KEEP_ENTRIES", 2):
            result = self.store.mark_in_vault(["github", "discord"])
            self.store.update_account("discord", {"checklist": {"reviewed": True, "saved_in_bitwarden": True,
                                                                 "password_changed": True}})
            with self.store.connect() as db:
                batches = {row[0] for row in db.execute("SELECT DISTINCT batch FROM change_log")}
        # The newest batch is kept whole; older ones beyond the limit go.
        self.assertEqual(len(batches), 1)
        self.assertNotIn(result["batch"], batches)
        self.store.undo()
        self.assertEqual(self.account("discord")["decision"], "undecided")

    def test_undoing_a_sign_in_method_change_restores_method_and_password_step(self):
        self.store.update_account("github", {"login_method": "sso"})
        self.store.update_account("github", {"login_method": "password"})
        self.store.undo()
        github = self.account("github")
        self.assertEqual((github["login_method"], github["steps"]["password"]["state"]), ("sso", "not_applicable"))
        self.store.undo()
        github = self.account("github")
        self.assertEqual((github["login_method"], github["steps"]["password"]["state"]), ("password", "open"))

    def test_default_undo_after_a_redo_reverts_the_redo(self):
        self.store.decide("discord", "confirmed")
        self.store.decide("github", "confirmed")
        undone = self.store.undo()
        self.store.undo(undone["batch"])  # redo from the history
        self.assertEqual(self.account("github")["decision"], "confirmed")
        self.store.undo()
        self.assertEqual(self.account("github")["decision"], "undecided")
        self.assertEqual(self.account("discord")["decision"], "confirmed")

    def test_undo_restores_the_reconsider_hint_after_a_rejection(self):
        self.store.decide("github", "rejected", "not_mine")
        scan_messages(self.store, [synthetic_mail("security@github.com", "Your password has been changed",
                                                  "Your password has been changed.", recipient=OWN)])
        self.assertTrue(self.account("github")["reconsider"])
        self.store.decide("github", "undecided")
        self.store.undo()
        github = self.account("github")
        self.assertEqual((github["decision"], github["reconsider"]), ("rejected", True))

    def test_a_new_clue_after_the_newest_was_removed_still_counts_as_new(self):
        self.store.decide("github", "rejected", "not_mine")
        with self.store.connect() as db:
            newest = db.execute("SELECT fingerprint, id FROM evidence ORDER BY id DESC LIMIT 1").fetchone()
        # A re-analysis removes the newest clue; its id must not come back.
        self.store.record_analysis(newest["fingerprint"], None)
        clue = Evidence("github", "github.com", OWN, "password_changed", 85, "f" * 64, None, "import")
        self.store.record_analysis(clue.fingerprint, clue)
        with self.store.connect() as db:
            self.assertGreater(db.execute("SELECT id FROM evidence WHERE fingerprint=?", (clue.fingerprint,)).fetchone()[0],
                               newest["id"])
        self.assertTrue(self.account("github")["reconsider"])

    def test_clues_from_older_rules_show_as_stale_evidence(self):
        with self.store.connect() as db:
            db.execute("UPDATE evidence SET rule_version=1 WHERE provider_id='github'")
        github = self.account("github")
        self.assertEqual((github["evidence_level"], github["classification"]), ("stale", "unknown"))
        self.assertEqual(github["reason"], "Older evidence; reanalyze the original message locally")

    @unittest.skipUnless(hasattr(time, "tzset"), "needs time.tzset")
    def test_dates_follow_the_persons_calendar_day_west_of_utc(self):
        from datetime import datetime, timezone
        from argus_security.workflow import custom_snooze_date
        current = datetime(2026, 10, 18, 3, 0, tzinfo=timezone.utc)  # 17 October, 20:00 in Los Angeles
        try:
            with patch.dict(os.environ, {"TZ": "America/Los_Angeles"}):
                time.tzset()
                # "Tomorrow" in the date field is 18 October there.
                self.assertTrue(custom_snooze_date("2026-10-18", current).startswith("2026-10-18"))
        finally:
            time.tzset()

    def test_old_log_entries_without_an_evidence_mark_can_still_be_undone(self):
        result = self.store.decide("github", "confirmed")
        with self.store.connect() as db:
            for column in ("old", "new"):
                value = json.loads(db.execute(f"SELECT {column} FROM change_log WHERE batch=?", (result["batch"],)).fetchone()[0])
                value.pop("evidence_mark")
                db.execute(f"UPDATE change_log SET {column}=? WHERE batch=?", (json.dumps(value), result["batch"]))
        self.store.undo()
        self.assertEqual(self.account("github")["decision"], "undecided")

    def test_reimporting_old_clues_with_new_wording_is_not_a_change(self):
        with self.store.connect() as db:
            db.execute("UPDATE evidence SET features=NULL, caveat='alt', created_rev=0, changed_rev=0")
        scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                   for sender in ("noreply@github.com", "support@discord.com")], recheck=True)
        snapshot = self.store.snapshot()
        self.assertEqual((snapshot["changes"]["new"], snapshot["changes"]["changed"]), (0, 0))
        with self.store.connect() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM evidence WHERE features IS NULL").fetchone())



class ReviewBackupTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.profile = self.root / "profile"
        store = Store(self.profile, Registry())
        store.configure([OWN])

    def test_restoring_the_oldest_automatic_backup_never_deletes_it(self):
        made = [create_backup(self.profile, reason="pre-migration") for _ in range(5)]
        oldest = sorted(made)[0]
        with patch("argus_security.backup.os.replace", side_effect=PermissionError):
            with self.assertRaises(BackupError):
                restore_backup(self.profile, oldest)
        self.assertTrue(oldest.exists())
        restore_backup(self.profile, oldest)
        self.assertTrue(oldest.exists())

    def test_a_damaged_profile_can_be_replaced_and_its_bytes_are_kept(self):
        backup = create_backup(self.profile)
        (self.profile / "accounts.sqlite3").write_bytes(b"\x00garbage" * 100)
        result = restore_backup(self.profile, backup)
        self.assertTrue(result["safety_backup"].endswith(".sqlite3"))
        self.assertEqual(Path(result["safety_backup"]).read_bytes(), b"\x00garbage" * 100)
        Store(self.profile, Registry())

    def test_a_backup_from_a_newer_version_is_refused_before_anything_changes(self):
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
        newer = create_backup(self.profile)
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.execute("UPDATE meta SET value='10' WHERE key='schema_version'")
        before = (self.profile / "accounts.sqlite3").read_bytes()
        with self.assertRaises(BackupError):
            restore_backup(self.profile, newer)
        self.assertEqual((self.profile / "accounts.sqlite3").read_bytes(), before)

    def test_catalog_additions_are_backed_up_and_restored(self):
        store = Store(self.profile, Registry())
        ident = store.add_provider({"name": "Tiny Shop", "website": "https://tiny-shop.example", "category": "Shopping",
                                    "domains": ["tiny-shop.example"], "priority": "normal"})["id"]
        backup = create_backup(self.profile)
        target = self.root / "elsewhere"
        restore_backup(target, backup)
        self.assertIn(ident, Store(target, Registry()).registry.providers)
        # An older backup without additions keeps the current ones.
        (self.profile / "my-providers.json").unlink()
        older = create_backup(self.profile)
        restore_backup(target, older)
        self.assertIn(ident, Store(target, Registry()).registry.providers)

    def test_format_1_backups_still_restore_and_newer_formats_are_named(self):
        import zipfile
        backup = create_backup(self.profile)

        def rewrite(version):
            target = self.root / f"format-{version}.zip"
            with zipfile.ZipFile(backup) as source, zipfile.ZipFile(target, "w") as out:
                for info in source.infolist():
                    data = source.read(info)
                    if info.filename == "manifest.json":
                        manifest = json.loads(data)
                        manifest["version"] = version
                        data = json.dumps(manifest).encode()
                    out.writestr(info.filename, data)
            return target
        restore_backup(self.profile, rewrite(1))
        with self.assertRaisesRegex(BackupError, "newer ARGUS version"):
            restore_backup(self.profile, rewrite(3))

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_a_chosen_backup_folder_keeps_its_permissions(self):
        chosen = self.root / "shared"
        chosen.mkdir(mode=0o755)
        chosen.chmod(0o755)
        create_backup(self.profile, folder=chosen)
        self.assertEqual(chosen.stat().st_mode & 0o777, 0o755)


if __name__ == "__main__":
    unittest.main()
