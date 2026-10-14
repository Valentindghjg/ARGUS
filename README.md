# Account Compass 1.6.1

[Deutsch](README_DE.md) · English

[![Checks](https://github.com/Valentindghjg/account-compass/actions/workflows/ci.yml/badge.svg)](https://github.com/Valentindghjg/account-compass/actions/workflows/ci.yml)

A local Python account finder with a **German/English dashboard**, **527
extensible providers**, local email analysis and a Bitwarden security checklist.
Users choose their interface language. Email detection always supports both
English and German, independently of that choice.

The app finds **evidence in your own messages**. It does not probe accounts on
provider websites. Missing evidence leaves a service “Unknown”; it does not prove
that no account exists. Synthetic demo data and personal profiles stay separate.

## License status

Account Compass Free is licensed under the
[Mozilla Public License 2.0](LICENSE) (MPL-2.0). A future commercial Pro edition
will be distributed separately under its own terms; it is not included in this
repository. See [LICENSING.md](LICENSING.md) and the
[publication checklist](docs/PUBLISHING.md).

## Account Compass Free and Pro

This build is **Account Compass Free**: its account inventory, local mail import,
security checklists and password-free Bitwarden metadata are available without an
online account, payment data or telemetry. The dashboard also explains a future
**Pro edition in development**. It is not implemented, purchasable or
activatable yet, so Free is not limited by an artificial trial. See [the Freemium plan](docs/FREEMIUM.md).

**Quick start:** Python 3.11 or newer and a modern browser. Install the one
security dependency from the project metadata; npm and Docker are not required.
Extract the archive, open a terminal in `account-finder`, then run:

```bash
python -m pip install .
python -m account_finder --data-dir .local/demo demo --serve --open
```

Open `http://127.0.0.1:8765/` if your browser does not open automatically. Ctrl+C
stops the server. Use `--port 8766` if the port is occupied. On Windows, replace
`python` with `py -3` if needed; on macOS/Linux, use `python3` where appropriate.

The demo uses 17 synthetic messages, 12 discovered providers, two simulated manual
confirmations and one completed checklist. **These are not your real accounts.**

You can also clone the GitHub repository:

```bash
git clone https://github.com/Valentindghjg/account-compass.git
cd account-compass
python -m pip install .
python -m account_finder --data-dir .local/demo demo --serve --open
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
python -m account_finder --language en --help
python -m account_finder --language de --help
python -m account_finder --language de --data-dir .local/demo demo --serve
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
python -m account_finder init --email your.email@example.org
python -m account_finder serve --open
```

The default personal directory is `~/.local/share/account-finder/`. To use a
different directory, put `--data-dir /absolute/path` **before the subcommand**.
Your new personal profile initially has no discovered accounts until emails are
imported. The demo directory is separate.

You can configure multiple own registration addresses:

```bash
python -m account_finder --data-dir .local/personal init --email your.email@example.org --email your.alias@example.org
```

Add another own address later in “Mailbox & Import”, or with:

```bash
python -m account_finder add-email --email your.alias@example.org
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
python -m account_finder import /path/to/eml-folder --format eml
python -m account_finder import /path/to/mailbox.mbox --format mbox
python -m account_finder import /path/to/Maildir --format maildir
python -m account_finder report
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
python -m account_finder discover --domain example.org
```

If you explicitly authorize the public DNS query:

```bash
python -m account_finder discover --domain example.org --allow-dns
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
python -m account_finder setup-imap
```

The assistant asks for the host and username and saves private `imap.json`; it
does not connect. Defaults: TLS port 993 and all selectable folders, including
archives. To choose folders explicitly:

```bash
python -m account_finder setup-imap --host VERIFIED-IMAP-HOST --username your.email@example.org --folder INBOX --folder Archive
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
python -m account_finder scan-imap --allow-imap --list-folders
python -m account_finder scan-imap --allow-imap --limit 500
python -m account_finder scan-imap --allow-imap
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

## Review and secure accounts with Bitwarden

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

1. Assign existing vault items first. Those providers are excluded from downloads.
2. Select genuinely missing items. Probable accounts are not selected by default;
   your explicit selection survives automatic refreshes.
3. Download **metadata JSON**. Items contain provider name, official URI, identified
   address and notes. Password fields are empty; TOTP is null.
4. In the official Bitwarden app, choose Import → **Bitwarden (json)** and import
   into your existing vault, regardless of its account email address.
5. Import the file **once**, check the result, then delete it. Bitwarden adds items
   without duplicate checking. This app never reads or overwrites vault entries.
   Importing an empty item does not mean a password change succeeded.

Alternatively, after you unlock the official Bitwarden CLI in your own terminal,
the dashboard can create the explicitly selected password-free items directly.
It never reads or overwrites existing items and never receives your master
password. Follow the [Bitwarden CLI handoff guide](docs/BITWARDEN_CLI.md).

A command-line metadata export is also supported:

```bash
python -m account_finder bitwarden-export /local/protected/path/account-finder.json --id github --id steam
```

CLI exports are created with private permissions and never overwrite existing
files. JSON contains no passwords but does contain personal metadata. Browser
downloads use the permissions and backup settings of your downloads directory.

## Extend the provider catalog

`account_finder/data/providers.json` contains 527 curated providers. Add a separate
JSON file without editing the built-in catalog:

```bash
python -m account_finder --providers examples/providers-extra.json --data-dir .local/demo-custom demo --serve
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

Version 1.6 adds signed, offline Pro-license verification and local activation.
The default build contains no publisher public key, so it cannot activate Pro or
contact a payment service. Version 1.5 adds local Free/Pro product presentation.
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
```

| File | Purpose |
|---|---|
| `account_finder/analysis.py` | Local MIME parsing and bilingual detection rules |
| `account_finder/data/providers.json` | Extensible provider catalog |
| `account_finder/i18n.py`, `data/translations.json` | Local German/English presentation |
| `account_finder/store.py` | SQLite evidence and checklist persistence |
| `account_finder/imap_client.py` | TLS IMAP, PEEK and resuming |
| `account_finder/discovery.py` | Explicitly authorized MX hints |
| `account_finder/bitwarden.py` | Official metadata-only import format |
| `account_finder/server.py`, `web/` | Local dashboard |
| `tests/` | Automated regression tests |
| [Catalog policy](docs/CATALOG.md) | Scope, review standards and how to propose providers |
| [Freemium plan](docs/FREEMIUM.md) | Available Free functionality, Pro-in-development status and product boundaries |
| [Commercial-release checklist](docs/COMMERCIAL_RELEASE.md) | Owner decisions before accepting a Pro payment |
| [License implementation](docs/LICENSE_IMPLEMENTATION.md) | Signed offline Pro licenses and publisher key handling |
| [Publishing checklist](docs/PUBLISHING.md) | Owner-controlled steps before making the repository public |
| [Technical plan](docs/PLAN.md) | Architecture and development sequence |
| [Security model](docs/SECURITY.md) | Privacy, protections and limits |
| [Test report](docs/TEST_REPORT.md) | Checks actually performed |
| [Official sources](docs/SOURCES.md) | Bitwarden, settings links and mail providers |

**Run personal analysis on your own computer.** A remote development environment
processes data on that remote machine, not locally on your device. Use synthetic
demo data there. Do not publish the dashboard or forward its port without access
protection. The database is not encrypted by the app; use drive encryption and
protected backups.
