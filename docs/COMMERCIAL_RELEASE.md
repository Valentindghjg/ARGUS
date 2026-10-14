# Commercial-release checklist

This checklist is for the publisher before offering Account Compass Pro for
payment. It deliberately does not select a country, seller, payment provider or
legal terms on the owner's behalf.

## Product and legal decisions

- Choose the legal seller name, business address/contact route and jurisdiction.
- Set the Pro price, currency, trial policy, upgrades, refunds and support scope.
- Have applicable terms, privacy notice, license and tax/invoice obligations
  reviewed for the intended market.
- Decide whether the public repository is source-available proprietary software,
  open core with a proprietary Pro add-on, or uses another reviewed model.
- Replace the current license-status notice with the exact final license text and
  copyright notice before public commercial distribution.

## Checkout and entitlement design

- Use a payment provider's hosted checkout or another isolated payment system.
  Never commit payment keys, webhook secrets, customer email exports or invoices.
- Keep checkout and license delivery separate from local mailbox processing.
- Define the minimum entitlement data and retention period. Do not use mailbox
  addresses, IMAP credentials or Bitwarden data as a customer identifier.
- Implement signed entitlement verification with a public key built into a
  reviewed release. Include offline expiry/renewal behavior and support recovery.
- Verify webhook signatures and enforce server-side authorization before sending
  an entitlement. Do not treat a browser redirect as proof of payment.

## Release and support

- Complete [PUBLISHING.md](PUBLISHING.md), then publish a reviewed release tag.
- Add a public product page, support contact, pricing and legal links controlled
  by the publisher.
- Test a purchase, refund, failed payment, offline activation and account-recovery
  path using synthetic data before accepting real customers.
- Keep Free functional without a customer account and keep the local security
  model accurate in all marketing material.
