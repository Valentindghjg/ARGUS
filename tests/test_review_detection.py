# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Regressions from the 2.6 review: catalog additions, digest, worklist order, identity links, reviews, sessions."""
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store
from argus_security.workflow import change_worklist

OWN = "owner@example.invalid"
SHOP = {"name": "Tiny Shop", "website": "https://shop.example", "category": "Shopping",
        "domains": ["shop.example"], "priority": "normal"}


def created(sender):
    return synthetic_mail(sender, "Your account has been created", "Your account has been created.", recipient=OWN)


class ReviewDetectionTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.profile = self.root / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN])

    def accounts(self, store=None):
        return {a["id"]: a for a in (store or self.store).snapshot()["accounts"]}

    def test_an_addition_the_catalog_later_covers_never_locks_the_profile(self):
        ident = self.store.add_provider(SHOP)["id"]
        scan_messages(self.store, [created("hello@shop.example")])
        extra = self.root / "extra.json"
        extra.write_text(json.dumps({"providers": [{"id": "shop", "name": "Shop", "website": "https://shop.example",
                                                    "category": "Shopping", "domains": ["shop.example"]}]}))
        store = Store(self.profile, Registry(extra))
        snapshot = store.snapshot()
        self.assertEqual(snapshot["catalog"]["skipped"], [{"id": ident, "name": "Tiny Shop"}])
        self.assertNotIn(ident, store.registry.providers)
        # Its clue waits for a re-import under the catalog provider instead of vanishing.
        self.assertEqual(snapshot["catalog"]["reanalysis"], 1)
        store.remove_provider(ident)
        self.assertEqual(Store(self.profile, Registry(extra)).snapshot()["catalog"]["skipped"], [])

    def test_an_addition_cannot_take_a_sub_domain_of_a_catalog_provider(self):
        with self.assertRaisesRegex(UserFacingError, "already belongs to a provider"):
            self.store.add_provider({**SHOP, "website": "https://accounts.google.com", "domains": ["accounts.google.com"]})

    def test_moving_next_to_a_tie_moves_exactly_one_place_and_undoes_whole(self):
        scan_messages(self.store, [created(s) for s in ("noreply@github.com", "support@discord.com",
                                                        "hello@spotify.com", "noreply@epicgames.com")])
        change_worklist(self.store, {"action": "add", "ids": ["github", "discord", "spotify", "epic"]})
        order = "SELECT account_id FROM instance_work_queue ORDER BY position,account_id"
        with self.store.connect() as db:
            # A tie behind the target, as an undo of an earlier removal can leave it.
            for account_id, position in (("spotify", 2), ("discord", 3), ("epic", 3)):
                db.execute("UPDATE instance_work_queue SET position=? WHERE account_id=?", (position, account_id))
            self.assertEqual([r[0] for r in db.execute(order)], ["github", "spotify", "discord", "epic"])
        change_worklist(self.store, {"action": "move", "id": "spotify", "direction": "down"})
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in db.execute(order)], ["github", "discord", "spotify", "epic"])
        self.store.undo()
        with self.store.connect() as db:
            rows = dict(db.execute("SELECT account_id, position FROM instance_work_queue").fetchall())
        self.assertEqual((rows["spotify"], rows["discord"], rows["epic"]), (2, 3, 3))

    def test_a_hidden_domain_does_not_ask_for_a_decision_in_whats_new(self):
        scan_messages(self.store, [created("hello@new-service.example")])
        self.store.exclude_domain("new-service.example", "not_relevant")
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["unclear"], [])
        self.assertEqual(snapshot["changes"]["attention"], 0)
        self.assertNotIn("decide_first", [item["kind"] for item in snapshot["return_summary"]["items"]])

    def test_new_clues_are_grouped_under_the_account_that_holds_them(self):
        scan_messages(self.store, [created("noreply@github.com")])
        self.store.create_account({"provider_id": "github", "email": OWN, "label": "work", "confirmed": True})
        groups = self.store.snapshot()["changes"]["groups"]
        self.assertEqual([group["account_id"] for group in groups], ["github"])

    def test_a_rejected_account_signs_in_with_nothing(self):
        scan_messages(self.store, [created("support@discord.com"), created("hello@notion.so")])
        self.store.decide("discord", "confirmed")
        self.store.update_account("notion", {"login_method": "sso"})
        self.store.link_sign_in("notion", "discord")
        self.store.decide("notion", "rejected", "not_mine")
        discord = self.accounts()["discord"]
        self.assertEqual(discord["priority"], discord["catalog_priority"])

    def test_clearing_a_due_review_counts_as_reviewed_today(self):
        scan_messages(self.store, [created("noreply@github.com")])
        self.store.update_account("github", {"checklist": {"reviewed": True, "saved_in_bitwarden": True,
                                                           "password_changed": True, "login_tested": True,
                                                           "mfa_checked": True}, "status": "done"})
        self.store.set_review_rule(12, "all")
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with self.store.connect() as db:
            db.execute("UPDATE account_steps SET review_after=?, done_at='2020-01-01T00:00:00+00:00'", (yesterday,))
        self.assertTrue(self.accounts()["github"]["reviews_due"])
        for step in self.accounts()["github"]["reviews_due"]:
            self.store.set_step("github", step, review_after=None)
        proposal = self.accounts()["github"]["review_proposal"]
        self.assertGreater(proposal, (date.today() + timedelta(days=300)).isoformat())

    def test_the_session_report_names_a_rejection(self):
        scan_messages(self.store, [created("support@discord.com")])
        change_worklist(self.store, {"action": "add", "ids": ["discord"]})
        self.store.start_session(1)
        self.store.decide("discord", "rejected", "not_mine")
        text = self.store.session_report_text("en")
        self.assertIn("Discord: done: Rejected by you; next: Nothing more to do", text)


if __name__ == "__main__":
    unittest.main()
