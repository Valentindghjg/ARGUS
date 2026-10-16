"""Regression tests for 1.1: real account clues, rescan, aliases and scan accounting."""
from dataclasses import replace
import http.client
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from account_finder.analysis import analyze
from account_finder.imap_client import IMAPConfig, imap_messages
from account_finder.registry import Registry
from account_finder.scan import ScanSession, scan_messages, synthetic_mail
from account_finder.server import DashboardServer
from account_finder.store import CHECKLIST, Store
from tests.test_imap_discovery import FakeIMAP


class DetectionImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def inspect(self, subject, body="", newsletter=False):
        raw = synthetic_mail("notify@github.com", subject, body, newsletter=newsletter)
        return analyze(raw, self.registry, ["demo@example.invalid"])

    def test_unsubscribe_footer_does_not_hide_created_account(self):
        e = self.inspect("Your account has been created", "Your account has been created. Unsubscribe from marketing.", True)
        self.assertEqual((e.signal,e.score),("account_created",90))

    def test_newsletter_offer_in_footer_does_not_hide_registration(self):
        e = self.inspect("Your account has been created", "Your account has been created. Subscribe to our newsletter in settings.", True)
        self.assertEqual(e.signal,"account_created")

    def test_verification_footer_keeps_account_hint(self):
        e = self.inspect("Verify your email", "Complete your registration by verifying your email. Unsubscribe.", True)
        self.assertEqual(e.signal,"verification_requested")
        self.assertGreaterEqual(e.score,60)

    def test_newsletter_signups_are_not_accounts(self):
        for subject,body in [("Thanks for signing up","Thanks for signing up for our newsletter"),
                             ("Welcome to our newsletter","Your email has been verified"),
                             ("Verify your email","Confirm your email to subscribe to the newsletter")]:
            e = self.inspect(subject,body,True)
            self.assertEqual((e.signal,e.score),("newsletter",0))
            self.assertIsNone(e.registered_email)

    def test_negated_events_are_not_account_evidence(self):
        for subject in ["Dein Passwort wurde nicht geändert", "Deine Registrierung ist nicht erfolgreich", "Your account has not been created"]:
            self.assertIsNone(self.inspect(subject))

    def test_additional_transactional_variants(self):
        for subject,signal in [("Your new account was successfully created","account_created"),
                               ("Your email address was successfully verified","email_verified"),
                               ("Activate your account","verification_requested"),
                               ("Registrierung abschließen","verification_requested")]:
            self.assertEqual(self.inspect(subject).signal,signal)

    def test_subject_and_body_do_not_join_into_fictitious_event(self):
        self.assertIsNone(self.inspect("Welcome","Information about your account preferences"))

    def test_multiple_own_recipients_never_choose_arbitrary_username(self):
        raw = synthetic_mail("notify@github.com","Your account has been created","",recipient="one@example.invalid, two@example.invalid")
        e = analyze(raw,self.registry,["one@example.invalid","two@example.invalid"])
        self.assertLess(e.score,60)
        self.assertIsNone(e.registered_email)
        self.assertIn("Multiple",e.caveat)


class StoreFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = Registry()
        self.store = Store(self.root / "data",self.registry)
        self.store.configure(["demo@example.invalid"])
        self.raw = synthetic_mail("notify@github.com","Your account has been created","")
        self.evidence = analyze(self.raw,self.registry,["demo@example.invalid"])

    def tearDown(self):
        self.temp.cleanup()


class PersistenceImprovements(StoreFixture):
    def test_english_display_preserves_existing_german_evidence_and_status(self):
        legacy = replace(self.evidence, caveat="Weiterleitung / Empfängerzuordnung unklar; Nur Header ausgewertet (Nachricht über Größenlimit)")
        self.store.add_evidence(legacy)
        self.store.update_account("github", {"checklist":{"reviewed":True}})
        snapshot = self.store.snapshot()
        account = next(a for a in snapshot["accounts"] if a["id"]=="github")
        self.assertEqual(account["classification"], "confirmed")
        self.assertEqual(account["reason"], "You confirmed that this account exists")
        self.assertIn("Forwarding / recipient association uncertain", account["unassigned_evidence"][0]["caveat"])
        self.assertIn("Only headers analyzed", account["unassigned_evidence"][0]["caveat"])
        self.assertEqual(account["evidence"], [])
        self.assertEqual(snapshot["stale_evidence"], 0)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT caveat FROM evidence").fetchone()[0], legacy.caveat)

    def test_alias_addition_preserves_state_and_resets_cursors(self):
        scan_messages(self.store,[self.raw])
        self.store.update_account("github",{"checklist":{k:True for k in CHECKLIST},"status":"done"})
        self.store.set_meta("imap_cursors",{"old": {"uid":100}})
        self.assertEqual(self.store.add_emails(["second@example.invalid"]),["second@example.invalid"])
        self.assertEqual(self.store.meta("imap_cursors"),{})
        self.assertEqual(self.store.snapshot()["summary"]["done"],1)
        self.assertIn("demo@example.invalid",self.store.meta("emails"))

    def test_repeated_alias_addition_does_not_reset_new_progress(self):
        self.store.add_emails(["second@example.invalid"])
        self.store.set_meta("imap_cursors",{"new":{"uid":10}})
        self.assertEqual(self.store.add_emails(["SECOND@example.invalid"]),[])
        self.assertIn("new",self.store.meta("imap_cursors"))

    def test_new_alias_requires_reanalysis_and_discovers_old_mail(self):
        raw = synthetic_mail("notify@github.com","Your account has been created","",recipient="second@example.invalid")
        self.assertEqual(scan_messages(self.store,[raw])["evidence"],0)
        self.store.add_emails(["second@example.invalid"])
        self.assertEqual(scan_messages(self.store,[raw])["evidence"],1)

    def test_reclassification_replaces_old_signal_without_duplicates(self):
        self.store.add_evidence(self.evidence)
        replacement = replace(self.evidence,signal="newsletter",score=0,registered_email=None)
        self.assertEqual(self.store.record_analysis(self.evidence.fingerprint,replacement),"updated")
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],1)
        account = next(a for a in self.store.snapshot()["accounts"] if a["id"]=="github")
        self.assertEqual(account["classification"],"unknown")

    def test_catalogue_reclassification_moves_unknown_candidate(self):
        self.store.add_evidence(replace(self.evidence,provider_id=None))
        self.assertEqual(len(self.store.snapshot()["candidates"]),1)
        self.assertEqual(self.store.record_analysis(self.evidence.fingerprint,self.evidence),"updated")
        self.assertEqual(self.store.snapshot()["candidates"],[])

    def test_obsolete_evidence_removed_without_losing_manual_checklist(self):
        self.store.add_evidence(self.evidence)
        self.store.update_account("github",{"checklist":{"reviewed":True}})
        self.assertEqual(self.store.record_analysis(self.evidence.fingerprint,None),"removed")
        account = next(a for a in self.store.snapshot()["accounts"] if a["id"]=="github")
        self.assertEqual(account["classification"],"confirmed")
        self.assertEqual(account["evidence_count"],0)

    def test_legacy_scores_require_current_rules_and_reimport_updates_them(self):
        self.store.add_evidence(self.evidence)
        with self.store.connect() as db:
            db.execute("UPDATE evidence SET rule_version=1")
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot["stale_evidence"],1)
        self.assertEqual(snapshot["summary"]["probable"],0)
        self.assertEqual(scan_messages(self.store,[self.raw])["updated_evidence"],1)
        self.assertEqual(self.store.snapshot()["stale_evidence"],0)

    def test_migration_of_v1_schema_and_duplicate_signals(self):
        directory = self.root / "v1"
        directory.mkdir()
        with closing(sqlite3.connect(directory / "accounts.sqlite3")) as db, db:
            db.execute("""CREATE TABLE evidence(id INTEGER PRIMARY KEY, provider_id TEXT, sender_domain TEXT NOT NULL,
                registered_email TEXT, signal TEXT NOT NULL, score INTEGER NOT NULL, fingerprint TEXT NOT NULL,
                date TEXT, source TEXT NOT NULL, caveat TEXT, UNIQUE(fingerprint,sender_domain,signal))""")
            for signal in ["account_created","login_activity"]:
                db.execute("INSERT INTO evidence(provider_id,sender_domain,signal,score,fingerprint,source) VALUES (?,?,?,?,?,?)",
                           ("github","github.com",signal,90,self.evidence.fingerprint,"eml"))
        migrated = Store(directory,self.registry)
        migrated.configure(["demo@example.invalid"])
        self.assertEqual(migrated.snapshot()["stale_evidence"],1)
        self.assertEqual(scan_messages(migrated,[self.raw])["updated_evidence"],1)
        self.assertEqual(migrated.snapshot()["summary"]["probable"],1)


class ScanImprovements(StoreFixture):
    def test_whole_batch_totals_and_skips_survive_restart(self):
        session = ScanSession(self.store,expected=3)
        session.process(self.raw)
        session.process(self.raw)
        session.skip()
        result = session.finish()
        self.assertEqual((result["processed"],result["evidence"],result["duplicates"],result["skipped"]),(3,1,1,1))
        self.assertEqual(result["result"],"completed_with_gaps")
        restarted = Store(self.store.data_dir,self.registry)
        self.assertEqual(restarted.meta("last_scan")["id"],result["id"])

    def test_abort_retains_processed_evidence_and_blocks_more_files(self):
        session = ScanSession(self.store,expected=3)
        session.process(self.raw)
        self.assertEqual(session.finish("partial")["result"],"partial")
        with self.assertRaises(ValueError):
            session.process(self.raw)
        self.assertEqual(self.store.snapshot()["summary"]["probable"],1)

    def test_incomplete_batch_cannot_claim_complete(self):
        session = ScanSession(self.store,expected=2)
        session.process(self.raw)
        self.assertEqual(session.finish()["result"],"partial")

    def test_imap_limit_is_visible_and_exact_end_is_complete(self):
        config = IMAPConfig("imap.example.invalid","demo@example.invalid")
        messages = {uid:synthetic_mail("notify@github.com","Your account has been created",str(uid)) for uid in range(1,4)}
        stream = imap_messages(self.store,config,"fake",allow_network=True,limit=1,factory=lambda *a,**kw:FakeIMAP(messages),delay=0)
        limited = scan_messages(self.store,stream,"imap")
        self.assertEqual(limited["result"],"limited")
        self.assertEqual(limited["folders_processed"],0)
        stream = imap_messages(self.store,config,"fake",allow_network=True,limit=2,factory=lambda *a,**kw:FakeIMAP(messages),delay=0)
        self.assertEqual(scan_messages(self.store,stream,"imap")["result"],"completed")

    def test_header_only_scan_is_reported_with_gaps(self):
        raw = b"X-Account-Finder-Headers-Only: yes\n" + self.raw
        result = scan_messages(self.store,[raw],"imap")
        self.assertEqual(result["headers_only"],1)
        self.assertEqual(result["result"],"completed_with_gaps")

    def test_failure_before_first_message_marks_scan_partial(self):
        class BrokenIterable:
            def __iter__(self):
                raise RuntimeError("synthetic iterator failure")
        with self.assertRaises(RuntimeError):
            scan_messages(self.store,BrokenIterable())
        self.assertEqual(self.store.meta("last_scan")["result"],"partial")

    def test_old_scope_checkpoint_cannot_hide_new_alias_messages(self):
        config = IMAPConfig("imap.example.invalid","demo@example.invalid")
        messages = {1:self.raw, 2:synthetic_mail("notify@github.com","Your account has been created","",recipient="second@example.invalid")}
        stream = imap_messages(self.store,config,"fake",allow_network=True,limit=1,factory=lambda *a,**kw:FakeIMAP(messages),delay=0)
        scan_messages(self.store,stream,"imap")
        old_cursors = self.store.meta("imap_cursors")
        self.store.add_emails(["second@example.invalid"])
        self.store.set_meta("imap_cursors",old_cursors)
        stream = imap_messages(self.store,config,"fake",allow_network=True,factory=lambda *a,**kw:FakeIMAP(messages),delay=0)
        result = scan_messages(self.store,stream,"imap")
        self.assertEqual((result["processed"],result["duplicates"],result["evidence"]),(2,1,1))

    def test_alias_change_during_prepared_scan_is_partial_and_preserves_evidence(self):
        config = IMAPConfig("imap.example.invalid","demo@example.invalid")
        self.store.add_evidence(self.evidence)
        stream = imap_messages(self.store,config,"fake",allow_network=True,factory=lambda *a,**kw:FakeIMAP({1:self.raw}),delay=0)
        self.store.add_emails(["second@example.invalid"])
        result = scan_messages(self.store,stream,"imap")
        self.assertEqual(result["result"],"partial")
        self.assertTrue(result["scope_changed"])
        self.assertEqual(self.store.snapshot()["summary"]["probable"],1)


class BatchAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "data",Registry())
        self.store.configure(["demo@example.invalid"])
        self.server = DashboardServer(self.store,0)
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self,path,data=None,raw=None,job_id=None):
        headers = {"Authorization":"Bearer "+self.server.token}
        body = raw if raw is not None else json.dumps(data or {})
        headers["Content-Type"] = "message/rfc822" if raw is not None else "application/json"
        if job_id:
            headers["X-Import-ID"] = job_id
        with closing(http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=5)) as conn:
            conn.request("POST",path,body,headers)
            response = conn.getresponse()
            return response.status,json.loads(response.read())

    def test_multi_file_stats_and_skip(self):
        status,job = self.request("/api/import/start",{"expected":3})
        self.assertEqual(status,200)
        raw = synthetic_mail("notify@github.com","Your account has been created","")
        for _ in range(2):
            self.assertEqual(self.request("/api/import",raw=raw,job_id=job["id"])[0],200)
        self.request("/api/import/skip",{"id":job["id"]})
        status,result = self.request("/api/import/finish",{"id":job["id"]})
        self.assertEqual((status,result["processed"],result["duplicates"]),(200,3,1))
        self.assertEqual(self.store.meta("last_scan")["result"],"completed_with_gaps")

    def test_parallel_batch_rejected_and_cancel_preserves_progress(self):
        _,job = self.request("/api/import/start",{"expected":2})
        self.assertEqual(self.request("/api/import/start",{"expected":1})[0],409)
        self.assertEqual(self.request("/api/profile/emails",{"emails":["second@example.invalid"]})[0],409)
        raw = synthetic_mail("notify@github.com","Your account has been created","")
        self.request("/api/import",raw=raw,job_id=job["id"])
        _,result = self.request("/api/import/finish",{"id":job["id"],"result":"partial"})
        self.assertEqual(result["processed"],1)
        self.assertEqual(self.store.snapshot()["summary"]["probable"],1)
        self.assertEqual(self.request("/api/import/start",{"expected":1})[0],200)

    def test_profile_alias_api_is_local_and_keeps_original(self):
        status,result = self.request("/api/profile/emails",{"emails":["second@example.invalid"]})
        self.assertEqual((status,result["rescan_recommended"]),(200,True))
        self.assertEqual(len(self.store.meta("emails")),2)
        self.assertEqual(self.request("/api/profile/emails",{"emails":["invalid"]})[0],400)
        self.assertEqual(self.request("/api/profile/emails",{"emails":[],"password":"never-accepted"})[0],400)

    def test_expired_job_and_mismatched_id_cannot_write(self):
        _,job = self.request("/api/import/start",{"expected":1})
        self.server.import_job.last_activity -= 1000
        self.assertEqual(self.request("/api/import/start",{"expected":1})[0],200)
        raw = synthetic_mail("notify@github.com","Your account has been created","")
        self.assertEqual(self.request("/api/import",raw=raw,job_id=job["id"])[0],400)

    def test_server_shutdown_marks_active_batch_partial(self):
        self.request("/api/import/start",{"expected":1})
        self.server.server_close()
        self.assertEqual(self.store.meta("last_scan")["result"],"partial")
