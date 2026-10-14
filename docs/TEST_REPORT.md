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
- Local Free product metadata, unavailable Pro preview, no billing configuration
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
transparent unavailable Pro preview and hidden activation controls without a
publisher key, as well as switching filters and open
checklists, remembered language after reload, German metadata export notes,
retained export selection, German mobile layout, independent browser locales,
unsupported-language fallback, blocked preference storage and switching during
an active import without losing progress or releasing import locks. The unknown
provider count is derived from the catalog at test time, so the browser suite also
covers the expanded catalog without a hard-coded provider total. **14 browser
groups passed, zero page errors and zero external browser requests.** German previews:
[desktop](preview/dashboard-de.png) and [mobile](preview/mobile-de.png).
