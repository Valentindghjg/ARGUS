# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan E1 and E2: every clue explains its rule features, its kind and its age."""
from contextlib import closing
from email.message import EmailMessage
from pathlib import Path
import sqlite3
import tempfile
import unittest

from argus_security.analysis import FEATURES, analyze
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN = "owner@example.invalid"


def mail(sender, subject, body, *, to=OWN, cc=None, date="Mon, 05 Oct 2026 10:00:00 +0000", headers=None):
    message = EmailMessage()
    message["From"], message["To"], message["Subject"], message["Date"] = sender, to, subject, date
    if cc:
        message["Cc"] = cc
    for name, value in (headers or {}).items():
        message[name] = value
    message.set_content(body)
    return message.as_bytes()


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()

    def evidence(self, raw, own=(OWN,)):
        return analyze(raw, self.registry, list(own))

    def test_features_name_where_the_rule_matched_and_who_received_it(self):
        subject = self.evidence(mail("noreply@github.com", "Your account has been created", "Hello."))
        self.assertEqual((subject.signal, set(subject.features)), ("account_created", {"matched_subject", "recipient_to", "catalog_domain"}))
        body = self.evidence(mail("noreply@github.com", "Hello", "Your account has been created."))
        self.assertIn("matched_body", body.features)
        indirect = self.evidence(mail("noreply@github.com", "Your account has been created", "",
                                      to="list@example.org", cc=OWN))
        self.assertIn("recipient_indirect", indirect.features)
        several = self.evidence(mail("noreply@github.com", "Your account has been created", "",
                                     to=f"{OWN}, second@example.invalid"), own=(OWN, "second@example.invalid"))
        self.assertIn("multiple_recipients", several.features)

    def test_features_explain_marketing_forwarding_and_unknown_domains(self):
        newsletter = self.evidence(mail("news@zalando.de", "Welcome to the newsletter", "Special offers. Unsubscribe.",
                                        headers={"List-Unsubscribe": "<https://example.invalid/u>"}))
        self.assertEqual(newsletter.signal, "newsletter")
        self.assertTrue({"mailing_list_header", "advertising_words"} <= set(newsletter.features))
        subscription = self.evidence(mail("news@zalando.de", "Confirm your email for our newsletter", "Thanks."))
        self.assertEqual(subscription.signal, "newsletter")
        self.assertIn("subscription_wording", subscription.features)
        forwarded = self.evidence(mail("noreply@github.com", "Fwd: Your account has been created", ""))
        self.assertIn("forwarded", forwarded.features)
        unknown = self.evidence(mail("hello@new-service.example", "Your account has been created", ""))
        self.assertIn("unknown_domain", unknown.features)
        self.assertTrue(set(newsletter.features + forwarded.features + unknown.features) <= FEATURES)

    def test_snapshot_shows_kind_age_and_features_but_never_message_text(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "profile", self.registry)
            store.configure([OWN])
            scan_messages(store, [mail("noreply@github.com", "Your account has been created", "SECRET-BODY-TEXT",
                                       date="Mon, 05 Oct 2020 10:00:00 +0000"),
                                  mail("orders@amazon.de", "Order confirmation", "Your order has shipped.")])
            snapshot = store.snapshot()
            github = next(a for a in snapshot["accounts"] if a["id"] == "github")
            clue = github["evidence"][0]
            self.assertEqual(clue["kind"], "account")
            self.assertTrue(clue["historical"])
            self.assertGreater(clue["age_days"], 730)
            self.assertTrue(github["historical"])
            self.assertTrue(github["latest_clue_at"].startswith("2020-10-05"))
            self.assertIn("matched_subject", clue["features"])
            amazon = next(a for a in snapshot["accounts"] if a["id"] == "amazon")
            self.assertEqual(amazon["unassigned_evidence"][0]["kind"], "order")
            self.assertNotIn(b"SECRET-BODY-TEXT", store.path.read_bytes())

    def test_older_clues_gain_their_explanation_on_the_next_import(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "profile", self.registry)
            store.configure([OWN])
            raw = synthetic_mail("noreply@github.com", "Your account has been created", "", recipient=OWN)
            scan_messages(store, [raw])
            with closing(sqlite3.connect(store.path)) as db, db:
                db.execute("UPDATE evidence SET features=NULL")
                # Clues from before 2.3 have no processed-message index yet.
                db.execute("DELETE FROM processed_messages")
            clue = next(a for a in store.snapshot()["accounts"] if a["id"] == "github")["evidence"][0]
            self.assertEqual(clue["features"], [])
            result = scan_messages(store, [raw])
            self.assertEqual(result["updated_evidence"], 1)
            clue = next(a for a in store.snapshot()["accounts"] if a["id"] == "github")["evidence"][0]
            self.assertIn("recipient_to", clue["features"])


if __name__ == "__main__":
    unittest.main()
