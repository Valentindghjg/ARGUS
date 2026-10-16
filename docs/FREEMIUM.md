# ARGUS Free and Pro

ARGUS is being prepared as a privacy-preserving Freemium product.
This repository currently ships **ARGUS Free**. It is a fully usable,
local edition; it does not require an account, payment details or telemetry.

## Available now: Free

- Local account inventory with the 527-provider catalog.
- Local EML, mbox and Maildir imports, plus explicitly authorized read-only IMAP.
- Account review, security checklists and password-free Bitwarden metadata export.
- German and English interface.

## Pro edition in development

The dashboard lists three Pro capabilities in development: encrypted local backup
and recovery workflow, scheduled local review reminders, and advanced personal
security reports. They are not implemented or purchasable in this release. The
application has a signed offline licensing foundation, but this default build
does not include a publisher public key and cannot activate Pro. Free
functionality is not disabled by an artificial trial limit.

## Product boundaries

- Passwords are generated and stored in Bitwarden, never in ARGUS.
- Mail content, IMAP secrets, payment data and Bitwarden vault data are not sent
  to a product service. An optional already-unlocked Bitwarden CLI can create
  explicitly selected password-free items locally without changing existing items.
  A separately confirmed read-only audit derives only a local match summary.
- A future purchase flow must be a separate publisher-controlled checkout. It
  must not embed payment keys in the desktop application or this repository.
- A future Pro entitlement needs independently reviewed, signed offline
  verification before paid features are enforced. A writable local flag is not a
  valid payment or license control.
- The implemented entitlement format and publisher key process are documented in
  [LICENSE_IMPLEMENTATION.md](LICENSE_IMPLEMENTATION.md).

## Before selling Pro

The publisher must choose the seller identity, jurisdiction, price, tax handling,
refund policy, support channel, commercial license and payment provider. Add the
final legal texts and a verified checkout only after those decisions. See the
[commercial-release checklist](COMMERCIAL_RELEASE.md).
