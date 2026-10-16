# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""ADR-0001 state model: migration of every 1.x state, change log and the model's rules."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from argus_security import changes
from argus_security.backup import read_manifest, restore_backup, schema_version
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.states import from_legacy
from argus_security.store import CORE_SCHEMA, SCHEMA_VERSION, Store

OWN = "owner@example.invalid"

# Frozen copy of the 1.9-1.16 account table, only to build old profiles here.
V1_TABLES = """
CREATE TABLE account_instances (
  id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, identity_email TEXT,
  canonical INTEGER NOT NULL DEFAULT 1, label TEXT NOT NULL DEFAULT '',
  identity_review_required INTEGER NOT NULL DEFAULT 0, confirmed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending', checklist TEXT NOT NULL DEFAULT '{}',
  priority_override TEXT, login_method TEXT NOT NULL DEFAULT 'password', manual_email TEXT,
  updated TEXT NOT NULL);
CREATE INDEX instances_provider ON account_instances(provider_id);
CREATE UNIQUE INDEX instances_canonical_email ON account_instances(provider_id,identity_email)
  WHERE canonical=1 AND identity_email IS NOT NULL;
CREATE TABLE instance_work_queue (account_id TEXT PRIMARY KEY, position INTEGER NOT NULL,
  deferred INTEGER NOT NULL DEFAULT 0, resume_after TEXT);
CREATE TABLE instance_bitwarden_handoffs (id TEXT PRIMARY KEY, account_id TEXT NOT NULL,
  provider_id TEXT NOT NULL, email TEXT NOT NULL, state TEXT NOT NULL, operation_id TEXT NOT NULL,
  lease_until REAL NOT NULL DEFAULT 0, vault_item_id TEXT, updated TEXT NOT NULL, UNIQUE(account_id,email));
"""
ALL = {key: True for key in ("reviewed", "saved_in_bitwarden", "password_changed", "login_tested", "mfa_checked")}
# id, identity, review, confirmed, status, checklist, login method
V1_ROWS = [
    ("github", OWN, 0, 1, "in_progress", {"reviewed": True}, "password"),
    ("discord", OWN, 0, 1, "done", {**ALL, "mfa_checked": False}, "password"),
    ("steam", OWN, 0, 1, "done", ALL, "password"),
    ("spotify", OWN, 0, 0, "skipped", {}, "password"),
    ("netflix", OWN, 0, 1, "in_progress", {"reviewed": True, "saved_in_bitwarden": True}, "password"),
    ("epic", OWN, 0, 1, "in_progress", {"reviewed": True, "saved_in_bitwarden": True}, "password"),
    ("notion", OWN, 0, 1, "in_progress", {"reviewed": True}, "sso"),
    ("klarna", None, 1, 1, "in_progress", {"reviewed": True, "login_tested": True}, "password"),
    ("apple", None, 0, 0, "pending", {}, "password"),
]


class StateModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.profile = self.root / "profile"

    def build_v1_profile(self):
        self.profile.mkdir()
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db, db:
            db.executescript(CORE_SCHEMA + V1_TABLES)
            for key, value in {"emails": [OWN], "demo": False, "account_instances_migrated": True,
                               "schema_version": 1}.items():
                db.execute("INSERT INTO meta VALUES (?,?)", (key, json.dumps(value)))
            for ident, email, review, confirmed, status, checklist, method in V1_ROWS:
                db.execute("""INSERT INTO account_instances(id,provider_id,identity_email,identity_review_required,
                              confirmed,status,checklist,login_method,updated) VALUES (?,?,?,?,?,?,?,?,?)""",
                           (ident, ident, email, review, confirmed, status, json.dumps(checklist), method,
                            "2026-01-02T03:04:05+00:00"))
            db.execute("INSERT INTO instance_work_queue VALUES ('github',1,0,NULL)")
            db.execute("""INSERT INTO instance_bitwarden_handoffs VALUES
                          ('h1','netflix','netflix',?,'created','op-1',0,'11111111-1111-4111-8111-111111111111','x')""", (OWN,))

    def accounts(self, store):
        return {account["id"]: account for account in store.snapshot()["accounts"]}

    def test_every_1x_state_maps_to_the_documented_axes(self):
        self.build_v1_profile()
        store = Store(self.profile, Registry())
        accounts = self.accounts(store)
        state = lambda ident, step: accounts[ident]["steps"][step]["state"]
        # "reviewed" confirms the decision and the sign-in check, nothing else.
        self.assertEqual((accounts["github"]["decision"], state("github", "identity"), state("github", "vault")),
                         ("confirmed", "done", "open"))
        self.assertEqual(accounts["github"]["decided_at"], "2026-01-02T03:04:05+00:00")
        # Done stays done; an unticked 1.x MFA box becomes not applicable, never "reviewed".
        self.assertEqual(accounts["discord"]["progress"], "complete")
        self.assertEqual(state("discord", "mfa_recovery"), "not_applicable")
        self.assertEqual(state("steam", "mfa_recovery"), "done")
        self.assertEqual(accounts["steam"]["completed_at"], "2026-01-02T03:04:05+00:00")
        # "skipped" exists only as a worklist deferral now.
        self.assertTrue(accounts["spotify"]["deferred"])
        self.assertEqual(accounts["spotify"]["status"], "skipped")
        self.assertEqual(accounts["spotify"]["decision"], "undecided")
        # An item ARGUS created is prepared; one the person ticked is done.
        self.assertEqual(state("netflix", "vault"), "prepared")
        self.assertEqual(state("epic", "vault"), "done")
        self.assertEqual(state("notion", "password"), "not_applicable")
        # A pending identity review keeps the identity open and blocks completion.
        self.assertEqual((state("klarna", "identity"), state("klarna", "signin_test")), ("open", "done"))
        self.assertEqual(accounts["apple"]["progress"], "not_started")
        # Worklist rows, handoffs and ids survive unchanged.
        with store.connect() as db:
            self.assertEqual(db.execute("SELECT position FROM instance_work_queue WHERE account_id='github'").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT account_id FROM instance_bitwarden_handoffs").fetchone()[0], "netflix")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(account_instances)")}
        self.assertNotIn("checklist", columns)
        self.assertEqual(schema_version(store.path), SCHEMA_VERSION)

    def test_migration_backup_restores_the_1x_profile(self):
        self.build_v1_profile()
        Store(self.profile, Registry())
        backups = sorted((self.profile / "backups").glob("*pre-migration-v1-to-v2*.zip"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(read_manifest(backups[0])["schema_version"], 1)
        target = self.root / "restored"
        restore_backup(target, backups[0])
        with closing(sqlite3.connect(target / "accounts.sqlite3")) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(account_instances)")}
        self.assertIn("checklist", columns)
        # The restored 1.x profile migrates again to the same result.
        again = self.accounts(Store(target, Registry()))
        self.assertEqual(again["discord"]["progress"], "complete")

    def test_an_interrupted_migration_leaves_the_1x_profile_intact(self):
        self.build_v1_profile()
        calls = []
        def fail_late(state, created):
            calls.append(state["id"])
            if len(calls) == 3:
                raise RuntimeError("power loss")
            return from_legacy(state, created)
        with patch("argus_security.instances.from_legacy", side_effect=fail_late), self.assertRaises(RuntimeError):
            Store(self.profile, Registry())
        with closing(sqlite3.connect(self.profile / "accounts.sqlite3")) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(account_instances)")}
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            count = db.execute("SELECT COUNT(*) FROM account_instances").fetchone()[0]
        self.assertIn("checklist", columns)
        self.assertNotIn("account_instances_v1", tables)
        self.assertEqual(count, len(V1_ROWS))
        self.assertEqual(schema_version(self.profile / "accounts.sqlite3"), 1)
        self.assertEqual(self.accounts(Store(self.profile, Registry()))["steam"]["progress"], "complete")

    def personal_store(self):
        store = Store(self.profile, Registry())
        store.configure([OWN])
        scan_messages(store, [synthetic_mail("noreply@github.com", "Your account has been created", "", recipient=OWN)])
        return store

    def test_new_evidence_changes_only_axis_a(self):
        store = self.personal_store()
        store.update_account("github", {"checklist": {"reviewed": True, "saved_in_bitwarden": True}})
        before = self.accounts(store)["github"]
        scan_messages(store, [synthetic_mail("security@github.com", "New sign-in to your account", "", recipient=OWN)])
        after = self.accounts(store)["github"]
        for key in ("decision", "decided_at", "steps", "progress"):
            self.assertEqual(after[key], before[key])
        self.assertEqual(after["evidence_count"], before["evidence_count"] + 1)

    def log(self, store):
        with store.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM change_log ORDER BY id")]

    def test_every_change_to_decision_steps_and_planning_is_logged_per_action(self):
        store = self.personal_store()
        store.update_account("github", {"checklist": {"reviewed": True, "saved_in_bitwarden": True}})
        store.update_account("github", {"login_method": "sso"})
        store.update_account("github", {"status": "skipped"})
        entries = self.log(store)
        self.assertEqual([entry["field"] for entry in entries],
                         ["decision", "step:identity", "step:vault", "step:password", "planning"])
        self.assertEqual(len({entry["batch"] for entry in entries}), 3)
        self.assertEqual(json.loads(entries[0]["old"])["decision"], "undecided")
        self.assertEqual(json.loads(entries[0]["new"])["decision"], "confirmed")
        self.assertEqual(json.loads(entries[3]["new"])["state"], "not_applicable")
        self.assertEqual(json.loads(entries[4]["new"])["deferred"], True)
        # An unchanged value is not logged again.
        store.update_account("github", {"checklist": {"reviewed": True}})
        self.assertEqual(len(self.log(store)), 5)

    def test_change_log_keeps_whole_batches_within_its_limit(self):
        store = self.personal_store()
        with patch.object(changes, "KEEP_ENTRIES", 4):
            for _ in range(3):
                store.update_account("github", {"checklist": {"reviewed": True, "saved_in_bitwarden": True}})
                store.update_account("github", {"checklist": {"reviewed": False, "saved_in_bitwarden": False}})
        entries = self.log(store)
        self.assertLessEqual(len(entries), 6)
        sizes = {}
        for entry in entries:
            sizes[entry["batch"]] = sizes.get(entry["batch"], 0) + 1
        self.assertTrue(all(size == 3 for size in sizes.values()), sizes)

    def test_automatic_vault_preparation_is_the_only_automatic_step_change(self):
        store = self.personal_store()
        from argus_security import handoffs
        attempt = handoffs.reserve(store, "github", OWN)
        handoffs.finish(store, attempt, "created", "22222222-2222-4222-8222-222222222222")
        account = self.accounts(store)["github"]
        self.assertEqual(account["steps"]["vault"]["state"], "prepared")
        self.assertEqual(account["decision"], "undecided")
        self.assertEqual([entry["field"] for entry in self.log(store)], ["step:vault"])
        # The person's own tick makes it done; unticking returns to open.
        store.update_account("github", {"checklist": {"saved_in_bitwarden": True}})
        self.assertEqual(self.accounts(store)["github"]["steps"]["vault"]["state"], "done")


if __name__ == "__main__":
    unittest.main()
