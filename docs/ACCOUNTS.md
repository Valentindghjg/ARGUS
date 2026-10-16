# Separate accounts at one service / Getrennte Accounts bei einem Dienst

## English

ARGUS tracks each sign-in identity separately. Strong, current email evidence
addressed directly to one configured own address is grouped by service and
address. A second address produces a separate probable entry with its own
checklist, sign-in method, priority, worklist membership and Bitwarden transfer.
The dashboard counts entries and also shows the number of distinct services.

Different addresses can refer to aliases, an address change or a historical
account. Review each entry before treating it as a separate active account.
Emails alone never mark an entry Confirmed. Forwarded mail, several own
recipients, newsletters and other weak clues stay under **Unassigned service
clues**, without inheriting a particular entry's identity or checklist.

To add a known separate account yourself:

1. Open the service's account details, including an Unknown catalog service.
2. Under **Add another account at this service**, choose a configured own email
   address or leave it unknown, and optionally add a label such as “Work”.
3. Confirm that you have checked this is a separate account you own, then choose
   **Add to local inventory**. This creates a local record only.

Use distinct labels for separate accounts that share an email address. These
manually distinguished accounts do not automatically receive email evidence,
because an email recipient cannot identify which profile it concerns.
Unknown addresses can be assigned later, before a Bitwarden transfer. A bound
address cannot be replaced or cleared: changing it would move completed work to
another identity. Add another entry instead and review the existing one.

Each Bitwarden selection prepares exactly one password-free item for that entry.
Creating or assigning an item for one account never marks another account saved,
changes its password or completes its checklist. Interrupted transfers retain
their account and transfer IDs for explicit review.

For command-line selections, `python -m account_finder list-accounts` shows the
stable account IDs. Use the chosen `id` with `bitwarden-export --id`; an old
provider ID still selects its original entry, and never silently selects all
sibling accounts. `list-accounts --all` also includes entries without reliable
evidence.

### Older profiles

The first start migrates existing local state in a transaction. When a legacy
provider entry has one unambiguous current own address, its checklist and queue
position follow that identity. An explicitly assigned own address also anchors
the existing entry. Other identities start with clean checklists.

If an old completed or partially completed entry spans several addresses without
an explicit assignment, ARGUS preserves it as an entry that needs identification.
Its previous work is never copied to the newly separated entries. The preserved
entry is excluded from Bitwarden export until its identity is resolved. If its
address already has another entry or a transfer exists, review both locally;
ARGUS does not merge checklists or external vault items automatically.

Back up your protected profile before upgrading. Previous provider-level tables
remain as migration sources; after upgrading, use this version or newer to work
on that profile. Returning to an earlier application version would show its
earlier provider-level state rather than the new per-account progress.

## Deutsch

ARGUS verwaltet Anmeldezuordnungen getrennt. Starke aktuelle E-Mail-Belege, die
direkt an genau eine konfigurierte eigene Adresse gerichtet sind, werden je
Dienst und Adresse gruppiert. Eine zweite Adresse erzeugt einen separaten
wahrscheinlichen Eintrag mit eigener Checkliste, Anmeldemethode, Priorität,
Arbeitsliste und Bitwarden-Übertragung. Das Dashboard zählt Einträge und zeigt
zusätzlich die Anzahl verschiedener Dienste.

Verschiedene Adressen können Aliase, eine Adressänderung oder einen historischen
Account betreffen. Prüfe jeden Eintrag, bevor du ihn als separaten aktiven
Account behandelst. E-Mails allein ergeben niemals „Bestätigt“. Weiterleitungen,
mehrere eigene Empfänger, Newsletter und andere schwache Hinweise bleiben unter
**Nicht zugeordnete Diensthinweise** getrennt von Identität und Checkliste eines
bestimmten Eintrags.

So ergänzt du einen bekannten separaten Account:

1. Öffne die Account-Details des Dienstes, auch bei einem unbekannten Katalogdienst.
2. Wähle unter **Weiteren Account bei diesem Dienst hinzufügen** eine konfigurierte
   eigene E-Mail-Adresse oder lasse die Adresse unbekannt. Ergänze optional eine
   Bezeichnung wie „Arbeit“.
3. Bestätige, dass du einen separaten eigenen Account geprüft hast, und wähle
   **Zur lokalen Inventur hinzufügen**. Dadurch entsteht nur ein lokaler Eintrag.

Separate Accounts mit derselben E-Mail-Adresse benötigen unterschiedliche
Bezeichnungen. Diese manuell unterschiedenen Accounts erhalten keine
automatischen Mailbelege, weil die Empfängeradresse das jeweilige Profil nicht
erkennen lässt. Unbekannte Adressen lassen sich später vor einer
Bitwarden-Übertragung zuordnen. Eine fest zugeordnete Adresse kann nicht ersetzt
oder geleert werden, da sonst erledigte Arbeit einer anderen Anmeldung
zugeschrieben würde. Ergänze dafür einen weiteren Eintrag und prüfe den bisherigen.

Jede Bitwarden-Auswahl bereitet genau einen passwortfreien Eintrag für diesen
Account vor. Eine Zuordnung oder Übertragung setzt niemals den Bitwarden-Haken
eines anderen Accounts, ändert dessen Passwort oder schließt dessen Checkliste
ab. Unterbrochene Übertragungen behalten ihre Account- und Übertragungskennung
für die ausdrückliche Prüfung.

Für die Kommandozeile zeigt `python -m account_finder list-accounts` die stabilen
Account-Kennungen. Verwende die gewählte `id` bei `bitwarden-export --id`. Eine
bisherige Anbieterkennung wählt weiterhin ihren ursprünglichen Eintrag aus,
niemals stillschweigend alle anderen Accounts. `list-accounts --all` zeigt auch
Einträge ohne zuverlässige Belege.

### Bestehende Profile

Der erste Start übernimmt vorhandene lokale Zustände in einer Transaktion. Hat
ein bisheriger Anbietereintrag eine eindeutige aktuelle eigene Adresse, folgen
Checkliste und Arbeitslistenposition dieser Zuordnung. Auch eine ausdrücklich
zugewiesene eigene Adresse verankert den bisherigen Eintrag. Weitere Zuordnungen
beginnen mit leeren Checklisten.

Umfasst ein bisher erledigter oder teilweise bearbeiteter Eintrag mehrere
Adressen ohne ausdrückliche Zuordnung, erhält ARGUS ihn als Eintrag mit offener
Identitätsprüfung. Bisherige Arbeit wird nie auf die neu getrennten Einträge
kopiert. Bis zur Zuordnung ist der erhaltene Eintrag vom Bitwarden-Export
ausgeschlossen. Existiert die Adresse bereits als anderer Eintrag oder besteht
eine Übertragung, prüfe beide lokal; ARGUS führt Checklisten oder externe
Tresoreinträge nicht automatisch zusammen.

Sichere dein geschütztes Profil vor dem Update. Die bisherigen Tabellen je
Anbieter bleiben als Migrationsquelle erhalten. Bearbeite das Profil anschließend
mit dieser oder einer neueren Version. Eine ältere Anwendung würde ihren alten
Anbieterstand statt des neuen Fortschritts je Account anzeigen.
