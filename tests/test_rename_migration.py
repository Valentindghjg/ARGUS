# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""The ARGUS rename must keep existing profiles, vault links and commands working."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from argus_security import __version__
from argus_security.bitwarden import ACCOUNT_FIELD, _audit_result, make_export
from argus_security.cli import default_data_dir, main
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

REPOSITORY = Path(__file__).resolve().parents[1]


class DefaultProfileMigration(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        redirect = patch("argus_security.cli.data_root", return_value=self.root)
        redirect.start()
        self.addCleanup(redirect.stop)

    def legacy_profile(self):
        legacy = self.root / "account-finder"
        store = Store(legacy, Registry())
        store.configure(["person@example.invalid"])
        (legacy / "imap.json").write_text("{}", encoding="utf-8")
        return legacy

    def test_pre_rename_profile_moves_once_with_contents_and_permissions(self):
        legacy = self.legacy_profile()
        mode = legacy.stat().st_mode & 0o777
        errors = StringIO()
        with redirect_stderr(errors):
            current = default_data_dir("en")
        self.assertEqual(current, self.root / "argus")
        self.assertFalse(legacy.exists())
        self.assertTrue((current / "imap.json").is_file())
        self.assertEqual(current.stat().st_mode & 0o777, mode)
        self.assertEqual(Store(current, Registry()).meta("emails"), ["person@example.invalid"])
        self.assertIn("Moved your profile", errors.getvalue())
        with redirect_stderr(StringIO()) as quiet:
            self.assertEqual(default_data_dir("en"), current)
        self.assertEqual(quiet.getvalue(), "")

    def test_existing_new_profile_wins_and_old_folder_is_never_touched(self):
        legacy = self.legacy_profile()
        (self.root / "argus").mkdir(mode=0o700)
        errors = StringIO()
        with redirect_stderr(errors):
            self.assertEqual(default_data_dir("de"), self.root / "argus")
        self.assertTrue((legacy / "accounts.sqlite3").is_file())
        self.assertIn("älterer Profilordner", errors.getvalue())

    def test_symlinked_legacy_folder_is_not_followed(self):
        target = self.root / "elsewhere"
        target.mkdir()
        (self.root / "account-finder").symlink_to(target, target_is_directory=True)
        self.assertEqual(default_data_dir("en"), self.root / "argus")
        self.assertTrue((self.root / "account-finder").is_symlink())
        self.assertFalse((self.root / "argus").exists())

    def test_concurrent_move_by_another_process_uses_the_new_folder(self):
        legacy = self.legacy_profile()

        def raced(self_path, target):
            os.rename(self_path, target)
            raise FileNotFoundError("already moved")

        with patch.object(Path, "rename", raced), redirect_stderr(StringIO()):
            self.assertEqual(default_data_dir("en"), self.root / "argus")
        self.assertFalse(legacy.exists())

    def test_explicit_data_dir_is_never_migrated(self):
        legacy = self.legacy_profile()
        explicit = self.root / "chosen"
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(main(["--data-dir", str(explicit), "init", "--email", "person@example.invalid"]), 0)
        self.assertTrue(legacy.is_dir())
        self.assertFalse((self.root / "argus").exists())

    def test_default_command_uses_the_migrated_profile(self):
        self.legacy_profile()
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(StringIO()):
            self.assertEqual(main(["report"]), 0)
        self.assertIn('"providers"', output.getvalue())
        self.assertTrue((self.root / "argus" / "accounts.sqlite3").is_file())


class RenamedIdentifiers(unittest.TestCase):
    def test_bitwarden_items_use_the_argus_field_and_audit_accepts_both_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "profile", Registry())
            store.configure(["demo@example.invalid"])
            scan_messages(store, [synthetic_mail("notify@github.com", "Your account has been created", "")])
            export = make_export(store, ["github"], "en")
            fields = {field["name"] for field in export["items"][0]["fields"]}
            self.assertEqual(fields, {ACCOUNT_FIELD, "ARGUS-Provider-ID"})
            self.assertTrue(export["folders"][0]["name"].startswith("ARGUS · "))
            self.assertTrue(export["items"][0]["notes"].startswith("ARGUS: "))
            account = next(a for a in store.snapshot()["accounts"] if a["id"] == "github")
            for name in (ACCOUNT_FIELD, "Account-Finder-ID"):
                item = {"name": "x", "fields": [{"name": name, "value": "github"}], "login": {}}
                self.assertEqual(_audit_result(account, [item])["match"], "found", name)

    def test_legacy_module_and_command_still_work_with_a_notice(self):
        result = subprocess.run([sys.executable, "-m", "account_finder", "--language", "en", "--help"],
                                cwd=REPOSITORY, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: argus", result.stdout)
        self.assertIn("deprecated", result.stderr)
        current = subprocess.run([sys.executable, "-m", "argus_security", "--language", "de", "--help"],
                                 cwd=REPOSITORY, capture_output=True, text=True, timeout=60)
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertIn("Aufruf: argus", current.stdout)
        self.assertEqual(current.stderr, "")

    def test_dashboard_reports_argus_identity_and_single_version_source(self):
        import http.client
        import threading
        from contextlib import closing
        from argus_security.server import DashboardServer
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "profile", Registry())
            store.configure(["demo@example.invalid"])
            server = DashboardServer(store, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with closing(http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)) as connection:
                    connection.request("GET", "/")
                    response = connection.getresponse()
                    page = response.read().decode("utf-8")
                    self.assertTrue(response.getheader("Server").startswith("ARGUS"))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
        self.assertIn(f"ARGUS / {__version__}", page)
        self.assertNotIn("__APP_VERSION__", page)
        self.assertNotIn("Account Compass", page)
        pyproject = (REPOSITORY / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertNotIn('\nversion = "', pyproject)

    def test_translations_use_the_new_name(self):
        catalog = json.loads((REPOSITORY / "argus_security" / "data" / "translations.json").read_text(encoding="utf-8"))
        self.assertFalse([key for key in catalog["de"] if "Account Compass" in key or "Account-Finder" in key])


if __name__ == "__main__":
    unittest.main()
