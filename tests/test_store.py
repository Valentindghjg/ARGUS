import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from account_finder.bitwarden import BitwardenCliError, add_to_unlocked_cli, audit_unlocked_cli, make_export, export_file
from account_finder.registry import Registry
from account_finder.scan import file_messages, load_demo, scan_messages, synthetic_mail
from account_finder.store import Store, CHECKLIST


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = Registry()
        self.store = Store(self.root / "data", self.registry)
        self.store.configure(["demo@example.invalid"])

    def tearDown(self):
        self.temp.cleanup()

    def account(self, ident="github"):
        return next(a for a in self.store.snapshot()["accounts"] if a["id"] == ident)

    def scan(self):
        return scan_messages(self.store, [synthetic_mail("notify@github.com", "Your account has been created", "Your account has been created. SECRET-CONTENT")])

    def test_automatic_evidence_never_confirmed(self):
        self.scan()
        self.assertEqual(self.account()["classification"], "probable")
        self.assertEqual(self.account("netflix")["classification"], "unknown")

    def test_dedup_and_manual_status_survive_reimport(self):
        self.assertEqual(self.scan()["evidence"], 1)
        self.store.update_account("github", {"checklist": {key: True for key in CHECKLIST}, "status": "done"})
        self.assertEqual(self.scan()["duplicates"], 1)
        self.assertEqual((self.account()["status"], self.account()["classification"]), ("done", "confirmed"))
        recreated = Store(self.store.data_dir, self.registry)
        self.assertEqual(recreated.snapshot()["summary"]["done"], 1)

    def test_no_raw_content_stored(self):
        self.scan()
        content = self.store.path.read_bytes()
        self.assertNotIn(b"SECRET-CONTENT", content)
        self.assertNotIn(b"Your account has been created", content)

    def test_imap_cursor_updates_merge_independent_folders(self):
        self.store.set_imap_cursor("folder-a", {"validity": "1", "uid": 10})
        self.store.set_imap_cursor("folder-b", {"validity": "2", "uid": 20})
        self.assertEqual(self.store.meta("imap_cursors"), {
            "folder-a": {"validity": "1", "uid": 10},
            "folder-b": {"validity": "2", "uid": 20},
        })

    def test_completion_requires_checklist_and_can_reopen(self):
        with self.assertRaises(ValueError):
            self.store.update_account("github", {"status": "done"})
        self.store.update_account("github", {"checklist": {key: True for key in CHECKLIST}, "status": "done"})
        self.store.update_account("github", {"checklist": {"reviewed": False}})
        self.assertEqual(self.account()["status"], "in_progress")
        self.assertEqual(self.account()["classification"], "unknown")

    def test_sso_does_not_need_separate_password(self):
        self.store.update_account("github", {"login_method":"sso","checklist":{"reviewed":True,"saved_in_bitwarden":True,"login_tested":True},"status":"done"})
        self.assertEqual(self.account()["status"], "done")

    def test_invalid_changes_rejected(self):
        for change in [{"password":"bad"},{"status":"invalid"},{"priority":"extreme"},{"login_method":"invalid"},{"checklist":{"reviewed":"true"}},{"checklist":{"unknown":True}}]:
            with self.assertRaises(ValueError):
                self.store.update_account("github", change)

    def test_bitwarden_empty_passwords_and_official_uri(self):
        self.scan()
        exported = make_export(self.store, ["github"])
        self.assertFalse(exported["encrypted"])
        item = exported["items"][0]
        self.assertEqual(item["login"]["password"], "")
        self.assertIsNone(item["login"]["totp"])
        self.assertEqual(item["login"]["username"], "demo@example.invalid")
        self.assertEqual(item["login"]["uris"][0]["uri"], "https://github.com/")
        self.assertNotIn("SECRET-CONTENT", json.dumps(exported))
        self.assertEqual(item["folderId"], exported["folders"][0]["id"])

    def test_manual_email_must_be_owned_and_does_not_use_vault_email(self):
        self.store.update_account("steam", {"registered_email":"demo@example.invalid", "checklist":{"reviewed":True}})
        exported = make_export(self.store, ["steam"])
        self.assertEqual(exported["items"][0]["login"]["username"], "demo@example.invalid")
        with self.assertRaises(ValueError):
            self.store.update_account("steam", {"registered_email":"bitwarden-login@another.example"})

    def test_export_does_not_change_parent_permissions(self):
        self.scan()
        parent = self.root / "existing"
        parent.mkdir(mode=0o755)
        before = parent.stat().st_mode & 0o777
        export_file(self.store, parent / "bitwarden.json", ["github"])
        self.assertEqual(parent.stat().st_mode & 0o777, before)

    def test_bitwarden_reject_unknown_or_already_assigned(self):
        with self.assertRaises(ValueError):
            make_export(self.store, ["github"])
        self.scan()
        self.store.update_account("github", {"checklist":{"saved_in_bitwarden":True}})
        with self.assertRaises(ValueError):
            make_export(self.store, ["github"])

    def test_cli_transfer_creates_password_free_items_without_reading_vault(self):
        self.scan()
        calls = []
        def runner(arguments, **kwargs):
            calls.append((arguments, kwargs))
            if arguments[1:] == ["status"]:
                return SimpleNamespace(returncode=0, stdout='{"status":"unlocked"}')
            self.assertEqual(arguments[1:3], ["create", "item"])
            return SimpleNamespace(returncode=0, stdout='{"id":"46caf902-0e99-4bc1-bb92-6075b813233c"}')
        with patch("account_finder.bitwarden.shutil.which", return_value="/usr/bin/bw"):
            result = add_to_unlocked_cli(self.store, ["github"], runner=runner, environment={"BW_SESSION":"not-stored"})
        self.assertEqual(result, {"items": 1, "providers": ["github"], "status": "completed"})
        self.assertTrue(self.account()["checklist"]["saved_in_bitwarden"])
        self.assertEqual(len(calls), 2)
        created = calls[1][0][-1]
        import base64
        payload = json.loads(base64.b64decode(created))
        self.assertIsNone(payload["login"]["password"])
        self.assertNotIn("SECRET-CONTENT", json.dumps(payload))
        self.assertEqual(calls[1][1]["env"]["BW_SESSION"], "not-stored")

    def test_cli_transfer_requires_preunlocked_session(self):
        self.scan()
        with self.assertRaises(BitwardenCliError):
            add_to_unlocked_cli(self.store, ["github"], environment={})

    def test_cli_audit_returns_only_match_summary_and_never_persists_vault_fields(self):
        self.scan()
        vault_password = "VAULT-PASSWORD-MUST-NOT-BE-STORED"
        calls = []

        def runner(arguments, **kwargs):
            calls.append((arguments, kwargs))
            if arguments[1:] == ["status"]:
                return SimpleNamespace(returncode=0, stdout='{"status":"unlocked"}')
            self.assertEqual(arguments[1:3], ["list", "items"])
            return SimpleNamespace(returncode=0, stdout=json.dumps([{
                "name": "GitHub personal",
                "fields": [{"name": "Account-Finder-ID", "value": "github"}],
                "login": {"username": "demo@example.invalid", "password": vault_password,
                          "uris": [{"uri": "https://github.com/"}]},
            }]))

        with patch("account_finder.bitwarden.shutil.which", return_value="/usr/bin/bw"):
            result = audit_unlocked_cli(self.store, ["github"], runner=runner,
                                        environment={"BW_SESSION": "not-stored"})
        self.assertEqual(result, {"accounts": [{"account_id": "github", "match": "found", "count": 1}]})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1][0][1:3], ["list", "items"])
        self.assertNotIn(vault_password.encode(), self.store.path.read_bytes())
        self.assertNotIn(b"not-stored", self.store.path.read_bytes())

    def test_export_exclusive_no_overwrite(self):
        self.scan()
        path = self.root / "exports" / "bitwarden.json"
        export_file(self.store, path, ["github"])
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            export_file(self.store, path, ["github"])
        self.assertEqual(path.read_bytes(), before)
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_private_permissions_and_profile_isolation(self):
        if os.name == "posix":
            self.assertEqual(self.store.data_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            self.store.configure(["someone@example.invalid"])
        with self.assertRaises(ValueError):
            load_demo(self.store)

    def test_generator_failure_marks_partial_scan(self):
        def messages():
            yield synthetic_mail("notify@github.com", "Your account has been created", "")
            raise RuntimeError("synthetic failure")
        with self.assertRaises(RuntimeError):
            scan_messages(self.store, messages())
        self.assertEqual(self.store.meta("last_scan")["result"], "partial")
        self.assertFalse(self.store.meta("last_scan")["running"])
        self.assertEqual(self.account()["classification"], "probable")

    def test_eml_and_maildir_import_original_unchanged(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        path = self.root / "sample.eml"
        path.write_bytes(raw)
        self.assertEqual(list(file_messages(path, "eml")), [raw])
        self.assertEqual(path.read_bytes(), raw)
        maildir = self.root / "maildir"
        (maildir / "cur").mkdir(parents=True)
        (maildir / "new").mkdir()
        (maildir / "new" / "one").write_bytes(raw)
        self.assertEqual(list(file_messages(maildir, "maildir")), [raw])

    def test_mbox_read_does_not_alter_file(self):
        raw = synthetic_mail("notify@github.com", "Your account has been created", "")
        path = self.root / "sample.mbox"
        path.write_bytes(b"From sender Mon Oct 05 10:00:00 2026\n" + raw + b"\n")
        before = path.read_bytes()
        messages = list(file_messages(path, "mbox"))
        self.assertEqual(len(messages), 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(path.with_name(path.name + ".lock").exists())

    def test_demo_expected_results(self):
        demo = Store(self.root / "demo", self.registry)
        load_demo(demo)
        summary = demo.snapshot()["summary"]
        self.assertEqual((summary["found"], summary["confirmed"], summary["done"]), (12,2,1))
        self.assertEqual(len(demo.snapshot()["candidates"]), 2)
