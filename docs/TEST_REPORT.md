# Test report — Version 2.6.1 (review fixes, not yet tagged)

Review fixes, part 1: **359 Python tests**. New regression tests reproduce each
fixed finding first: a batch larger than the log limit, method and decision
undo, redo followed by undo, reused clue numbers, silent re-imports, stale
evidence, the local calendar day west of UTC, restoring the oldest automatic
backup, a damaged profile, a newer backup, catalog additions in backups and a
chosen backup folder. A three-process migration race ran 90 times without error.

Review fixes, part 2: **367 Python tests**. New regression tests cover an own
addition a newer catalog covers, a sub-domain addition, a worklist move next to
a tie and its undo, hidden domains and labelled siblings in "What's new", a
rejected single-sign-on account, clearing a due review and a rejection in the
session report.

# Test report — Version 2.6.0 (quality and trust, not yet tagged)

Step S19: **336 Python tests** and **42 browser check groups**. New tests cover
the coverage summary (sources, period, gap months, addresses without clues, no
total) and the catalog quality rules. The browser masks and unmasks addresses,
checks the current-page marker, the coverage panel, that every visible button
and field has an accessible name, and that the skip link comes first.

Step S20: **343 Python tests** and **43 browser check groups**. New tests cover
the release check (versions, declared connections and permissions, the release
notes template, checksums, a workflow that only reads), `argus about` (counts
without addresses, paths or providers; the database stays byte-identical; a
missing profile is not created) and the bug report form. The browser follows
the five demo tour steps and checks that the report field gets the focus.

Step S21: **344 Python tests** and **43 browser check groups**. A new test
checks that every relative Markdown link in the README files, `docs/` and
`.github/` points to an existing file. The preview images were regenerated from
the synthetic demo and inspected on desktop and mobile in both languages.

# Test report — Version 2.5.0 (former Pro features, not yet tagged)

Step S17: **326 Python tests** and **39 browser check groups**. New tests cover
separate profile folders that never read each other, profile names, the
`--profile`/`--data-dir` conflict, daily counts with comparisons and pruning,
the history columns, report levels with and without addresses, invalid
combinations, the private export file and the report API. The browser previews
a progress report without addresses.

Step S18a: **329 Python tests** and **40 browser check groups**. New tests cover
the ordering with the mailbox account first, refusals (same, foreign or unused
address, a second open plan), marking without changing any account, closing,
and CLI and API shapes. The browser creates a plan, marks one account and closes
it.

Step S18b: **332 Python tests** and **41 browser check groups**. New tests cover
built-in templates with matches, preview, apply and undo, refusal without
matches, validation of every template field, own templates with skipped
not-applicable steps, deleting, and CLI and API shapes. The browser previews,
applies and undoes a template.

# Test report — Version 2.4.0 (package E, not yet tagged)

Step S16: **323 Python tests** and **38 browser check groups**. New tests cover
readiness (ready, check first, every blocking reason), journaled downloads in
the dashboard and the CLI blocking a second download and a CLI transfer until
resolved, a confirmed import becoming “prepared”, the existing-file check, and
undoable manual assignment through store, CLI and API. The browser resolves an
unclear transfer, sees a download journaled and released, and assigns and
undoes an account without reading the vault.

# Test report — Version 2.3.0 (package D, not yet tagged)

Step S13a: **301 Python tests** and **35 browser check groups**. New tests cover
job states for imports, failures, cancellations and interrupted jobs, counts
and integer-only activity entries, the pause (new jobs refused, running scans
stopped between messages with saved clues kept, scheduled scans not claimed, a
paused scheduled run keeping its schedule, Bitwarden transfers blocked),
retention limits, and CLI and API shapes. The browser pauses and resumes in
both languages and sees the pause in the overview.

Step S13b: **305 Python tests** and **35 browser check groups**. New tests cover
the recorded approval (host, folders, limit, date, no username), a changed
folder selection refused before any keyring use and logged, revocation removing
the keyring entry, the offline checkpoint preview in the CLI, and the control
API showing and revoking the approval. The browser checks the permissions
panel.

Step S14a: **310 Python tests** and **35 browser check groups**. New tests cover
recognition by content with no second analysis, full re-analysis after new
addresses or catalog entries, a message and a size budget with continuation
across runs, continuation after an interruption, the fingerprint-only index and
the CLI options. Earlier re-import tests now expect `unchanged`; tests that
simulate older stored clues also remove the index, as profiles from before 2.3
have none.

Step S14b: **314 Python tests** and **36 browser check groups**. New tests cover
remembering and repeating the last source, a missing source, refusing a path
together with `--again`, retrying only failed items (and none left afterwards),
numbered mbox items, the pre-check without jobs or clues, and that the dashboard
sees only the number of failed items. The browser shows the last terminal
import with its commands.

Step S15: **318 Python tests** and **37 browser check groups**. New tests cover
the folder rules (root, home, hidden, missing, file, profile, parent of the
profile, network paths, links, interval), imports of new files only from the
folder itself, quiet passes, unchanged touched files, the pause, the per-pass
limit, a missing folder, disabling with activity entries, and the CLI and
control API. The browser shows the watch as a permission and a waiting job and
stops it.

# Test report — Version 2.2.0 (package C, not yet tagged)

Step S11: **283 Python tests** and **32 browser check groups**. New tests cover
new versus changed clues, quiet identical re-imports, grouping with unclear
items first, counted-only advertising, orders and resets, the review mark
(forward only, one undo, later clues stay new, decisions untouched), visible
import gaps, the return summary order, older profiles, the CLI and strict API
shapes. The browser opens the summary, marks changes reviewed, undoes it in
both languages and checks that the overview summary disappears.

Step S12a: **289 Python tests** and **33 browser check groups**. New tests cover
catalog reasons and the person's override, mailbox and sign-in relations (own
addresses, confirmed accounts, single sign-on only, no cycles, inactive after
rejection, removal), identity accounts leading the suggestions with reasons,
swapping two worklist tasks with undo, and CLI and API shapes. The browser
notes a sign-in and a mailbox account, reads the reasons and moves a task with
undo.

Step S12b: **294 Python tests** and **34 browser check groups**. New tests cover
the review rule (validation, scope, never a past date, month ends, one undoable
apply), sessions (ready tasks only, sizes, report from recorded steps, no
addresses in the text, end), confirmed-only export details, and CLI and API
shapes. The browser checks the single sign-on checklist, a session with report
preview and download, and applying and undoing proposed review dates.

# Test report — Version 2.1.0 (package B, not yet tagged)

Step S8: **257 Python tests** and **28 browser check groups**. Rule features are
checked for subject and body matches, direct, indirect and multiple recipients,
newsletters, subscriptions, forwarding and unknown domains; the snapshot shows
kind, age and features and the database holds no message text; older clues gain
their explanation on re-import; the browser shows the explanation in both
languages.

Step S9: **263 Python tests** and **30 browser check groups**. The unclear list,
exclusions (only domains outside the catalog, back on new clues, reversible),
address notes (own addresses only, no merging), CLI and API shapes are covered;
the browser hides and shows a domain and saves and removes a note.

Step S10 (E5, E6): **268 Python tests** and **31 browser check groups**. Own
catalog additions are checked for every refusal (shared sender, catalog domain,
HTTP or foreign website, category, priority, field shape) without leaving files
behind, for private permissions, reloading and removal rules; rule changes on
re-import list old and new reasons while decisions stay. The browser adds a
provider after a refused website, sees the re-import notice and removes it.

Step S10 (G3, G5): **273 Python tests** and **31 browser check groups**. The
synthetic benchmark (27 cases) must match every documented outcome, explain each
gap between truth and outcome, use only invented addresses and state that it is
no proof of real accuracy; the proposal form offers exactly the catalog's
categories. Current result on the synthetic set: of 15 real accounts, 10 count
as probable, 3 are kept for review and 2 are missed (documented limits); of 7
non-accounts, 1 is a false alarm (forged sender, documented limit).

# Test report — Version 2.0.0 (package A, not yet tagged)

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

Step S4: **229 Python tests**. Backups are restored for real and compared
with the saved state; damaged, foreign, path-traversal and newer-format archives
leave the profile untouched; a backup is consistent during a concurrent write;
older profiles are backed up once before migration, a failed backup stops it
and newer profiles are refused. The CI package check backs up and restores on
Linux, Windows and macOS.

Step S5 (schema and migration): **236 Python tests**. Every 1.x account state
is migrated and checked against the documented mapping; an interruption mid-way
leaves the 1.x profile intact; the automatic backup restores the 1.x profile,
which then migrates to the same result; new evidence changes only the evidence
axis; every change is logged per action and the log keeps whole batches.

Step S5 (decisions and undo): **247 Python tests**. Rejecting hides an account
everywhere and one undo restores it with its worklist row; strong new evidence
only raises a hint; steps and review dates are validated and dated; undo walks
back in order, refuses to overwrite later changes and never reverses an
external effect; API shapes and CLI commands are covered.

Step S6: **247 Python tests** and **26 browser check groups**. The browser
confirms, rejects with a reason and undoes from the toast and from the history,
walks the guided decision and sign-in steps, completes an account only after
every step is answered (MFA marked not used), sets a review date and checks
both languages.

Step S7: **253 Python tests** and **28 browser check groups**. The next task
follows the documented order (import, unfinished import, identities, unclear
transfer, due review, worklist, decide, secure, done); the summary counts unclear
items and gaps; a new profile shows three ways in; a test requires a German
translation for every dashboard text.

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

[Desktop preview](preview/dashboard.png) · [Mobile preview](preview/mobile.png)

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
