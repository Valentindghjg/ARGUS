# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Profile backups: automatic before migrations, manual, and restores that are actually tested."""
from contextlib import closing, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from argus_security import backup
from argus_security.backup import BackupError, create_backup, list_backups, read_manifest, restore_backup
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.imap_client import IMAPConfig, save_config
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import SCHEMA_VERSION, Store

OWN = "owner@example.invalid"


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail("noreply@github.com", "Your account has been created", "", recipient=OWN)])
        self.store.update_account("github", {"checklist": {"reviewed": True}})

    def account(self, store=None):
        return next(a for a in (store or self.store).snapshot()["accounts"] if a["id"] == "github")

    def backups(self):
        folder = self.profile / "backups"
        return sorted(folder.glob("*.zip")) if folder.is_dir() else []

    def test_restore_brings_back_exactly_the_saved_profile(self):
        save_config(self.profile / "imap.json", IMAPConfig("imap.example.invalid", OWN, folders=("INBOX",)))
        archive = create_backup(self.profile)
        self.assertEqual(read_manifest(archive)["reason"], "manual")
        if os.name == "posix":
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertEqual(archive.parent.stat().st_mode & 0o777, 0o700)
        before = self.store.snapshot()
        self.store.update_account("github", {"checklist": {"saved_in_bitwarden": True}, "priority": "critical"})
        (self.profile / "imap.json").unlink()
        result = restore_backup(self.profile, archive)
        restored = Store(self.profile, Registry())
        self.assertEqual(restored.snapshot()["accounts"], before["accounts"])
        self.assertTrue((self.profile / "imap.json").is_file())
        # The replaced state was saved first and can itself be restored.
        safety = Path(result["safety_backup"])
        self.assertEqual(read_manifest(safety)["reason"], "pre-restore")
        restore_backup(self.profile, safety)
        self.assertEqual(self.account(Store(self.profile, Registry()))["priority"], "critical")

    def test_backup_is_consistent_while_another_process_writes(self):
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3", timeout=1)) as writer:
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("INSERT INTO meta VALUES ('uncommitted','true')")
            archive = create_backup(self.profile)
            writer.rollback()
        target = self.root / "check"
        restore_backup(target, archive)
        with closing(sqlite3.connect(target / "accounts.sqlite3")) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM meta WHERE key='uncommitted'").fetchone())
            self.assertIsNotNone(db.execute("SELECT 1 FROM evidence").fetchone())

    def tampered(self, name, change):
        source = create_backup(self.profile)
        target = self.root / name
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, "w") as copy:
            members = {info.filename: original.read(info.filename) for info in original.infolist()}
            for member, data in change(members).items():
                copy.writestr(member, data)
        return target

    def test_damaged_or_foreign_archives_never_touch_the_profile(self):
        manifest = lambda members: json.loads(members["manifest.json"])
        flip = lambda data: data[:200] + bytes([data[200] ^ 0xFF]) + data[201:]
        def newer(members):
            data = manifest(members)
            data["version"] = 99
            return {**members, "manifest.json": json.dumps(data)}
        def not_sqlite(members):
            data, fake = manifest(members), b"not a database" * 100
            import hashlib
            data["files"]["accounts.sqlite3"] = {"sha256": hashlib.sha256(fake).hexdigest(), "size": len(fake)}
            return {**members, "accounts.sqlite3": fake, "manifest.json": json.dumps(data)}
        cases = {
            "checksum": lambda members: {**members, "accounts.sqlite3": flip(members["accounts.sqlite3"])},
            "traversal": lambda members: {**members, "../escape.txt": b"x"},
            "no-manifest": lambda members: {k: v for k, v in members.items() if k != "manifest.json"},
            "newer": newer,
            "not-sqlite": not_sqlite,
        }
        before = (self.profile / "accounts.sqlite3").read_bytes()
        for name, change in cases.items():
            with self.subTest(case=name), self.assertRaises(BackupError):
                restore_backup(self.profile, self.tampered(name + ".zip", change))
            self.assertEqual((self.profile / "accounts.sqlite3").read_bytes(), before)
            self.assertFalse((self.root / "escape.txt").exists())
            self.assertEqual([p for p in self.profile.iterdir() if p.name.startswith(".argus-restore-")], [])
        plain = self.root / "plain.zip"
        plain.write_bytes(b"not a zip")
        with self.assertRaises(BackupError):
            restore_backup(self.profile, plain)

    def test_older_profile_is_backed_up_once_before_migration(self):
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.execute("DELETE FROM meta WHERE key='schema_version'")
        Store(self.profile, Registry())
        automatic = self.backups()
        self.assertEqual(len(automatic), 1)
        self.assertIn("pre-migration-v0-to-v", automatic[0].name)
        self.assertIsNone(read_manifest(automatic[0])["schema_version"])
        Store(self.profile, Registry())
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(backup.schema_version(self.profile / "accounts.sqlite3"), SCHEMA_VERSION)

    def test_a_failed_backup_stops_the_migration(self):
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.execute("DELETE FROM meta WHERE key='schema_version'")
        with patch("argus_security.backup.create_backup", side_effect=BackupError("x")), \
                self.assertRaises(BackupError):
            Store(self.profile, Registry())
        self.assertIsNone(backup.schema_version(self.profile / "accounts.sqlite3"))

    def test_profile_from_a_newer_version_is_not_opened(self):
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
        with self.assertRaises(UserFacingError):
            Store(self.profile, Registry())
        self.assertEqual(self.backups(), [])

    def test_new_profiles_need_no_backup_and_automatic_backups_are_pruned(self):
        Store(self.root / "fresh", Registry())
        self.assertFalse((self.root / "fresh" / "backups").exists())
        manual = create_backup(self.profile)
        for _ in range(backup.KEEP_AUTOMATIC + 2):
            create_backup(self.profile, reason="pre-migration")
        remaining = self.backups()
        self.assertIn(manual, remaining)
        self.assertEqual(len(remaining), backup.KEEP_AUTOMATIC + 1)
        self.assertEqual(len(list_backups(self.profile)), backup.KEEP_AUTOMATIC + 1)

    def run_cli(self, *arguments):
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            code = main(["--language", "en", "--data-dir", str(self.profile), *arguments])
        return code, out.getvalue()

    def test_cli_backup_and_confirmed_restore(self):
        code, output = self.run_cli("backup")
        self.assertEqual(code, 0)
        archive = self.backups()[0]
        self.assertIn(str(archive), output)
        self.store.update_account("github", {"priority": "critical"})
        code, output = self.run_cli("restore", str(archive))
        self.assertEqual(code, 0)
        self.assertIn("--yes", output)
        self.assertEqual(self.account()["priority"], "critical")
        code, output = self.run_cli("restore", str(archive), "--yes")
        self.assertEqual(code, 0)
        self.assertIn("previous state was saved", output)
        self.assertNotEqual(self.account(Store(self.profile, Registry()))["priority"], "critical")
        code, output = self.run_cli("backup", "--list")
        self.assertEqual({entry["reason"] for entry in json.loads(output)}, {"manual", "pre-restore"})


if __name__ == "__main__":
    unittest.main()
