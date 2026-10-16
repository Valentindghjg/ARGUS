# Offizielle Quellen und Verifizierung

Öffentliche Dokumentation wurde am 13.10.2026 für die Implementierung geprüft.
Die Dokumentationsaufrufe enthielten keine private Mailadresse, Mailtexte,
Zugangsdaten oder Tokens. Anbieter-Domains im allgemeinen Katalog sind kuratiert;
**nicht alle 527 Websites wurden live überprüft**. Dienste und Versanddomains
können sich ändern. Die drei Passwortlinks haben separate Quellenbelege.

| Funktion | Offizielle Quelle | Ergebnis |
|---|---|---|
| Bitwarden-Import | [Import to your Vault or Collections](https://bitwarden.com/help/import-data/) | Import über Apps/CLI; keine Duplikatprüfung, wiederholter Import erzeugt zusätzliche Einträge |
| Bitwarden-JSON | [Import from a Custom File](https://bitwarden.com/help/condition-bitwarden-import/) | Ordner-, Item- und Login-Struktur; Format „Bitwarden (json)“ |
| Bitwarden-CLI | [Bitwarden CLI](https://bitwarden.com/help/cli/) | Optionale lokale Erstellung ausdrücklich ausgewählter passwortfreier Einträge nach dem Entsperren durch den Nutzer |
| Passwortgenerierung | [Username & Password Generator](https://bitwarden.com/help/generator/) | Neue Passwörter werden im Bitwarden-Client erzeugt |
| Google-Passwort | [Change or reset your password](https://support.google.com/accounts/answer/41078) | Passwortverwaltung im offiziellen Google-Konto; keine Reset-Automatisierung |
| GitHub-Passwort | [Updating your GitHub access credentials](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/updating-your-github-access-credentials) | Vorhandenes Passwort in „Password and authentication“ ändern |
| Apple-Passwort | [Change your Apple Account password](https://support.apple.com/en-us/101567) | Vertrauenswürdiges Gerät oder account.apple.com → Sign-In and Security → Password |
| Google-App-Passwort | [Sign in with app passwords](https://support.google.com/mail/answer/185833) | App-Passwörter nur unter den unterstützten Sicherheits-/Kontobedingungen |
| Exchange-Basic-Auth | [Deprecation of Basic authentication in Exchange Online](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online) | App-Passwörter umgehen die Abschaltung nicht |
| Microsoft-IMAP-OAuth2 | [Authenticate an IMAP, POP or SMTP connection using OAuth](https://learn.microsoft.com/en-us/exchange/client-developer/legacy-protocols/how-to-authenticate-an-imap-pop-smtp-application-by-using-oauth) | XOAUTH2; freigegebenes Access-Token extern beschaffen |
| Fastmail-IMAP | [Server names and ports](https://www.fastmail.help/hc/en-us/articles/1500000278342-Server-names-and-ports) | imap.fastmail.com:993, TLS, separates App-Passwort; nicht alle Tarife unterstützen IMAP |
| iCloud-IMAP | [iCloud Mail server settings](https://support.apple.com/en-us/102525) | imap.mail.me.com:993, App-Passwort, Benutzername prüfen |

Ergänzende technische Referenzen:

- [Python imaplib](https://docs.python.org/3/library/imaplib.html):
  `select(..., readonly=True)`, UID, TLS und Authentifizierung.
- [IMAP4rev2 / RFC 9051](https://www.rfc-editor.org/rfc/rfc9051.html):
  EXAMINE und BODY.PEEK für lesenden Zugriff.
- [MX / RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html):
  DNS-Format und MX-Abfrage. Keine Account-Erkennung über DNS.

MX-basierte Zusatzhinweise für mailbox.org und Infomaniak sind konservative
Einrichtungskandidaten und müssen individuell anhand der aktuellen Dokumentation
geprüft werden. Es wird keine Verbindung zu diesen Hinweisen automatisch aufgebaut.
