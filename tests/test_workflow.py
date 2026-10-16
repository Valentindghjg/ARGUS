# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Persistent progress, manual completion and ambiguous external writes."""
import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from argus_security.bitwarden import add_to_unlocked_cli, BitwardenCliError, make_export
from argus_security.handoffs import HandoffError, handoff_snapshot, reserve, resolve
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.store import CHECKLIST, Store
from argus_security.workflow import MAX_PRIORITY_WORKLIST, change_worklist, next_step, recommended_accounts


class ProfileFixture:

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'profile'
        self.store = Store(self.root, Registry())
        self.store.configure(['demo@example.invalid'])
        scan_messages(self.store, [synthetic_mail('notify@github.com', 'Your account has been created', ''),
                                   synthetic_mail('notify@discord.com', 'Your account has been created', '')])

    def account(self, ident='github'):
        return next(a for a in self.store.snapshot()['accounts'] if a['id'] == ident)

    def queue(self):
        return self.store.snapshot()['workflow']


class WorkflowTests(ProfileFixture, unittest.TestCase):
    def test_existing_worklist_schema_gains_snooze_column_without_losing_rows(self):
        with self.store.connect() as db:
            db.execute('ALTER TABLE instance_work_queue RENAME TO prior_instance_work_queue')
            db.execute('CREATE TABLE instance_work_queue (account_id TEXT PRIMARY KEY, position INTEGER NOT NULL, deferred INTEGER NOT NULL DEFAULT 0)')
            db.execute("INSERT INTO instance_work_queue VALUES ('github',3,1)")
            db.execute('DROP TABLE prior_instance_work_queue')
        self.store = Store(self.root, Registry())
        with self.store.connect() as db:
            columns = {row['name'] for row in db.execute('PRAGMA table_info(instance_work_queue)')}
            row = db.execute("SELECT account_id,position,deferred,resume_after FROM instance_work_queue").fetchone()
        self.assertIn('resume_after', columns)
        self.assertEqual(tuple(row), ('github', 3, 1, None))

    def test_priority_ranking_is_deterministic_and_limited(self):
        accounts = [{"id": f"service-{index}", "name": f"Service {index}",
                     "classification": "confirmed", "status": "pending",
                     "priority": "critical" if index == 10 else "normal", "score": index}
                    for index in range(12)]
        ranked = recommended_accounts(accounts, limit=MAX_PRIORITY_WORKLIST)
        self.assertEqual(len(ranked), MAX_PRIORITY_WORKLIST)
        self.assertEqual(ranked[0]["id"], "service-10")
        self.assertNotIn("service-0", [account["id"] for account in ranked])

    def test_additive_migration_preserves_earlier_checklists(self):
        self.store.update_account('github', {'checklist':{'reviewed':True}})
        with self.store.connect() as db:
            db.execute('DROP TABLE IF EXISTS work_queue')
            db.execute('DROP TABLE IF EXISTS bitwarden_handoffs')
        restarted = Store(self.root, Registry())
        account = next(a for a in restarted.snapshot()['accounts'] if a['id'] == 'github')
        self.assertTrue(account['checklist']['reviewed'])
        self.assertEqual(restarted.snapshot()['workflow']['total'], 0)

    def test_queue_survives_restart_with_order_focus_and_pause(self):
        change_worklist(self.store, {'action':'add', 'ids':['github', 'discord', 'github']})
        change_worklist(self.store, {'action':'add', 'ids':['github']})
        change_worklist(self.store, {'action':'focus', 'id':'discord'})
        change_worklist(self.store, {'action':'pause'})
        restarted = Store(self.root, Registry())
        queue = restarted.snapshot()['workflow']
        self.assertEqual([i['id'] for i in queue['items']], ['github', 'discord'])
        self.assertEqual(queue['current'], 'discord')
        self.assertTrue(queue['paused'])
        change_worklist(restarted, {'action':'resume'})
        self.assertFalse(self.queue()['paused'])

    def test_defer_remove_and_restore_do_not_change_accounts(self):
        change_worklist(self.store, {'action':'add', 'ids':['github', 'discord']})
        before = self.account()
        change_worklist(self.store, {'action':'defer', 'id':'github'})
        self.assertEqual(self.queue()['current'], 'discord')
        self.assertEqual(self.queue()['deferred'], 1)
        change_worklist(self.store, {'action':'restore', 'id':'github'})
        self.assertEqual(self.queue()['current'], 'github')
        change_worklist(self.store, {'action':'remove', 'id':'github'})
        self.assertEqual(self.account(), before)
        self.assertEqual(self.queue()['current'], 'discord')

    def test_snooze_becomes_ready_locally_after_its_due_time(self):
        change_worklist(self.store, {'action':'add', 'ids':['github', 'discord']})
        before = self.account('github')
        fixed = datetime(2030, 1, 1, tzinfo=timezone.utc)
        with patch('argus_security.workflow.utcnow', return_value=fixed):
            change_worklist(self.store, {'action':'snooze', 'id':'github', 'days':7})
            snapshot = self.queue()
            github = next(item for item in snapshot['items'] if item['id'] == 'github')
            self.assertTrue(github['deferred'])
            self.assertEqual(github['snoozed_until'], (fixed + timedelta(days=7)).isoformat())
            self.assertEqual(snapshot['current'], 'discord')
        with patch('argus_security.workflow.utcnow', return_value=fixed + timedelta(days=8)):
            snapshot = self.queue()
            github = next(item for item in snapshot['items'] if item['id'] == 'github')
            self.assertFalse(github['deferred'])
            self.assertIsNone(github['snoozed_until'])
            self.assertEqual(snapshot['current'], 'github')
        self.assertEqual(self.account('github'), before)

    def test_custom_snooze_date_is_bounded_and_stored_at_utc_midnight(self):
        change_worklist(self.store, {'action':'add', 'ids':['github']})
        fixed = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
        with patch('argus_security.workflow.utcnow', return_value=fixed):
            change_worklist(self.store, {'action':'snooze_until', 'id':'github', 'date':'2030-01-08'})
            item = self.queue()['items'][0]
            self.assertEqual(item['snoozed_until'], '2030-01-08T00:00:00+00:00')
            self.assertTrue(item['deferred'])
        for value in ('2030-01-01', '2029-12-31', '2031-01-02', 'not-a-date', None):
            with patch('argus_security.workflow.utcnow', return_value=fixed):
                with self.assertRaises(ValueError):
                    change_worklist(self.store, {'action':'snooze_until', 'id':'github', 'date':value})

    def test_completion_advances_and_reopening_restores_pending_work(self):
        change_worklist(self.store, {'action':'add', 'ids':['github', 'discord']})
        self.store.update_account('github', {'checklist': {k: True for k in CHECKLIST}})
        self.assertEqual(self.queue()['items'][0]['step'], 'finish')
        self.assertEqual(self.queue()['done'], 0)
        self.store.update_account('github', {'status':'done'})
        self.assertEqual(self.queue()['done'], 1)
        self.assertEqual(self.queue()['current'], 'discord')
        self.store.update_account('github', {'checklist': {'login_tested':False}})
        self.assertEqual(self.queue()['items'][0]['step'], 'test_signin')
        self.assertEqual(self.queue()['done'], 0)

    def test_sso_and_passkeys_skip_password_change(self):
        for method in ('sso', 'passkey'):
            self.store.update_account('github', {'login_method':method,
                'checklist':{'reviewed':True, 'saved_in_bitwarden':True}})
            self.assertEqual(next_step(self.account()), 'test_signin')
        self.store.update_account('github', {'login_method':'password'})
        self.assertEqual(next_step(self.account()), 'change_password')

    def test_guided_workflow_includes_mfa_and_recovery_review_before_finish(self):
        self.store.update_account('github', {'checklist': {
            'reviewed': True, 'saved_in_bitwarden': True, 'password_changed': True,
            'login_tested': True,
        }})
        self.assertEqual(next_step(self.account()), 'mfa')
        self.store.update_account('github', {'checklist': {'mfa_checked': True}})
        self.assertEqual(next_step(self.account()), 'finish')

    def test_guided_start_selects_priority_without_changing_checklists(self):
        self.store.update_account('github', {'priority': 'normal'})
        self.store.update_account('discord', {'priority': 'critical'})
        before = {account['id']: dict(account['checklist']) for account in self.store.snapshot()['accounts']
                  if account['id'] in {'github', 'discord'}}
        result = change_worklist(self.store, {'action': 'start'})
        self.assertEqual(result, {'ok': True, 'current': 'discord', 'created': True})
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['workflow']['current'], 'discord')
        self.assertFalse(snapshot['workflow']['paused'])
        self.assertEqual(before, {account['id']: account['checklist'] for account in snapshot['accounts']
                                  if account['id'] in before})

    def test_guided_start_keeps_existing_ready_item_and_suggests_another(self):
        self.store.update_account('discord', {'priority': 'critical'})
        change_worklist(self.store, {'action': 'add', 'ids': ['github']})
        result = change_worklist(self.store, {'action': 'start'})
        self.assertEqual(result, {'ok': True, 'current': 'github', 'created': False})
        workflow = self.queue()
        self.assertEqual(workflow['current'], 'github')
        self.assertEqual(workflow['suggested'], 'discord')

    def test_deferred_accounts_are_never_suggested_or_prioritized(self):
        self.store.update_account('discord', {'priority': 'critical', 'status': 'skipped'})
        self.assertEqual(change_worklist(self.store, {'action': 'start'})['current'], 'github')
        workflow = self.queue()
        self.assertNotIn('discord', workflow['priority_preview'])
        self.assertNotEqual(workflow['suggested'], 'discord')
        self.assertNotIn('discord', change_worklist(self.store, {'action': 'prioritize'})['added'])

    def test_priority_builder_adds_available_accounts_without_changing_progress(self):
        self.store.update_account('github', {'priority': 'normal'})
        self.store.update_account('discord', {'priority': 'critical'})
        before = {account['id']: (dict(account['checklist']), account['status'])
                  for account in self.store.snapshot()['accounts']}
        change_worklist(self.store, {'action': 'add', 'ids': ['github']})
        self.assertEqual(self.queue()['priority_preview'], ['discord'])
        result = change_worklist(self.store, {'action': 'prioritize'})
        self.assertEqual(result, {'ok': True, 'added': ['discord']})
        self.assertEqual([item['id'] for item in self.queue()['items']], ['github', 'discord'])
        self.assertEqual(before, {account['id']: (account['checklist'], account['status'])
                                  for account in self.store.snapshot()['accounts']})
        self.assertEqual(change_worklist(self.store, {'action': 'prioritize'}), {'ok': True, 'added': []})

    def test_invalid_actions_leave_queue_unchanged(self):
        for data in ({'action':'add','ids':['netflix']}, {'action':'add','ids':['github','unknown']},
                     {'action':'add','ids':'github'}, {'action':'add','ids':[]},
                     {'action':'pause','password':'secret'}, {'action':[]},
                     {'action':'focus','id':'github'}, {'action':'add','ids':[None]},
                     {'action':'start','password':'rejected'}, {'action':'prioritize','password':'rejected'},
                     {'action':'snooze','id':'github','days':0}, {'action':'snooze','id':'github','days':'7'},
                     {'action':'snooze_until','id':'github','date':'not-a-date','password':'rejected'}):
            with self.assertRaises(ValueError):
                change_worklist(self.store, data)
            self.assertEqual(self.queue()['total'], 0)


class HandoffTests(ProfileFixture, unittest.TestCase):
    def transfer(self, ids=None, runner=None):
        with patch('argus_security.bitwarden.shutil.which', return_value='/fake/bw'):
            return add_to_unlocked_cli(self.store, ids or ['github'], runner=runner or self.success,
                                       environment={'BW_SESSION':'SESSION-MUST-NOT-BE-STORED'})

    def success(self, arguments, **kwargs):
        if arguments[1:] == ['status']:
            return SimpleNamespace(returncode=0, stdout='{"status":"unlocked"}')
        return SimpleNamespace(returncode=0, stdout=json.dumps({'id':str(uuid.uuid4())}))

    def review(self, created):
        attempt = handoff_snapshot(self.store)[-1]
        resolve(self.store, {'id':attempt['id'], 'created':created, 'confirmed':True})

    def test_timeout_is_durable_blocks_both_cli_and_export(self):
        def timeout(arguments, **kwargs):
            if arguments[1] == 'status':
                return self.success(arguments, **kwargs)
            raise subprocess.TimeoutExpired(arguments, 20, output='NEVER-LOG-THIS')
        result = self.transfer(runner=timeout)
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(self.account()['checklist']['saved_in_bitwarden'])
        self.assertEqual(handoff_snapshot(self.store)[0]['state'], 'uncertain')
        self.store = Store(self.root, Registry())
        with self.assertRaises(HandoffError):
            self.transfer(runner=lambda *a, **k: self.fail('Must not retry an ambiguous write'))
        with self.assertRaises(HandoffError):
            make_export(self.store, ['github'])
        database = self.store.path.read_bytes()
        self.assertNotIn(b'NEVER-LOG-THIS', database)
        self.assertNotIn(b'SESSION-MUST-NOT-BE-STORED', database)

    def test_manual_found_marks_only_vault_assignment(self):
        attempt = reserve(self.store, 'github', 'demo@example.invalid')
        from argus_security.handoffs import finish
        finish(self.store, attempt, 'uncertain')
        self.review(True)
        checks = self.account()['checklist']
        self.assertTrue(checks['saved_in_bitwarden'])
        self.assertFalse(checks['password_changed'])
        self.assertFalse(checks['login_tested'])
        with self.assertRaises(ValueError):
            self.transfer()

    def test_explicit_not_created_allows_one_new_attempt_with_new_id(self):
        def failed(arguments, **kwargs):
            return self.success(arguments, **kwargs) if arguments[1] == 'status' else SimpleNamespace(returncode=1, stdout='private-error')
        self.transfer(runner=failed)
        operation = handoff_snapshot(self.store)[0]['operation_id']
        self.review(False)
        self.assertEqual(self.transfer()['items'], 1)
        self.assertNotEqual(handoff_snapshot(self.store)[0]['operation_id'], operation)

    def test_crash_does_not_allow_reconciliation_until_lease_expires(self):
        reserve(self.store, 'github', 'demo@example.invalid')
        with self.assertRaises(HandoffError):
            self.review(False)
        with patch('argus_security.handoffs.time.time', return_value=10**12):
            self.assertEqual(handoff_snapshot(self.store)[0]['state'], 'uncertain')
            self.review(False)
        self.assertEqual(self.transfer()['items'], 1)

    def test_two_concurrent_claims_can_create_only_one_attempt(self):
        barrier = threading.Barrier(2)
        outcomes = []
        def claim():
            barrier.wait()
            try:
                outcomes.append(reserve(self.store, 'github', 'demo@example.invalid'))
            except HandoffError:
                outcomes.append('blocked')
        threads = [threading.Thread(target=claim) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertEqual(outcomes.count('blocked'), 1)
        self.assertEqual(len(handoff_snapshot(self.store)), 1)

    def test_partial_alias_transfer_never_recreates_successful_alias(self):
        self.store.add_emails(['other@example.invalid'])
        scan_messages(self.store, [synthetic_mail('notify@github.com', 'Your account has been created', '', recipient='other@example.invalid')])
        accounts = [a for a in self.store.snapshot()['accounts'] if a['provider_id'] == 'github']
        first = next(a for a in accounts if a['identity_email'] == 'demo@example.invalid')
        second = next(a for a in accounts if a['identity_email'] == 'other@example.invalid')
        payloads = []
        def fail_second(arguments, **kwargs):
            if arguments[1] == 'status': return self.success(arguments, **kwargs)
            payloads.append(json.loads(base64.b64decode(kwargs['input'])))
            if len(payloads) == 2: raise subprocess.TimeoutExpired(arguments,20)
            return self.success(arguments, **kwargs)
        self.assertEqual(self.transfer(ids=[first['id'], second['id']], runner=fail_second)['items'], 1)
        self.assertTrue(self.account(first['id'])['checklist']['saved_in_bitwarden'])
        self.assertFalse(self.account(second['id'])['checklist']['saved_in_bitwarden'])
        self.review(False)
        exported = make_export(self.store, [second['id']])
        self.assertEqual(len(exported['items']), 1)
        created_email = payloads[0]['login']['username']
        self.assertNotEqual(exported['items'][0]['login']['username'], created_email)
        self.assertEqual(self.transfer(ids=[second['id']])['items'], 1)
        self.assertTrue(self.account()['checklist']['saved_in_bitwarden'])
        self.assertTrue(self.account(second['id'])['checklist']['saved_in_bitwarden'])
        self.assertTrue(all(item['state'] == 'created' for item in handoff_snapshot(self.store)))

    def test_invalid_selection_locked_vault_and_demo_never_create(self):
        called = []
        def locked(arguments, **kwargs):
            called.append(arguments)
            return SimpleNamespace(returncode=0, stdout='{"status":"locked"}')
        with self.assertRaises(BitwardenCliError): self.transfer(runner=locked)
        self.assertEqual(len(called), 1)
        self.assertFalse(handoff_snapshot(self.store))
        with self.assertRaises(ValueError): self.transfer(ids=['netflix'], runner=locked)
        self.assertEqual(len(called), 1)
        self.store.set_meta('demo', True)
        with self.assertRaises(BitwardenCliError): self.transfer(runner=locked)
        self.assertEqual(len(called), 1)

    def test_missing_item_id_is_ambiguous_and_confirmations_are_strict(self):
        def malformed(arguments, **kwargs):
            return self.success(arguments, **kwargs) if arguments[1]=='status' else SimpleNamespace(returncode=0, stdout='{}')
        self.assertEqual(self.transfer(runner=malformed)['status'], 'needs_review')
        ident = handoff_snapshot(self.store)[0]['id']
        for data in ({'id':ident,'created':True,'confirmed':False},
                     {'id':ident,'created':'false','confirmed':True},
                     {'id':ident,'created':True,'confirmed':True,'password':'no'}):
            with self.assertRaises(ValueError): resolve(self.store, data)
        self.assertEqual(handoff_snapshot(self.store)[0]['state'], 'uncertain')
