# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Terminal interface; passwords are never command-line arguments."""
import getpass
import json
from pathlib import Path
import sys
from .i18n import translate, cli_language, LocalizedArgumentParser, localize_discovery
from .registry import Registry
from .discovery import discover, DNSError
from .guidance import hint_for
from .imap_client import IMAPConfig, MailboxError, load_config, save_config, imap_messages, with_keep_alive
from .mailbox_lease import MailboxLease
from .background import (BackgroundScanService, CredentialError, KeyringCredentialStore,
                         DEFAULT_INTERVAL_SECONDS, DEFAULT_LIMIT,
                         MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS, MAX_LIMIT)
from .backup import create_backup, list_backups, read_manifest, restore_backup
from .bitwarden import export_file, preview_export
from .scan import file_messages, load_demo, scan_messages
from .server import serve
from .store import Store


def data_root():
    """Parent folder of the default profile; a function so tests can redirect it."""
    return Path.home() / '.local' / 'share'


def default_data_dir(language="en"):
    """Return the default profile, moving a pre-rename profile there once.

    The old ``account-finder`` folder is renamed atomically inside the same
    parent, which keeps its private permissions and every file in it. Keyring
    entries use an opaque selector and the "ARGUS IMAP authorization" service
    name, so they need no migration. An explicit --data-dir is never moved.
    """
    root = data_root()
    current, legacy = root / 'argus', root / 'account-finder'
    if legacy.is_symlink() or not legacy.is_dir():
        return current
    if current.exists() or current.is_symlink():
        print(translate('An older profile folder still exists at {p0}; ARGUS does not use it. Check it, then move or delete it yourself.',
                        language, p0=legacy), file=sys.stderr)
        return current
    try:
        legacy.rename(current)
    except OSError:
        # Another ARGUS process may have completed the same move first.
        if current.is_dir() and not legacy.exists():
            return current
        print(translate('The previous profile folder {p0} could not be moved; ARGUS keeps using it.',
                        language, p0=legacy), file=sys.stderr)
        return legacy
    print(translate('Moved your profile from {p0} to {p1}.', language, p0=legacy, p1=current), file=sys.stderr)
    return current


def parser(language="en"):
    t = lambda message, **values: translate(message, language, **values)
    p = LocalizedArgumentParser(prog='argus', language=language, description=t('ARGUS local account inventory. No login attempts at cataloged services.'))
    p.add_argument('--data-dir', type=Path, help=t('Private local results directory (default: ~/.local/share/argus)'))
    p.add_argument('--providers', type=Path, help=t('Additional JSON provider catalog'))
    p.add_argument("--language", choices=["en", "de"], default=language, help=t("Interface language (defaults to your system language)"))
    sub = p.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help=t('Configure your own email address(es)'))
    init.add_argument('--email', action='append', required=True)
    alias = sub.add_parser('add-email', help=t('Add your own sign-in addresses and preserve checklists'))
    alias.add_argument('--email', action='append', required=True)
    demo = sub.add_parser('demo', help=t('Load synthetic data; requires a separate directory'))
    demo.add_argument('--serve', action='store_true')
    demo.add_argument('--port', type=int, default=8765)
    demo.add_argument('--open', action='store_true')
    srv = sub.add_parser('serve', help=t('Start the dashboard on 127.0.0.1 only'))
    srv.add_argument('--port', type=int, default=8765)
    srv.add_argument('--open', action='store_true')
    imp = sub.add_parser('import', help=t('Read local emails without changing the originals'))
    imp.add_argument('path', type=Path)
    imp.add_argument('--format', choices=['eml', 'mbox', 'maildir'], default='eml')
    sub.add_parser('report', help=t('Show local statistics only'))
    accounts = sub.add_parser('list-accounts', help=t('Show local account IDs for individual selections'))
    accounts.add_argument('--all', action='store_true', help=t('Include entries without reliable account evidence'))
    dis = sub.add_parser('discover', help=t('Mail provider hints; offline by default'))
    dis.add_argument('--domain', help=t('Mail domain only, not a full email address'))
    dis.add_argument('--allow-dns', action='store_true', help=t('Explicitly allow a public MX query to the DNS resolver'))
    dis.add_argument('--resolver', help=t('Optional explicitly selected DNS resolver IP'))
    setup = sub.add_parser('setup-imap', help=t('Save IMAP settings without credentials'))
    setup.add_argument('--host', help=t('IMAP host verified with your provider'))
    setup.add_argument('--username')
    setup.add_argument('--port', type=int, default=993)
    setup.add_argument('--auth', choices=['app_password', 'oauth2'], default='app_password')
    setup.add_argument('--folder', action='append', help=t('Folder name; defaults to all selectable folders'))
    imap = sub.add_parser('scan-imap', help=t('Explicitly authorized TLS IMAP connection, read-only'))
    imap.add_argument('--allow-imap', action='store_true', help=t('Explicitly allow a connection to the configured IMAP host'))
    imap.add_argument('--full-scan', action='store_true', help=t('Recheck all messages and deduplicate locally'))
    imap.add_argument('--limit', type=int, help=t('Maximum messages; no limit scans all selected folders'))
    imap.add_argument('--list-folders', action='store_true', help=t('Show folder names only'))
    background = sub.add_parser('background-imap', help=t('Configure explicitly authorized scheduled read-only IMAP scans'))
    background.add_argument('action', choices=['enable', 'disable', 'revoke', 'status'])
    background.add_argument('--interval-minutes', type=int, default=DEFAULT_INTERVAL_SECONDS // 60,
                            help=t('Minutes between scheduled scans (15 to 10080)'))
    background.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                            help=t('Maximum messages in each scheduled scan (1 to 10000)'))
    export = sub.add_parser('bitwarden-export', help=t('Selected metadata as Bitwarden JSON, no passwords'))
    export.add_argument('path', type=Path)
    export.add_argument('--id', action='append', required=True, help=t('Account ID from list-accounts; may be repeated'))
    export.add_argument('--preview', action='store_true', help=t('Show the items that would be written; create no file'))
    sub.add_parser('changes', help=t('Show your recent local changes to decisions, steps and the worklist'))
    undo = sub.add_parser('undo', help=t('Undo your latest local change; external actions are never undone'))
    undo.add_argument('--batch', help=t('Undo this change instead of the latest one'))
    backup = sub.add_parser('backup', help=t('Save a private, unencrypted copy of this profile'))
    backup.add_argument('--output', type=Path, help=t('Folder for the backup file (default: backups in the profile)'))
    backup.add_argument('--list', action='store_true', help=t('List the backups in the profile folder'))
    restore = sub.add_parser('restore', help=t('Replace this profile with a backup; the current state is saved first'))
    restore.add_argument('path', type=Path)
    restore.add_argument('--yes', action='store_true', help=t('Confirm the replacement'))
    return p

def main(argv=None):
    language = cli_language(argv)
    t = lambda message, **values: translate(message, language, **values)
    args = parser(language).parse_args(argv)
    try:
        data_dir = args.data_dir if args.data_dir is not None else default_data_dir(language)
        if args.command in {'backup', 'restore'}:
            # Work on the files as they are, before any migration opens them.
            return backup_command(args, data_dir, t)
        registry = Registry(args.providers)
        store = Store(data_dir, registry)
        if args.command == 'init':
            store.configure(args.email)
            print(t('Local profile initialized. {p0} providers; no network connection.', p0=len(registry.providers)))
        elif args.command == 'add-email':
            added = store.add_emails(args.email)
            print(t('Added {p0} own address(es). Checklists are preserved; re-import local email files. The next authorized IMAP scan rechecks older messages for the expanded address scope.', p0=len(added)))
        elif args.command == 'demo':
            print(json.dumps(load_demo(store), ensure_ascii=False))
            if args.serve:
                serve(store, args.port, args.open, language=language)
        elif args.command == 'serve':
            if not store.meta('emails'):
                raise ValueError('Run init or demo first')
            serve(store, args.port, args.open, language=language)
        elif args.command == 'import':
            result = scan_messages(store, file_messages(args.path, args.format), args.format, lambda s: print(t('Processed locally: {p0}; new clues: {p1}', p0=s['processed'], p1=s['evidence']), flush=True))
            report_scan(result, t)
        elif args.command == 'report':
            print(json.dumps(store.snapshot()['summary'], ensure_ascii=False, indent=2))
        elif args.command == 'list-accounts':
            fields = ('id', 'provider_id', 'name', 'identity_email', 'label',
                      'classification', 'status', 'identity_review_required')
            rows = [{key: account[key] for key in fields} for account in store.snapshot()['accounts']
                    if args.all or account['classification'] != 'unknown']
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        elif args.command == 'discover':
            domain = args.domain
            if not domain:
                emails = store.meta('emails', [])
                if not emails:
                    raise ValueError('Specify --domain or run init first')
                domain = emails[0].split('@', 1)[1]
            print(json.dumps(localize_discovery(discover(domain, allow_network=args.allow_dns, resolver=args.resolver), language), ensure_ascii=False, indent=2))
        elif args.command == 'setup-imap':
            emails = store.meta('emails', [])
            if not emails or store.meta('demo', False):
                raise ValueError('Initialize a personal local profile with init first')
            print(t('No connection will be opened. Verify the host in official provider documentation first.'))
            host = args.host or input(t('Verified IMAP host (TLS): ')).strip()
            username = args.username or input(t('IMAP username [{p0}]: ', p0=emails[0])).strip() or emails[0]
            config = IMAPConfig(host, username, args.port, args.auth, tuple(args.folder or ['*']))
            save_config(store.data_dir / 'imap.json', config)
            print(t('Saved private imap.json without passwords or tokens. Run scan-imap --allow-imap to scan.'))
        elif args.command == 'scan-imap':
            if not args.allow_imap:
                raise MailboxError('No connection authorized; explicitly choose scan-imap --allow-imap')
            if store.meta('demo', False) or not store.meta('emails'):
                raise ValueError('IMAP requires an initialized personal local profile')
            if args.limit is not None and args.limit < 1:
                raise ValueError('The scan limit must be positive')
            config = load_config(store.data_dir / 'imap.json')
            print(t('Authorized TLS host: {p0}:{p1}; read-only access.', p0=config.host, p1=config.port))
            if not sys.stdin.isatty():
                raise MailboxError('Enter credentials only in an interactive terminal; no pipes or command-line passwords')
            # Claim the profile's mailbox before asking for the secret, so a
            # running scheduled scan is reported instead of a second session.
            mailbox = MailboxLease(store, kind='manual').acquire()
            secret = ''
            try:
                secret = getpass.getpass(t('Short-lived IMAP OAuth2 token: ') if config.auth == 'oauth2' else t('Separate IMAP app password (not Bitwarden): '))
                messages = imap_messages(store, config, secret, allow_network=True, full_scan=args.full_scan, limit=args.limit, list_only=args.list_folders)
                messages = with_keep_alive(messages, mailbox.keep_alive)
                if args.list_folders:
                    for folder in messages:
                        print(folder)
                else:
                    result = scan_messages(store, messages, 'imap', lambda s: print(t('Processed locally: {p0}; new clues: {p1}', p0=s['processed'], p1=s['evidence']), flush=True))
                    report_scan(result, t)
            finally:
                secret = ''
                mailbox.release()
        elif args.command == 'background-imap':
            if store.meta('demo', False) or not store.meta('emails'):
                raise ValueError('Background IMAP requires an initialized personal local profile')
            service = BackgroundScanService(store, KeyringCredentialStore())
            if args.action == 'status':
                print(json.dumps(service.snapshot(), ensure_ascii=False, indent=2))
            elif args.action == 'disable':
                service.disable()
                print(t('Scheduled IMAP scans are disabled. The app password remains only in your OS keyring until you revoke it.'))
            elif args.action == 'revoke':
                service.revoke()
                print(t('Scheduled IMAP scans are disabled and the IMAP authorization was removed from your OS keyring.'))
            else:
                if not MIN_INTERVAL_SECONDS <= args.interval_minutes * 60 <= MAX_INTERVAL_SECONDS:
                    raise ValueError('Scheduled scan interval must be between 15 minutes and 7 days')
                if not 1 <= args.limit <= MAX_LIMIT:
                    raise ValueError('Scheduled scan limit must be between 1 and 10000')
                # Load and validate the existing credential-free configuration before
                # asking for the secret. This command never opens an IMAP socket.
                config = load_config(store.data_dir / 'imap.json')
                if not sys.stdin.isatty():
                    raise MailboxError('Enter credentials only in an interactive terminal; no pipes or command-line passwords')
                # The approval covers exactly these settings; any later change
                # to imap.json stops scheduled scans until enable runs again.
                folders = t('all selectable folders') if config.folders == ('*',) else ', '.join(config.folders)
                print(t('Scheduled scans will be approved only for {p0}:{p1} as {p2} ({p3}).',
                        p0=config.host, p1=config.port, p2=config.username, p3=folders))
                schedule = service.schedule()
                secret = getpass.getpass(t('Separate IMAP app password / OAuth2 token for OS keyring: '))
                try:
                    selector = service.credentials.save(secret, schedule.credential_id)
                finally:
                    secret = ''
                service.configure(credential_id=selector, target=config.target_fingerprint(),
                                  interval_seconds=args.interval_minutes * 60, limit=args.limit)
                print(t('Scheduled read-only IMAP scans are enabled. They run only while the local ARGUS dashboard is running.'))
                if config.auth == 'oauth2':
                    print(t('Note: OAuth2 access tokens usually expire within hours. Scheduled scans fail safely once it expires; run enable again with a fresh token or use a provider-supported app password.'))
        elif args.command == 'changes':
            print(json.dumps(store.recent_changes(), ensure_ascii=False, indent=2))
        elif args.command == 'undo':
            result = store.undo(args.batch)
            print(t('Undid one local change affecting {p0} account(s). Run undo again to go further back.', p0=len(result['accounts'])))
        elif args.command == 'bitwarden-export' and args.preview:
            print(json.dumps(preview_export(store, args.id, language), ensure_ascii=False, indent=2))
        elif args.command == 'bitwarden-export':
            count = export_file(store, args.path, args.id, language=language)
            print(t('Saved {p0} metadata items privately; password fields are empty. Import the file into Bitwarden yourself, only once.', p0=count))
        return 0
    except (MailboxError, DNSError, CredentialError) as exc:
        return fail(str(exc), t)
    except FileExistsError:
        return fail('The destination file already exists and will not be overwritten.', t)
    except (ValueError, FileNotFoundError) as exc:
        return fail(str(exc), t, prefix=t('Error: '))
    except (OSError, KeyboardInterrupt):
        return fail('Operation interrupted or local file access / port unavailable.', t)


def backup_command(args, data_dir, t):
    if args.command == 'backup' and args.list:
        print(json.dumps(list_backups(data_dir), ensure_ascii=False, indent=2))
    elif args.command == 'backup':
        path = create_backup(data_dir, folder=args.output)
        print(t('Saved a private backup: {p0}. It is not encrypted; keep it on an encrypted drive.', p0=path))
    elif not args.yes:
        manifest = read_manifest(args.path)
        print(t('Backup from {p0} (ARGUS {p1}). Run restore again with --yes to replace the current profile; its current state is saved first.',
                p0=manifest['created_at'], p1=manifest['app_version']))
    else:
        result = restore_backup(data_dir, args.path)
        Store(data_dir, Registry(args.providers))
        print(t('Profile restored from the backup of {p0}.', p0=result['restored']))
        if result['safety_backup']:
            print(t('The previous state was saved to {p0}.', p0=result['safety_backup']))
        print(t('Keyring authorizations are not part of a backup. If scheduled scans stop, approve them again with background-imap enable.'))
    return 0


def fail(message, t, prefix=''):
    """Print a constant error and, when one is known, its next step (plan F4)."""
    print(prefix + t(message), file=sys.stderr)
    hint = hint_for(message)
    if hint:
        print(t('Next step: ') + t(hint), file=sys.stderr)
    return 2


def report_scan(result, t):
    """JSON on stdout for scripts; translated next steps on stderr for people."""
    print(json.dumps(result, ensure_ascii=False))
    for step in result.get('next_steps', []):
        print(t('Next step: ') + t(step), file=sys.stderr)
