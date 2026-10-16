# Pro-license implementation

ARGUS (since 1.6) verifies Pro entitlements locally with Ed25519 signatures.
The desktop application contains only a public key; it never contains a payment
secret or publisher private key. A license contains no purchaser name, email,
mailbox information or Bitwarden data.

## Entitlement format

A signed JSON document contains only format version, product identifier, license
identifier, issue date, optional expiry, permitted feature IDs and signature. The
signature covers a canonical JSON payload. Unknown fields, wrong product IDs,
duplicate or unknown features, invalid dates, bad signatures and expired licenses
are rejected. The local dashboard remains on Free if verification fails.

The shipped project deliberately has no `license_public_key.pem`. That means the
default build cannot activate Pro files. This avoids treating a user-editable
setting or a placeholder key as a payment control.

## Publisher setup before the first paid release

1. On a protected publisher machine, generate a key pair:

   ```bash
   python scripts/generate_license_keys.py \
     --private-key /secure/offline/argus-ed25519-private.pem \
     --public-key /secure/release/argus-ed25519-public.pem
   ```

2. Keep the private key offline, backed up securely and outside Git. Copy only
   the public key into `argus_security/data/license_public_key.pem` for the
   release build. Review it, run the tests, build and distribute that version.
3. After a payment provider has independently verified a completed purchase,
   issue a license with the private key:

   ```bash
   python scripts/issue_license.py \
     --private-key /secure/offline/argus-ed25519-private.pem \
     --output /secure/delivery/argus-pro.json
   ```

4. Deliver that JSON file to the buyer through the chosen commercial system. The
   buyer activates it in **Plans** or runs:

   ```bash
   argus activate-license /path/to/argus-pro.json
   ```

The app stores the verified local file as `license.json` with private permissions.
It is ignored by Git. `argus license-status` shows only the local status.

## Payment provider and webhook boundary

Do not expose the loopback dashboard as a webhook receiver. A future Paddle,
Lemon Squeezy or other provider integration belongs in a separate publisher-owned
service. That service must verify the provider's webhook signature and event
identifier, record only the minimum commercial data required by the seller, then
issue and deliver a signed entitlement. The provider-specific secret remains only
in that service's secret store, never in this repository, app, license file or
GitHub Actions.

The provider, seller identity, pricing and legal terms have not been selected in
this repository. See [COMMERCIAL_RELEASE.md](COMMERCIAL_RELEASE.md) before any
real sale.
