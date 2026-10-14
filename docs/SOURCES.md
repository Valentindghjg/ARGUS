# Official sources and verification

The public documentation below was checked on 13 October 2026. Those requests
included no private email address, message content, credentials or tokens. Catalog
domains are curated; **not all 527 websites have been checked live**. Provider
domains may change. The three password-settings links have separate sources.

| Feature | Official source | Basis |
|---|---|---|
| Bitwarden import | [Import to your Vault or Collections](https://bitwarden.com/help/import-data/) | Apps/CLI support import; duplicate checking is not performed |
| Bitwarden JSON | [Import from a Custom File](https://bitwarden.com/help/condition-bitwarden-import/) | Folder, item and login structure; “Bitwarden (json)” format |
| Bitwarden CLI | [Bitwarden CLI](https://bitwarden.com/help/cli/) | Optional local creation of explicitly selected password-free items after the user unlocks the CLI |
| Password generation | [Username & Password Generator](https://bitwarden.com/help/generator/) | Generate passwords in the Bitwarden client |
| Google settings | [Change or reset your password](https://support.google.com/accounts/answer/41078) | Official Google account settings; no automated reset |
| GitHub settings | [Updating your GitHub access credentials](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/updating-your-github-access-credentials) | Change an existing password under Password and authentication |
| Apple settings | [Change your Apple Account password](https://support.apple.com/en-us/101567) | Trusted device or account.apple.com → Sign-In and Security → Password |
| Google app passwords | [Sign in with app passwords](https://support.google.com/mail/answer/185833) | Availability depends on account and security settings |
| Exchange Basic Authentication | [Deprecation in Exchange Online](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online) | App passwords do not bypass its removal |
| Microsoft IMAP OAuth2 | [Authenticate IMAP, POP or SMTP using OAuth](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth) | XOAUTH2 with an externally authorized access token |
| Fastmail IMAP | [Server names and ports](https://www.fastmail.help/hc/en-us/articles/1500000278342-Server-names-and-ports) | imap.fastmail.com:993, TLS, app password; plan restrictions apply |
| iCloud IMAP | [iCloud Mail server settings](https://support.apple.com/en-us/102525) | imap.mail.me.com:993, app password, verify username |

Technical references:

- [Python imaplib](https://docs.python.org/3/library/imaplib.html): read-only
  selection, UID, TLS and authentication.
- [IMAP4rev2 / RFC 9051](https://www.rfc-editor.org/rfc/rfc9051.html): EXAMINE and
  BODY.PEEK for read-only access.
- [DNS / RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html): MX records and the
  DNS wire format. DNS is not used to determine service-account existence.

Additional MX hints for mailbox.org and Infomaniak are setup candidates requiring
individual verification in current provider documentation. No connection to a
hinted host is made automatically. Version 1.4 expands sender-domain coverage but
does not claim fresh live verification of all provider websites.
