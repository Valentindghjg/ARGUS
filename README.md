# ARGUS 1.16.0

[Deutsch](README_DE.md) · English

[![Checks](https://github.com/Valentindghjg/ARGUS/actions/workflows/ci.yml/badge.svg)](https://github.com/Valentindghjg/ARGUS/actions/workflows/ci.yml)

ARGUS is a local Python account inventory with a **German/English dashboard**, **527
extensible providers**, local email analysis and a Bitwarden security checklist.
Users choose their interface language. Email detection always supports both
English and German, independently of that choice.

## Preview

The screenshots below use only the bundled synthetic demo data.

| Dashboard | Security worklist |
| --- | --- |
| [![ARGUS dashboard](https://github.com/Valentindghjg/ARGUS/releases/download/v1.16.0/argus-dashboard-demo.png)](https://github.com/Valentindghjg/ARGUS/releases/tag/v1.16.0) | [![ARGUS security worklist](https://github.com/Valentindghjg/ARGUS/releases/download/v1.16.0/argus-worklist-demo.png)](https://github.com/Valentindghjg/ARGUS/releases/tag/v1.16.0) |

The app finds **evidence in your own messages**. It does not probe accounts on
provider websites. Missing evidence leaves a service “Unknown”; it does not prove
that no account exists. Synthetic demo data and personal profiles stay separate.

## License

ARGUS is licensed under the
[Mozilla Public License 2.0](LICENSE) (MPL-2.0). Every feature is free: there
are no editions, license keys, online accounts, payment data or telemetry. See
[LICENSING.md](LICENSING.md) and the [publication checklist](docs/PUBLISHING.md).

**Quick start:** Python 3.11 or newer and a modern browser. ARGUS uses only the
Python standard library; npm and Docker are not required.
Extract the archive or clone the repository, open a terminal in its folder
(`ARGUS` for a Git clone), then run:

```bash
python -m pip install .
python -m argus_security --data-dir .local/demo demo --serve --open
```

Open `http://127.0.0.1:8765/` if your browser does not open automatically. Ctrl+C
stops the server. Use `--port 8766` if the port is occupied. On Windows, replace
`python` with `py -3` if needed; on macOS/Linux, use `python3` where appropriate.

The demo uses 17 synthetic messages, 12 discovered providers, two simulated manual
confirmations and one completed checklist. **These are not your real accounts.**

You can also clone the GitHub repository:

```bash
git clone https://github.com/Valentindghjg/ARGUS.git
cd ARGUS
python -m pip install .
python -m argus_security --data-dir .local/demo demo --serve --open
```

Use `git pull --ff-only` to update an existing clean checkout. Personal profiles
and credentials are excluded from Git; keep their protected backups separately.

## What this project does

- Finds local evidence for services by matching sender domains in your own email.
- Helps you review accounts, track security work and prepare password-free
  Bitwarden metadata imports.
- Runs locally; it does not mass-probe provider accounts, automate password
  resets, bypass CAPTCHAs or modify email.

It cannot prove that an account does not exist. A missing email, a phone-only
registration, an SSO account, deleted messages or another mailbox can all leave
no local evidence. Read [the safety model](docs/SECURITY.md) before importing
personal email.

## Choose your language

Use **Language → English / Deutsch** in the dashboard header. The same selector
is available inside an account checklist. The initial language follows your
browser language: German for `de`, English otherwise. Your explicit choice is
remembered in this browser on this local dashboard address. If browser preference
storage is blocked, switching still works for the current page.

Switching preserves filters, checklists, confirmation, assigned sign-in addresses,
Bitwarden selections and import progress. It changes navigation, setup guidance,
categories, detection explanations, dates and checklist labels. Provider names,
URLs, addresses and machine identifiers retain their original values. Custom
catalog names/categories remain as supplied. Email detection always uses both
languages. Different browser profiles can choose different languages.

The CLI follows your system language, or accepts a global flag **before** the
subcommand:

```bash
python -m argus_security --language en --help
python -m argus_security --language de --help
python -m argus_security --language de --data-dir .local/demo demo --serve
```

Human-readable help, prompts, validation and metadata notes use that language.
Command names, flags and JSON keys stay stable for scripts. The browser chooses
its language separately from the terminal. Language switching makes no external
requests; only the two-letter preference is stored in browser Local Storage.
Tokens, email content, account results and credentials are never stored there.

## Your personal profile

Run the app on **your own computer** before processing real emails or credentials.
Replace `your.email@example.org` with your own registration address:

```bash
python -m argus_security init --email your.email@example.org
python -m argus_security serve --open
```

The default personal directory is `~/.local/share/argus/`. A profile from
before the ARGUS rename (`~/.local/share/account-finder/`) is moved there
automatically once, with its files and permissions. To use a
different directory, put `--data-dir /absolute/path` **before the subcommand**;
such a directory is never moved. After `pip install .` the shorter `argus`
command works the same as `python -m argus_security`. The old `account-finder`
command and `python -m account_finder` still work for now but print a
deprecation notice.
Your new personal profile initially has no discovered accounts until emails are
imported. The demo directory is separate.

You can configure multiple own registration addresses:

```bash
python -m argus_security --data-dir .local/personal init --email your.email@example.org --email your.alias@example.org
```

Add another own address later in “Mailbox & Import”, or with:

```bash
python -m argus_security add-email --email your.alias@example.org
```

Adding addresses preserves existing addresses, confirmations and checklists.
Re-import local email files afterwards. The next explicitly authorized IMAP scan
rechecks older messages for the expanded scope. Adding an existing alias does not
reset progress. Up to 64 own addresses can be added to a profile. Plus aliases
are not automatically treated as identical. Personal aliases cannot be added to
the demo profile.

**Your Bitwarden account can use a different email address.** It is not needed by
this app. Each vault item uses the sign-in address of its service, not your
Bitwarden account address. Never put IMAP secrets or your Bitwarden master
password in this chat, the source code or a configuration file.

## Import local emails

Choose multiple **EML files** in “Mailbox & Import”. Data travels only between
your browser and 127.0.0.1. Email bodies are analyzed locally but not stored as
results. Original files stay unchanged. The upload limit is 2 MiB per message;
export large messages without attachments in your email client where practical.

Command-line imports do not use outgoing network connections:

```bash
python -m argus_security import /path/to/eml-folder --format eml
python -m argus_security import /path/to/mailbox.mbox --format mbox
python -m argus_security import /path/to/Maildir --format maildir
python -m argus_security report
```

Maildir needs `cur/` and `new/`. Re-importing does not duplicate evidence or reset
your checklist. Current rules or a newly added provider domain can replace an
older automatic assessment of the same message. A message that no longer provides
evidence loses only its automatic clue; manual confirmations remain.

The dashboard retains statistics for the entire multi-file import after reload.
“Cancel import” stops after the current file and preserves processed clues. You
can also cancel an unfinished import after reloading. Imports idle for ten
minutes are marked interrupted when next accessed. Skipped files, errors and
header-only analysis are visible as “Completed with gaps”. CLI changes appear in
the open dashboard within 15 seconds.

## Identify your email provider

For a custom domain, the provider cannot be inferred from the address alone.
Replace `example.org` with your own mail domain in these commands.
**No real MX lookup or mailbox connection has been performed for you.** Offline
guidance:

```bash
python -m argus_security discover --domain example.org
```

If you explicitly authorize the public DNS query:

```bash
python -m argus_security discover --domain example.org --allow-dns
```

Only the domain is sent to your DNS resolver, not the full email address or any
credentials. Results contain MX records and possible provider hints. MX describes
the receiving route; an upstream spam filter can hide the real mail host. Verify
the actual IMAP settings in your email client, hosting account or official
provider documentation. No guessed IMAP host is tried automatically.

On Windows, `/etc/resolv.conf` may not provide a system resolver. Use an explicitly
selected resolver IP with `--resolver RESOLVER-IP`, configure offline, or run
`Resolve-DnsName -Name example.org -Type MX` yourself. That PowerShell command
also makes a network query; the app does not run it automatically.

## Set up secure IMAP

1. Create a separate **IMAP app password** with your actual provider if supported.
2. Verify the documented host. Do not guess or try a list of hosts.
3. Save settings without credentials:

```bash
python -m argus_security setup-imap
```

The assistant asks for the host and username and saves private `imap.json`; it
does not connect. Defaults: TLS port 993 and all selectable folders, including
archives. To choose folders explicitly:

```bash
python -m argus_security setup-imap --host VERIFIED-IMAP-HOST --username your.email@example.org --folder INBOX --folder Archive
```

Replace `VERIFIED-IMAP-HOST` with the actual host. Folder names depend on the
provider. Existing `imap.json` is not overwritten; edit it locally to change
settings. Do not add credentials. Only these fields are accepted:

```json
{
  "host": "imap.mailprovider.example",
  "username": "your.email@example.org",
  "port": 993,
  "auth": "app_password",
  "folders": ["*"]
}
```

4. Explicitly authorize the connection, first with a limited scan:

```bash
python -m argus_security scan-imap --allow-imap --list-folders
python -m argus_security scan-imap --allow-imap --limit 500
python -m argus_security scan-imap --allow-imap
```

The secret is entered in a hidden interactive terminal prompt on every run and
is not saved. TLS certificates and hostnames are checked. Folders are opened
read-only; messages use `BODY.PEEK`; sessions end with LOGOUT. No read flags,
deletions or email modifications. Messages over 2 MiB use at most 64 KiB of headers,
with a reduced clue score and visible coverage warning.

UID checkpoints support resuming. “Limit reached” means messages remain; rerun the
authorized scan to continue. Reaching the limit exactly at the end of selected
folders completes normally. Errors, skips and header-only analysis indicate gaps.
Changing the address scope during a scan interrupts it; restart to use the new
scope. Use `--full-scan` to explicitly recheck previously read messages.

### Optional scheduled scans

After you have verified `imap.json` with a manual read-only scan, you can opt in
to incremental scans while the local ARGUS dashboard is running. Install a
supported **OS-protected** Python keyring first; ARGUS refuses plaintext keyring
backends and has no file fallback:

```bash
python -m pip install keyring
python -m argus_security background-imap enable --interval-minutes 1440 --limit 500
python -m argus_security serve --open
```

The command asks for the separate app password or externally obtained OAuth2
token only in a hidden terminal prompt. It saves that secret only in the OS
keyring; the local SQLite database keeps an opaque selector and schedule metadata
only. The first scan is due when the dashboard starts, then it resumes from the
normal IMAP UID checkpoints. It never runs when ARGUS is closed, does not do a
full rescan, does not change mail, and backs off after a safe fixed error.

The approval covers exactly the settings shown by `enable` (host, port,
username, sign-in method and folders). If `imap.json` changes later, scheduled
scans stop before using the stored authorization; run `background-imap enable`
again to approve the new settings. Schedules created before this check also ask
for one new approval.

Check, pause, or remove the authorization with:

```bash
python -m argus_security background-imap status
python -m argus_security background-imap disable
python -m argus_security background-imap revoke
```

`disable` pauses future scans while retaining the keyring entry. `revoke`
disables scans first and then removes the entry from the OS keyring. A scan that
is already running stops before its next message fetch. Dashboard
setup shows status only and never accepts a password or token.

### OAuth2 and provider differences

Exchange Online requires OAuth2 where Basic Authentication is disabled; an app
password does not bypass this. Choose `--auth oauth2` during setup or edit the
field in `imap.json`. XOAUTH2 accepts a **short-lived access token obtained
externally**, entered in a hidden terminal prompt. The app does not register an
OAuth application, run a login flow, or save refresh tokens. Obtain authorization
through your provider or administrator; use a local email export if that is not
practical.

Google app passwords depend on account and security settings; managed accounts
may impose further restrictions. Follow the official provider documentation.
Proton Mail does not provide an ordinary direct IMAP login. The local Bridge is
not automatically configured by this TLS-only scanner; use official export tools
and import EML/mbox instead.

## Optional browser companion

`browser-companion/` contains an unpacked Chromium extension prototype. When you
open its popup, it checks only the active tab’s hostname against a bundled public
ARGUS catalog. It can copy or open a verified password-management link where one
exists. It never reads page content, forms, cookies, passwords, history, tokens,
email or Bitwarden data, and a site visit never creates or confirms an account.

```bash
python browser-companion/scripts/build.py
python browser-companion/tests/validate.py
```

Load the generated `browser-companion/dist/` with your Chromium browser’s
**Load unpacked** option. See its [companion guide](browser-companion/README.md).

## Resume a security worklist

Open **Security worklist** and choose **Secure next account** to let ARGUS add
one highest-priority incomplete local account to the worklist. Your queue, pause
state and checklists persist locally after a restart. Each dialog shows the next
missing step. The guided Bitwarden button has a second confirmation and creates
one password-free item only for the current account. Accounts using SSO or
passkeys skip a separate password change. Nothing is submitted to a provider
automatically.
Choose **Build priority worklist** to explicitly add up to ten more highest-
priority incomplete accounts in deterministic local order. Existing worklist
items keep their place; the action changes no checklist, password, provider or
Bitwarden item. Before the button can be used, the worklist shows the exact local
priority preview, including each account's current next step. Review it before
confirming the append action.
For an account that cannot be handled immediately, choose **Tomorrow** or **In
one week**. ARGUS stores the date only in the local worklist and makes the item
ready again when that date is reached while the dashboard is open. It sends no
notification and contacts no service.
For a different date, choose it in the worklist calendar and select **Schedule
date**. Dates must be in the next 365 days and are saved only locally.
For review, password-change, sign-in and MFA/recovery steps, **I completed this
step** records your explicit local confirmation and immediately advances the
guide.
See the [worklist guide](docs/WORKLIST.md) and
[interrupted-transfer guidance](docs/BITWARDEN_CLI.md).

## Review and secure accounts with Bitwarden

Each sign-in identity has its own entry, checklist, worklist and Bitwarden
handoff. Strong direct evidence at different own addresses produces separate
probable entries; review them because aliases and address changes may still
refer to one account. In account details, **Add another account at this service**
lets you explicitly add a known local record, including labeled accounts that
share an email address. Nothing is created at the provider. See the
[separate-account and migration guide](docs/ACCOUNTS.md).

Each provider has an official website, category, known own sign-in addresses,
clue type and strength, status and security priority. Documented password-settings
links are supplied for Google, Apple and GitHub with source and verification date.
Others link to the curated homepage; email links are never used for this purpose.

- **Confirmed:** you checked “I verified that this account exists”.
- **Probable:** an account-related local clue reaches the rule threshold. Emails
  may still be historical or spoofed.
- **Unknown:** insufficient evidence. This never means “does not exist”.

Newsletters, guest orders and reset requests do not establish an account. A score
is a heuristic clue-strength value, not a calibrated probability. Multiple own
To-recipients are ambiguous; no arbitrary sign-in address is selected.

Click “Review”. Confirm existence yourself, assign a known own sign-in address
if needed, and select password, SSO or passkey. Use an existing Bitwarden item
where possible. Generate new passwords **in Bitwarden**, change them yourself at
the provider and test sign-in. Review MFA and recovery too. Marking “Done” requires
the checklist steps; SSO/passkeys do not require a separate service password.
You can manually confirm a catalog provider even without email evidence.

Under “Prepare Bitwarden”:

1. Optionally choose **Check selected accounts in unlocked Bitwarden**. After a
   separate confirmation, ARGUS uses the already-unlocked official CLI to search
   only for each selected account and returns only **found / possible / none**
   plus a count. The CLI response may contain vault fields while it is being
   processed, but ARGUS neither saves nor displays names, usernames or passwords.
   Review any possible match yourself.
2. Assign existing vault items first. Those providers are excluded from downloads.
3. Select genuinely missing items. Probable accounts are not selected by default;
   your explicit selection survives automatic refreshes.
4. Download **metadata JSON**. Items contain provider name, official URI, identified
   address and notes. Password fields are empty; TOTP is null.
5. In the official Bitwarden app, choose Import → **Bitwarden (json)** and import
   into your existing vault, regardless of its account email address.
6. Import the file **once**, check the result, then delete it. Bitwarden adds items
   without duplicate checking. This JSON-import path never reads or overwrites
   vault entries. Importing an empty item does not mean a password change
   succeeded.

Alternatively, after you unlock the official Bitwarden CLI in your own terminal,
the dashboard can create the explicitly selected password-free items directly.
The separate optional audit is read-only; the creation action never reads or
overwrites existing items. Neither action receives your master password. Follow
the [Bitwarden CLI handoff guide](docs/BITWARDEN_CLI.md).

A command-line metadata export is also supported:

```bash
python -m argus_security bitwarden-export /local/protected/path/argus-bitwarden.json --id github --id steam
```

CLI exports are created with private permissions and never overwrite existing
files. JSON contains no passwords but does contain personal metadata. Browser
downloads use the permissions and backup settings of your downloads directory.

## Extend the provider catalog

`argus_security/data/providers.json` contains 527 curated providers. Add a separate
JSON file without editing the built-in catalog:

```bash
python -m argus_security --providers examples/providers-extra.json --data-dir .local/demo-custom demo --serve
```

The example is synthetic and uses `.example`. IDs and domain roots must be unique;
websites must use HTTPS and belong to a configured provider domain. Subdomains
are matched automatically; more specific domains take precedence. Do not assign
generic shared email-delivery domains to a service. Custom names and category
labels are used as supplied.

A password link requires `password_url`, `password_source` and
`password_verified`. Add these only after verifying an official source. Re-import
emails or run `scan-imap --allow-imap --full-scan` afterwards, and restart the
dashboard with the same additional catalog.

## Upgrade and tests

The repository includes GitHub Actions checks for Python 3.11–3.14 on Linux,
installation of the built package, and German/English browser regression tests.
These use synthetic data and do not connect to personal mailboxes or Bitwarden.
See [contributing](CONTRIBUTING.md) for development and
[security reporting](SECURITY.md) for confidential vulnerability reports.

Version 1.9 migrates provider-wide state to separate account identities. Stop the
app and back up your protected profile before upgrading. Progress follows one
unambiguous or explicitly assigned address; unresolved legacy progress stays
visible for review and is never copied to every sibling account. Use version
1.9 or newer with the migrated profile. See [migration details](docs/ACCOUNTS.md).

Version 1.7 adds a persistent security worklist and a durable Bitwarden transfer
journal that blocks retries after ambiguous writes. Existing inventories gain two
new local tables automatically; evidence and checklists are preserved. Back up
your protected data directory before upgrading.

Versions 1.5 and 1.6 added a Free/Pro presentation and offline Pro licenses. The
next major version removes both again because every feature stays free. A
leftover `license.json` in an old profile is ignored and can be deleted.
Detection, the database schema and account results remain compatible. Version 1.4
expands the built-in catalog from 372 to 527 providers. Existing profiles and checklists remain compatible.
Re-import local source emails or run a separately authorized
`scan-imap --allow-imap --full-scan` to evaluate the new domains against them.
This does not modify the original emails. See [the change log](docs/CHANGELOG.md).

Tests use synthetic messages, fake IMAP and local loopback connections only:

```bash
python -m unittest discover -s tests -v
```

The optional browser test needs an already installed Playwright library and
Chromium, neither of which is required to run the app:

```bash
python scripts/browser_smoke.py --browser /usr/bin/chromium --screenshots-dir docs/preview
python scripts/browser_multi_account.py --browser /usr/bin/chromium
```

| File | Purpose |
|---|---|
| `argus_security/analysis.py` | Local MIME parsing and bilingual detection rules |
| `argus_security/data/providers.json` | Extensible provider catalog |
| `argus_security/i18n.py`, `data/translations.json` | Local German/English presentation |
| `argus_security/store.py` | SQLite evidence and checklist persistence |
| `argus_security/instances.py` | Stable account identities and conservative profile migration |
| `argus_security/imap_client.py` | TLS IMAP, PEEK and resuming |
| `argus_security/background.py` | Explicit keyring-backed incremental IMAP schedule |
| `argus_security/discovery.py` | Explicitly authorized MX hints |
| `argus_security/bitwarden.py` | Official metadata-only import format |
| `argus_security/server.py`, `web/` | Local dashboard |
| `argus_security/cli.py` | Command line (`argus`), default profile and its one-time move |
| `argus_security/scan.py` | EML, mbox and Maildir import sessions and the synthetic demo |
| `argus_security/registry.py` | Strict provider-catalog validation and domain matching |
| `argus_security/workflow.py` | Local security worklist and guided next step |
| `argus_security/handoffs.py` | Durable Bitwarden transfer journal |
| `argus_security/mailbox_lease.py` | One mailbox session per profile across processes |
| `argus_security/errors.py` | Fixed, translatable messages that may reach the dashboard |
| `account_finder/` | Deprecated alias for `python -m account_finder` and `account-finder` |
| `tests/` | Automated regression tests |
| `browser-companion/` | Minimal unpacked Chromium domain/settings-link companion |
| [Catalog policy](docs/CATALOG.md) | Scope, review standards and how to propose providers |
| [Publishing checklist](docs/PUBLISHING.md) | Owner-controlled steps before making the repository public |
| [Product strategy (German)](docs/strategy/README.md) | Master plan for features and safe automation, with implementation status |
| [Technical plan](docs/PLAN.md) | Architecture and development sequence |
| [Security model](docs/SECURITY.md) | Privacy, protections and limits |
| [Privacy statement](PRIVACY.md) | What the local app processes and when it connects |
| [Support](SUPPORT.md) | Discussions, issues and safe reporting rules |
| [Test report](docs/TEST_REPORT.md) | Checks actually performed |
| [Official sources](docs/SOURCES.md) | Bitwarden, settings links and mail providers |

**Run personal analysis on your own computer.** A remote development environment
processes data on that remote machine, not locally on your device. Use synthetic
demo data there. Do not publish the dashboard or forward its port without access
protection. The database is not encrypted by the app; use drive encryption and
protected backups.
