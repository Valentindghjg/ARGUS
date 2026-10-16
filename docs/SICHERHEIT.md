# Sicherheits- und Datenschutzmodell

## Netzwerk und Freigaben

Alle Erkennungsregeln, MIME-Parsing und Ergebnisberechnungen laufen in Python auf
dem ausführenden Rechner. Es gibt weder KI-APIs noch Telemetrie, CDN-Schriften,
Remote-Icons oder automatische Anbieterabfragen. Der Scanner führt keine
Loginversuche bei katalogisierten Diensten, keine Reset-Anforderungen und keine
Passwortänderungen aus. Das Dashboard erstellt keine Online-Accounts.

`discover` ist standardmäßig offline. Ausschließlich `--allow-dns` aktiviert eine
DNS-MX-Abfrage an den Systemresolver oder die bewusst gewählte Resolver-IP. Dabei
wird nur die Maildomain übertragen. Der MX-Hinweis wird nicht automatisch als
verifizierter IMAP-Host übernommen. Ein vorgeschalteter Spamfilter kann den
eigentlichen Anbieter verdecken. Ein Null-MX bedeutet, dass die Domain keinen
Mail-Empfang erklärt. Das ersetzt keine Prüfung im Kundenkonto.

`setup-imap` speichert nur Host, Port, Benutzername, Authentifizierungsmethode und
Ordnerauswahl. `scan-imap --allow-imap` ist die ausdrückliche Freigabe für genau
diesen TLS-Host. Mit dem Mailanbieter werden notwendige Authentifizierung und
lesende IMAP-Befehle ausgetauscht. Externe Links im Mailinhalt werden nie geöffnet.
Links im Dashboard öffnen sich erst bei deinem Klick. Bitwarden-Import und
Passwortänderungen führst du selbst in den offiziellen Anwendungen aus.

## Zugangsdaten

IMAP-App-Passwort und OAuth2-Token werden verdeckt in einem interaktiven Terminal
abgefragt. Es gibt dafür keine HTTP-Endpunkte, Kommandozeilenargumente, Dateien
oder Logs. Der Scanner führt nur einen Anmeldeversuch an deinem konfigurierten
Postfach durch; fehlgeschlagene Anmeldung führt zum Abbruch, nicht zu einer
Versuchsschleife. IMAP-Debug-Ausgabe ist deaktiviert und serverseitige
Fehlermeldungen werden durch feste, nicht-sensitive Meldungen ersetzt.

Zeitgesteuerte IMAP-Scans sind standardmäßig deaktiviert. Sie lassen sich erst
nach bestehender IMAP-Konfiguration über ein interaktives Terminal aktivieren und
laufen nur, während der lokale Dashboard-Prozess geöffnet ist. Das App-Passwort
oder extern erhaltene OAuth2-Token liegt ausschließlich über das optionale Paket
`keyring` im Schlüsselbund des Betriebssystems. ARGUS besitzt keinen
Klartext-Datei-Fallback und lehnt bekannte Klartext-Keyring-Backends ab. SQLite
speichert nur einen undurchsichtigen UUID-Verweis, Intervall und sichere
Statusmetadaten. `disable` stoppt künftige Läufe; `revoke` stoppt sie zuerst und
entfernt den Schlüsselbund-Eintrag. Jeder Lauf nutzt den vorhandenen
inkrementellen TLS-/IMAP-Pfad und feste sichere Fehlermeldungen, niemals eine
Passwort-Versuchsliste.
Die Freigabe ist an ihr Ziel gebunden: `enable` zeigt einen Fingerabdruck aus
Host, Port, Benutzername, Anmeldeart und Ordnern und speichert ihn. Vor jedem
Zugriff auf den Schlüsselbund und jeder Verbindung vergleicht ein Lauf ihn mit
der aktuellen `imap.json`. Bei einer Abweichung, oder bei einem Zeitplan aus der
Zeit vor dieser Bindung, stoppen geplante Scans, bis `enable` die aktuellen
Einstellungen freigibt; die gespeicherte Freigabe geht nie an einen geänderten Host.
Eine atomare SQLite-Lease stellt sicher, dass nur ein geplanter Lauf pro Profil
gleichzeitig das Postfach öffnet. Ein veralteter Worker kann weder ein neueres
Ergebnis überschreiben noch einen deaktivierten Zeitplan wieder aktivieren. Ein
laufender Scan verlängert seine Lease zwischen zwei Nachrichten höchstens alle
15 Sekunden, sodass auch lange Läufe exklusiv bleiben. Wurde der Zeitplan
inzwischen deaktiviert, widerrufen oder ersetzt, endet der Lauf vor dem nächsten
Nachrichtenabruf, meldet sich ab und behält bereits gespeicherte Belege.
Ordner-Checkpoints werden atomar zusammengeführt. Solange Zeitpläne aktiv sind,
weist die Startmeldung des Dashboards auf mögliche Postfachverbindungen hin.
Manuelle `scan-imap`-Läufe und geplante Scans teilen sich zusätzlich eine
prozessübergreifende Postfach-Lease. So öffnet ein Profil nie zwei IMAP-Sitzungen
gleichzeitig: Ein manueller Scan wird während eines geplanten Laufs noch vor der
Passwortabfrage abgelehnt, und ein geplanter Lauf wartet auf einen manuellen.

Das Bitwarden-Hauptpasswort wird niemals abgefragt. Die Anwendung meldet sich
nicht bei Bitwarden an. Die optionale direkte Übertragung benötigt eine bereits
entsperrte offizielle Bitwarden-CLI und erstellt nur
ausdrücklich ausgewählte, passwortfreie Einträge; bestehende Tresoreinträge werden
weder gelesen noch geändert. Eine getrennte optionale Prüfung verlangt eine
zweite ausdrückliche Browserbestätigung und verwendet für jeden ausgewählten
lokalen Account `bw list items --search`. Die CLI-Antwort kann entschlüsselte
Tresorfelder im Arbeitsspeicher enthalten; ARGUS leitet sofort nur
**gefunden / möglich / nichts gefunden** mit Anzahl ab und speichert, protokolliert
oder gibt keine Eintragsnamen, Benutzernamen oder Passwörter zurück. Die
Bitwarden-Konto-Adresse ist unabhängig von den Anmeldeadressen der einzelnen
Dienste.

Die geführte Ansicht **Nächsten Account absichern** bewertet nur lokal gespeicherte
Accountdaten. Ein Start ergänzt oder setzt genau einen lokalen Arbeitslisten-Eintrag
fort. Die Bitwarden-Aktion akzeptiert nur die Kennung des aktuellen Accounts und
fordert eine zweite ausdrückliche Browserbestätigung; das Öffnen eines geprüften
Anbieterlinks schließt niemals einen Checklistenpunkt ab.

Python kann unveränderliche Strings im Arbeitsspeicher nicht zuverlässig löschen.
Zugangsdaten sind daher während der autorisierten Sitzung im Prozessspeicher;
die Anwendung verspricht kein garantiertes Memory-Zeroing. Ein Prozess mit
gleichen Benutzerrechten oder lokale Malware bleibt außerhalb des Schutzmodells.

## IMAP und lokale Originale

Nur TLS mit aktivierter Hostname- und Zertifikatsprüfung, mindestens TLS 1.2.
Kein unverschlüsselter IMAP-Port und kein Schalter zum Abschalten der Prüfung.
Eine lokale Proton Bridge mit eigener TLS-Konfiguration wird nicht automatisch
unterstützt; verwende den offiziellen Export und den lokalen Dateiimport.

Alle ausgewählten Mailboxen werden über `select(..., readonly=True)` geöffnet;
Python verwendet dafür EXAMINE. Nachrichtenabruf verwendet ausschließlich
`BODY.PEEK` mit einem Größenlimit. Es gibt keine STORE-, DELETE-, EXPUNGE-,
APPEND- oder CLOSE-Befehle. PEEK setzt keine Gelesen-Markierung. Bei Nachrichten
über 2 MiB werden maximal 64 KiB Header gelesen und die Belegstärke begrenzt.
Lokale EML-, Maildir- und mbox-Originale werden nicht verändert.

UID-Checkpoints werden erst nach lokaler Verarbeitung gespeichert. Änderung der
UIDVALIDITY löst eine erneute Prüfung aus. Abbruch vor einem Checkpoint kann einen
erneuten Abruf verursachen; die lokale Belegdatenbank dedupliziert diesen.
Die Cursor-Auswahl berücksichtigt auch Adressauswahl und Erkennungsregeln.
Neu ergänzte eigene Aliase werden daher nicht durch ältere Checkpoints verdeckt.
Schreibvorgänge prüfen die Adressauswahl atomar; ändert sie sich während des
Scans, wird dieser als unterbrochen beendet und überschreibt keine neueren
Belege mit einer Bewertung für die alte Adressauswahl.
`--full-scan` ist notwendig, wenn neue Erkennungsregeln oder Katalogdomains auch
auf bereits gelesene Mails angewendet werden sollen.

## Gespeicherte Ergebnisse

SQLite enthält Anbieter-ID, die eigene Anmeldeadresse soweit aus To-Headern
bekannt oder ausdrücklich zugeordnet, Absenderdomain, Hinweisart, Heuristikscore,
Datum, Quellformat, SHA-256-Fingerabdruck und Arbeitsstatus. Kein Mailtext, kein
Betreff, kein Anhang, keine Mail-Links, kein Authentifizierungstoken und kein
Passwort werden als Beleg gespeichert. Unbekannte Domains werden als ungeprüfte
Kandidaten mit leerer offizieller Website aufgeführt.

Erkennungsstände sind versioniert. Belege aus älteren Regeln werden bis zur
erneuten Auswertung nicht als aktuelle wahrscheinliche Accounts behandelt.
Manuelle Bestätigungen und Checklisten bleiben erhalten. Die erneute Auswertung
aktualisiert denselben Fingerabdruck; sie kann einen früheren automatischen Beleg
entfernen, wenn die Originalnachricht nach aktuellen Regeln keinen Hinweis mehr
liefert. Das betrifft ausschließlich lokale Belegmetadaten, keine Mailoriginale.
Die Scan-Statistik enthält Zähler für neue, aktualisierte und entfernte Belege,
Duplikate, Fehler, übersprungene Dateien und Header-Auswertungen; keine Mailtexte
oder Fehlermeldungen des Anbieters.

Eigene Datenverzeichnisse erhalten auf POSIX-Systemen 0700, Datenbank, Konfiguration
und CLI-Exportdateien 0600. Bestehende Exportdateien werden nicht überschrieben.
Dateirechte unter Windows richten sich nach deinem Benutzerkonto und dessen ACLs.
Die Datenbank ist **nicht anwendungsseitig verschlüsselt**. Verwende
Datenträgerverschlüsselung wie FileVault, BitLocker oder LUKS und sichere Backups.
Browser-Downloads haben die Rechte deines Downloadverzeichnisses und können in
Cloud-Backups geraten. Wähle ein lokales, geschütztes Verzeichnis.

## Dashboard

Der HTTP-Server bindet ausschließlich 127.0.0.1. Jeder Start erzeugt ein neues,
nur im Prozess und in der aktiven Browserseite gehaltenes API-Token. Es wird
nicht in URLs, Local Storage oder Logs geschrieben. Die lokale Startseite
übergibt es dem Browser; alle API-Aufrufe benötigen einen Bearer-Header.
Host-/Origin-Prüfung, fehlende CORS-Freigabe, Content Security Policy,
Frame-Schutz und `no-store` begrenzen browserbasierte Angriffe. Dynamische Daten
werden mit `textContent` eingefügt. Passwortlinks stammen ausschließlich aus dem
validierten Katalog, nie aus Mails. Fehlerantworten enthalten nur feste,
übersetzbare Regelmeldungen (etwa eine Anmeldeadresse, die bereits zu einem
anderen Account gehört); Ausnahme-, Server-, Pfad- und Tresordetails bleiben
allgemein.

Der optionale Chromium-Browser-Begleiter ist eine entpackte Manifest-V3-Erweiterung
mit ausschließlich der Berechtigung `activeTab`. Beim Öffnen des Popups liest sie
die URL des aktiven Tabs lokal, gleicht nur den Hostnamen mit einem gebündelten
öffentlichen Katalog ab und kann einen bereits verifizierten Einstellungslink
kopieren oder öffnen. Sie hat keine Host-Berechtigungen, Content-Skripte,
Hintergrund-Worker, Native Messaging, Netzwerkzugriffe oder Zugriff auf
Seiteninhalt, Formulare, Cookies, Passwörter, Verlauf, Tokens, E-Mails oder
Bitwarden. Ein Webseitenbesuch ist niemals ein Account-Beleg.

Andere lokale Prozesse können wie dein Browser die Startseite abrufen. Dieses
Programm ist eine Einzelbenutzer-Anwendung und schützt nicht vor anderen
unvertrauenswürdigen Nutzern auf demselben Rechner. Stelle es nicht als öffentlichen
Webservice bereit und leite den Port nicht ungeschützt ins Netzwerk weiter.

## Aussagekraft und Grenzen

Absenderheaders können gefälscht werden; aus einem importierten
Authentication-Results-Header wird keine sichere DKIM-Bestätigung abgeleitet.
E-Mail-Belege erzeugen daher höchstens „Wahrscheinlich“. Nur deine ausdrückliche
Prüfung setzt „Bestätigt“. Scores sind feste Regelwerte, keine statistisch
kalibrierten Wahrscheinlichkeiten. Historische Hinweise beweisen keinen aktuell
aktiven Account. Unbekannt bedeutet niemals „existiert nicht“.

Gastbestellungen, Newsletter und Reset-Anforderungen bleiben unbekannt. Konten
ohne Mails, gelöschte Nachrichten, Telefonnummer-Registrierungen, andere Aliase,
andere Postfächer und SSO können fehlen. Gemeinsame Produktfamilien können Mails
über die Domain des zentralen Identitätsanbieters versenden; ein Xbox-Konto kann
beispielsweise ausschließlich Microsoft-Hinweise hinterlassen. Accounts beim
selben Anbieter erhalten getrennte stabile Kennungen, Checklisten und
Übertragungsprotokolle. Nur aktuelle starke Belege an genau eine konfigurierte
eigene Adresse werden einer entsprechenden Zuordnung zugeteilt. Mehrdeutige,
weitergeleitete und schwache Hinweise bleiben beim Dienst. Unterschiedliche
Adressen können Aliase oder geänderte Adressen betreffen; separate Accounts
erfordern weiterhin deine Prüfung. Manuell bezeichnete Accounts mit derselben
Adresse erben keine automatischen Empfängerbelege. Alte Fortschritte werden
vorsichtig zugeordnet und nie auf alle neuen Zuordnungen kopiert. Ungeklärte
Alteinträge benötigen vor Export und Abschluss eine Prüfung. Siehe die
[Account-Anleitung](ACCOUNTS.md).

Der automatische Katalogabgleich arbeitet mit kuratierten Domains und einem
begrenzten Satz deutscher/englischer Regeln. Weitere Versanddomains und eigene
Dienste müssen ergänzt werden. Überprüfe Domains anhand offizieller Quellen und
vertraue nicht ungeprüft der Markenbezeichnung in einer E-Mail.

## Sprachauswahl und Browser-Speicher

Version 1.3 bietet Deutsch und Englisch. Übersetzungskatalog und Verarbeitung
liegen lokal; kein externer Übersetzungsdienst wird aufgerufen. Im Local Storage
steht nur die Sprachwahl `de` oder `en`. Das lokale Sitzungstoken, Account-Daten,
Mailtexte und Zugangsdaten werden dort nicht gespeichert. Gespeicherte Belege und
Erkennungsregeln werden beim Sprachwechsel nicht verändert.

Die App ist für einen einzelnen Nutzer auf seinem eigenen Computer gedacht.
Die Sprachauswahl macht sie nicht zu einem Dienst mit getrennten Benutzerkonten.
