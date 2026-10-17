# ARGUS 2.6.1 – lokales Account-Inventar

Deutsch · [English](README.md)

[![Checks](https://github.com/Valentindghjg/ARGUS/actions/workflows/ci.yml/badge.svg)](https://github.com/Valentindghjg/ARGUS/actions/workflows/ci.yml)

ARGUS ist ein lokales Python-Programm mit **deutscher und englischer Weboberfläche**, **527
erweiterbaren Diensten**, lokaler E-Mail-Analyse und einer Checkliste zum
Absichern mit Bitwarden. Die Nutzer wählen ihre Sprache selbst. Die Erkennung von
Mails funktioniert unabhängig davon immer auf Deutsch und Englisch.

**Was ARGUS verspricht:** Es hilft dir, Account-Hinweise in deinen eigenen
E-Mails zu verstehen und wichtige Sicherheitsaufgaben kontrolliert abzuarbeiten.
Es kann weder alle Accounts finden noch allein aus E-Mails beweisen, wie gut ein
Konto geschützt ist. Eine erledigte Checkliste hält deine eigenen Schritte fest;
sie ist keine Sicherheitsgarantie.

## Vorschau

Die Bilder zeigen ausschließlich die mitgelieferten künstlichen Demodaten.

| Dashboard | Sicherheits-Arbeitsliste |
| --- | --- |
| [![ARGUS-Dashboard](docs/preview/dashboard-de.png)](docs/preview/dashboard-de.png) | [![ARGUS-Sicherheits-Arbeitsliste](docs/preview/worklist.png)](docs/preview/worklist.png) |

Die Anwendung findet **Hinweise in deinen eigenen Nachrichten**. Ein fehlender
Hinweis bedeutet „Unbekannt“ und beweist nicht, dass kein Account existiert.
Künstliche Demo und persönliche Ergebnisse bleiben getrennt.

## Lizenz

ARGUS steht unter der
[Mozilla Public License 2.0](LICENSE) (MPL-2.0). Alle Funktionen sind kostenlos:
Es gibt keine Editionen, Lizenzschlüssel, Online-Konten, Zahlungsdaten oder
Telemetrie. Details stehen in [LICENSING.md](LICENSING.md) und in der
[Veröffentlichungs-Checkliste](docs/PUBLISHING.md).

## In zwei Minuten starten

Voraussetzung: **Python 3.11 oder neuer** und ein aktueller Browser. ARGUS nutzt
nur die Python-Standardbibliothek; npm und Docker sind nicht nötig.

1. Projektarchiv entpacken oder Repository klonen und ein Terminal in diesem Ordner
   öffnen (bei einem Git-Klon `ARGUS`).
2. Python-Version mit `python --version` prüfen. Auf Windows bei Bedarf alle
   `python`-Befehle durch `py -3` ersetzen; auf macOS/Linux gegebenenfalls `python3`.
3. Demo starten:

```bash
python -m pip install .
python -m argus_security --data-dir .local/demo demo --serve --open
```

Der Browser öffnet `http://127.0.0.1:8765/`. Falls er nicht automatisch öffnet,
diese Adresse selbst aufrufen. Strg+C beendet den Server. Die Demo enthält 18
künstliche Nachrichten an zwei erfundene eigene Adressen: 13 gefundene Accounts
bei 12 Anbietern, zwei simulierte manuelle Bestätigungen und eine erledigte
Checkliste. Eine kurze Erklärung in der Übersicht zeigt die schwierigen Fälle:
Newsletter, Gastbestellung und Rücksetz-Mail belegen keinen Account, zwei
Accounts beim selben Dienst, Single Sign-on und eine ähnlich aussehende
Absenderdomain. **Das sind keine echten Accounts.** Die Liste „Probier diesen
Weg“ führt in fünf Schritten vom Import bis zur Übergabe an Bitwarden; die
[Demo-Anleitung](docs/DEMO_DE.md) beschreibt sie. Antworten auf häufige Fragen
stehen in den [FAQ](docs/FAQ_DE.md).
Mit `--port 8766` lässt sich ein bereits belegter Port umgehen.

Alternativ das GitHub-Repository klonen:

```bash
git clone https://github.com/Valentindghjg/ARGUS.git
cd ARGUS
python -m pip install .
python -m argus_security --data-dir .local/demo demo --serve --open
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

## Abdeckung, Tastaturbedienung und maskierte Ansicht

Die Übersicht nennt, was deine Importe abdecken: jede Quelle mit Läufen,
Nachrichten und letztem Datum, den Zeitraum deiner Hinweise, Monate ohne Hinweis
und eigene Adressen ohne Hinweis. ARGUS kann nicht wissen, wie viel deiner Mails
oder deines Online-Lebens das ist, deshalb zeigt es keine Gesamtquote.

Jedes Bedienelement ist per Tastatur erreichbar; ein Link **Zum Hauptinhalt
springen** kommt zuerst, die aktuelle Seite wird angesagt, und Dialoge halten den
Fokus. **Persönliche Angaben verbergen** in der oberen Leiste maskiert
E-Mail-Adressen auf dem Bildschirm (etwa `d•••@e•••.invalid`), was beim Teilen
des Bildschirms hilft. Die Maskierung ändert nur die Anzeige: Sie ist weder
Verschlüsselung noch ein bereinigter Export, und die Wahl merkt sich nur dieser
Browser.

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
python -m argus_security --language de --help
python -m argus_security --language en --help
python -m argus_security --language de --data-dir .local/demo demo --serve
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
python -m argus_security init --email deine.email@example.org
python -m argus_security serve --open
```

Standardmäßig liegen persönliche Ergebnisse unter `~/.local/share/argus/`. Ein
Profil aus der Zeit vor der Umbenennung (`~/.local/share/account-finder/`) wird
einmalig automatisch mit allen Dateien und Rechten dorthin verschoben. Ein eigenes
Verzeichnis wird mit `--data-dir /absoluter/pfad` **vor dem Unterbefehl**
angegeben; ein solches Verzeichnis wird nie verschoben. Nach `pip install .`
funktioniert der kürzere Befehl `argus` genauso wie `python -m argus_security`.
Der alte Befehl `account-finder` und `python -m account_finder` funktionieren
vorerst weiter, zeigen aber einen Hinweis, dass sie veraltet sind. Im Dashboard
erscheinen jetzt zunächst keine gefundenen Accounts, bis du echte Mails importierst.

Weitere **eigene Anmeldeadressen** kannst du bei der Einrichtung angeben:

```bash
python -m argus_security --data-dir .local/eigene-aliase init --email deine.email@example.org --email eigene-aliasadresse@example.org
```

Weitere eigene Adressen kannst du später **im selben Profil** ergänzen, im
Dashboard unter „Postfach & Import“ oder mit:

```bash
python -m argus_security add-email --email eigene-aliasadresse@example.org
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
python -m argus_security import /pfad/zu/eml-ordner --format eml
python -m argus_security import /pfad/zu/postfach.mbox --format mbox
python -m argus_security import /pfad/zu/Maildir --format maildir
python -m argus_security report
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

### Nur Geändertes, mit Budget, und später fortsetzen

ARGUS erkennt eine Nachricht, die es unter gleichen Bedingungen schon
ausgewertet hat, an ihrem Inhalts-Fingerabdruck, nie an Dateiname oder Datum, und
wertet sie nicht erneut aus; das Ergebnis zählt sie als unverändert. Neue eigene
Adressen, Katalogergänzungen oder neue Regeln werten alles erneut aus. Ein Lauf
lässt sich mit `--max-messages` oder `--max-megabytes` auf neue Arbeit begrenzen;
er endet dann als „Grenze erreicht; nicht alles wurde verarbeitet“, nie als
vollständig. Derselbe Import setzt beim nächsten Mal fort, auch nach einer
Unterbrechung oder Pause. `--recheck` wertet jede Nachricht erneut aus. Der Index
enthält nur Fingerabdrücke, nie Nachrichteninhalte.

ARGUS merkt sich den letzten Terminal-Import (Quelle und Format) für
`import --again`; das Dashboard zeigt ihn unter „Postfach & Import“ mit dem
Befehl. Leere, zu große oder unlesbare Elemente werden lokal vermerkt, und
`import --retry-failed` liest nach dem Beheben nur diese. Eine fehlende Quelle
wird gemeldet, nie stillschweigend ersetzt. Für ein großes Archiv zählt
`import --check` zuerst Nachrichten, Größe, neue und unveränderte Nachrichten und
zu große Elemente, ohne etwas zu importieren. Im Browser ausgewählte Dateien
merkt sich ARGUS nie.

```bash
python -m argus_security import /pfad/zu/postfach.mbox --format mbox --check
python -m argus_security import /pfad/zu/postfach.mbox --format mbox --max-messages 5000
python -m argus_security import --again          # setzt dieselbe Quelle fort
python -m argus_security import --retry-failed   # nur fehlgeschlagene Elemente
```

### Einen Exportordner überwachen

Speichert dein Mailprogramm EML-Dateien in einen Ordner, kann ARGUS neue Dateien
daraus importieren, solange das Dashboard läuft. Du gibst genau einen
vorhandenen lokalen Ordner im Terminal frei; ARGUS liest nur `*.eml`-Dateien
direkt darin, nie Unterordner, und verändert, verschiebt oder löscht nie eine
Datei. Abgelehnt werden das ganze Laufwerk, dein Benutzerordner, versteckte
Ordner, Verknüpfungen, Netzwerkpfade und der Profilordner. Die Überwachung
erscheint unter „Kontrolle“ als Berechtigung und wartender Vorgang, folgt der
globalen Pause und lässt sich dort beenden; ein fehlender Ordner wird gemeldet,
nie anderswo gesucht.

```bash
python -m argus_security watch-folder enable ~/Mail/ARGUS-export --interval-minutes 5
python -m argus_security watch-folder status
python -m argus_security watch-folder disable
```

## Mailanbieter ermitteln

Bei einer eigenen Domain lässt sich der Anbieter nicht aus der Adresse allein
ableiten. Ersetze `example.org` in den Befehlen durch deine eigene Maildomain.
Es wurde **keine echte MX-Abfrage und keine Postfachverbindung** vorab durchgeführt.
Der folgende Befehl ist nur eine Offline-Hilfe:

```bash
python -m argus_security discover --domain example.org
```

Wenn du die öffentliche Abfrage ausdrücklich erlaubst:

```bash
python -m argus_security discover --domain example.org --allow-dns
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
python -m argus_security setup-imap
```

Der Assistent fragt nur Host und Benutzername ab, prüft deren Format und legt eine
private `imap.json` an. Er baut noch keine Verbindung auf. Standard ist TLS-Port
993 und die Auswahl aller lesbar auswählbaren Ordner, einschließlich Archiv.
Ordnernamen lassen sich ausdrücklich festlegen:

```bash
python -m argus_security setup-imap --host GEPRUEFTER-IMAP-HOST --username deine.email@example.org --folder INBOX --folder Archive
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
python -m argus_security scan-imap --allow-imap --list-folders
python -m argus_security scan-imap --allow-imap --limit 500
python -m argus_security scan-imap --allow-imap
```

Das App-Passwort wird jedes Mal verdeckt im interaktiven Terminal eingegeben,
nicht gespeichert. Der Scanner öffnet Ordner nur lesend, ruft Nachrichten mit
`BODY.PEEK` ab und beendet die Sitzung mit LOGOUT. Keine Gelesen-Markierungen,
Löschungen oder Mailänderungen. Bei Mails über 2 MiB werden nur die Header gelesen
und als begrenzte Belege gekennzeichnet. Scans sind über UID-Checkpoints
wiederaufnehmbar. `--full-scan` prüft bereits gelesene Nachrichten erneut; er beginnt
jedes Mal bei der ersten Nachricht und läuft deshalb ohne `--limit`.

Bei `--limit` erscheint „Limit erreicht“, wenn Nachrichten übrig bleiben. Starte
denselben freigegebenen Scan erneut, um fortzusetzen. Ist das Limit genau am Ende
aller ausgewählten Ordner erreicht, ist der Scan regulär abgeschlossen. Fehler,
übersprungene Nachrichten und reine Header-Auswertungen ergeben einen sichtbaren
Hinweis auf Lücken. Eine während des Scans geänderte Adressauswahl führt zu einem
unterbrochenen Scan und erfordert einen Neustart; vorhandene Hinweise bleiben
erhalten.

### Optionale geplante Scans

Nachdem du `imap.json` mit einem manuellen schreibgeschützten Scan geprüft hast,
kannst du inkrementelle Scans aktivieren, solange das lokale ARGUS-Dashboard läuft.
Installiere dafür zuerst einen unterstützten, **vom Betriebssystem geschützten**
Python-Schlüsselbund. ARGUS lehnt Klartext-Schlüsselbund-Backends ab und besitzt
keinen Datei-Fallback:

```bash
python -m pip install keyring
python -m argus_security background-imap enable --interval-minutes 1440 --limit 500
python -m argus_security serve --open
```

Der Befehl fragt das separate App-Passwort oder ein extern bezogenes OAuth2-Token
nur verdeckt im Terminal ab. Das Geheimnis wird ausschließlich im Schlüsselbund
des Betriebssystems gespeichert; die lokale SQLite-Datenbank enthält nur einen
undurchsichtigen Verweis und Zeitplan-Metadaten. Der erste Scan ist beim Start des
Dashboards fällig und setzt danach an den normalen IMAP-UID-Checkpoints fort. Er
läuft nicht, wenn ARGUS geschlossen ist, führt keinen Vollscan aus, verändert keine
Mails und wartet nach einem festen sicheren Fehler bis zum nächsten Intervall.

Die Freigabe gilt genau für die Einstellungen, die `enable` anzeigt (Host, Port,
Benutzername, Anmeldeart und Ordner). Ändert sich `imap.json` später, stoppen
geplante Scans, bevor sie die gespeicherte Freigabe verwenden; führe dann
`background-imap enable` erneut aus, um die neuen Einstellungen freizugeben.
Zeitpläne aus der Zeit vor dieser Prüfung verlangen ebenfalls einmal eine neue
Freigabe.

Status, Pause und Widerruf:

```bash
python -m argus_security background-imap status
python -m argus_security background-imap disable
python -m argus_security background-imap revoke
```

`disable` pausiert künftige Scans und behält den Schlüsselbund-Eintrag. `revoke`
deaktiviert zuerst die Scans und entfernt anschließend den Eintrag aus dem
Schlüsselbund. Ein bereits laufender Scan bemerkt das innerhalb von etwa 15 Sekunden
und endet vor dem nächsten Nachrichtenabruf. Das Dashboard zeigt nur den Status und fragt niemals nach Passwort
oder Token.

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

## Optionaler Browser-Begleiter

`browser-companion/` enthält einen entpackten Chromium-Erweiterungsprototyp. Wenn
du sein Popup öffnest, prüft er ausschließlich den Hostnamen des aktiven Tabs
gegen den gebündelten öffentlichen ARGUS-Katalog. Wo vorhanden, kann er einen
verifizierten Passwortverwaltungslink kopieren oder öffnen. Er liest weder
Seiteninhalt noch Formulare, Cookies, Passwörter, Verlauf, Tokens, E-Mails oder
Bitwarden-Daten. Ein Webseitenbesuch erstellt oder bestätigt nie einen Account.

```bash
python browser-companion/scripts/build.py
python browser-companion/tests/validate.py
```

Lade das erzeugte `browser-companion/dist/` über **Entpackte Erweiterung laden**
in einem Chromium-Browser. Details stehen in der
[Begleiter-Anleitung](browser-companion/README.md).

## Sicherheits-Arbeitsliste fortsetzen

Öffne **Sicherheits-Arbeitsliste** und wähle **Nächsten Account absichern**. ARGUS
nimmt dann einen einzelnen unvollständigen lokalen Account mit höchster Priorität
in die Arbeitsliste auf. Liste, Pausenstatus und Checklisten bleiben nach
Neustarts lokal erhalten. Jeder Dialog zeigt den nächsten offenen Schritt. Die
geführte Bitwarden-Schaltfläche verlangt eine zweite Bestätigung und erstellt nur
einen passwortfreien Eintrag für den aktuellen Account. SSO und Passkeys
überspringen einen separaten Passwortwechsel. Es wird nichts automatisch beim
Anbieter abgeschickt. Siehe die [Arbeitslisten-Anleitung](docs/WORKLIST.md) und
[Hinweise zu unterbrochenen Übertragungen](docs/BITWARDEN_CLI.md).

Bei Prüfung, Passwortwechsel, Anmeldetest sowie MFA/Wiederherstellung speichert
**Ich habe diesen Schritt erledigt** deine ausdrückliche lokale Bestätigung und
führt danach direkt mit dem nächsten Schritt weiter.

## Prioritäten und Identitätskonten

Jeder Account zeigt, warum er seine Priorität hat: die Einstufung dieser Art
Dienst im Katalog und Accounts, von denen andere abhängen. Du kannst notieren,
welcher bestätigte Account das Postfach jeder eigenen Adresse hostet („Wo deine
Postfächer liegen“ unter „Postfach & Import“) und, bei einem Account mit Single
Sign-on, mit welchem bestätigten Account er sich anmeldet. Solche
Identitätskonten werden zu „Zuerst“ mit sichtbarem Grund, und Vorschläge für die
Arbeitsliste nennen sie zuerst, jeweils mit kurzem „Warum“. ARGUS leitet diese
Beziehungen nie aus E-Mails oder Websitebesuchen ab. Deine eigene Priorität hat
immer Vorrang; **Automatisch** stellt die abgeleitete wieder her. **Nach oben**
und **Nach unten** ändern die Reihenfolge der Arbeitsliste und lassen sich
zurücknehmen; Vorschläge hinzuzufügen sortiert geplante Aufgaben nie um.
Prioritäten ordnen nur deine Arbeit; sie sind kein gemessenes Angriffsrisiko.

```bash
python -m argus_security mailbox du@example.org google
python -m argus_security sign-in-with notion google
python -m argus_security sign-in-with notion --remove
```

## Kontrolle: Vorgänge, Aktivität und eine Pause für alles

„Kontrolle“ listet jeden Import, IMAP-Scan und jede Bitwarden-Prüfung oder
-Übertragung mit Zustand (läuft, pausiert, abgeschlossen, mit Lücken
abgeschlossen, fehlgeschlagen, abgebrochen, braucht Freigabe, Ergebnis unklar,
unterbrochen) und zeigt einen geplanten Scan als wartend bis zu seiner nächsten
Zeit; keine Hintergrundarbeit bleibt verborgen. **Gesamte Automatik pausieren**
sperrt neue Vorgänge und beendet laufende zwischen zwei Nachrichten, innerhalb
etwa einer Sekunde; gespeicherte
Hinweise und IMAP-Checkpoints bleiben, und nichts, was außerhalb von ARGUS schon
geschah, wird rückgängig gemacht. Die Übersicht zeigt die Pause, bis du
fortsetzt. Das Aktivitätsprotokoll enthält nur Zeit, Vorgangsart, Ergebnis und
Anzahlen (keinen E-Mail-Text, keine Adressen, Geheimnisse oder
Befehlsausgaben), höchstens 500 Einträge für 180 Tage.

Unter „Berechtigungen“ zeigt die Kontrolle die einzige dauerhafte Freigabe, die
ARGUS halten kann: geplante IMAP-Scans, mit Host, Ordnern, Höchstmenge, Abstand,
Freigabedatum und wie viele Ordner an einem gespeicherten Checkpoint fortsetzen
(nie Benutzername oder Geheimnis). Ein geänderter Host, Account, eine geänderte
Anmeldeart oder Ordnerauswahl erscheint als „Braucht Freigabe“ und wird nicht
genutzt. **Freigabe widerrufen** beendet sie endgültig und entfernt die
gespeicherte Berechtigung aus dem Schlüsselbund des Systems; eine Pause hält
Vorgänge nur an. Manuelle IMAP-Scans, Bitwarden-Übertragungen und MX-Abfragen
werden jedes Mal einzeln freigegeben. `background-imap preview` zeigt ohne
Verbindung, was eine Freigabe umfassen würde, und `enable` zeigt dasselbe, bevor
es nach dem Passwort fragt.

```bash
python -m argus_security automation status
python -m argus_security automation pause
python -m argus_security automation resume
python -m argus_security background-imap preview --interval-minutes 60 --limit 200
```

## Kurze Sitzungen, Prüfdaten und Checkliste nach Anmeldeart

Unter „Sicherheits-Arbeitsliste“ startet **Eine Aufgabe** oder **Drei Aufgaben**
eine kurze Sitzung mit den nächsten bereiten Aufgaben. Es gibt kein Zeitlimit.
Die Sitzung zeigt, was du seit ihrem Start erfasst hast; **Bericht ansehen**
zeigt die vollständige Textdatei (nur Accountnamen und Schritte, keine Adressen,
Belege oder Passwörter), bevor dein Browser sie speichert. Die Checkliste folgt
der gewählten Anmeldeart: Single-Sign-on- und Passkey-Accounts erhalten
passende Schritte statt einer Passwortänderung, und ein Account, der von einem
unvollständigen Anmelde-Account abhängt, sagt das.

Eine **Prüfregel** (nach 6, 12 oder 24 Monaten; Accounts mit hoher Priorität
oder alle abgeschlossenen) schlägt ein Datum vor, an dem du abgeschlossene
Accounts erneut prüfst. Nichts ändert sich, bis du **Dieses Datum übernehmen**
oder **Vorgeschlagene Daten übernehmen** wählst; beides lässt sich
zurücknehmen. Alter allein ist kein Zeichen für ein Sicherheitsproblem.
Bitwarden-Notizen enthalten jetzt auch die von dir bestätigte Anmeldeart, den
Anmelde-Account und eine geprüfte Seite für Passwort-Einstellungen; Unbekanntes
bleibt weg.

```bash
python -m argus_security session start --size 3
python -m argus_security session report
python -m argus_security session end
python -m argus_security review-rule --months 12 --scope important --apply
```

## Neu seit deiner letzten Durchsicht

Nach einem Import zeigt „Neu seit…“ nur Hinweise, die neu sind oder anders
bewertet werden, seit du Änderungen zuletzt als gesehen markiert hast. Dieselbe
E-Mail erneut importiert erscheint nicht wieder. Hinweise sind nach Account
gruppiert; was deine Entscheidung braucht (Absender außerhalb des Katalogs,
Hinweise ohne eindeutigen Account, eine zu wählende Anmeldeadresse, neue Belege
nach einem Verwerfen), steht zuerst. Werbung, Bestellungen und
Rücksetz-Anfragen werden nur gezählt. Lücken des letzten Imports (übersprungene,
unlesbare oder nur aus Kopfzeilen gelesene Nachrichten) bleiben sichtbar, bis du
sie als gesehen markierst.

Wenn du zurückkommst, fasst die Übersicht das an einer Stelle zusammen:
zuerst Importlücken und unklare Bitwarden-Übertragungen, dann neue
Entscheidungen, neue Hinweise und erreichte Prüfdaten. **Als gesehen markieren**
ändert keine Entscheidung und keinen Schritt und lässt sich einmal über die
Meldung zurücknehmen. Die Gruppierung bestätigt, vereinigt oder ordnet nie einen
Account zu. Die CLI bietet dasselbe:

```bash
python -m argus_security whats-new
python -m argus_security whats-new --mark-reviewed
```

## Unklares, ausgeblendete Domains und Adressnotizen

„Unklares“ sammelt alles, was deine Mails nicht klären, damit du einmal statt an
vielen Stellen entscheidest: Accounts ohne Anmeldeadresse, Dienste mit Hinweisen
ohne eindeutigen Account, verworfene Accounts mit neuen Belegen und
Absenderdomains außerhalb des Katalogs. ARGUS wählt nie eine Adresse für dich
und führt keine Accounts zusammen.

Eine Absenderdomain außerhalb des Katalogs lässt sich mit Grund ausblenden
(Newsletter, Spam, nicht relevant). Neue Hinweise holen sie zurück, „Wieder
anzeigen“ hebt den Ausschluss auf. Unter „Postfach & Import“ kannst du notieren,
wie zwei eigene Adressen zusammenhängen (dasselbe Postfach oder ersetzt durch);
die Notiz erscheint bei den betroffenen Accounts und führt sie nie zusammen. Die
CLI bietet dasselbe:

```bash
python -m argus_security unclear
python -m argus_security exclude newsletter-absender.example --reason newsletter
python -m argus_security relate alt@example.org neu@example.org --kind replaced_by
```

## Accounts prüfen und mit Bitwarden absichern

Jede Anmeldezuordnung erhält einen eigenen Eintrag, eine eigene Checkliste,
Arbeitsliste und Bitwarden-Übertragung. Starke direkte Belege an unterschiedliche
eigene Adressen ergeben separate wahrscheinliche Einträge. Prüfe diese, da
Aliase oder Adressänderungen weiterhin denselben Account betreffen können. Über
**Weiteren Account bei diesem Dienst hinzufügen** in den Account-Details kannst
du bekannte lokale Einträge ergänzen, auch bezeichnete Accounts mit derselben
E-Mail-Adresse. Beim Anbieter wird nichts erstellt. Details und Hinweise für
ältere Profile stehen in der [Mehrkonto-Anleitung](docs/ACCOUNTS.md).

Für jeden Katalogdienst gibt es Kategorie, offizielle Website, bekannte eigene
Anmeldeadressen, Hinweisart, Stärke des Belegs, Status und Priorität. Verifizierte
Passwortverwaltungslinks mit Quellenbeleg sind für Google, Apple und GitHub
hinterlegt. Andere Dienste führen auf die kuratierte offizielle Startseite;
es wird kein unüberprüfter Passwortlink aus einer E-Mail übernommen.

Jeder Account zeigt drei getrennte Marken; „Was die drei Marken bedeuten“ unter
der Liste erklärt sie:

- **Beleg** (automatisch): wahrscheinlich, schwach, älter oder keiner. Er folgt
  deinen importierten Mails, die alt oder gefälscht sein können. „Keine Belege“
  heißt nie „existiert nicht“. Der Wert ist eine Hinweisstärke, keine
  Wahrscheinlichkeit.
- **Deine Entscheidung**: offen, von dir bestätigt oder mit Grund verworfen
  (nicht meiner, kein Account, geschlossen). Neue Belege ändern sie nie; starke
  neue Belege nach dem Verwerfen zeigen nur einen Hinweis. Verworfene Accounts
  verschwinden aus Listen, Arbeitsliste und Vorschlägen.
- **Fortschritt**: deine fünf datierten Schritte. Abgeschlossen heißt, jeder
  Schritt ist erledigt oder trifft nicht zu. Das ist keine Sicherheitsgarantie.

Newsletter, Gastbestellungen und Reset-Anforderungen zählen nicht als Nachweis.

Öffne einen Account über „Prüfen“, entscheide, ob er dir gehört, und arbeite dann
die Schritte ab: Anmeldung prüfen (bei Bedarf eine eigene Adresse zuordnen), in
Bitwarden speichern, eigenes Passwort setzen (bei SSO oder Passkey nicht nötig),
Anmeldung testen sowie MFA und Wiederherstellung prüfen (oder als nicht angeboten
bzw. nicht genutzt markieren). Erzeuge neue Passwörter **in Bitwarden** und ändere
sie selbst beim Anbieter. Jeder erledigte Schritt speichert sein Datum und kann
eine lokale Wiedervorlage bekommen. Ein von ARGUS passwortfrei angelegter Eintrag
gilt als „vorbereitet“, bis du den Tresor-Schritt abhakst. Der Hinweis nach jeder
Änderung und „Deine letzten Änderungen“ in der Arbeitsliste machen lokale
Entscheidungen und Schritte rückgängig; Bitwarden-Einträge und Scans werden nie
zurückgenommen. Katalogdienste ohne Mailbeleg kannst du ebenfalls bestätigen.

### Drei gleichwertige Wege, Bereitschaft und ein Journal

„Bitwarden vorbereiten“ bietet drei gleichwertige Wege, von denen keiner ein
Lesen deines Tresors durch ARGUS braucht: **1 · Schon in deinem Tresor**
markiert die gewählten Accounts als gespeichert, nachdem du selbst nachgesehen
hast (rücknehmbar; auch `bitwarden-assign --id …`), **2 · Passwortfreie Datei
herunterladen** und **3 · Optional: Bitwarden-CLI** zum direkten Anlegen. Das
Prüfen vorhandener Einträge mit der CLI liest deinen Tresor und braucht für genau
diese Prüfung ein eigenes Häkchen. Jeder Account zeigt zuerst seine
Bereitschaft: „Bereit“, „Erst prüfen“ (nicht von dir bestätigt oder keine
Anmeldeadresse, sodass der Benutzername leer bleibt) oder „Jetzt nicht“
(Anmeldeadresse zu wählen, unklare Übertragung, Download ohne festgehaltenen
Import oder schon in Bitwarden). Bereit ist keine Sicherheitsaussage. Das
Übergabejournal listet jeden Download und jede CLI-Übertragung; ein unklarer
Eintrag sperrt einen weiteren Versuch, bis du festhältst, was du im Tresor
gefunden hast, damit keine Datei versehentlich doppelt importiert wird. Im
Terminal zeigt `bitwarden-journal list` diese Einträge, und
`bitwarden-journal resolve ID --found` (oder `--not-found`) hält das Ergebnis
fest. Unter Windows startet ARGUS nur die eigenständige `bw.exe` aus dem PATH,
nicht den npm-Wrapper `bw.cmd`.

Unter „Bitwarden vorbereiten“:

1. Optional **Ausgewählte Accounts im entsperrten Bitwarden prüfen** wählen.
   Nach einer separaten Bestätigung durchsucht ARGUS über die bereits entsperrte
   offizielle CLI nur die ausgewählten Accounts und zeigt ausschließlich
   **gefunden / möglich / nichts gefunden** mit Anzahl. Die CLI-Antwort kann beim
   Verarbeiten Tresorfelder enthalten; ARGUS speichert oder zeigt jedoch keine
   Namen, Benutzernamen oder Passwörter. Mögliche Treffer selbst prüfen.
2. Vorhandene Tresoreinträge zuerst zuordnen. Diese Accounts werden vom Download
   ausgeschlossen.
3. Ausschließlich tatsächlich fehlende Einträge auswählen. Wahrscheinliche
   Accounts werden nicht automatisch angehakt.
4. **Metadaten-JSON** herunterladen. Jeder Eintrag enthält Anbieter, offizielle
   URI, ermittelte Adresse und Hinweise; Passwort ist leer, TOTP ist null.
5. In deiner offiziellen Bitwarden-App „Importieren“ → **Bitwarden (json)**
   wählen und die Datei selbst importieren. Dazu nutzt du deinen bestehenden
   Tresor, unabhängig von dessen Konto-Adresse.
6. Datei nur **einmal** importieren, kontrollieren und danach löschen. Bitwarden
   ergänzt beim Import Einträge, prüft jedoch keine Duplikate. Dieser JSON-Import
   liest oder überschreibt bestehende Tresoreinträge nicht. Ein leerer
   Importeintrag bedeutet noch keine erfolgreiche Passwortänderung.

Alternativ kann das Dashboard nach dem Entsperren der offiziellen Bitwarden-CLI
in deinem eigenen Terminal die ausdrücklich ausgewählten passwortfreien Einträge
direkt erstellen. Die getrennte optionale Prüfung ist nur lesend; die Erstellung
liest oder überschreibt keine bestehenden Einträge. Keine Aktion erhält dein
Hauptpasswort. Folge der
[Bitwarden-CLI-Übergabeanleitung](docs/BITWARDEN_CLI.md).

Bevor einer der beiden Wege etwas schreibt, zeigt das Dashboard genau, was
geschrieben wird: Name, offizielle Website, Anmeldeadresse, Notiz und Zusatzfelder
je Eintrag sowie die Accounts, die ausgelassen werden, weil das lokale Protokoll
sie als angelegt führt. Passwort-, TOTP-, Passkey- und Wiederherstellungsfelder
gehören nie zu einem Eintrag.

Auch ein Metadaten-Export über die Kommandozeile ist möglich. Mit `--preview`
siehst du die Einträge vorher; dabei entsteht keine Datei:

```bash
python -m argus_security bitwarden-export /lokaler/geschützter/pfad/argus-bitwarden.json --id github --id steam --preview
python -m argus_security bitwarden-export /lokaler/geschützter/pfad/argus-bitwarden.json --id github --id steam
```

Die Datei wird mit privaten Rechten neu angelegt; existierende Dateien werden
nicht überschrieben. Die JSON-Datei enthält keine Passwörter, aber persönliche
Metadaten. Browser-Downloads haben die Rechte deines Downloadverzeichnisses.

## Katalog erweitern

`argus_security/data/providers.json` enthält 527 kuratierte Dienste.
Alternativ eigene Einträge ergänzen, ohne den eingebauten Katalog zu ändern:

```bash
python -m argus_security --providers examples/providers-extra.json --data-dir .local/demo-custom demo --serve
```

Das Beispiel enthält ausschließlich einen künstlichen Dienst unter `.example`.
Neue IDs und Domains müssen eindeutig sein; Websites müssen HTTPS verwenden und
auf einer eingetragenen Anbieterdomain liegen. Subdomains werden automatisch
berücksichtigt. Keine generischen Versandplattform-Domains als Dienst hinterlegen:
ein gemeinsam genutzter Mailversender beweist nicht, welcher Account gemeint ist.
Spezifischere Subdomains gewinnen bei unterschiedlichen Katalogeinträgen.

### Dienst im Dashboard ergänzen

Unter „Unklares“ füllt **Zu meinem Katalog hinzufügen** ein Formular für eine
Absenderdomain außerhalb des Katalogs vor. ARGUS prüft den Eintrag wie den
eingebauten Katalog (eindeutige Domains, HTTPS-Website auf einer der
Absenderdomains, vorhandene Kategorie) und speichert ihn nur in deinem Profil als
`my-providers.json` mit privaten Rechten. Online nachgeschlagen wird nichts.
Gemeinsam genutzte Versanddienste (Massenmail-Plattformen wie `sendgrid.net` oder
`amazonses.com`) werden abgelehnt, weil sie für viele Firmen senden. Gespeicherte
Hinweise behalten ihre bisherige Zuordnung, bis du die ursprünglichen E-Mails
erneut importierst; deren Inhalt hat ARGUS nie gespeichert. Unter „Postfach &
Import“ lässt sich eine Ergänzung entfernen, solange kein Hinweis, keine
Entscheidung und kein Schritt darauf verweist.

Nach einem erneuten Import listet das Importergebnis Hinweise, deren Bewertung
sich mit den aktuellen Regeln geändert hat, mit alter und neuer Begründung und
Punktzahl; die CLI nennt die Anzahl. Deine Entscheidungen und Schritte bleiben,
wie sie waren.

Für einen Passwort-Direktlink sind `password_url`, `password_source` und
`password_verified` erforderlich. Ergänze diese nur nach Prüfung einer offiziellen
Quelle. Danach lokal neu importieren bzw. `scan-imap --allow-imap --full-scan`
ausführen und den Server mit dem gleichen Katalog neu starten.

## Getrennte Profile, Fortschritt im Zeitverlauf und Berichte

`--profile NAME` nutzt ein getrenntes, benanntes Profil, etwa eines für die
Arbeit und eines für private Accounts. Jedes Profil ist ein eigener Ordner neben
dem Standardprofil, mit eigener Datenbank, eigenen Postfach-Einstellungen,
Katalogergänzungen, Sicherungen und Freigaben; nichts wird geteilt oder
übergreifend gelesen. Ein zweites Dashboard läuft mit eigenem `--port`.
`argus profiles` listet nur die Namen.

Die Übersicht zeigt, wie sich deine Zahlen in der letzten Woche, im letzten
Monat und Quartal verändert haben. Dafür behält ARGUS je Tag eine Zeile mit
Zahlen (Hinweise, gefundene, bestätigte, abgeschlossene und noch offene
Accounts, Unklares, offen mit hoher Priorität), nie Namen, Adressen oder Belege,
für etwa dreizehn Monate. **Bericht ansehen** erstellt einen datensparsamen
Fortschrittsbericht: nur Zahlen oder Zahlen und eine Zeile je Account.
Anmeldeadressen kommen nur hinzu, wenn du sie ankreuzt. Der Text wird vollständig
gezeigt, bevor dein Browser ihn speichert.

```bash
python -m argus_security --profile arbeit init --email du@arbeit.example
python -m argus_security --profile arbeit serve --port 8766
python -m argus_security profiles
python -m argus_security report --text --level tasks
python -m argus_security report --level numbers --export /lokaler/pfad/argus-bericht.txt
```

## Ablaufvorlagen

„Ablaufvorlagen“ in der Arbeitsliste planen wiederkehrende Arbeit. Eine Vorlage
ist reine Daten, nie ein Skript oder Browsermakro: welche Accounts sie umfasst
(Katalogkategorien, Mindestpriorität, nur bestätigte Accounts) und was sie plant
(zur Arbeitsliste hinzufügen, ein Prüfdatum für gewählte Schritte). ARGUS bringt
zwei Vorlagen mit, eine jährliche Prüfung wichtiger Accounts und eine
Wiederherstellungsprüfung für Finanz-Accounts, und du kannst eigene speichern.
**Vorschau** nennt zuerst jeden betroffenen Account; **Vorlage anwenden** ist eine
Änderung, die du zurücknehmen kannst. Vorlagen handeln nie bei einem Anbieter.

```bash
python -m argus_security template list
python -m argus_security template preview yearly-important
python -m argus_security template apply yearly-important
```

## Adresswechsel planen

Wenn du eine Adresse aufgibst, listet „Adresswechsel planen“ unter „Postfach &
Import“ jeden Account, der sich damit anmeldet: zuerst die, von denen andere
abhängen (etwa der Postfach-Account), dann nach Priorität. Ändere die Adresse bei
jedem Anbieter selbst und markiere den Account als geändert oder übersprungen;
ARGUS ändert nichts bei Anbietern und verschiebt nie selbst die Anmeldung eines
Accounts. Der Plan notiert außerdem, dass die alte Adresse durch die neue ersetzt
wurde.

```bash
python -m argus_security move-address create alt@example.org neu@example.org
python -m argus_security move-address mark PLAN_ID github --state changed
python -m argus_security move-address list
```

## Profil sichern und wiederherstellen

ARGUS legt automatisch eine Sicherung an, bevor eine neue Version die
Profildatenbank aktualisiert, und öffnet kein Profil einer neueren Version.
Sicherungen kannst du auch selbst erstellen und wiederherstellen:

```bash
python -m argus_security backup                 # in den Ordner backups des Profils
python -m argus_security backup --output /verschluesseltes/laufwerk/argus
python -m argus_security backup --list
python -m argus_security restore /pfad/argus-backup-….zip         # zeigt, was wiederhergestellt würde
python -m argus_security restore /pfad/argus-backup-….zip --yes   # ersetzt das Profil
```

Eine Sicherung ist eine ZIP-Datei mit der Datenbank und der passwortfreien
`imap.json`. Sie ist **nicht verschlüsselt** und enthält persönliche Metadaten;
bewahre sie auf einem verschlüsselten Laufwerk auf. Dateien werden mit privaten
Rechten angelegt und nie überschrieben. Vor dem Wiederherstellen prüft ARGUS
jede Prüfsumme und die Datenbank und sichert den aktuellen Stand als weitere
Sicherung. Beende Dashboard und Scans vor dem Wiederherstellen. Freigaben im
Schlüsselbund gehören nicht zur Sicherung; geplante Scans brauchen danach
eventuell ein neues `background-imap enable`. Die neuesten fünf automatischen
Sicherungen bleiben erhalten; deine eigenen werden nie gelöscht.

## Bestehende Profile aktualisieren

Version 1.9 übernimmt den bisherigen Anbieterstand in getrennte
Account-Zuordnungen. Beende die App und sichere dein geschütztes Profil vor dem
Update. Fortschritte folgen einer eindeutigen oder ausdrücklich zugewiesenen
Adresse. Nicht eindeutig zuordenbare bisherige Fortschritte bleiben zur Prüfung
sichtbar und werden niemals auf alle anderen Accounts kopiert. Verwende das
migrierte Profil mit Version 1.9 oder neuer. Siehe die
[Migrationshinweise](docs/ACCOUNTS.md).

Version 1.7 ergänzt eine dauerhafte Sicherheits-Arbeitsliste und ein lokales
Bitwarden-Vorgangsprotokoll. Unklare Übertragungen werden vor einem erneuten
Versuch geprüft. Zwei lokale Tabellen werden automatisch ergänzt; Belege und
Checklisten bleiben erhalten. Sichere dein geschütztes Datenverzeichnis vor dem
Update.

Die Versionen 1.5 und 1.6 brachten eine Free/Pro-Anzeige und Offline-Pro-Lizenzen.
Die nächste Hauptversion entfernt beides wieder, weil alle Funktionen kostenlos
bleiben. Eine übrig gebliebene `license.json` in einem alten Profil wird ignoriert
und kann gelöscht werden. Erkennung, Datenbankschema und
Account-Ergebnisse bleiben kompatibel. Version 1.4 erweitert den eingebauten
Katalog von 372 auf 527 Dienste. Bestehende Profile und Checklisten bleiben
kompatibel. Lokale Originalmails erneut importieren oder einen separat
freigegebenen `scan-imap --allow-imap --full-scan` ausführen, um die neuen Domains
auszuwerten. Dabei werden die Originalmails nicht verändert.

Beim Upgrade von Version 1.0 gelten zusätzlich die Hinweise zur erneuten
Bewertung in [Änderungen](docs/AENDERUNGEN.md).

## Tests und Projektstruktur

Das Repository enthält automatische GitHub-Actions-Prüfungen für Python
3.11–3.14 auf Linux, Unit-Tests und eine Installationsprüfung auf Windows und
macOS sowie Browser-Prüfungen auf Deutsch und Englisch. Dafür werden nur künstliche Daten verwendet, keine
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
python scripts/browser_multi_account.py --browser /usr/bin/chromium
```

Der Test erzeugt ein temporäres Demo-Profil, sperrt ausgehende Browseranfragen
und prüft beide Sprachen, Sprachwechsel, Filter, Checklisten, Export, EML-Import,
Spracherkennung und mobile Ansichten.

### Synthetischer Erkennungs-Benchmark

`python scripts/benchmark.py` schickt erfundene Nachrichten aus
`benchmarks/detection-cases.json` durch dieselbe Auswertung wie ein Import. Jeder
Fall nennt, was die Nachricht tatsächlich zeigt und was ARGUS daraus macht; wo
beides abweicht, beschreibt der Fall die Grenze (etwa gefälschte Absender, andere
Sprachen, ungewöhnliche Formulierungen). Der Bericht zählt Treffer, zur Prüfung
behaltene Nachrichten, Verfehlte und Fehlalarme. **Die Fälle sind künstlich; die
Zahlen beweisen keine Genauigkeit bei echten Postfächern.** Ein Unit-Test schlägt
fehl, wenn sich ein Ergebnis ändert, sodass eine Regeländerung Fall und
Begründung mitziehen muss. `--json` gibt den vollständigen Bericht aus.

### Fehlerberichte und Releases

`argus about` gibt aus, was ein Fehlerbericht braucht: die Versionen von ARGUS,
Python, SQLite und Schema, das System und Zahlen wie Hinweise oder Vorgänge je
Zustand. Adressen, Anbieter, Pfade oder Nachrichten zeigt es nie; ein
vorhandenes Profil wird nur gelesen, ein fehlendes nicht angelegt. Das
Fehlerformular fragt nach dieser Ausgabe und nach synthetischen Schritten; siehe
die [FAQ](docs/FAQ_DE.md).

`python scripts/release_check.py` prüft, dass Paket und beide Änderungsprotokolle
dieselbe Version nennen, dass jedes Modul, das ins Netz gehen oder ein Programm
starten kann, angegeben ist und dass der Browser-Begleiter nur `activeTab`
behält. Der Workflow „Release files“ führt die Prüfung bei einem Versions-Tag aus,
baut die Dateien und listet ihre Prüfsummen. Er braucht nur Leserechte und
veröffentlicht nichts; Releases legt der Eigentümer von Hand mit der
[Vorlage für Release-Hinweise](docs/RELEASE_NOTES_TEMPLATE.md) an, die neue
Verbindungen und Rechte immer nennt. Siehe [Veröffentlichung](docs/PUBLISHING.md).

| Datei | Zweck |
|---|---|
| `argus_security/analysis.py` | Lokale MIME-Auswertung und Erkennungsregeln |
| `argus_security/data/providers.json` | Erweiterbarer Katalog |
| `argus_security/i18n.py`, `data/translations.json` | Lokale Deutsch/Englisch-Texte |
| `argus_security/store.py` | SQLite und Statuspersistenz |
| `argus_security/instances.py` | Stabile Account-Zuordnungen und vorsichtige Profilübernahme |
| `argus_security/imap_client.py` | TLS-IMAP, PEEK, Wiederaufnahme |
| `argus_security/background.py` | Ausdrücklich aktivierter Keyring-gestützter inkrementeller IMAP-Zeitplan |
| `argus_security/discovery.py` | Ausdrücklich aktivierte MX-Hinweise |
| `argus_security/bitwarden.py` | Offizielles Metadaten-Importformat |
| `argus_security/server.py`, `web/` | Lokales Dashboard |
| `argus_security/cli.py` | Befehlszeile (`argus`), Standardprofil und dessen einmalige Verschiebung |
| `argus_security/scan.py` | EML-, mbox- und Maildir-Importe sowie die künstliche Demo |
| `argus_security/registry.py` | Strenge Katalogprüfung, Domainabgleich und gemeinsam genutzte Versanddienste |
| `argus_security/catalog.py` | Eigene Katalogergänzungen des Profils |
| `argus_security/states.py`, `changes.py` | Getrennte Account-Zustände (ADR-0001), Änderungsprotokoll und Rückgängig |
| `argus_security/review.py` | Unklares, ausgeblendete Absenderdomains und Adressnotizen |
| `argus_security/summary.py`, `guidance.py` | Ergebniszusammenfassung, nächste Aufgabe und Hinweise zum nächsten Schritt |
| `argus_security/digest.py` | Neues seit der letzten Durchsicht und Zusammenfassung beim Wiederkommen |
| `argus_security/identity.py` | Bestätigte Anmelde- und Postfachbeziehungen und begründete Prioritäten |
| `argus_security/sessions.py`, `reviews.py` | Kurze Arbeitssitzungen mit Bericht und die Prüfregel |
| `argus_security/jobs.py` | Gemeinsame Vorgangszustände, globale Pause und minimales Aktivitätsprotokoll |
| `argus_security/imports.py` | Index verarbeiteter Nachrichten, Importbudget und Fortsetzen |
| `argus_security/watch.py` | Eng begrenzte, freigegebene Überwachung eines Exportordners |
| `argus_security/profiles.py`, `history.py`, `reports.py` | Benannte Profile, tägliche Zahlen und datensparsame Berichte |
| `argus_security/moves.py` | Geordnete, manuelle Pläne für den Umzug von Accounts auf eine andere eigene Adresse |
| `argus_security/templates.py` | Deklarative Ablaufvorlagen mit Vorschau |
| `argus_security/coverage.py` | Was Importe abdecken: Quellen, Zeitraum und Lücken |
| `argus_security/about.py` | Versionen, System und Zahlen für Fehlerberichte, nie Inhalte |
| `argus_security/backup.py` | Lokale Profilsicherungen und Wiederherstellung |
| `argus_security/workflow.py` | Lokale Sicherheits-Arbeitsliste und geführter nächster Schritt |
| `argus_security/handoffs.py` | Dauerhaftes Journal für Bitwarden-Übertragungen |
| `argus_security/mailbox_lease.py` | Eine Postfachsitzung pro Profil über Prozesse hinweg |
| `argus_security/errors.py` | Feste, übersetzbare Meldungen, die das Dashboard zeigen darf |
| `account_finder/` | Veralteter Alias für `python -m account_finder` und `account-finder` |
| `tests/` | Automatisierte Regressionstests |
| `scripts/benchmark.py`, `benchmarks/` | Synthetischer Erkennungs-Benchmark |
| `scripts/release_check.py` | Release-Prüfung: Versionen, angegebene Verbindungen und Rechte, Prüfsummen |
| `browser-companion/` | Minimaler entpackter Chromium-Begleiter für Domain- und Einstellungslinks |
| [Katalogrichtlinie](docs/KATALOG.md) | Umfang, Qualitätsmaßstäbe und neue Dienste vorschlagen |
| [Veröffentlichungs-Checkliste](docs/PUBLISHING.md) | Schritte, die der Inhaber vor der Veröffentlichung selbst prüft |
| [Produktstrategie](docs/strategy/README.md) | Gesamtplan für Funktionen und sichere Automatisierung, mit Umsetzungsstand |
| [Technischer Plan](docs/PLAN_DE.md) | Reihenfolge und Architektur |
| [Sicherheitsmodell](docs/SICHERHEIT.md) | Datenschutz, Grenzen und Schutzmaßnahmen |
| [Datenschutzerklärung](PRIVACY.md) | Was die lokale App verarbeitet und wann sie sich verbindet |
| [Hilfe](SUPPORT.md) | Discussions, Issues und sichere Meldewege |
| [Prüfbericht](docs/PRUEFBERICHT.md) | Tatsächlich ausgeführte Prüfungen |
| [Offizielle Quellen](docs/QUELLEN.md) | Bitwarden, Passwortlinks und Mailanbieter |

Die App ist für den eigenen Rechner gedacht. Eine Ausführung in einer entfernten
Entwicklungsumgebung verarbeitet Daten auf **diesem entfernten Rechner** und ist
daher für echte Maildaten nicht „lokal auf deinem Gerät“. Nutze hier nur die Demo
und installiere die Anwendung auf deinem eigenen Rechner, bevor du echte Mails
oder Zugangsdaten verwendest. Nicht ungeschützt ins Internet veröffentlichen.
