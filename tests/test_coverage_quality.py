# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan D4 and catalog quality: what imports cover, and rules every catalog entry keeps."""
from collections import Counter
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from argus_security import jobs
from argus_security.registry import Registry, SHARED_SENDERS, is_shared_sender, is_subdomain
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import Store

OWN, SPARE = "owner@example.invalid", "spare@example.invalid"
CATEGORIES = {"Communication", "Dating", "Education", "Finance", "Food & Delivery", "Gaming", "Health & Fitness",
              "Media & Community", "Productivity", "Shopping", "Social Media", "Streaming", "Technology",
              "Travel & Mobility"}


def created(sender, month):
    raw = synthetic_mail(sender, "Your account has been created", "", recipient=OWN)
    stamp = format_datetime(datetime(2026, month, 5, 10, tzinfo=timezone.utc))
    return raw.replace(b"Mon, 05 Oct 2026 10:00:00 +0000", stamp.encode())


class CoverageTests(unittest.TestCase):
    def test_coverage_names_sources_period_and_gaps_without_a_total(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "profile", Registry())
            store.configure([OWN, SPARE])
            self.assertEqual(store.snapshot()["coverage"]["sources"], [])
            scan_messages(store, [created("noreply@github.com", 1), created("noreply@dropbox.com", 4)])
            coverage = store.snapshot()["coverage"]
        self.assertEqual((coverage["sources"][0]["kind"], coverage["sources"][0]["runs"], coverage["sources"][0]["messages"]),
                         ("import", 1, 2))
        self.assertEqual((coverage["first_clue"], coverage["last_clue"]), ("2026-01", "2026-04"))
        self.assertEqual(coverage["months_without_clues"], ["2026-02", "2026-03"])
        self.assertEqual(coverage["addresses_without_clues"], [SPARE])
        self.assertFalse(any("percent" in key or "share" in key for key in coverage))

    def test_runs_that_leave_the_job_list_still_count(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "profile", Registry())
            store.configure([OWN])
            senders = ("noreply@github.com", "noreply@dropbox.com", "hello@spotify.com", "support@discord.com")
            with patch.object(jobs, "KEEP_JOBS", 2):
                for sender in senders:
                    scan_messages(store, [created(sender, 1)])
                # A message read again unchanged still counts once after its job is gone.
                scan_messages(store, [created(senders[0], 1)])
                with store.connect() as db:
                    jobs.single(db, "bitwarden_check", "completed")
                    jobs.single(db, "bitwarden_check", "completed")
                    listed = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                    newest = db.execute("SELECT MAX(started_at) FROM jobs WHERE kind='import'").fetchone()[0]
                    totals = [tuple(row) for row in db.execute("SELECT kind, runs, messages FROM source_totals")]
            source = store.snapshot()["coverage"]["sources"]
        self.assertEqual(listed, 2)
        # Every import job has left the list; only numbers are kept, never other job kinds.
        self.assertIsNone(newest)
        self.assertEqual(totals, [("import", 5, 4)])
        self.assertEqual([(s["kind"], s["runs"], s["messages"]) for s in source], [("import", 5, 4)])
        self.assertIsNotNone(source[0]["last_run"])


class CatalogQualityTests(unittest.TestCase):
    """Rules that keep the shared catalog trustworthy beyond what loading already checks."""

    def setUp(self):
        self.providers = list(Registry().providers.values())

    def test_identifiers_names_and_categories_are_clean(self):
        names = Counter(provider.name.casefold() for provider in self.providers)
        self.assertEqual([name for name, count in names.items() if count > 1], [])
        for provider in self.providers:
            with self.subTest(provider=provider.id):
                self.assertRegex(provider.id, r"^[a-z0-9][a-z0-9_-]*$")
                self.assertIn(provider.category, CATEGORIES)
                self.assertEqual(provider.name, provider.name.strip())

    def test_domains_are_specific_unique_and_never_shared_senders(self):
        roots = Counter(domain for provider in self.providers for domain in provider.domains)
        self.assertEqual([domain for domain, count in roots.items() if count > 1], [])
        for provider in self.providers:
            for domain in provider.domains:
                with self.subTest(domain=domain):
                    self.assertFalse(is_shared_sender(domain))
                    self.assertGreaterEqual(domain.count("."), 1)
        self.assertTrue(all(re.fullmatch(r"[a-z0-9.-]+", domain) for domain in SHARED_SENDERS))

    def test_links_are_https_on_own_domains_and_password_pages_are_dated(self):
        for provider in self.providers:
            with self.subTest(provider=provider.id):
                host = provider.website.split("/")[2]
                self.assertTrue(provider.website.startswith("https://"))
                self.assertTrue(any(is_subdomain(host, domain) for domain in provider.domains))
                if provider.password_url:
                    self.assertTrue(provider.password_source.startswith("https://"))
                    self.assertLessEqual(date.fromisoformat(provider.password_verified), date.today())


if __name__ == "__main__":
    unittest.main()
