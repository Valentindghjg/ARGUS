"""Account identity isolation, local manual entry, and conservative v1 migration."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from argus_security.analysis import analyze
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import CHECKLIST, Store


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.registry = Registry()
        self.directory = Path(self.temp.name) / "data"
        self.store = Store(self.directory, self.registry)
        self.primary, self.secondary = "first@example.invalid", "second@example.invalid"
        self.store.configure([self.primary, self.secondary])

    def tearDown(self):
        self.temp.cleanup()

    def mail(self, email=None, subject="Your account has been created"):
        return synthetic_mail("notify@github.com", subject, "", recipient=email or self.primary)

    def scan(self, email=None):
        return scan_messages(self.store, [self.mail(email)])

    def rows(self, provider="github"):
        return [row for row in self.store.snapshot()["accounts"] if row["provider_id"] == provider]

    def by_email(self):
        return {row["identity_email"]: row for row in self.rows()}

    def finish_primary(self):
        self.store.update_account("github", {"status": "done", "checklist": {key: True for key in CHECKLIST}})

    def restore_legacy(self, *, manual=None, done=True, handoffs=()):
        """Convert the fixture to the exact pre-instance persisted model."""
        with self.store.connect() as db:
            db.execute("DELETE FROM account_instances")
            db.execute("DELETE FROM meta WHERE key='account_instances_migrated'")
            db.execute("""INSERT INTO accounts(provider_id,confirmed,status,checklist,manual_email,updated)
                          VALUES ('github',?,?,?,?, 'legacy')""",
                       (int(done), "done" if done else "pending", json.dumps({key: True for key in CHECKLIST}) if done else "{}", manual))
            db.execute("INSERT INTO work_queue VALUES ('github',4,1)")
            for index, (email, state) in enumerate(handoffs):
                db.execute("""INSERT INTO bitwarden_handoffs(id,provider_id,email,state,operation_id,lease_until,updated)
                              VALUES (?,'github',?,?,?,0,'legacy')""", ("journal-" + str(index), email, state, "op-" + str(index)))
        self.store = Store(self.directory, self.registry)

    def test_new_identity_has_own_progress_and_stable_id(self):
        self.scan()
        self.finish_primary()
        self.scan(self.secondary)
        first, second = self.by_email()[self.primary], self.by_email()[self.secondary]
        self.assertEqual(first["id"], "github")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual((first["status"], second["status"]), ("done", "pending"))
        self.assertFalse(any(second["checklist"].values()))
        self.assertEqual(second["registered_emails"], [self.secondary])
        self.assertEqual(self.store.snapshot()["summary"]["services_found"], 1)
        self.assertEqual(self.store.snapshot()["summary"]["instances_found"], 2)
        self.assertEqual(self.store.snapshot()["summary"]["providers"], len(self.registry.providers))
        self.store = Store(self.directory, self.registry)
        self.assertEqual(self.by_email()[self.secondary]["id"], second["id"])
        self.store.update_account(second["id"], {"checklist": {"reviewed": True}})
        self.assertEqual(self.by_email()[self.primary]["status"], "done")

    def test_aliases_do_not_infer_additional_accounts(self):
        self.scan()
        self.store.add_emails(["third@example.invalid"])
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["registered_emails"], [self.primary])

    def test_forwarded_and_weak_messages_remain_provider_clues(self):
        self.scan()
        self.scan(self.secondary)
        scan_messages(self.store, [self.mail(self.secondary, "Fwd: Your account has been created")])
        rows = self.rows()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["evidence_count"] == 1 for row in rows))
        self.assertTrue(all(row["unassigned_evidence_count"] == 1 for row in rows))
        self.assertTrue(all(row["unassigned_evidence"][0]["registered_email"] is None for row in rows))

    def test_reclassification_removes_proof_without_moving_progress(self):
        self.scan()
        self.finish_primary()
        item = analyze(self.mail(), self.registry, [self.primary, self.secondary])
        self.assertEqual(self.store.record_analysis(item.fingerprint, replace(item, registered_email=self.secondary)), "updated")
        identities = self.by_email()
        self.assertEqual(identities[self.primary]["evidence_count"], 0)
        self.assertEqual(identities[self.primary]["status"], "done")
        self.assertEqual(identities[self.secondary]["status"], "pending")
        self.assertEqual(self.store.record_analysis(item.fingerprint, None), "removed")
        self.assertEqual(self.by_email()[self.secondary]["classification"], "unknown")
        self.assertEqual(self.by_email()[self.primary]["status"], "done")

    def test_stale_evidence_never_proves_a_sibling(self):
        self.scan()
        with self.store.connect() as db:
            db.execute("UPDATE evidence SET rule_version=1")
        row = self.rows()[0]
        self.assertEqual(row["classification"], "unknown")
        self.assertEqual(row["evidence_count"], 0)
        self.assertEqual(row["unassigned_evidence"][0]["score"], 35)
        self.assertIsNone(row["unassigned_evidence"][0]["registered_email"])

    def test_bound_identity_cannot_be_changed_or_cleared(self):
        self.scan()
        self.finish_primary()
        for value in [self.secondary, "", None, "foreign@example.invalid"]:
            with self.assertRaises(ValueError):
                self.store.update_account("github", {"registered_email": value})
        self.assertEqual(self.rows()[0]["identity_email"], self.primary)
        self.assertEqual(self.rows()[0]["status"], "done")

    def test_unassigned_identity_assignment_rejects_conflict_and_prior_transfer(self):
        self.scan()
        unknown = self.store.create_account({"provider_id": "github", "email": "", "label": "Unassigned", "confirmed": True})
        with self.assertRaises(ValueError):
            self.store.update_account(unknown, {"registered_email": self.primary})
        with self.store.connect() as db:
            db.execute("""INSERT INTO instance_bitwarden_handoffs
                (id,account_id,provider_id,email,state,operation_id,updated)
                VALUES ('write',?,'github','','not_created','op','test')""", (unknown,))
        with self.assertRaises(ValueError):
            self.store.update_account(unknown, {"registered_email": self.secondary})
        self.assertIsNone(next(row for row in self.rows() if row["id"] == unknown)["identity_email"])

    def test_explicit_same_email_accounts_require_unique_label_and_do_not_steal_proof(self):
        self.scan()
        base = {"provider_id": "github", "email": self.primary, "confirmed": True}
        with self.assertRaises(ValueError):
            self.store.create_account({**base, "label": ""})
        ident = self.store.create_account({**base, "label": "Work username"})
        row = next(row for row in self.rows() if row["id"] == ident)
        self.assertEqual(row["classification"], "confirmed")
        self.assertEqual(row["evidence_count"], 0)
        self.assertEqual(self.by_email()[self.primary]["registered_emails"], [self.primary])
        with self.assertRaises(ValueError):
            self.store.create_account({**base, "label": "WORK USERNAME"})
        self.assertEqual(next(row for row in self.rows() if row["id"] == "github")["evidence_count"], 1)

    def test_labeled_duplicate_cannot_lose_its_distinguishing_label(self):
        self.scan()
        base = {"provider_id": "github", "email": self.primary, "confirmed": True}
        ident = self.store.create_account({**base, "label": "Straße"})
        for label in ("", "   "):
            with self.assertRaises(ValueError):
                self.store.update_account(ident, {"label": label})
        second = self.store.create_account({**base, "label": "Work"})
        with self.assertRaises(ValueError):
            self.store.update_account(second, {"label": "STRASSE"})

    def test_inconsistent_forwarded_legacy_score_does_not_create_a_probable_account(self):
        item = analyze(self.mail(), self.registry, [self.primary])
        self.store.add_evidence(replace(item, caveat="Forwarding / recipient association uncertain"))
        row = self.rows()[0]
        self.assertEqual(row["classification"], "unknown")
        self.assertIsNone(row["identity_email"])
        self.assertLess(row["unassigned_evidence"][0]["score"], 60)

    def test_manual_entry_rejects_foreign_addresses_unconfirmed_and_control_labels(self):
        entry = {"provider_id": "github", "email": self.primary, "label": "Personal", "confirmed": True}
        for change in [{"email": "foreign@example.invalid"}, {"confirmed": False}, {"label": "bad\nlabel"}, {"label": "x" * 81}, {"provider_id": "unknown"}, {"password": "must-not-be-accepted"}]:
            with self.assertRaises(ValueError):
                self.store.create_account({**entry, **change})
        self.assertEqual(self.rows()[0]["classification"], "unknown")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM account_instances").fetchone()[0], 0)

    def test_migration_multi_email_progress_stays_unassigned(self):
        self.scan()
        self.scan(self.secondary)
        self.restore_legacy()
        identities = self.by_email()
        legacy = identities[None]
        self.assertEqual(legacy["id"], "github")
        self.assertTrue(legacy["identity_review_required"])
        self.assertEqual(legacy["status"], "done")
        from argus_security.bitwarden import make_export
        from argus_security.handoffs import HandoffError
        with self.assertRaises(HandoffError):
            make_export(self.store, [legacy["id"]])
        self.assertEqual(self.store.snapshot()["summary"]["done"], 0)
        self.assertEqual(self.store.snapshot()["workflow"]["items"][0]["step"], "identify")
        for email in [self.primary, self.secondary]:
            self.assertEqual(identities[email]["status"], "pending")
            self.assertFalse(any(identities[email]["checklist"].values()))
        with self.store.connect() as db:
            row = db.execute("SELECT * FROM instance_work_queue").fetchone()
            self.assertEqual((row["account_id"], row["position"], row["deferred"], row["resume_after"]),
                             ("github", 4, 1, None))
        before = {row["id"] for row in self.rows()}
        self.store = Store(self.directory, self.registry)
        self.assertEqual({row["id"] for row in self.rows()}, before)

    def test_migration_explicit_address_anchors_only_that_identity(self):
        self.scan()
        self.scan(self.secondary)
        self.restore_legacy(manual=self.secondary)
        identities = self.by_email()
        self.assertNotIn(None, identities)
        self.assertEqual(identities[self.secondary]["id"], "github")
        self.assertEqual(identities[self.secondary]["status"], "done")
        self.assertEqual(identities[self.primary]["status"], "pending")
        self.assertFalse(any(identities[self.primary]["checklist"].values()))

    def test_migration_single_direct_address_carries_legacy_progress(self):
        self.scan()
        self.restore_legacy()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["identity_email"], self.primary)
        self.assertEqual(self.rows()[0]["status"], "done")
        self.assertFalse(self.rows()[0]["identity_review_required"])

    def test_migration_empty_and_known_email_handoffs_preserve_separate_identity(self):
        self.scan()
        self.restore_legacy(handoffs=[("", "uncertain"), (self.secondary, "created")])
        rows = self.by_email()
        with self.store.connect() as db:
            journals = {row["email"]: dict(row) for row in db.execute("SELECT * FROM instance_bitwarden_handoffs")}
        self.assertEqual(journals[self.secondary]["account_id"], rows[self.secondary]["id"])
        self.assertTrue(rows[self.secondary]["checklist"]["saved_in_bitwarden"])
        self.assertFalse(rows[self.secondary]["checklist"]["password_changed"])
        self.assertEqual(journals[""]["account_id"], rows[None]["id"])
        self.assertTrue(rows[None]["identity_review_required"])
        self.assertNotEqual(journals[""]["account_id"], rows[self.primary]["id"])
        self.assertEqual(journals[""]["operation_id"], "op-0")

    def test_expected_scope_check_prevents_any_new_identity(self):
        item = analyze(self.mail(), self.registry, [self.primary])
        self.assertEqual(self.store.record_analysis(item.fingerprint, item, expected_emails=[self.primary]), "scope_changed")
        self.assertEqual(self.rows()[0]["classification"], "unknown")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM account_instances").fetchone()[0], 0)

    def test_interrupted_migration_rolls_back_state_and_can_restart(self):
        self.scan()
        with self.store.connect() as db:
            db.execute("DELETE FROM account_instances")
            db.execute("DELETE FROM meta WHERE key='account_instances_migrated'")
            db.execute("""INSERT INTO accounts(provider_id,confirmed,status,checklist,updated)
                          VALUES ('github',1,'done',?,'legacy')""",
                       (json.dumps({key: True for key in CHECKLIST}),))
        from argus_security.instances import migrate_instances
        def interrupt_after_copy(db, registry):
            migrate_instances(db, registry)
            raise RuntimeError("Synthetic interruption before commit")
        with patch("argus_security.store.migrate_instances", side_effect=interrupt_after_copy):
            with self.assertRaises(RuntimeError):
                Store(self.directory, self.registry)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM account_instances").fetchone()[0], 0)
            self.assertIsNone(db.execute("SELECT 1 FROM meta WHERE key='account_instances_migrated'").fetchone())
            self.assertEqual(db.execute("SELECT status FROM accounts WHERE provider_id='github'").fetchone()[0], "done")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0], 1)
        self.store = Store(self.directory, self.registry)
        self.assertEqual(self.rows()[0]["status"], "done")
        self.assertEqual(self.rows()[0]["identity_email"], self.primary)


if __name__ == "__main__":
    unittest.main()
