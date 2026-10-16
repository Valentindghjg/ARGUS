# Privacy statement / Datenschutzerklärung

## English

ARGUS is a local desktop-style Python application. It does not operate a hosted
account-discovery service, collect telemetry, use analytics, embed advertising,
or send email contents to an AI service.

The local profile can contain account evidence, configured own email addresses,
checklist state and optional IMAP settings metadata. Email bodies are analysed
locally to create bounded evidence records; raw message bodies, attachments,
passwords, Bitwarden master passwords and OAuth refresh tokens are not stored by
ARGUS. The only exception is opt-in: `background-imap enable` keeps a separate
IMAP app password or access token in your operating-system keyring, never in
the profile, until you run `background-imap revoke`. Protect the profile and its backups with your operating system account and
an encrypted drive.

Network connections occur only when you explicitly start an allowed action:

- `discover --allow-dns` sends the mail domain to the selected DNS resolver.
- `scan-imap --allow-imap` and an explicitly enabled background scan connect to
  the configured TLS IMAP server with a separate authorization you provide.
- An explicitly confirmed Bitwarden action uses an already-unlocked official
  Bitwarden CLI. The read-only audit derives only a local match summary and does
  not persist vault names, usernames or passwords.

The dashboard binds to `127.0.0.1`; do not expose its port publicly. Provider
pages and Bitwarden links open only after your click. The project cannot erase
data from operating-system backups, browser download folders or a third-party
service after you choose to contact it.

GitHub separately processes data when you use its repository, Issues or
Discussions under GitHub's own policies. Do not post real emails, credentials,
vault exports or account inventories there.

ARGUS has no paid tier, customer account or checkout and collects no customer
details. Anyone who later offers a hosted or paid service around it must publish
their own legally appropriate privacy notice first.

## Deutsch

ARGUS ist eine lokale Python-Anwendung. Sie betreibt keinen gehosteten
Account-Suchdienst, sammelt keine Telemetrie, nutzt keine Analysewerkzeuge, enthält
keine Werbung und überträgt keine Mailinhalte an einen KI-Dienst.

Das lokale Profil kann Account-Belege, konfigurierte eigene Mailadressen,
Checklisten und Metadaten optionaler IMAP-Einstellungen enthalten. Mailtexte
werden lokal ausgewertet, um begrenzte Belegdaten zu erzeugen; rohe Mailtexte,
Anhänge, Passwörter, Bitwarden-Hauptpasswörter und OAuth-Refresh-Tokens speichert
ARGUS nicht. Einzige, ausdrücklich gewählte Ausnahme: `background-imap enable`
legt ein separates IMAP-App-Passwort oder Access-Token im Schlüsselbund des
Betriebssystems ab, nie im Profil, bis du `background-imap revoke` ausführst. Schütze das Profil und seine Sicherungen mit deinem Betriebssystem-
Konto und einem verschlüsselten Laufwerk.

Netzwerkverbindungen entstehen nur durch ausdrücklich gestartete erlaubte
Aktionen:

- `discover --allow-dns` sendet die Maildomain an den gewählten DNS-Resolver.
- `scan-imap --allow-imap` und ein ausdrücklich aktivierter Hintergrundscan
  verbinden sich mit dem konfigurierten TLS-IMAP-Server und einer getrennten,
  von dir bereitgestellten Freigabe.
- Eine ausdrücklich bestätigte Bitwarden-Aktion verwendet eine bereits entsperrte
  offizielle Bitwarden-CLI. Die nur lesende Prüfung erzeugt nur eine lokale
  Trefferübersicht und speichert keine Tresornamen, Benutzernamen oder Passwörter.

Das Dashboard bindet an `127.0.0.1`; veröffentliche seinen Port nicht. Anbieter-
und Bitwarden-Links öffnen sich nur nach deinem Klick. Das Projekt kann Daten
nicht aus Betriebssystem-Sicherungen, Browser-Downloadordnern oder einem
Drittdienst löschen, nachdem du selbst dessen Kontakt ausgelöst hast.

GitHub verarbeitet Daten separat, wenn du Repository, Issues oder Discussions
nutzt, nach seinen eigenen Richtlinien. Veröffentliche dort keine echten Mails,
Zugangsdaten, Tresorexporte oder Account-Listen.

ARGUS hat keine Bezahlstufe, kein Kundenkonto und keinen Bezahlvorgang und
erfasst keine Kundendaten. Wer später einen gehosteten oder bezahlten Dienst
darum herum anbietet, muss vorher eine eigene, rechtlich passende
Datenschutzerklärung veröffentlichen.
