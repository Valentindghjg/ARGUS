# Frequently asked questions

[Deutsch](FAQ_DE.md)

## Does ARGUS find all my accounts?

No. ARGUS reads only the emails you import or scan and looks for clues such as
welcome, sign-in or password-change messages. An account without such an email
stays unknown, and an unknown account is not an absent one. ARGUS therefore shows
what your imports cover, but never a total percentage.

## Is a clue proof of an account?

No. A newsletter, a guest order or a password-reset email is a clue, not an
account. ARGUS marks accounts as confirmed, probable or unknown and explains
each one; you decide what is true.

## Does ARGUS log in anywhere or change anything at providers?

No. ARGUS makes no login attempts, changes no passwords and acts at no provider.
Its worklist and task templates only plan steps that you carry out yourself.

## Does ARGUS need or store my passwords?

ARGUS never stores passwords in its profile. A manual IMAP scan asks for the app
password in the terminal and forgets it afterwards. A scheduled IMAP scan that
you approve keeps it only in your operating system's keyring. Bitwarden exports
contain metadata such as the name, sign-in address and links, never passwords.

## When does ARGUS connect to the internet?

Only in these cases, each one started or approved by you:

- `scan-imap --allow-imap` or an approved scheduled scan reads your mailbox over
  TLS IMAP, read-only.
- `discover --allow-dns` asks your DNS resolver for MX records.
- The Bitwarden steps run the official Bitwarden CLI you unlocked, after your
  confirmation.

The dashboard listens on 127.0.0.1 only. Every release names new connections and
permissions in its notes; `scripts/release_check.py` fails when a module could
reach out without such a declaration.

## Where is my data, and how do I move it?

The default profile lives in `~/.local/share/argus`; named profiles live in
`~/.local/share/argus-profiles`. `argus backup` saves an unencrypted copy and
`argus restore` brings it back on another computer. Keep backups private.

## Can I stop everything at once?

Yes. `argus automation pause` or the Control view stops scheduled scans, the
folder watch and other background work until you resume.

## Is there a paid version?

No. Every feature is free under the MPL-2.0 license. There is no license key,
account or checkout.

## How do I report a bug without sharing data?

Open a bug report and paste the output of `argus about`. It shows versions,
platform and counts only, never addresses, paths or messages. Describe the
steps with invented messages or with the demo (`argus --data-dir .local/demo demo`).
Never attach a profile, database, vault export, real email or credential. Report
security problems privately as described in [SECURITY.md](../SECURITY.md).
