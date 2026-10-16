# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan E5 and E6: a validated personal catalog, shared senders, visible rule changes."""
from contextlib import closing, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from argus_security.cli import report_scan
from argus_security.errors import UserFacingError
from argus_security.i18n import translate
from argus_security.registry import Registry, is_shared_sender
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"
NEW = {"name": "New Service", "website": "https://new-service.example/", "category": "Productivity",
       "domains": ["new-service.example"], "priority": "normal"}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])
        self.raw = synthetic_mail("hello@new-service.example", "Your account has been created", "", recipient=OWN)
        scan_messages(self.store, [self.raw])

    def test_addition_is_validated_private_and_waits_for_a_reimport(self):
        self.assertEqual([c["domain"] for c in self.store.snapshot()["candidates"]], ["new-service.example"])
        ident = self.store.add_provider(dict(NEW))["id"]
        self.assertEqual(ident, "new-service-mine")
        catalog_file = self.profile / "my-providers.json"
        if os.name == "posix":
            self.assertEqual(catalog_file.stat().st_mode & 0o777, 0o600)
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["catalog"]["personal"][0]["source"], "personal")
        # The clue stays visible until its email is imported again.
        self.assertEqual([(c["domain"], c["catalog_match"]) for c in snapshot["candidates"]],
                         [("new-service.example", "New Service")])
        self.assertEqual(snapshot["catalog"]["reanalysis"], 1)
        # Only the original email can assign the stored clue.
        result = scan_messages(self.store, [self.raw])
        self.assertEqual(result["rule_changes_count"], 1)
        account = next(a for a in self.store.snapshot()["accounts"] if a["provider_id"] == ident)
        self.assertEqual((account["evidence_level"], account["identity_email"]), ("probable", OWN))
        self.assertEqual((self.store.snapshot()["catalog"]["reanalysis"], self.store.snapshot()["candidates"]), (0, []))
        # A new process loads the profile's additions again.
        self.assertIn(ident, Store(self.profile, Registry()).registry.providers)

    def test_invalid_or_conflicting_additions_are_refused_without_changes(self):
        cases = {
            "shared sender": {**NEW, "domains": ["bounce.sendgrid.net"]},
            "catalog domain": {**NEW, "domains": ["github.com"], "website": "https://github.com/"},
            "http website": {**NEW, "website": "http://new-service.example/"},
            "foreign website": {**NEW, "website": "https://elsewhere.example/"},
            "category": {**NEW, "category": "Spyware"},
            "priority": {**NEW, "priority": "urgent"},
            "too many domains": {**NEW, "domains": [f"d{i}.example" for i in range(6)]},
            "empty name": {**NEW, "name": " "},
            "extra field": {**NEW, "password_url": "https://new-service.example/pw"},
        }
        for case, data in cases.items():
            with self.subTest(case=case), self.assertRaises(UserFacingError):
                self.store.add_provider(data)
        self.assertFalse((self.profile / "my-providers.json").exists())
        self.assertEqual([p.name for p in self.profile.iterdir() if p.name.startswith(".my-providers-")], [])

    def test_only_unused_additions_can_be_removed(self):
        ident = self.store.add_provider(dict(NEW))["id"]
        other = self.store.add_provider({**NEW, "name": "Spare", "domains": ["spare.example"],
                                         "website": "https://spare.example/"})["id"]
        self.store.remove_provider(other)
        self.assertNotIn(other, self.store.registry.providers)
        scan_messages(self.store, [self.raw])
        with self.assertRaises(UserFacingError):
            self.store.remove_provider(ident)
        with self.assertRaises(UserFacingError):
            self.store.remove_provider("github")

    def test_shared_senders_never_identify_a_provider(self):
        self.assertTrue(is_shared_sender("o1.ptr1234.sendgrid.net"))
        self.assertFalse(is_shared_sender("github.com"))
        extra = self.root / "extra.json"
        extra.write_text(json.dumps({"providers": [{**NEW, "id": "mailer", "domains": ["amazonses.com"],
                                                    "website": "https://amazonses.com/"}]}), encoding="utf-8")
        with self.assertRaises(ValueError):
            Registry(extra)
        scan_messages(self.store, [synthetic_mail("bounce@amazonses.com", "Your account has been created", "",
                                                  recipient=OWN)])
        candidate = next(c for c in self.store.snapshot()["candidates"] if c["domain"] == "amazonses.com")
        self.assertTrue(candidate["shared_sender"])
        item = next(i for i in self.store.snapshot()["unclear"] if i.get("domain") == "amazonses.com")
        self.assertTrue(item["shared"])

    def test_reanalysis_lists_what_current_rules_changed(self):
        raw = synthetic_mail("noreply@github.com", "Your account has been created", "", recipient=OWN)
        scan_messages(self.store, [raw])
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("UPDATE evidence SET signal='welcome_account', score=70 WHERE provider_id='github'")
        self.store.decide("github", "confirmed")
        result = scan_messages(self.store, [raw])
        change = result["rule_changes"][0]
        self.assertEqual((change["old_reason"], change["new_reason"]),
                         ("Welcome message with account context", "Registration / account creation reported"))
        self.assertEqual((change["old_score"], change["new_score"]), (70, 90))
        # Decisions survive any re-analysis.
        self.assertEqual(next(a for a in self.store.snapshot()["accounts"] if a["id"] == "github")["decision"], "confirmed")
        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            report_scan(result, lambda message, **values: translate(message, "de", **values))
        self.assertIn("1 gespeicherte(n) Hinweis(e) geändert", errors.getvalue())


class ProposalTemplateTests(unittest.TestCase):
    """Plan G3: the public proposal form offers exactly the catalog's categories."""

    def test_template_categories_match_the_catalog(self):
        text = (Path(__file__).resolve().parents[1] / ".github" / "ISSUE_TEMPLATE" / "provider.yml").read_text(encoding="utf-8")
        block = text.split("id: category", 1)[1].split("validations:", 1)[0]
        offered = [line.strip()[2:] for line in block.splitlines() if line.strip().startswith("- ")]
        self.assertEqual(offered, sorted({p.category for p in Registry().providers.values()}))
        self.assertIn("Do not attach real emails", text)


if __name__ == "__main__":
    unittest.main()
