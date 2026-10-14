# Account Compass 1.6 – lokaler Account-Finder

Deutsch · [English](README.md)

Ein Python-Programm mit **deutscher und englischer Weboberfläche**, **527
erweiterbaren Diensten**, lokaler E-Mail-Analyse und einer Checkliste zum
Absichern mit Bitwarden. Die Nutzer wählen ihre Sprache selbst.

Die Anwendung findet **Hinweise in deinen eigenen Nachrichten**. Ein fehlender
Hinweis bedeutet „Unbekannt“ und beweist nicht, dass kein Account existiert.
Künstliche Demo und persönliche Ergebnisse bleiben getrennt.

## Lizenzstatus

Es wurde noch keine Open-Source-Lizenz ausgewählt. Vor der Veröffentlichung muss
der Repository-Inhaber eine Lizenz hinzufügen, damit andere die erlaubte Nutzung
kennen. Details stehen in [LICENSING.md](LICENSING.md) und in der
[Veröffentlichungs-Checkliste](docs/PUBLISHING.md).

## Account Compass Free und Pro

Diese Version ist **Account Compass Free**: Account-Inventur, lokaler Mailimport,
Sicherheitschecklisten und passwortfreie Bitwarden-Metadaten stehen ohne
Online-Konto, Zahlungsdaten oder Telemetrie bereit. Das Dashboard erläutert
zusätzlich eine künftige **Pro-Vorschau**. Pro ist noch nicht implementiert,
kauf- oder aktivierbar; Free wird daher nicht durch ein künstliches Testlimit
eingeschränkt. Details stehen im [Freemium-Plan](docs/FREEMIUM_DE.md).

## In zwei Minuten starten

Voraussetzung: **Python 3.11 oder neuer** und ein aktueller Browser. Installiere
die eine Sicherheitsabhängigkeit aus den Projektmetadaten; npm und Docker sind
nicht nötig.

1. Projektarchiv entpacken und Terminal im Ordner `account-finder` öffnen.
2. Python-Version mit `python --version` prüfen. Auf Windows bei Bedarf alle
   `python`-Befehle durch `py -3` ersetzen; auf macOS/Linux gegebenenfalls `python3`.
3. Demo starten:

```bash
python -m pip install .
python -m account_finder --data-dir .local/demo demo --serve --open
```

Der Browser öffnet `http://127.0.0.1:8765/`. Falls er nicht automatisch öffnet,
diese Adresse selbst aufrufen. Strg+C beendet den Server. Die Demo enthält 17
künstliche Nachrichten, 12 gefundene Anbieter, zwei simulierte manuelle
Bestätigungen und eine erledigte Checkliste. **Das sind keine echten Accounts.**
Mit `--port 8766` lässt sich ein bereits belegter Port umgehen.

Alternativ das GitHub-Repository klonen:

```bash
git clone https://github.com/Valentindghjg/account-compass.git
cd account-compass
python -m pip install .
python -m account_finder --data-dir .local/demo demo --serve --open
```

Eine bestehende Arbeitskopie ohne lokale Änderungen aktualisierst du mit
`git pull --ff-only`. Persönliche Profile und Zugangsdaten sind von Git
ausgeschlossen; sichere sie separat geschützt.

## Was dieses Projekt macht

- Es findet lokale Hinweise auf Dienste über Absenderdomains in deinen eigenen
  E-Mails.
- Es hilft beim Prüfen von Accounts, beim Nachverfolgen der Absicherung und bei
  passwortfreien Bitwarden-Metadatenimporten.
- Es läuft lokal. Es probiert keine Account-Logins massenhaft aus, löst keine
  Passwort-Resets aus, umgeht keine CAPTCHAs und verändert keine E-Mails.

Fehlende Hinweise beweisen nicht, dass kein Account existiert. Registrierung per
Telefon, SSO, andere Postfächer oder gelöschte Nachrichten können ohne lokalen
Hinweis bleiben. Vor persönlichen Daten bitte das
[Sicherheitsmodell](docs/SICHERHEIT.md) lesen.

## Sprache wählen

Im Dashboard oben **Sprache → Deutsch / English** wählen. Der Schalter ist auch
innerhalb einer geöffneten Account-Checkliste verfügbar. Beim ersten Aufruf wird
Deutsch für eine deutsche Browsersprache gewählt, andernfalls Englisch. Deine
ausdrückliche Auswahl wird in diesem Browser für diese lokale Dashboard-Adresse
gemerkt. Ist der Browser-Speicher gesperrt, funktioniert der Wechsel trotzdem
für die aktuelle Seite.

Filter, Checklisten, Bestätigungen, Anmeldeadressen, Bitwarden-Auswahl und
Importfortschritt bleiben beim Wechsel erhalten. Navigation, Kategorien,
Einrichtungshinweise, Erkennungsgründe, Checklisten und Datumsanzeige werden
übersetzt. Anbieternamen, Websites, E-Mail-Adressen und technische Kennungen
bleiben unverändert; eigene Katalogtexte werden wie angegeben verwendet.
Die Erkennung berücksichtigt **immer deutsche und englische E-Mails**, unabhängig
von der Oberflächensprache. Verschiedene Browserprofile können unterschiedliche
Sprachen wählen.

Die Kommandozeile folgt der Systemsprache. Du kannst die Sprache mit einer
globalen Option **vor dem Unterbefehl** festlegen:

```bash
python -m account_finder --language de --help
python -m account_finder --language en --help
python -m account_finder --language de --data-dir .local/demo demo --serve
```

Hilfetexte, Eingabeaufforderungen, Fehlermeldungen und Bitwarden-Exporthinweise
nutzen diese Sprache. Befehlsnamen, Optionen und JSON-Schlüssel bleiben für
Skripte stabil. Der Browser wählt seine Sprache unabhängig vom Terminal.
Der Sprachwechsel sendet keine externen Anfragen. Im Local Storage des Browsers
wird ausschließlich die Sprachwahl `de` oder `en` gespeichert, keine Tokens,
E-Mail-Inhalte, Zugangsdaten oder Account-Ergebnisse.

## Dein echtes Profil

Auf deinem eigenen Rechner und getrennt von der Demo einrichten. Ersetze
`deine.email@example.org` durch deine eigene Registrierungsadresse:

```bash
python -m account_finder init --email deine.email@example.org
python -m account_finder serve --open
```

Standardmäßig liegen persönliche Ergebnisse unter
`~/.local/share/account-finder/`. Ein eigenes Verzeichnis wird mit
`--data-dir /absoluter/pfad` **vor dem Unterbefehl** angegeben. Im Dashboard
erscheinen jetzt zunächst keine gefundenen Accounts, bis du echte Mails importierst.

Weitere **eigene Anmeldeadressen** kannst du bei der Einrichtung angeben:

```bash
python -m account_finder --data-dir .local/eigene-aliase init --email deine.email@example.org --email eigene-aliasadresse@example.org
```

Weitere eigene Adressen kannst du später **im selben Profil** ergänzen, im
Dashboard unter „Postfach & Import“ oder mit:

```bash
python -m account_finder add-email --email eigene-aliasadresse@example.org
```

Bis zu 64 eigene Adressen können ergänzt werden. Bestehende Adressen, manuelle
Bestätigungen und Checklisten bleiben erhalten. Danach lokale Maildateien erneut
importieren; der nächste ausdrücklich freigegebene IMAP-Scan prüft ältere
Nachrichten für die erweiterte Adressauswahl erneut. Ein bereits eingetragener
Alias verändert den Fortschritt nicht. Das Demo-Profil nimmt keine echten
Aliasadressen auf. Plus-Aliase werden nicht automatisch gleichgesetzt.

**Dein Bitwarden-Konto darf eine völlig andere E-Mail-Adresse haben.** Sie wird
nicht benötigt. In einen Bitwarden-Eintrag kommt die Anmeldeadresse des jeweiligen
Dienstes, nicht die Adresse deines Bitwarden-Kontos. IMAP-Zugangsdaten und dein
Bitwarden-Hauptpasswort gehören niemals in diesen Chat, den Quellcode oder eine
Konfigurationsdatei.

## Bereits gespeicherte Mails analysieren

Im Dashboard unter „Postfach & Import“ mehrere **EML-Dateien** auswählen. Analyse
und Upload erfolgen ausschließlich zwischen deinem Browser und 127.0.0.1. Die
Mailtexte werden verarbeitet, aber nicht als Ergebnis gespeichert. Originale
bleiben unverändert. Maximal 2 MiB pro EML; große Anhänge vorher mit deinem
Mailprogramm als separate EML ohne Anhänge exportieren.

Alternativ über das Terminal, jeweils ohne ausgehendes Netzwerk:

```bash
python -m account_finder import /pfad/zu/eml-ordner --format eml
python -m account_finder import /pfad/zu/postfach.mbox --format mbox
python -m account_finder import /pfad/zu/Maildir --format maildir
python -m account_finder report
```

Ein wiederholter Import erzeugt keine doppelten Belege und erhält deinen
Bearbeitungsstatus. Mit aktuellen Regeln oder neu ergänzten Katalogdomains wird
derselbe Beleg aktualisiert, statt die alte Bewertung zusätzlich zu behalten.
Nachrichten ohne aktuellen Hinweis verlieren nur ihren automatischen Beleg;
manuelle Bestätigungen bleiben bestehen. Neue Daten sind spätestens nach 15
Sekunden im geöffneten Dashboard sichtbar. Maildir benötigt `cur/` und `new/`.

Das Dashboard zeigt die Statistik für den gesamten Mehrdatei-Import, auch nach
Neuladen. „Import abbrechen“ hält nach der aktuellen Datei an und bewahrt bereits
gefundene Hinweise. Ein nach Neuladen zurückgebliebener Import kann ebenfalls
abgebrochen werden; nach zehn Minuten ohne Aktivität wird er als unterbrochen
markiert. Übersprungene Dateien und Header-Auswertung sind sichtbar; ein solcher
Scan wird als „Mit Lücken beendet“ gekennzeichnet.

## Mailanbieter ermitteln

Bei einer eigenen Domain lässt sich der Anbieter nicht aus der Adresse allein
ableiten. Ersetze `example.org` in den Befehlen durch deine eigene Maildomain.
Es wurde **keine echte MX-Abfrage und keine Postfachverbindung** vorab durchgeführt.
Der folgende Befehl ist nur eine Offline-Hilfe:

```bash
python -m account_finder discover --domain example.org
```

Wenn du die öffentliche Abfrage ausdrücklich erlaubst:

```bash
python -m account_finder discover --domain example.org --allow-dns
```

Nur `example.org` wird an deinen DNS-Resolver übertragen, nicht die vollständige
Adresse und keine Zugangsdaten. Die Ausgabe enthält MX-Einträge und ggf. Hinweise
auf Google Workspace, Microsoft 365, Fastmail, iCloud und weitere Anbieter. Ein
MX-Eintrag ist **kein Beweis für den richtigen IMAP-Host**; Spamfilter können den
Anbieter verdecken. Prüfe bestehende Mailprogramm-Einstellungen, das Hosting-Konto
und offizielle Anbieterdokumentation.

Unter Windows ist ggf. kein Systemresolver über `/etc/resolv.conf` verfügbar.
Verwende dann den bekannten DNS-Resolver deines Netzes mit
`--resolver RESOLVER-IP` oder ermittle die MX-Einträge selbst über
`Resolve-DnsName -Name example.org -Type MX`. Dieser PowerShell-Befehl ist
ebenfalls eine Netzwerkabfrage und wird nicht vom Programm automatisch ausgeführt.

## IMAP sicher einrichten

1. Erstelle beim tatsächlichen Mailanbieter möglichst ein separates **IMAP-App-Passwort**.
2. Verwende den dort dokumentierten Host; probiere keine geratenen Hosts aus.
3. Richte die Konfiguration ohne Passwort ein:

```bash
python -m account_finder setup-imap
```

Der Assistent fragt nur Host und Benutzername ab, prüft deren Format und legt eine
private `imap.json` an. Er baut noch keine Verbindung auf. Standard ist TLS-Port
993 und die Auswahl aller lesbar auswählbaren Ordner, einschließlich Archiv.
Ordnernamen lassen sich ausdrücklich festlegen:

```bash
python -m account_finder setup-imap --host GEPRUEFTER-IMAP-HOST --username deine.email@example.org --folder INBOX --folder Archive
```

`GEPRUEFTER-IMAP-HOST` ist ein Platzhalter und muss ersetzt werden. Ordnernamen sind
anbieterabhängig. Bestehende `imap.json` wird nicht überschrieben; bearbeite diese
Datei lokal, falls du Host, Methode oder Ordner ändern möchtest. Speichere darin
**keine Passwörter oder Tokens**. Es werden nur folgende Felder akzeptiert:

```json
{
  "host": "imap.mailanbieter.example",
  "username": "deine.email@example.org",
  "port": 993,
  "auth": "app_password",
  "folders": ["*"]
}
```

4. Die Verbindung bewusst freigeben und zunächst begrenzt testen:

```bash
python -m account_finder scan-imap --allow-imap --list-folders
python -m account_finder scan-imap --allow-imap --limit 500
python -m account_finder scan-imap --allow-imap
```

Das App-Passwort wird jedes Mal verdeckt im interaktiven Terminal eingegeben,
nicht gespeichert. Der Scanner öffnet Ordner nur lesend, ruft Nachrichten mit
`BODY.PEEK` ab und beendet die Sitzung mit LOGOUT. Keine Gelesen-Markierungen,
Löschungen oder Mailänderungen. Bei Mails über 2 MiB werden nur die Header gelesen
und als begrenzte Belege gekennzeichnet. Scans sind über UID-Checkpoints
wiederaufnehmbar. `--full-scan` prüft bereits gelesene Nachrichten erneut.

Bei `--limit` erscheint „Limit erreicht“, wenn Nachrichten übrig bleiben. Starte
denselben freigegebenen Scan erneut, um fortzusetzen. Ist das Limit genau am Ende
aller ausgewählten Ordner erreicht, ist der Scan regulär abgeschlossen. Fehler,
übersprungene Nachrichten und reine Header-Auswertungen ergeben einen sichtbaren
Hinweis auf Lücken. Eine während des Scans geänderte Adressauswahl führt zu einem
unterbrochenen Scan und erfordert einen Neustart; vorhandene Hinweise bleiben
erhalten.

### OAuth2, Microsoft, Google und Proton

Exchange Online unterstützt kein IMAP mit deaktivierter Basic Authentication;
hier hilft auch kein App-Passwort. Konfiguriere `--auth oauth2` oder setze das
Feld in `imap.json` entsprechend. Das Programm unterstützt XOAUTH2 mit einem
**kurzlebigen, extern erhaltenen Access-Token**, das verdeckt im Terminal eingegeben
wird. Es registriert selbst keine OAuth-Anwendung, führt keinen OAuth-Loginflow
aus und speichert keine Refresh-Tokens. Erhalte die Freigabe über deinen Anbieter
oder Administrator. Wenn das nicht praktikabel ist, nutze einen lokalen Mail-Export.

Für Google sind App-Passwörter nur bei unterstützten Konten mit den erforderlichen
Sicherheitseinstellungen verfügbar; verwaltete Konten können weitere Vorgaben
haben. Die offizielle Dokumentation entscheidet, nicht der Domain-Hinweis.

Proton Mail stellt keinen gewöhnlichen direkten IMAP-Zugang bereit. Der lokale
Bridge-Zugang wird hier nicht automatisch eingerichtet. Nutze offizielle
Proton-Exportwerkzeuge und den EML-/mbox-Import.

## Accounts prüfen und mit Bitwarden absichern

Für jeden Katalogdienst gibt es Kategorie, offizielle Website, bekannte eigene
Anmeldeadressen, Hinweisart, Stärke des Belegs, Status und Priorität. Verifizierte
Passwortverwaltungslinks mit Quellenbeleg sind für Google, Apple und GitHub
hinterlegt. Andere Dienste führen auf die kuratierte offizielle Startseite;
es wird kein unüberprüfter Passwortlink aus einer E-Mail übernommen.

- **Bestätigt:** du hast „Account geprüft und vorhanden“ abgehakt.
- **Wahrscheinlich:** mindestens ein kontobezogener lokaler Beleg mit ausreichender
  Regelstärke; historische oder gefälschte Mails bleiben möglich.
- **Unbekannt:** keine ausreichenden Hinweise. Das bedeutet nicht, dass kein
  Account existiert. Newsletter, Gastbestellungen und Reset-Anforderungen zählen
  nicht als Nachweis.

Öffne einen Account über „Prüfen“. Bestätige seine Existenz selbst, ordne bei Bedarf
eine konfigurierte eigene Anmeldeadresse zu und wähle Passwort, SSO oder Passkey.
Nutze einen bereits vorhandenen Bitwarden-Eintrag, wenn möglich. Erzeuge neue
Passwörter **in Bitwarden**, ändere sie selbst beim Anbieter und teste die Anmeldung.
MFA und Wiederherstellung werden zusätzlich empfohlen. „Erledigt“ ist erst nach
den erforderlichen Schritten möglich; SSO/Passkeys benötigen kein separates
Dienstpasswort. Unbekannte Katalogdienste können nach eigener Prüfung ebenfalls
manuell bestätigt werden.

Unter „Bitwarden vorbereiten“:

1. Vorhandene Tresoreinträge zuerst zuordnen. Diese Accounts werden vom Download
   ausgeschlossen.
2. Ausschließlich tatsächlich fehlende Einträge auswählen. Wahrscheinliche
   Accounts werden nicht automatisch angehakt.
3. **Metadaten-JSON** herunterladen. Jeder Eintrag enthält Anbieter, offizielle
   URI, ermittelte Adresse und Hinweise; Passwort ist leer, TOTP ist null.
4. In deiner offiziellen Bitwarden-App „Importieren“ → **Bitwarden (json)**
   wählen und die Datei selbst importieren. Dazu nutzt du deinen bestehenden
   Tresor, unabhängig von dessen Konto-Adresse.
5. Datei nur **einmal** importieren, kontrollieren und danach löschen. Bitwarden
   ergänzt beim Import Einträge, prüft jedoch keine Duplikate. Das Programm liest
   oder überschreibt bestehende Tresoreinträge nicht. Ein leerer Importeintrag
   bedeutet noch keine erfolgreiche Passwortänderung.

Auch über CLI ist eine ausdrückliche Auswahl möglich:

```bash
python -m account_finder bitwarden-export /lokaler/geschützter/pfad/account-finder.json --id github --id steam
```

Die Datei wird mit privaten Rechten neu angelegt; existierende Dateien werden
nicht überschrieben. Die JSON-Datei enthält keine Passwörter, aber persönliche
Metadaten. Browser-Downloads haben die Rechte deines Downloadverzeichnisses.

## Katalog erweitern

`account_finder/data/providers.json` enthält 527 kuratierte Dienste.
Alternativ eigene Einträge ergänzen, ohne den eingebauten Katalog zu ändern:

```bash
python -m account_finder --providers examples/providers-extra.json --data-dir .local/demo-custom demo --serve
```

Das Beispiel enthält ausschließlich einen künstlichen Dienst unter `.example`.
Neue IDs und Domains müssen eindeutig sein; Websites müssen HTTPS verwenden und
auf einer eingetragenen Anbieterdomain liegen. Subdomains werden automatisch
berücksichtigt. Keine generischen Versandplattform-Domains als Dienst hinterlegen:
ein gemeinsam genutzter Mailversender beweist nicht, welcher Account gemeint ist.
Spezifischere Subdomains gewinnen bei unterschiedlichen Katalogeinträgen.

Für einen Passwort-Direktlink sind `password_url`, `password_source` und
`password_verified` erforderlich. Ergänze diese nur nach Prüfung einer offiziellen
Quelle. Danach lokal neu importieren bzw. `scan-imap --allow-imap --full-scan`
ausführen und den Server mit dem gleichen Katalog neu starten.

## Bestehende Profile aktualisieren

Version 1.6 ergänzt signierte Offline-Prüfung und lokale Aktivierung einer
Pro-Lizenz. Der Standard-Build enthält keinen Herausgeber-Öffentlichkeitsschlüssel;
er kann daher weder Pro aktivieren noch einen Zahlungsdienst kontaktieren. Version
1.5 ergänzt die lokale Anzeige von Free und Pro. Erkennung, Datenbankschema und
Account-Ergebnisse bleiben kompatibel. Version 1.4 erweitert den eingebauten
Katalog von 372 auf 527 Dienste. Bestehende Profile und Checklisten bleiben
kompatibel. Lokale Originalmails erneut importieren oder einen separat
freigegebenen `scan-imap --allow-imap --full-scan` ausführen, um die neuen Domains
auszuwerten. Dabei werden die Originalmails nicht verändert.

Beim Upgrade von Version 1.0 gelten zusätzlich die Hinweise zur erneuten
Bewertung in [Änderungen](docs/AENDERUNGEN.md).

## Tests und Projektstruktur

Das Repository enthält automatische GitHub-Actions-Prüfungen für Python
3.11–3.14 auf Linux, die Installation des gebauten Pakets und Browser-Prüfungen
auf Deutsch und Englisch. Dafür werden nur künstliche Daten verwendet, keine
persönlichen Postfächer oder Bitwarden-Tresore. Hinweise zum
[Mitwirken](CONTRIBUTING.md) und zum vertraulichen
[Melden von Sicherheitsproblemen](SECURITY.md) liegen ebenfalls bei.

Alle Pflichtprüfungen verwenden künstliche Daten und Fake-IMAP-Server; es werden
keine echten Postfächer oder Bitwarden-Tresore benutzt. Die HTTP-Tests öffnen nur
lokale Loopback-Sockets:

```bash
python -m unittest discover -s tests -v
```

Optionaler Browser-Funktionstest benötigt eine bereits installierte
Playwright-Python-Bibliothek und Chromium. Das gehört nicht zu den
Laufzeitabhängigkeiten:

```bash
python scripts/browser_smoke.py --browser /usr/bin/chromium
```

Der Test erzeugt ein temporäres Demo-Profil, sperrt ausgehende Browseranfragen
und prüft beide Sprachen, Sprachwechsel, Filter, Checklisten, Export, EML-Import,
Spracherkennung und mobile Ansichten.

| Datei | Zweck |
|---|---|
| `account_finder/analysis.py` | Lokale MIME-Auswertung und Erkennungsregeln |
| `account_finder/data/providers.json` | Erweiterbarer Katalog |
| `account_finder/i18n.py`, `data/translations.json` | Lokale Deutsch/Englisch-Texte |
| `account_finder/store.py` | SQLite und Statuspersistenz |
| `account_finder/imap_client.py` | TLS-IMAP, PEEK, Wiederaufnahme |
| `account_finder/discovery.py` | Ausdrücklich aktivierte MX-Hinweise |
| `account_finder/bitwarden.py` | Offizielles Metadaten-Importformat |
| `account_finder/server.py`, `web/` | Lokales Dashboard |
| `tests/` | Automatisierte Regressionstests |
| [Katalogrichtlinie](docs/KATALOG.md) | Umfang, Qualitätsmaßstäbe und neue Dienste vorschlagen |
| [Freemium-Plan](docs/FREEMIUM_DE.md) | Verfügbare Free-Funktionen, transparente Pro-Vorschau und Produktgrenzen |
| [Checkliste für die kommerzielle Veröffentlichung](docs/COMMERCIAL_RELEASE.md) | Entscheidungen des Inhabers vor dem ersten Pro-Kauf |
| [Lizenztechnik](docs/LICENSE_IMPLEMENTATION.md) | Signierte Offline-Pro-Lizenzen und Umgang mit Herausgeber-Schlüsseln |
| [Veröffentlichungs-Checkliste](docs/PUBLISHING.md) | Schritte, die der Inhaber vor der Veröffentlichung selbst prüft |
| [Technischer Plan](docs/PLAN_DE.md) | Reihenfolge und Architektur |
| [Sicherheitsmodell](docs/SICHERHEIT.md) | Datenschutz, Grenzen und Schutzmaßnahmen |
| [Prüfbericht](docs/PRUEFBERICHT.md) | Tatsächlich ausgeführte Prüfungen |
| [Offizielle Quellen](docs/QUELLEN.md) | Bitwarden, Passwortlinks und Mailanbieter |

Die App ist für den eigenen Rechner gedacht. Eine Ausführung in einer entfernten
Entwicklungsumgebung verarbeitet Daten auf **diesem entfernten Rechner** und ist
daher für echte Maildaten nicht „lokal auf deinem Gerät“. Nutze hier nur die Demo
und installiere die Anwendung auf deinem eigenen Rechner, bevor du echte Mails
oder Zugangsdaten verwendest. Nicht ungeschützt ins Internet veröffentlichen.
