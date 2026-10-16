# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Master plan B2 and F6: the exact Bitwarden items are shown before any write."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from argus_security.bitwarden import (ACCOUNT_FIELD, PROVIDER_FIELD, TRANSFER_FIELD, make_export,
                                      preview_export)
from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security import handoffs
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"


class ExportPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root / "profile", Registry())
        self.store.configure([OWN])
        scan_messages(self.store, [synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
                                   for sender in ("noreply@github.com", "support@discord.com")])

    def journal(self):
        with self.store.connect() as db:
            return db.execute("SELECT COUNT(*) FROM instance_bitwarden_handoffs").fetchone()[0]

    def test_preview_shows_exactly_what_the_download_writes(self):
        preview = preview_export(self.store, ["github", "discord"], "de")
        exported = make_export(self.store, ["github", "discord"], "de")
        self.assertEqual(preview["target"], "file")
        self.assertEqual(preview["folder"], exported["folders"][0]["name"])
        self.assertEqual([(item["name"], item["uri"], item["username"], item["notes"]) for item in preview["items"]],
                         [(item["name"], item["login"]["uris"][0]["uri"], item["login"]["username"], item["notes"])
                          for item in exported["items"]])
        for shown, written in zip(preview["items"], exported["items"]):
            self.assertEqual(shown["fields"], [field["name"] for field in written["fields"]])
            self.assertEqual(shown["account_id"], written["fields"][0]["value"])
            self.assertEqual(shown["username"], OWN)
            self.assertNotIn("password", json.dumps(shown).casefold().replace("password-free", ""))
        self.assertEqual(self.journal(), 0)

    def test_direct_transfer_preview_names_the_transfer_field_and_writes_nothing(self):
        preview = preview_export(self.store, ["github"], "en", "cli")
        self.assertIsNone(preview["folder"])
        self.assertEqual(preview["items"][0]["fields"], [ACCOUNT_FIELD, PROVIDER_FIELD, TRANSFER_FIELD])
        self.assertEqual(self.journal(), 0)
        self.assertEqual(sorted(path.name for path in (self.root / "profile").iterdir()), ["accounts.sqlite3"])

    def test_accounts_the_journal_records_as_created_are_listed_not_written(self):
        attempt = handoffs.reserve(self.store, "github", OWN)
        handoffs.finish(self.store, attempt, "created", "11111111-1111-4111-8111-111111111111")
        # The user later unticks the checklist step; the journal still knows.
        self.store.update_account("github", {"checklist": {"saved_in_bitwarden": False}})
        preview = preview_export(self.store, ["github", "discord"])
        self.assertEqual([item["account_id"] for item in preview["items"]], ["discord"])
        self.assertEqual(preview["already_created"], ["github"])
        with self.assertRaises(UserFacingError):
            preview_export(self.store, ["github"])

    def test_invalid_target_and_selection_are_rejected(self):
        with self.assertRaises(UserFacingError):
            preview_export(self.store, ["github"], "en", "vault")
        with self.assertRaises(UserFacingError):
            preview_export(self.store, [], "en")
        with self.assertRaises(UserFacingError):
            preview_export(self.store, ["zalando"], "en")

    def test_cli_preview_prints_items_and_creates_no_file(self):
        target = self.root / "export.json"
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            code = main(["--language", "en", "--data-dir", str(self.root / "profile"), "bitwarden-export",
                         str(target), "--id", "github", "--preview"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["items"][0]["name"], "GitHub")
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
