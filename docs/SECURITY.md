# Security and privacy model

## Network authorization

All MIME parsing, detection rules and result calculations run on the executing
computer. There are no AI APIs, telemetry, remote fonts, remote icons or automatic
provider-account probes. The app does not attempt service logins, request password
resets, change passwords or create online accounts.

`discover` is offline by default. Only `--allow-dns` authorizes an MX query to the
system resolver or an explicitly selected resolver IP. It sends only the mail
domain. MX is a receiving-route hint, not a verified IMAP host; spam filters may
hide the real provider. A null MX declares that the domain does not accept mail.
Verify settings in your provider account.

`setup-imap` saves only host, port, username, authentication method and folders.
`scan-imap --allow-imap` explicitly authorizes a connection to that TLS host for
authentication and read-only commands. Email links are never followed. Dashboard
links open only when you click. Bitwarden imports and password changes are carried
out by you in the official apps.

## Credentials

IMAP app passwords and OAuth2 tokens are entered in hidden interactive terminal
prompts. There are no secret fields in the HTTP API, CLI arguments, configuration
files or logs. A failed mailbox authentication aborts instead of trying a password
list. IMAP debug output is disabled; server error text is replaced with fixed,
non-sensitive messages.

Scheduled IMAP scanning is disabled by default. It can be enabled only from an
interactive terminal after an IMAP configuration exists; it runs only while the
local dashboard process is open. Its app password or externally obtained OAuth2
token is stored only in the operating-system keyring through the optional
`keyring` package. ARGUS has no plaintext file fallback and rejects known
plaintext keyring backends. SQLite stores only an opaque UUID selector, interval
and safe status metadata. `disable` stops future runs; `revoke` stops them first
and removes the keyring entry. Each run uses the existing incremental TLS/IMAP
path and fixed safe failure text, never a password retry list.
An atomic SQLite lease ensures that only one scheduled runner per profile may
open the mailbox at a time; a stale worker cannot overwrite a later result or
reactivate a disabled schedule. Folder checkpoints merge atomically.

The app never requests your Bitwarden master password, signs into Bitwarden or
reads your vault. Its optional direct transfer requires an already-unlocked
official Bitwarden CLI and creates only explicitly selected, password-free items;
it never changes or reads existing vault items. The Bitwarden account address is
independent of individual service sign-in addresses.

Python cannot reliably erase immutable strings from memory. Authorized-session
secrets exist in process memory; guaranteed zeroing is not claimed. Local malware
or another process with the same user privileges remains outside this model.

## Read-only email access

TLS requires hostname and certificate verification, with TLS 1.2 or newer. There
is no insecure IMAP mode or option to disable verification. A Proton Bridge with
its own local TLS configuration is not configured automatically; use an official
export and local import instead.

Folders use `select(..., readonly=True)`, which Python implements as EXAMINE.
Messages use bounded `BODY.PEEK`; no STORE, DELETE, EXPUNGE, APPEND or CLOSE commands
are issued. PEEK does not mark messages read. Messages over 2 MiB use up to 64 KiB
of headers and a reduced clue score. EML, Maildir and mbox originals are not changed.

UID checkpoints are saved after local processing. Changed UIDVALIDITY causes
rechecking. An interruption before a checkpoint may repeat a fetch, which local
fingerprints deduplicate. Cursor identity includes address scope and detection
rules, so a new alias is not hidden by old checkpoints. Writes validate the
address scope atomically; changing it interrupts a scan rather than overwriting
newer evidence with assessments for an old scope.

## Local storage

SQLite stores provider ID, known own sign-in address, sender domain, clue type,
heuristic score, date, source format, fingerprint, rule version and task state.
No email body, subject, attachment, email link, authentication token or password
is stored as evidence. Unknown domains remain unverified candidates with no
official website assigned.

Older-rule evidence is not treated as a current probable account until reanalysis.
Manual confirmations and checklists remain. Reanalysis replaces the assessment
for the same fingerprint and can remove an obsolete automatic clue; this affects
only local metadata, not original messages. Scan statistics contain counts, not
message text or provider error details.

Version 1.3 displays legacy German program-generated explanations in the selected
language without modifying their stored values. It does not change detection
rules or require version 1.1/1.2 messages to be re-imported for translation alone.

On POSIX, app data directories use 0700; database, configuration and CLI exports
use 0600. Existing export files are not overwritten and existing user-chosen parent
directory permissions are not changed. Windows protection depends on account ACLs.
The database is **not encrypted by the application**: use FileVault, BitLocker,
LUKS or another appropriate encrypted drive, and protect backups. Browser downloads
inherit download-folder permissions and may be included in cloud backups.

## Dashboard

The HTTP server binds only to 127.0.0.1. Each start creates a memory-only bearer
token passed through the local page to its browser session. It is not stored in
URLs, Local Storage or logs. API requests require the bearer header. Host and
Origin checks, no CORS permission, CSP, frame protection and `no-store` limit
browser attacks. Dynamic content uses `textContent`; provider links come from the
validated catalog rather than emails.

The optional Chromium browser companion is an unpacked Manifest V3 extension
with only the `activeTab` permission. When the user opens its popup it reads the
active tab URL locally, matches its hostname against a bundled public catalog,
and may copy/open an already verified settings URL. It has no host permissions,
content scripts, background worker, native messaging, network access or access to
page content, forms, cookies, passwords, history, tokens, email or Bitwarden.
A visited site is never evidence of an account.

Other local processes can retrieve the page too. This is a single-user app, not
protection against untrusted users sharing the same computer. Do not expose it as
a public web service or forward its port without access controls.

## Interpretation and coverage limits

Sender headers may be spoofed. An imported Authentication-Results header is not
treated as proof of DKIM authentication. Email clues therefore produce at most
“Probable”; only your explicit review produces “Confirmed”. Rule scores are not
calibrated probabilities. Historical evidence does not prove an active account.
“Unknown” never means “does not exist”.

Newsletters, guest orders and reset requests do not establish an account. Accounts
without emails, deleted messages, phone registration, other mailboxes or aliases,
and SSO can be missed. Shared product families can send through their central
identity-provider domain; Xbox activity may appear only as Microsoft evidence.
Accounts at one provider have separate stable IDs, checklists and transfer
journals. Only current strong evidence to one configured own address is grouped
with a corresponding identity. Ambiguous, forwarded and weak clues remain
provider-wide. Different addresses can still refer to aliases or changed
addresses; only user review can establish that entries represent separate
accounts. Manually labeled accounts sharing an address never automatically
inherit the recipient's evidence. Legacy progress is assigned conservatively
and is never copied to every new identity; unresolved legacy entries require
review before exports or completion. See [the account guide](ACCOUNTS.md).

The catalog is curated and uses a bounded set of English/German rules. Sender
domains and services change; extend them using official sources, not an email's
brand display name. Proper provider names and user-supplied content are preserved.

## Local language preferences

Translations are bundled and processed locally. No external translation service
is contacted. Browser Local Storage contains only the language preference `en`
or `de`; never the session token, emails, account results or credentials. Language
changes do not mutate stored evidence or change detection rules. The app remains
a single-user local tool, with no isolation between people sharing its profile.
