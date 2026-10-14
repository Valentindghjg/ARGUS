"""Terminal interface; passwords are never command-line arguments."""
import argparse
import getpass
import json
from pathlib import Path
import sys
from .i18n import translate, cli_language, LocalizedArgumentParser, localize_discovery
from .registry import Registry
from .discovery import discover, DNSError
from .imap_client import IMAPConfig, MailboxError, load_config, save_config, imap_messages
from .bitwarden import export_file
from .scan import file_messages, load_demo, scan_messages
from .server import serve
from .store import Store
DEFAULT_DATA = Path.home() / '.local' / 'share' / 'account-finder'

def parser(language="en"):
    t = lambda message, **values: translate(message, language, **values)
    p = LocalizedArgumentParser(language=language, description=t('Local account finder. No login attempts at cataloged services.'))
    p.add_argument('--data-dir', type=Path, default=DEFAULT_DATA, help=t('Private local results directory'))
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
    export = sub.add_parser('bitwarden-export', help=t('Selected metadata as Bitwarden JSON, no passwords'))
    export.add_argument('path', type=Path)
    export.add_argument('--id', action='append', required=True, help=t('Provider ID; may be repeated'))
    sub.add_parser('license-status', help=t('Show the local Free or Pro license status'))
    activation = sub.add_parser('activate-license', help=t('Verify and store a signed Pro license locally'))
    activation.add_argument('path', type=Path, help=t('Signed Pro license JSON file'))
    return p

def main(argv=None):
    language = cli_language(argv)
    t = lambda message, **values: translate(message, language, **values)
    args = parser(language).parse_args(argv)
    try:
        registry = Registry(args.providers)
        store = Store(args.data_dir, registry)
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
                raise ValueError(t('Run init or demo first'))
            serve(store, args.port, args.open, language=language)
        elif args.command == 'import':
            result = scan_messages(store, file_messages(args.path, args.format), args.format, lambda s: print(t('Processed locally: {p0}; new clues: {p1}', p0=s['processed'], p1=s['evidence']), flush=True))
            print(json.dumps(result, ensure_ascii=False))
        elif args.command == 'report':
            print(json.dumps(store.snapshot()['summary'], ensure_ascii=False, indent=2))
        elif args.command == 'discover':
            domain = args.domain
            if not domain:
                emails = store.meta('emails', [])
                if not emails:
                    raise ValueError(t('Specify --domain or run init first'))
                domain = emails[0].split('@', 1)[1]
            print(json.dumps(localize_discovery(discover(domain, allow_network=args.allow_dns, resolver=args.resolver), language), ensure_ascii=False, indent=2))
        elif args.command == 'setup-imap':
            emails = store.meta('emails', [])
            if not emails or store.meta('demo', False):
                raise ValueError(t('Initialize a personal local profile with init first'))
            print(t('No connection will be opened. Verify the host in official provider documentation first.'))
            host = args.host or input(t('Verified IMAP host (TLS): ')).strip()
            username = args.username or input(t('IMAP username [{p0}]: ', p0=emails[0])).strip() or emails[0]
            config = IMAPConfig(host, username, args.port, args.auth, tuple(args.folder or ['*']))
            save_config(store.data_dir / 'imap.json', config)
            print(t('Saved private imap.json without passwords or tokens. Run scan-imap --allow-imap to scan.'))
        elif args.command == 'scan-imap':
            if not args.allow_imap:
                raise MailboxError(t('No connection authorized; explicitly choose scan-imap --allow-imap'))
            if store.meta('demo', False) or not store.meta('emails'):
                raise ValueError(t('IMAP requires an initialized personal local profile'))
            if args.limit is not None and args.limit < 1:
                raise ValueError(t('The scan limit must be positive'))
            config = load_config(store.data_dir / 'imap.json')
            print(t('Authorized TLS host: {p0}:{p1}; read-only access.', p0=config.host, p1=config.port))
            if not sys.stdin.isatty():
                raise MailboxError(t('Enter credentials only in an interactive terminal; no pipes or command-line passwords'))
            secret = getpass.getpass(t('Short-lived IMAP OAuth2 token: ') if config.auth == 'oauth2' else t('Separate IMAP app password (not Bitwarden): '))
            try:
                messages = imap_messages(store, config, secret, allow_network=True, full_scan=args.full_scan, limit=args.limit, list_only=args.list_folders)
                if args.list_folders:
                    for folder in messages:
                        print(folder)
                else:
                    result = scan_messages(store, messages, 'imap', lambda s: print(t('Processed locally: {p0}; new clues: {p1}', p0=s['processed'], p1=s['evidence']), flush=True))
                    print(json.dumps(result, ensure_ascii=False))
            finally:
                secret = ''
        elif args.command == 'bitwarden-export':
            count = export_file(store, args.path, args.id, language=language)
            print(t('Saved {p0} metadata items privately; password fields are empty. Import the file into Bitwarden yourself, only once.', p0=count))
        elif args.command == 'license-status':
            print(json.dumps(store.snapshot()["product"]["license"], ensure_ascii=False, indent=2))
        elif args.command == 'activate-license':
            from .licensing import read_document
            print(json.dumps(store.activate_license(read_document(args.path)), ensure_ascii=False, indent=2))
        return 0
    except (MailboxError, DNSError) as exc:
        print(t(str(exc)), file=sys.stderr)
        return 2
    except FileExistsError:
        print(t('The destination file already exists and will not be overwritten.'), file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError) as exc:
        print(t('Error: ') + t(str(exc)), file=sys.stderr)
        return 2
    except (OSError, KeyboardInterrupt):
        print(t('Operation interrupted or local file access / port unavailable.'), file=sys.stderr)
        return 2
