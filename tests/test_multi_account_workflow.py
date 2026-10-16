# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Independent security work and vault handoffs for sibling service accounts."""
import base64
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from argus_security.bitwarden import add_to_unlocked_cli, make_export
from argus_security.cli import main
from argus_security.handoffs import HandoffError, handoff_snapshot, resolve
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import CHECKLIST, Store
from argus_security.workflow import change_worklist


class SeparateAccountWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / "profile", Registry())
        self.emails = ["first@example.invalid", "second@example.invalid"]
        self.store.configure(self.emails)
        scan_messages(self.store, [synthetic_mail("notify@github.com", "Your account has been created", "",
                                                  recipient=email) for email in self.emails])

    def accounts(self):
        return {a["identity_email"]: a for a in self.store.snapshot()["accounts"]
                if a["provider_id"] == "github" and a["identity_email"]}

    def run_cli(self, ids, runner):
        with patch("argus_security.bitwarden.shutil.which", return_value="/fake/bw"):
            return add_to_unlocked_cli(self.store, ids, runner=runner,
                                       environment={"BW_SESSION": "FAKE-SESSION-NEVER-STORED"})

    @staticmethod
    def successful(arguments, **kwargs):
        if arguments[1] == "status":
            return SimpleNamespace(returncode=0, stdout='{"status":"unlocked"}')
        return SimpleNamespace(returncode=0, stdout=json.dumps({"id": str(uuid.uuid4())}))

    def test_queue_completion_and_one_item_export_are_independent(self):
        first, second = [self.accounts()[email] for email in self.emails]
        self.assertNotEqual(first["id"], second["id"])
        change_worklist(self.store, {"action": "add", "ids": [first["id"], second["id"]]})
        self.store.update_account(first["id"], {"checklist": {k: True for k in CHECKLIST}, "status": "done"})
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["workflow"]["done"], 1)
        self.assertEqual(snapshot["workflow"]["current"], second["id"])
        self.assertFalse(any(self.accounts()[self.emails[1]]["checklist"].values()))
        items = make_export(self.store, [second["id"]])["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["login"]["username"], self.emails[1])
        self.assertEqual(items[0]["login"]["password"], "")
        self.assertEqual(snapshot["summary"]["services_found"], 1)
        self.assertEqual(snapshot["summary"]["found"], 2)

    def test_partial_batch_and_ambiguous_handoff_affect_only_selected_account(self):
        first, second = [self.accounts()[email] for email in self.emails]
        payloads = []
        def fail_second(arguments, **kwargs):
            if arguments[1] == "status":
                return self.successful(arguments, **kwargs)
            payloads.append(json.loads(base64.b64decode(kwargs["input"])))
            if len(payloads) == 2:
                raise subprocess.TimeoutExpired(arguments, 20)
            return self.successful(arguments, **kwargs)
        result = self.run_cli([first["id"], second["id"]], fail_second)
        self.assertEqual((result["items"], result["status"]), (1, "needs_review"))
        self.assertEqual(self.accounts()[self.emails[0]]["steps"]["vault"]["state"], "prepared")
        self.assertEqual(self.accounts()[self.emails[1]]["steps"]["vault"]["state"], "open")
        with self.assertRaises(HandoffError):
            make_export(self.store, [second["id"]])
        entry = next(e for e in handoff_snapshot(self.store) if e["account_id"] == second["id"])
        resolve(self.store, {"id": entry["id"], "created": False, "confirmed": True})
        retry = self.run_cli([second["id"]], self.successful)
        self.assertEqual(retry["items"], 1)
        self.assertTrue(all(a["steps"]["vault"]["state"] == "prepared" for a in self.accounts().values()))
        self.assertTrue(all(not a["checklist"]["password_changed"] for a in self.accounts().values()))
        self.assertNotIn(b"FAKE-SESSION-NEVER-STORED", self.store.path.read_bytes())

    def test_labeled_same_address_account_has_a_separate_handoff(self):
        canonical = self.accounts()[self.emails[0]]
        ident = self.store.create_account({"provider_id": "github", "email": self.emails[0],
                                           "label": "Work account", "confirmed": True})
        self.assertNotEqual(ident, canonical["id"])
        self.assertEqual(self.run_cli([ident], self.successful)["items"], 1)
        rows = {a["id"]: a for a in self.store.snapshot()["accounts"]}
        self.assertEqual(rows[ident]["steps"]["vault"]["state"], "prepared")
        self.assertEqual(rows[canonical["id"]]["steps"]["vault"]["state"], "open")
        self.assertFalse(rows[ident]["evidence"])

    def test_changing_or_clearing_bound_address_does_not_move_completed_work(self):
        first = self.accounts()[self.emails[0]]
        self.store.update_account(first["id"], {"checklist": {k: True for k in CHECKLIST}, "status": "done"})
        for value in ("", self.emails[1]):
            with self.assertRaises(ValueError):
                self.store.update_account(first["id"], {"registered_email": value})
        self.assertEqual(self.accounts()[self.emails[0]]["status"], "done")
        self.assertEqual(self.accounts()[self.emails[1]]["status"], "pending")

    def test_cli_lists_the_two_ids_needed_for_separate_selections(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["--data-dir", str(self.store.data_dir), "list-accounts"]), 0)
        rows = json.loads(output.getvalue())
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["id"] for row in rows}, {a["id"] for a in self.accounts().values()})
        self.assertEqual({row["identity_email"] for row in rows}, set(self.emails))
        self.assertTrue(all("evidence" not in row and "checklist" not in row for row in rows))


if __name__ == "__main__":
    unittest.main()
