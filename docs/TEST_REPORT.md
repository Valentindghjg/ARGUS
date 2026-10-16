# Test report — unreleased security review (2026-10)

The security-review changes passed **208 Python tests** (previously 166) and
**24 Chromium browser check groups**, with zero page errors and zero external
browser requests.

Master-plan step S1 removed the licensing code and its tests and the Plans
page check. Since then: **206 Python tests** and **23 browser check groups**.
New repository tests reject runtime dependencies outside the standard library
and keep the source-header rule.

Step S3 (F4, G1): **215 Python tests** and **24 browser check groups**. New
tests cover next-step hints in the CLI, the API and the dashboard (both
languages), scan next steps, the local list of skipped files and a guard
against absolute product promises.

Step S3 (B2, F6): **221 Python tests** and **25 browser check groups**. The
preview must match the written items field by field, write nothing and list
journal-created accounts. The browser checks preview, cancel and download, and
the demo guide.

New simulations combine a real local store with a fake IMAP server, a fake
keyring and a simulated clock. They cover lease renewal during long scheduled
scans, cancellation by `disable`/`revoke`, the absence of secrets in profile
files, malformed messages that must not block later incremental scans,
byte-identical mbox originals, scheduler resilience and the startup notice.

Further checks:

- The multi-account browser check now covers both cancelling and confirming a
  permanent sign-in-address binding.
- The companion validator checks all 527 providers and the HTTPS-only labelling.
- The wheel was built and smoke-tested in a clean virtual environment.
- 30,000 mutated MIME messages raised no unhandled exception type.
- Follow-up simulations cover the one-time profile move (including a concurrent
  move and a symlinked old folder), the deprecated command alias, the shared
  mailbox lease between manual and scheduled scans, Bitwarden payloads via
  stdin, user-facing rule messages over the loopback API, deferred accounts in
  the guided step and the absence of pre-1.9 tables in new profiles.
- The browser check also covers moving a pre-rename language preference.
- The companion validator runs `popup.js` with simulated browser APIs in English
  and German against lookalike domains, third-party subdomains and non-HTTPS pages.
- Every source file carries the MPL-2.0 SPDX header, and no translation is unused.
- Target-binding simulations (master plan priority 10) change each approved
  field (host, port, username, sign-in method, folders) and check that a
  scheduled run then reads no keyring entry and opens no connection. They also
  cover schedules from before the binding and re-approval. A counter-check
  against the previous `main` showed the stored secret reaching a changed host.

Only Python 3.13 ran locally; GitHub Actions covers 3.11–3.14. No real mailbox,
provider, password, keyring or Bitwarden vault was used.

---

# Test report — Version 1.16.0

The read-only Bitwarden-audit and guided-MFA release passed **166 Python tests**
and **23 Chromium browser check groups** with zero page errors and zero external
browser requests. A fake already-unlocked CLI supplies a vault response containing
a synthetic password; tests verify that ARGUS returns only the match summary and
does not write that password or the session value to its SQLite profile. Loopback
tests require the exact request shape and a separate confirmation. Workflow tests
verify that MFA/recovery review follows sign-in testing. The companion static
validation still passes with 527 provider records. No real mailbox, provider,
password or Bitwarden vault was used.

The following report records version 1.15.0.

---

# Test report — Version 1.15.0

The calendar-scheduling release passed **163 Python tests** and **23 Chromium
browser check groups** with zero page errors and zero external browser requests.
New workflow tests verify the accepted date range and the exact UTC resume time.
The browser test selects the date picker's minimum date, schedules it and checks
the resulting synthetic snooze in English and German. Separate-account browser
checks and the static companion validation still pass with 527 provider records.
The offline wheel was built and installed in a clean temporary environment as
version 1.15.0. No real mailbox, provider, password or Bitwarden vault was used.

The following report records version 1.14.0.

---

# Test report — Version 1.14.0

The local-snooze release passed **162 Python tests** and **23 Chromium browser
check groups** with zero page errors and zero external browser requests. New
workflow tests verify a future local resume date, due-item readiness without
account mutation, strict bounded input and the additive upgrade of an older
worklist table. The browser test creates a synthetic one-day snooze and verifies
its German display. Separate-account browser checks and the static companion
validation still pass with 527 provider records. The offline wheel was built and
installed in a clean temporary environment as version 1.14.0. No real mailbox,
provider, password or Bitwarden vault was used.

The following report records version 1.13.0.

---

# Test report — Version 1.13.0

The reviewable-planning release passed **160 Python tests** and **23 Chromium
browser check groups** with zero page errors and zero external browser requests.
The browser test verifies the ten-entry priority preview in English and its
German translation before any worklist action. Workflow tests verify that the
preview uses the same deterministic candidates as the builder without altering
account progress. Separate-account browser checks and the companion static
validation still pass with 527 provider records. The offline wheel was built and
installed in a clean temporary environment as version 1.13.0. No real mailbox,
provider, password or Bitwarden vault was used.

The following report records version 1.12.0.

---

# Test report — Version 1.12.0

The priority-worklist release passed **160 Python tests** and **23 Chromium
browser check groups** with zero page errors and zero external browser requests.
The new local API test accepts only the exact `{"action":"prioritize"}` shape.
Workflow tests verify deterministic ranking, the ten-account limit, existing
queue preservation and that adding priorities does not alter account progress.
The browser companion static validation still bundles 527 records with only its
`activeTab` permission. The offline wheel was built and installed in a clean
temporary environment as version 1.12.0. No real mailbox, provider, password or
Bitwarden vault was used.

The following report records version 1.11.0.

---

# Test report — Version 1.11.0

The explicit-step release passed **158 Python tests** and **23 Chromium browser
check groups**. The guided browser scenario accepts a native confirmation, marks
only the current account's reviewed step and verifies the following Bitwarden
step without external browser requests. No real mailbox, provider, password or
vault was used.

The following report records version 1.10.0.

---

# Test report — Version 1.10.0

The guided-security release passed **158 Python tests** and **23 Chromium browser
check groups** (18 dashboard groups plus five account-identity groups), with zero
page errors and zero external browser requests. The companion static validation
still bundles 527 records while keeping only its `activeTab` permission.

New cases cover deterministic local priority selection, resuming an existing
ready worklist item, no checklist mutation when a guided session starts, and the
strict loopback Bitwarden route: it accepts only the current account and a second
explicit confirmation. The browser flow verifies guided worklist state in English
and German. An offline wheel was built and installed in a clean temporary virtual
environment. No real mailbox, provider, password or Bitwarden vault was used.

The following report records version 1.9.0.

---

# Test report — Version 1.9.0

The separate-account release passed **155 Python tests** and **23 Chromium
browser check groups** (18 existing groups plus five account-identity groups).
Both browser suites reported zero page errors and zero external requests.
German mobile details were inspected at a 390 px viewport.

New cases cover independent checklists/worklists/Bitwarden items for two
addresses at one service, explicit labeled accounts sharing an address,
immutable identity assignments, Unicode label uniqueness, ambiguous and stale
evidence, current address scope, failed handoff isolation, and precise CLI IDs.
Migration cases cover unambiguous and ambiguous legacy progress, exact mapping
of successful/uncertain transfers, queue persistence, idempotent restart, and
transaction rollback after an injected interruption.

The wheel was built offline and installed into a separate temporary environment,
using the environment's installed cryptography dependency. Version/module imports,
demo, account listing and report were exercised outside the checkout. JavaScript
syntax, companion validation, Python compilation and diff checks also passed.
All messages, keyrings and vault responses in these tests were synthetic; no real
mailbox, provider password or Bitwarden vault was used. Separate account inference
still requires user review because aliases and changed addresses may refer to
one historical account. Automated account merging is not implemented.

The following reports record earlier releases.

---

# Test report — Version 1.8.1

The concurrent-scan safety fix passed **132 Python tests**, companion static
validation, JavaScript syntax and a package-wheel build. New focused cases cover
atomic cross-process leasing, safe lease expiry, stale completion rejection,
disable while a worker is active, and atomic merging of IMAP folder cursors.
All inputs use fake keyrings, runners and local SQLite databases.

The following report records the 1.8.0 automation stage.

---

# Test report — Version 1.8.0

The background-scan and browser-companion stage passed **128 Python tests**,
the existing **18 Chromium dashboard check groups**, Python compilation, JSON
validation and the companion's isolated static validation. The companion build
bundled 527 catalog records, requested only `activeTab`, and was checked for
prohibited host/page/native/network access. The dashboard test recorded zero
external browser requests and no page errors.

The new tests use a fake OS keyring, a fake incremental IMAP runner and a
temporary profile. They cover disabled-by-default behavior, runtime network
consent, keyring-only storage, absence of secrets and selectors from public
state, safe failure/backoff, CLI enable/revoke, and a background schedule shape
in the authenticated loopback response. No real keyring secret, mailbox,
provider, Bitwarden vault or password was used.

The following report records the earlier 1.7 automation stage.

---

# Test report — Version 1.7.0

The first automation stage passed **119 Python tests**, JavaScript syntax
validation and **18 browser check groups** in Chromium. The browser suite covered
English/German worklist persistence, pause/resume, guided next steps, mobile
layout, ambiguous-transfer review and the existing import/export workflows.
There were no page errors and **zero external browser requests**.

A wheel was built without network access, installed in a separate environment,
and exercised outside the source checkout (new module imports, demo and report).
The test environment reused its installed security dependency. No live mailbox,
Bitwarden vault or provider password was used.

New regression cases cover additive migration, application restart, explicit
completion, SSO/passkeys, concurrent reservations, CLI timeout, malformed replies,
partial alias success, manual reconciliation, authentication and origin checks.
A fake CLI supplies all vault results; actual Bitwarden synchronization and real
provider changes remain untested. These changes automate workflow guidance, not
password rotation or scheduled scans.

The following report records the earlier 1.6 baseline.

---

# Test report — Version 1.6, 14 October 2026

Tested on Linux with Python 3.12.14 and system Chromium. Runtime requires Python
3.11 or newer. Windows/macOS have not been separately exercised. All email
messages used in testing were synthetic.

## Automated Python checks

```text
python -m unittest discover -s tests -q
Ran 101 tests
OK
```

Coverage includes:

- 527 catalog entries and every explicitly requested example provider; extensions,
  unique domains, HTTPS and safe provider links.
- English/German registration, verification, password and sign-in clues;
  newsletters, guest orders, reset requests and unsubscribe footers.
- Domain spoofing, display names, unrelated recipients, multiple own recipients,
  forwarding, MIME attachments, HTML scripts, limits, aliases and negated events.
- Manual confirmation only; state persistence, deduplication, SSO and required
  completion steps.
- No stored email body/subject; private permissions, profile isolation, unchanged
  EML/Maildir/mbox originals and exclusive exports without changing parent permissions.
- TLS verification, read-only PEEK, size bounds, XOAUTH2, international folders,
  UID/UIDVALIDITY resuming, message limits, logout and secret-safe error messages.
- No DNS or IMAP without authorization flags; synthetic DNS packets, domain
  boundaries, malformed compression pointers and truncated responses.
- Local bearer API, Host/Origin/CORS/CSP, frame protection, `no-store`, upload limits,
  malformed requests, traversal, import and metadata export.
- Empty Bitwarden passwords, null TOTP, known own usernames, official URI,
  folder association and exclusion of assigned entries.
- Alias additions without state loss, idempotency, old checkpoints, consistent
  captured address scope and atomic writes during scope changes.
- Reclassification and removal of obsolete clues, unknown-to-catalog reassignment
  and migration of a version-1 database with duplicate signals.
- Whole-batch statistics, cancellation, limits, header gaps, incomplete batches,
  parallel imports, expiry and server shutdown.
- English display of stored German explanations while retaining the original
  stored value, manual confirmation and current rule version.
- Local Free product metadata, Pro marked as in development, no billing configuration
  and no telemetry flag.
- Ed25519 Pro-license verification for valid, expired and tampered files;
  private local activation storage and safe Free fallback without a public key.

## Language-specific regression checks

- Both presentation languages preserve account IDs, classification, score,
  confirmation, checklists, emails, URLs and stored evidence; analysis version 2.
- German and English artificial registration messages are detected in either
  interface language. Compound warnings retain all uncertainty qualifiers.
- Localized CLI help, system locale, explicit override, error messages and
  password-free exports; unauthorized IMAP does not prompt for a secret.
- German export counts format correctly and an existing export is not overwritten.
- Translation placeholders are consistent across languages; no external service.

## Browser checks

```text
python scripts/browser_smoke.py --browser /usr/bin/chromium --screenshots-dir docs/preview
15 functional groups passed
page_errors: []
external_requests: 0
```

A separate temporary synthetic profile was used. The checks cover the English
desktop page and `lang="en"`, local Free/Pro product presentation without a
checkout, statistics, search, category and unknown filters,
password-free download, manual review and checklist persistence, EML import,
multi-file totals with a duplicate and invalid file after reload, alias addition,
preserved export choices, and the mobile layout at 390 px. Outgoing browser
requests were blocked and none were attempted. Desktop and mobile screenshots
were inspected visually.

[Desktop preview](preview/dashboard.png) · [Plans preview](preview/plans.png) · [Mobile preview](preview/mobile.png)

Additional checks: JavaScript syntax, Python compilation, CLI help, archive
integrity and running the demo from an extracted archive. The version-1.1, version-1.2 and version-1.3 `RULES` values were compared directly
and are identical.

The fresh demo has 17 messages and 12 discovered providers: two simulated manual
confirmations, ten probable accounts and one completed checklist. Newsletter,
guest order and reset request remain unknown. Two uncataloged sender domains
remain unverified candidates.

## Verification limits

No real MX query for a personal email domain, real IMAP login or import into a real Bitwarden
vault has been performed. IMAP uses a recording fake implementation; Bitwarden
uses documented JSON structure and browser download checks. Personal provider
settings still need individual verification before an authorized connection.
Not all 527 provider websites were visited. Complete account coverage is not claimed.

Version 1.6 additionally passed browser checks for the local Free edition,
transparent Pro-in-development notice and hidden activation controls without a
publisher key, as well as switching filters and open
checklists, remembered language after reload, German metadata export notes,
retained export selection, German mobile layout, independent browser locales,
unsupported-language fallback, blocked preference storage and switching during
an active import without losing progress or releasing import locks. The unknown
provider count is derived from the catalog at test time, so the browser suite also
covers the expanded catalog without a hard-coded provider total. **14 browser
groups passed, zero page errors and zero external browser requests.** (This
count was carried over from the 1.3 language report; the 1.6 run above counted
15 groups, as the German report also states. Note added in the 2026-10 review.) German previews:
[desktop](preview/dashboard-de.png) and [mobile](preview/mobile-de.png).
