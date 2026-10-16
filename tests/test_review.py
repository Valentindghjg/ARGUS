# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan E3, E4 and A9: one list of unclear items, reversible exclusions, address notes."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from argus_security.cli import main
from argus_security.errors import UserFacingError
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store

OWN, WORK = "owner@example.invalid", "work@example.invalid"


def created(sender, recipient=OWN, subject="Your account has been created"):
    return synthetic_mail(sender, subject, "", recipient=recipient)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.profile = Path(self.temporary.name) / "profile"
        self.store = Store(self.profile, Registry())
        self.store.configure([OWN, WORK])
        scan_messages(self.store, [created("hello@new-service.example"), created("noreply@github.com"),
                                   created("noreply@github.com", f"{OWN}, {WORK}",
                                           "New sign-in to your account")])

    def kinds(self):
        return [(item["kind"], item.get("domain") or item.get("account_id")) for item in self.store.snapshot()["unclear"]]

    def test_one_list_collects_unclear_items(self):
        kinds = self.kinds()
        self.assertIn(("unassigned", "github"), kinds)
        self.assertIn(("domain", "new-service.example"), kinds)
        self.store.decide("github", "rejected", "not_mine")
        scan_messages(self.store, [created("security@github.com", OWN, "Your password has been changed")])
        self.assertIn(("reconsider", "github"), self.kinds())

    def test_exclusions_hide_a_domain_until_new_clues_arrive_and_are_reversible(self):
        self.store.exclude_domain("New-Service.example", "newsletter")
        snapshot = self.store.snapshot()
        self.assertEqual([c["domain"] for c in snapshot["candidates"]], [])
        self.assertEqual(snapshot["exclusions"][0]["domain"], "new-service.example")
        self.assertEqual(snapshot["result"]["unclear"]["unknown_domains"], 0)
        self.assertNotIn(("domain", "new-service.example"), self.kinds())
        scan_messages(self.store, [created("hello@new-service.example", OWN, "Your password has been changed")])
        self.assertIn(("excluded_new", "new-service.example"), self.kinds())
        self.store.remove_exclusion("new-service.example")
        self.assertIn(("domain", "new-service.example"), self.kinds())
        with self.assertRaises(UserFacingError):
            self.store.remove_exclusion("new-service.example")

    def test_exclusions_are_limited_to_sender_domains_outside_the_catalog(self):
        for domain, reason in [("github.com", "spam"), ("unknown.example", "spam"), ("new-service.example", "dislike"),
                               ("not a domain", "spam")]:
            with self.subTest(domain=domain), self.assertRaises(UserFacingError):
                self.store.exclude_domain(domain, reason)

    def test_relations_are_notes_between_own_addresses(self):
        self.store.relate_addresses(OWN, WORK, "replaced_by")
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["relations"][0]["kind"], "replaced_by")
        github = [a for a in snapshot["accounts"] if a["identity_email"] == OWN][0]
        self.assertEqual(github["related_addresses"][0]["other"], WORK)
        # The note never merges or moves anything.
        self.assertEqual(len([a for a in snapshot["accounts"] if a["provider_id"] == "github"]), 1)
        for address, other, kind in [(OWN, OWN, "same_mailbox"), (OWN, "stranger@example.invalid", "same_mailbox"),
                                     (OWN, WORK, "merge")]:
            with self.subTest(other=other, kind=kind), self.assertRaises(UserFacingError):
                self.store.relate_addresses(address, other, kind)
        self.store.remove_relation(OWN, WORK)
        self.assertEqual(self.store.snapshot()["relations"], [])

    def test_cli_unclear_exclude_and_relate(self):
        out = StringIO()
        with redirect_stdout(out), redirect_stderr(StringIO()):
            base = ["--language", "en", "--data-dir", str(self.profile)]
            self.assertEqual(main([*base, "exclude", "new-service.example", "--reason", "spam"]), 0)
            self.assertEqual(main([*base, "relate", OWN, WORK, "--kind", "same_mailbox"]), 0)
            self.assertEqual(main([*base, "unclear"]), 0)
        printed = out.getvalue()
        listing = json.loads(printed[printed.index("{"):])
        self.assertEqual(listing["exclusions"][0]["reason"], "spam")
        self.assertEqual(listing["relations"][0]["kind"], "same_mailbox")

    def test_api_routes_are_strictly_shaped(self):
        server = DashboardServer(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def post(path, body):
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
            self.addCleanup(connection.close)
            connection.request("POST", path, json.dumps(body), {"Authorization": "Bearer " + server.token,
                                                                "Content-Type": "application/json"})
            response = connection.getresponse()
            return response.status, json.loads(response.read())

        self.assertEqual(post("/api/exclusions", {"domain": "new-service.example", "reason": "spam"})[0], 200)
        self.assertEqual(post("/api/exclusions/remove", {"domain": "new-service.example"})[0], 200)
        self.assertEqual(post("/api/profile/relations", {"address": OWN, "other": WORK, "kind": "same_mailbox"})[0], 200)
        self.assertEqual(post("/api/profile/relations/remove", {"address": OWN, "other": WORK})[0], 200)
        for path, body in [("/api/exclusions", {"domain": "new-service.example"}),
                           ("/api/exclusions", {"domain": "github.com", "reason": "spam"}),
                           ("/api/profile/relations", {"address": OWN, "other": WORK}),
                           ("/api/profile/relations/remove", {"address": OWN, "other": WORK})]:
            with self.subTest(path=path, body=body):
                self.assertEqual(post(path, body)[0], 400)


if __name__ == "__main__":
    unittest.main()
