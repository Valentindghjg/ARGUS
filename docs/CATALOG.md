# Provider catalog policy

The built-in catalog contains **527 providers**. It is a local domain-matching
aid, not a directory of verified account ownership and not a service scanner.
The app compares a sender domain from your local email with a curated domain root.
It never sends that address to catalog providers or queries whether an account
exists.

## What an entry means

An entry includes a stable ID, display name, official HTTPS homepage, category and
one or more sender-domain roots. A match creates evidence only when the email's
local content also satisfies a detection rule. It can at most produce a
“Probable” account. Only the user’s review can mark an account “Confirmed”.

No entry claims that every service sends from the listed domain, that every email
from that domain proves an account, or that a provider currently operates in every
country. Newsletter subscriptions, guest orders and password-reset requests are
intentionally insufficient on their own.

## Selection and review rules

- Add a distinct service with an official HTTPS homepage and a stable sender-domain
  root controlled by that service.
- Use the smallest appropriate root. Do not add broad shared delivery, analytics,
  cloud-hosting or payment-processor domains to another provider.
- Keep IDs lowercase and stable. Do not reuse an existing ID or domain root.
- Avoid domains inferred only from a brand name or email display name.
- Set a direct password-management URL only with an official HTTPS source and the
  date you checked it; otherwise leave it out.
- Recheck the catalog through the test suite. The registry rejects duplicate roots,
  unsafe links and ambiguous ownership.

The bundled catalog is curated but not a live availability check. Services,
senders, domains and password settings can change. See [official sources](SOURCES.md)
for the separate verification basis of the built-in password links.

## Shared sending services

Bulk-mail platforms such as `sendgrid.net`, `amazonses.com`, `mailgun.org` or
`mcsv.net` send mail for many companies. Their domains never identify a
provider. The registry rejects them in every catalog (built-in, `--providers`
file and the profile's own additions), and the dashboard marks clues from them as
coming from a shared sending service. The list lives in
`argus_security/registry.py` (`SHARED_SENDERS`); extend it in its own pull
request with an official source for each domain.

## Proposing a provider

Use the **Provider proposal** issue form. It asks for the official HTTPS
website, the category, each domain root with a reason, public sources with the
date you checked them and four review criteria. Or open a pull request using
synthetic examples only. State the provider’s
official homepage, proposed domain roots, category and why each root is specific
to the service. Do not attach real emails, headers with personal addresses or
account lists. Keep unrelated catalog changes out of the same pull request.

For a personal extension, use **Add to my catalog** in the dashboard's “Unclear
items”; the entry is validated like this catalog and stays in your profile
(`my-providers.json`). Alternatively, create a separate JSON file and start the
app with `--providers path/to/providers-extra.json`. The built-in catalog does not need to
be edited for private additions. The example file uses only a synthetic `.example`
domain.
