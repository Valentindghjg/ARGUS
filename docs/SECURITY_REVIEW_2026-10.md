# Security review — October 2026 (base v1.16.0)

Date: 2026-10-16 · base commit `2ec9fb7`. The full German report, with details,
test evidence and open recommendations, is
[SICHERHEITSREVIEW_2026-10.md](SICHERHEITSREVIEW_2026-10.md).

## Basis

The handoff file named as the review basis (`docs/CLAUDE_CODE_HANDOFF.md`) and
the strategy PDF are not in the repository. Security boundaries and the test
scope were therefore derived from:

- `docs/SECURITY.md` and `docs/PLAN.md`
- `CONTRIBUTING.md` and `PRIVACY.md`
- the CI workflow

The review used only synthetic data, fake IMAP, a fake keyring and a fake
Bitwarden CLI. It made no provider action, login, password change, real mailbox
access or publication.

## Findings

| ID | Area | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| R-01 | Scheduled IMAP | The 5-minute lease was never renewed, so a second process could open the mailbox during long scans | medium | fixed |
| R-02 | Scheduled IMAP | `disable` and `revoke` did not stop a scan already running | medium | fixed |
| R-03 | Dashboard | The scheduler thread could die silently on a database lock or damaged schedule | medium | fixed |
| R-04 | Dashboard/CLI | The start message claimed "No mailbox connection is active" while schedules were enabled | medium | fixed |
| R-05 | UI/state | One select change permanently bound a sign-in address, without confirmation | medium | fixed |
| R-06 | Companion | Third-party-hostable subdomains and `http:` pages were labelled "official" | medium | fixed |
| R-07 | i18n | 24 user-visible messages had no German text | medium | fixed |
| R-08 | Bitwarden | The vault-write endpoint did not require `confirmed: true` | low | fixed |
| R-09 | Scheduled IMAP | No warning that OAuth2 access tokens expire | low | fixed |
| R-10 | Repository | Private key files (`*.pem`, `*.key`) were not git-ignored | low | fixed |
| R-11 | UI | The translation lookup could hit object prototype keys | low | fixed |
| R-12 | Import | The mbox import had a misleading read-only comment and an unused handle | low | fixed |
| R-13 | Companion | Matching depended on bundle order, and the validator checked too little | low | fixed |
| R-14 | Bitwarden | `bw create item <base64>` exposes metadata (no password) in the process list | low | fixed (stdin); confirm once with a test vault |
| R-15 | IMAP | A manual `scan-imap` does not take the scheduler lease | low | fixed (shared mailbox lease) |
| R-16 | Server/UI | Specific validation errors are replaced by generic messages | low | fixed (`UserFacingError`) |
| R-17/18 | Companion/i18n | English-only companion popup; 22 unused translations | info | fixed |
| D-01 | Docs | Claims contradicted the code (dependencies, stored secrets, vault access, activation path) | medium | fixed |
| D-02/03 | Packaging | `pyproject.toml` pointed to another repository and had no license metadata | medium | fixed (PEP 639 `MPL-2.0`) |
| D-04 | Keys | `data/*.pem` was packaged, private keys were not ignored, and the key generator wrote anywhere | medium | fixed |
| D-05/06/07 | Docs/CI/code | MPL switch missing from changelog, pip missing from Dependabot, dead code | low | fixed |
| D-08/09 | Owner | Stale Dependabot branches; a personal domain in Git history | medium | open: owner actions on GitHub |
| D-10–D-13 | Owner/docs | Copyright and data license, naming, reporting contact, doc parity | low | fixed after owner decisions |

## Verification

| Check | Result |
| --- | --- |
| Unit tests | 202 passed (previously 166) |
| `node --check` | passed |
| Companion validator | passed |
| Wheel build and clean install smoke test | passed |
| Chromium browser checks | 24 groups, 0 page errors, 0 external requests |
| MIME fuzzing | 30,000 mutated messages, no unhandled exception type |

The new file `tests/test_review_simulations.py` covers lease renewal,
cancellation, secret-free profile files, poison messages, read-only mbox
originals, scheduler resilience, the start message and the OAuth2 warning.

`main` is protected against direct pushes, so the changes are on the branch
`claude/security-review-2026-10`. No pull request was opened.

## Follow-up after owner decisions

- **Copyright:** "ARGUS contributors", with an SPDX MPL-2.0 header in every
  source file.
- **License scope:** MPL-2.0 covers code, data, documentation and images.
- **Reporting:** GitHub private vulnerability reporting is the only private
  channel.
- **Rename:** The project is now ARGUS throughout:
  - package `argus_security`, distribution `argus-account-security` and command
    `argus`, with deprecated `account_finder` aliases;
  - a one-time atomic move of the default profile to `~/.local/share/argus`;
  - the Bitwarden field `ARGUS-Account-ID`, with the old field still recognized;
  - the license product `argus-pro`.

New tests are `tests/test_rename_migration.py` and
`tests/test_followup_simulations.py`; a popup behavior simulation runs in
`browser-companion/tests/validate.py`.

Details are in section 11 of the German report.
