"""Persistent progress, manual completion and ambiguous external writes."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from account_finder.bitwarden import add_to_unlocked_cli, BitwardenCliError, make_export
from account_finder.handoffs import HandoffError, handoff_snapshot, reserve, resolve
from account_finder.registry import Registry
from account_finder.scan import scan_messages, synthetic_mail
from account_finder.store import CHECKLIST, Store
from account_finder.workflow import change_worklist, next_step


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
    def test_additive_migration_preserves_earlier_checklists(self):
        self.store.update_account('github', {'checklist':{'reviewed':True}})
        with self.store.connect() as db:
            db.execute('DROP TABLE work_queue')
            db.execute('DROP TABLE bitwarden_handoffs')
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

    def test_invalid_actions_leave_queue_unchanged(self):
        for data in ({'action':'add','ids':['netflix']}, {'action':'add','ids':['github','unknown']},
                     {'action':'add','ids':'github'}, {'action':'add','ids':[]},
                     {'action':'pause','password':'secret'}, {'action':[]},
                     {'action':'focus','id':'github'}, {'action':'add','ids':[None]}):
            with self.assertRaises(ValueError):
                change_worklist(self.store, data)
            self.assertEqual(self.queue()['total'], 0)


class HandoffTests(ProfileFixture, unittest.TestCase):
    def transfer(self, ids=None, runner=None):
        with patch('account_finder.bitwarden.shutil.which', return_value='/fake/bw'):
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
        from account_finder.handoffs import finish
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
        attempt = reserve(self.store, 'github', 'demo@example.invalid')
        with self.assertRaises(HandoffError):
            self.review(False)
        with patch('account_finder.handoffs.time.time', return_value=10**12):
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
            payloads.append(json.loads(base64.b64decode(arguments[-1])))
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
