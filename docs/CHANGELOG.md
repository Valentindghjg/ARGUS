# Change log

## 1.7.0 — Resumable security worklist and reliable Bitwarden handoff

- Added a persistent, bilingual security worklist with selection, pause/resume,
  deferral, manual completion and guided next steps for passwords, SSO and passkeys.
- Added a durable per-address Bitwarden creation journal and atomic reservations.
  CLI failures and timeouts require explicit vault review before another attempt.
  Successful addresses are excluded from later handoffs and metadata exports.
- Added explicit reconciliation of uncertain transfers, preservation of partial
  successes and protection against simultaneous creation attempts.
- Disabled real Bitwarden CLI transfers in the synthetic demo.
- Added migration, restart, concurrency, timeout, partial-batch, authorization and
  browser coverage using synthetic data and a fake CLI. No automatic provider
  password changes or scheduled background scans are included.

## 1.6.1 — Optional Bitwarden CLI handoff, 14 October 2026

- Added an opt-in dashboard handoff to an already-unlocked official Bitwarden CLI.
  It creates only explicitly selected, password-free metadata items and never
  reads, changes or overwrites existing vault items.
- Added German and English guidance for the local CLI handoff and a secure
  provider-change workflow. Passwords stay in Bitwarden; provider password
  changes still require the user to complete each service’s authentication, MFA
  and confirmation flow.
- Added regression coverage for the password-free CLI payload, required unlocked
  session and dashboard endpoint.

## 1.6.0 — Offline Pro licensing foundation, 14 October 2026

- Added Ed25519-signed, privacy-minimized Pro entitlement verification and local
  activation. The default build has no publisher public key, so it stays Free and
  cannot contact a payment service or activate arbitrary files.
- Added publisher-only key-generation and license-issuance tools. Private keys
  are never generated into, read from or committed by the application itself.
- Added license status and activation commands, a dashboard activation path for a
  future signed build, tests for valid, expired and tampered licenses, and
  commercial integration documentation.

## 1.5.0 — Freemium foundation, 14 October 2026

- Added the local **Account Compass Free** edition and a dashboard Plans page
  with a transparent, unavailable Pro preview.
- Product metadata is local and test-covered. The build contains no checkout,
  payment information, telemetry, online account or license activation.
- Added English/German Freemium documentation and a commercial-release checklist
  for the future publisher. It requires a real seller, license, legal terms,
  payment provider and signed entitlement design before paid features ship.
- Existing profiles, account detection, data schema and Free features remain
  unchanged.

## 1.4.0 — Public-release preparation and catalog expansion, 14 October 2026

- Built-in catalog expanded from 372 to **527** provider entries across all
  supported categories. The registry validates unique roots and specific
  subdomain precedence; no provider account queries were added.
- Public project materials: catalog policy, publication checklist, support guide,
  code of conduct, issue routing and Dependabot configuration.
- Package metadata now identifies the project, supported Python versions and
  repository URLs. A license remains an owner decision and is deliberately not
  assumed by this release.
- Readme reorganized for first-time users, with clear purpose, limitations,
  upgrade instructions and public-project links.
- Existing profiles remain compatible. Re-import local source emails or run an
  explicitly authorized full IMAP scan to consider new catalog domains.

## 1.3.0 — German/English interface, 14 October 2026

- Language selectors in the dashboard header and open account checklists;
  automatic browser language and locally remembered choice.
- Both languages for navigation, filters, categories, explanations, checklists,
  dates, imports, setup, validation and password-free Bitwarden notes.
- CLI follows system language with an explicit global `--language en|de` flag.
- Filters, checklist state, sign-in addresses, export selection and import
  progress survive language changes. Browser profiles choose independently.
- Full English and German installation/user guides; shared local translation
  catalog. No translation services or new runtime dependencies.
- Detection version remains 2; no re-import is needed from 1.1/1.2 for this change.
- 97 Python tests and 14 browser groups pass using artificial data only.

### Upgrade from 1.1 or 1.2

Stop the app, protect a backup of the data directory, replace source files and
restart with the same `--data-dir` and custom catalog. The database schema,
evidence, checklists, confirmations and identifiers are preserved. The language
preference belongs to each browser; it contains only `en` or `de`.

## 1.2.0 — English release, 14 October 2026

- English dashboard, navigation, checklists, filters, scan summaries, errors,
  setup guidance, CLI prompts and help, detection explanations, provider categories,
  Bitwarden notes, examples and documentation.
- App display name changed to **Account Compass**; package, command names,
  provider IDs, folder paths and database identifiers remain compatible.
- Legacy German program-generated caveats are displayed in English without
  rewriting stored data or changing manual confirmations.
- English date/search formatting. Official proper names and user-supplied text
  are preserved.
- English and German email detection rules are unchanged. No new runtime
  dependencies. Version 1.1 profiles need no email re-import solely for this change.
- 86 automated tests and eight browser checks pass with synthetic data, including
  preservation of a legacy German explanation and confirmation state.

### Upgrade from 1.1

Stop the dashboard and scanner, make a protected backup of your local data
directory, and replace the source code with version 1.2. Start with the same
`--data-dir` and additional catalog. Existing checklists, known addresses,
priorities, sign-in methods and evidence are preserved. Custom catalog labels are
used verbatim; translate your own labels if desired.

## 1.1.0 — Detection and workflow improvements, 14 October 2026

- Account creation is no longer hidden by an unsubscribe footer or a newsletter
  offer after the main message. Pure newsletter signups remain unknown.
- More English/German activation and verification phrases; negated events are
  rejected. Subject and body are not joined into an artificial event.
- Multiple own recipients do not cause an arbitrary username assignment.
- Reanalysis updates the original fingerprint, including changed clue type or
  newly cataloged domain. Obsolete automatic evidence is not retained as a second
  positive clue. Manual checklist state remains.
- Add own aliases through the dashboard or `add-email`. Existing aliases do not
  reset scan progress; demo and personal profiles stay separate.
- Durable multi-file statistics, import cancellation, expiry of abandoned import
  sessions, parallel-import protection and retained Bitwarden selection.
- Scan status distinguishes a message limit, interruption, errors, skips and
  header-only coverage. Address-scope changes interrupt a running scan safely.
- 85 automated tests and eight browser checks passed in the 1.1 release.

### Upgrade from 1.0

1. Stop the server and scanner and protect a backup of your local data directory.
2. Replace source code, keeping your personal data directory and additional catalog.
3. Start with the same `--data-dir`. The schema is extended automatically;
   checklists, manual confirmations, priorities and sign-in methods remain.
4. Older-rule evidence is marked for reanalysis and does not establish a current
   probable account until checked again. **Unknown never means no account exists.**
5. Re-import original local emails or explicitly authorize an IMAP scan. The rule
   change makes its first scan recheck older messages, without modifying them.

Email bodies are not stored, so old clues cannot be reinterpreted without access
to the original messages. This rule upgrade is separate from the 1.2 language change.

## 1.0.0 — Initial release, 13 October 2026

372-provider catalog, local email evidence, dashboard and checklists, local file
imports, read-only TLS IMAP, opt-in MX hints and password-free Bitwarden metadata
export. 56 automated tests and six browser groups passed with synthetic data.
