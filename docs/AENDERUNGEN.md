# Änderungen – unveröffentlicht (Sicherheitsreview 2026-10)

Details: [Sicherheitsreview](SICHERHEITSREVIEW_2026-10.md) und
[Umsetzungsstand des Masterplans](strategy/README.md).

## Inkompatibel: eine kostenlose Ausgabe, nur Standardbibliothek

- Alle Funktionen sind kostenlos (Entscheidung des Owners, Masterplan-Schritt S1).
  Entfernt sind die Seite „Editionen“, `license-status`, `activate-license`,
  `POST /api/license/activate`, das Snapshot-Feld `product` und die
  Herausgeber-Skripte für Lizenzen.
- ARGUS hängt nicht mehr von `cryptography` ab und läuft mit der
  Python-Standardbibliothek. `keyring` bleibt für geplante Scans optional. Ein
  Test lehnt neue Laufzeitabhängigkeiten ab.
- Eine übrig gebliebene `license.json` in einem alten Profil wird ignoriert und
  kann gelöscht werden.

## Inkompatibel: Das Projekt heißt jetzt überall ARGUS

- Paket `argus_security` (`python -m argus_security`), Distribution
  `argus-account-security` und Befehl `argus`. `python -m account_finder` und
  `account-finder` funktionieren weiter, zeigen aber einen Hinweis, dass sie
  veraltet sind.
- Das Standardprofil wird einmalig und atomar von `~/.local/share/account-finder`
  nach `~/.local/share/argus` verschoben, mit allen Dateien und Rechten. Ein
  ausdrückliches `--data-dir` wird nie verschoben. Schlüsselbund-Einträge müssen
  nicht migriert werden.
- Neue Bitwarden-Einträge tragen das Feld `ARGUS-Account-ID`; die nur lesende
  Prüfung erkennt weiterhin `Account-Finder-ID`. Die Sprachwahl im Dashboard
  wechselt beim ersten Aufruf auf einen neuen Browser-Speicherschlüssel.
- Die interne Header-Markierung behält ihren alten Namen, weil sie Teil des
  Nachrichten-Fingerabdrucks ist.

## Plattformen

- Die CI führt die Unit-Tests und eine Installationsprüfung jetzt auch auf
  Windows und macOS aus. Browser-Prüfungen bleiben auf Linux.

## Sicherheit und Robustheit

- **Freigaben sind an ihr Ziel gebunden (Masterplan, Priorität 10).** Geplante
  IMAP-Scans speichern bei `enable` einen Fingerabdruck aus Host, Port,
  Benutzername, Anmeldeart und Ordnern. Weicht `imap.json` ab, stoppt ein Lauf,
  bevor er Schlüsselbund oder Netzwerk berührt, und wartet auf ein neues
  `enable`. Bisher erhielt ein geänderter Host die gespeicherte Freigabe.
  Zeitpläne aus früheren Versionen brauchen einmal eine neue Freigabe.
- Geplante IMAP-Scans verlängern ihre Lease zwischen Nachrichten. So bleibt auch
  ein langer Scan exklusiv. `disable`, `revoke` oder eine ersetzte Lease beenden
  einen laufenden Scan vor dem nächsten Nachrichtenabruf.
- Der Scheduler-Thread des Dashboards übersteht Datenbanksperren und defekte
  Zeitpläne. Während eines Browser-Imports startet er keinen Scan.
- Die Startmeldung des Dashboards weist auf aktivierte geplante IMAP-Scans hin.
- Das Dashboard fragt nach, bevor es eine Anmeldeadresse dauerhaft bindet. Die
  API für die direkte Bitwarden-Übertragung verlangt ausdrücklich
  `confirmed: true`.
- Der Browser-Begleiter kennzeichnet nur HTTPS-Katalogdomains und ihren
  `www.`-Host als offiziell. Bei anderen Subdomains warnt er.
- 24 fehlende deutsche Meldungen ergänzt (Lizenz-, Schlüsselbund- und
  Zeitplanfehler), dazu deutsche Texte für die 4 neuen Meldungen dieser Review. Ein Regressionstest verlangt deutschen Text für jede
  typisierte Fehlermeldung.
- Hinweis auf ablaufende OAuth2-Tokens beim Aktivieren eines Zeitplans.
- `.gitignore` schließt private Schlüsseldateien aus. Gepackt wird nur der
  öffentliche Lizenzschlüssel. Der Schlüsselgenerator verweigert private Schlüssel
  innerhalb des Repositorys.
- Die Paketmetadaten nennen `MPL-2.0` (PEP 639) und das ARGUS-Repository.
  Dependabot überwacht zusätzlich pip-Abhängigkeiten.
- Dokumentation korrigiert, die dem aktuellen Verhalten widersprach; toter Code
  entfernt.
- Manuelle `scan-imap`-Läufe und geplante Scans teilen sich eine
  prozessübergreifende Postfach-Lease; ein manueller Scan wird während eines
  geplanten Laufs noch vor der Passwortabfrage abgelehnt.
- Bitwarden-Metadaten gelangen über die Standardeingabe an `bw create item`,
  nicht mehr über die Prozessliste.
- Das Dashboard zeigt feste, konkrete Regelmeldungen (etwa eine Adresse, die
  schon zu einem anderen Account gehört) statt eines allgemeinen Fehlers; andere
  Fehler bleiben allgemein.
- Zurückgestellte Accounts werden im geführten Ablauf nicht mehr vorgeschlagen.
- Der Browser-Begleiter hat eine deutsche Oberfläche, baut seinen Katalog über
  die Prüfung der Anwendung und wird mit simulierten Browser-APIs getestet.
- Neue Profile legen die Tabellen aus der Zeit vor 1.9 nicht mehr an; ältere
  Profile werden weiterhin übernommen.
- Jede Quelldatei trägt eine MPL-2.0-SPDX-Kopfzeile; LICENSING.md umfasst Daten,
  Dokumentation und Bilder. Sicherheitsmeldungen laufen nur über die private
  Meldefunktion von GitHub.
- 22 ungenutzte Übersetzungen entfernt, mit Regressionstest; deutsche README und
  Änderungsliste vervollständigt; Werkzeugversionen in der CI festgelegt.
- End-to-End-Simulationen mit Fake-IMAP-Server, Fake-Schlüsselbund und
  simulierter Uhr ergänzt.

---

# Änderungen – Version 1.16.0

- Eine ausdrücklich bestätigte, nur lesende Prüfung für ausgewählte Accounts über
  die bereits entsperrte offizielle Bitwarden-CLI ergänzt. Sie gibt lokal nur
  **gefunden / möglich / nichts gefunden** mit Anzahl zurück; Tresornamen,
  Benutzernamen, Passwörter, CLI-Ausgaben und Sitzungen werden weder gespeichert,
  protokolliert noch angezeigt.
- Die geführte lokale Arbeitsliste enthält nach dem Anmeldetest nun die
  ausdrückliche Prüfung von MFA und Wiederherstellung. Sie speichert nur deine
  Bestätigung und kontaktiert weder Anbieter noch verändert sie Einstellungen.
- Strenge Loopback-API-, Fake-CLI- und Workflow-Regressionstests sowie englische/
  deutsche Oberfläche und Sicherheitsdokumentation ergänzt.

---

# Änderungen – Version 1.15.0

- Die Arbeitsliste enthält nun einen lokalen Kalender und **Datum planen** für
  Wiedervorlagen außerhalb der festen Optionen Morgen und eine Woche.
- Die strenge lokale Aktion akzeptiert ISO-Kalenderdaten von morgen bis maximal
  365 Tage in die Zukunft und speichert den resultierenden UTC-Termin ohne
  Netzwerkverbindung.
- Unit- und Browser-Tests für begrenzte Datumseingaben und die zugängliche
  Kalender-Steuerung ergänzt.

---

# Änderungen – Version 1.14.0

- **Morgen** und **In einer Woche** stellen einen Arbeitslisten-Eintrag bis zu
  einem lokalen Wiedervorlagetermin zurück. Ist der Termin bei geöffnetem ARGUS
  erreicht, wird der Eintrag wieder bereit. Es werden keine Benachrichtigungen
  gesendet und keine Anbieter, Postfächer oder Bitwarden kontaktiert.
- Die SQLite-Übernahme ergänzt die neue Spalte auch für bestehende lokale
  Arbeitslisten. Die lokale API akzeptiert nur einen begrenzten Zeitraum von
  1–365 Tagen.
- Workflow-, Migrations-, Loopback-API- und zweisprachige Browser-Tests für
  Aufschub und Wiedervorlage ergänzt.

---

# Änderungen – Version 1.13.0

- Vor **Prioritäts-Arbeitsliste erstellen** zeigt ARGUS nun auf Deutsch und
  Englisch die genauen lokalen Kandidaten sowie ihren nächsten Sicherheitsschritt.
- Die Vorschau verwendet dieselbe deterministische Reihenfolge und
  Zehn-Account-Grenze wie die atomare Aktion, schreibt aber keinerlei Zustand und
  kontaktiert weder Anbieter noch Bitwarden.
- Workflow- und Browser-Regressionstests für Inhalt, Übersetzung und den Ablauf
  ohne externe Anfragen ergänzt.

---

# Änderungen – Version 1.12.0

- **Prioritäts-Arbeitsliste erstellen** ergänzt: Nach einer ausdrücklichen
  Bestätigung werden bis zu zehn unvollständige gefundene Accounts in
  deterministischer Sicherheitsreihenfolge an die lokale Arbeitsliste angehängt.
  Bestehende Einträge behalten ihre Reihenfolge.
- Die Aktion hat ein enges Datenformat und ein atomares SQLite-Update. Sie ändert
  weder Checklisten noch Passwörter, Anbieter-Accounts oder Bitwarden-Einträge.
- Englische/deutsche Oberfläche sowie Regressionstests für Reihenfolge,
  Zehn-Account-Grenze, Fortschrittsisolation und die lokale API ergänzt.

---

# Änderungen – Version 1.11.0

- Für Prüfung, Passwortwechsel und Anmeldetest gibt es nun **Ich habe diesen
  Schritt erledigt**. Die Schaltfläche verlangt eine weitere lokale Bestätigung,
  speichert nur den passenden Haken beim aktuellen Account und aktualisiert den
  nächsten angezeigten Schritt.
- Browser-Regressionstest für Bestätigung und Übergang ergänzt; dabei werden
  weder Anbieter-Webseite, Passwort, Account-Geschwister noch Tresoreinträge
  verändert.

---

# Änderungen – Version 1.10.0

- **Nächsten Account absichern** ergänzt: Eine lokale, deterministische Empfehlung
  setzt bereite Arbeit fort oder nimmt genau einen unvollständigen Account mit
  höchster Priorität auf. Dabei werden weder Anbieter, Checklisten noch
  Tresoreinträge automatisch geändert.
- Eine schrittspezifische Führung zeigt nur geprüfte Passwortseiten. Die geführte
  Bitwarden-CLI-Übergabe gilt nur für den aktuellen Account und verlangt eine
  zweite ausdrückliche Browserbestätigung.
- Der Browser-Begleiter bleibt bewusst von Accounts getrennt: Ein Webseitenbesuch
  kann weiterhin keinen ARGUS-Account auswählen, bestätigen oder ändern.

---

# Änderungen – Version 1.9.0

- Getrennte stabile Account-Zuordnungen je Dienst mit eigenen Checklisten,
  Anmeldemethoden, Prioritäten, Arbeitslisten und Bitwarden-Vorgängen ergänzt.
- Starke direkte Belege werden nach Dienst und konfigurierter eigener Adresse
  gruppiert. Weitergeleitete, mehrdeutige, veraltete und schwache Hinweise bleiben
  separate Diensthinweise. Aliase und Adressänderungen erfordern deine Prüfung.
- Ausdrücklich bestätigte lokale Einträge mit Bezeichnungen ermöglichen separate
  Profile mit derselben Adresse. Fest zugeordnete Adressen können nicht samt
  Fortschritt auf eine andere Anmeldung verschoben werden. Jede Account-Auswahl
  bereitet genau einen passwortfreien Bitwarden-Eintrag vor.
- Bestehende Profile werden in einer Transaktion übernommen. Alte Fortschritte
  folgen einer eindeutigen oder ausdrücklich zugewiesenen Adresse oder bleiben
  zur Prüfung erhalten; weitere Accounts erben keine Häkchen. Arbeitslisten und
  unklare Übertragungen behalten ihre Zuordnung.
- Dashboard, Suche, Arbeitslisten, Export und Mobilansicht unterscheiden die
  Einträge auf Deutsch und Englisch. `list-accounts` zeigt die Kennungen für
  einzelne Auswahlen über die Kommandozeile.

## Update auf 1.9.0

Beende ARGUS, sichere dein geschütztes Profil und installiere die neue Version.
Die Übernahme läuft beim nächsten Start. Für diese Änderung ist kein neuer
Mailimport nötig. Verwende migrierte Profile mit Version 1.9 oder neuer;
ältere Versionen zeigen nur ihren bisherigen Anbieterstand. Siehe die
[Mehrkonto-Anleitung](ACCOUNTS.md).

---

# Änderungen – Version 1.8.1

- Atomare SQLite-Lease für geplante IMAP-Läufe ergänzt. Ein zweites Dashboard
  mit demselben Profil erkennt den laufenden Scan statt eine zweite
  Postfachverbindung zu öffnen; abgelaufene Leases werden nach Abbruch sicher
  übernommen.
- Ein später Abschluss prüft die Lease-ID und kann daher einen deaktivierten
  oder widerrufenen Zeitplan nicht wieder aktivieren oder ein neueres Ergebnis
  überschreiben.
- IMAP-UID-Checkpoints führen Ordneraktualisierungen atomar zusammen, statt die
  gesamte Cursor-Map zu ersetzen.

## Update auf 1.8.1

Die Aktualisierung ist kompatibel mit vorhandenen Profilen und benötigt keine
erneute Einrichtung. Ein laufender geplanter Scan darf beim Update abgeschlossen
werden; danach Anwendung normal mit demselben Datenverzeichnis starten.

---

# Änderungen – Version 1.8.0

- Opt-in-Zeitplanung für inkrementelle, schreibgeschützte IMAP-Scans ergänzt.
  Sie läuft nur bei geöffnetem lokalen Dashboard und nutzt vorhandene UID-
  Checkpoints, TLS, `EXAMINE` und `BODY.PEEK`.
- Die Freigabe wird nur verdeckt im Terminal abgefragt und ausschließlich im
  Schlüsselbund des Betriebssystems gespeichert. Es gibt keinen Datei-Fallback;
  Klartext-Keyring-Backends werden abgelehnt. Status, Pause und Widerruf sind
  möglich.
- Das Dashboard zeigt nur den sicheren Zeitplanstatus und akzeptiert keine
  Mailzugangsdaten. Fehler bleiben feste lokale Meldungen.
- Entpackter Chromium-Manifest-V3-Browser-Begleiter mit ausschließlich
  `activeTab` ergänzt. Webseitenbesuche sind keine Account-Belege; angezeigt
  werden nur bereits verifizierte Passwortverwaltungslinks aus dem Katalog.

## Update auf 1.8.0

Beende die Anwendung, sichere dein geschütztes Datenverzeichnis und installiere
die neue Version. Es ist keine Datenbankmigration erforderlich. Geplante Scans
sind nach dem Update deaktiviert, bis sie ausdrücklich über `background-imap
enable` eingerichtet werden. Installiere `keyring` nur, wenn du diese optionale
Funktion nutzen möchtest.

---

# Änderungen – Version 1.7.0

- Fortsetzbare deutsche und englische Sicherheits-Arbeitsliste mit Auswahl,
  Pause, Zurückstellen, Schrittanzeige und ausdrücklichem Abschluss ergänzt.
- Bitwarden-Übertragungen werden je Adresse protokolliert. Nach Fehlern oder
  Zeitüberschreitungen ist vor einem neuen Versuch eine Prüfung im Tresor nötig.
- Bereits übertragene Adressen werden bei neuen Übergaben und Exporten
  übersprungen. Teilweise erfolgreiche Übertragungen bleiben erhalten.
- Gleichzeitige Erstellungsversuche werden atomar getrennt. Die künstliche Demo
  kann keine echten Bitwarden-CLI-Übertragungen ausführen.
- 119 Python-Tests und 18 Browser-Prüfgruppen verwenden ausschließlich künstliche
  Daten. Anbieterpasswörter werden weiterhin nicht automatisch geändert.

## Update auf 1.7.0

Beende die Anwendung, sichere dein geschütztes Datenverzeichnis und installiere
die neue Version. Starte mit demselben Datenverzeichnis. Zwei zusätzliche Tabellen
werden automatisch angelegt; Belege und Checklisten bleiben erhalten. Für diese
Arbeitslistenfunktion ist kein erneuter Mailimport erforderlich.

---

# Änderungen – Version 1.6

[English change log](CHANGELOG.md) · [Deutsche Anleitung](../README_DE.md)

- Ed25519-signierte Offline-Prüfung und lokale Aktivierung von Pro-Lizenzen
  ergänzt. Ohne eingebauten Herausgeber-Öffentlichkeitsschlüssel bleibt jede
  Installation Free und kann keine beliebige Datei freischalten.
- Herausgeberwerkzeuge für Schlüsselgenerierung und Lizenz-Ausstellung sowie eine
  technische Dokumentation für den getrennten Zahlungs-/Webhook-Dienst ergänzt.
- Weiterhin kein Checkout, keine Zahlungsdaten, Telemetrie oder Online-Konto in
  der Anwendung. Die bisherigen Free-Funktionen bleiben erhalten.
- Der Quellcode der Free-Edition steht ab 1.6.0 unter MPL-2.0 (`LICENSE`,
  `LICENSING.md`); frühere Versionen hatten keine gewählte Lizenz.
- 1.6.1 ergänzt die optionale Übergabe an eine bereits entsperrte offizielle
  Bitwarden-CLI (siehe [BITWARDEN_CLI.md](BITWARDEN_CLI.md)).
- 101 Python-Tests und 15 Browser-Prüfgruppen verwenden ausschließlich künstliche
  Daten.

## Update von 1.1 bis 1.3

App beenden, persönliche Daten geschützt sichern, Programmdateien ersetzen und
mit demselben Datenverzeichnis und Katalog starten. Die Erkennungsregeln bleiben gleich; Version 1.7 ergänzt zwei lokale Tabellen. Die Sprachwahl erfordert keinen neuen Mailimport.
Für die neuen Katalogdomains Originalmails erneut lokal importieren oder einen
IMAP-Scan ausdrücklich freigeben.

## Update von 1.0

Version 1.1 führte neue Erkennungsregeln ein. Alte Belege benötigen die
Originalnachrichten zur erneuten lokalen Bewertung; Mailtexte werden nicht als
Ergebnis gespeichert. Originaldateien erneut importieren oder einen IMAP-Scan
ausdrücklich freigeben. Checklisten und manuelle Bestätigungen bleiben erhalten.
„Unbekannt“ bedeutet nie, dass kein Account existiert.

---

# Änderungen – Version 1.5.0 (14. Oktober 2026)

- Lokale Edition **Account Compass Free** (heute ARGUS Free) und eine Seite
  „Pläne“ im Dashboard mit einer transparenten, nicht erhältlichen Pro-Vorschau.
- Produktangaben sind lokal und durch Tests abgedeckt. Kein Checkout, keine
  Zahlungsdaten, keine Telemetrie, kein Online-Konto, keine Lizenzaktivierung.
- Englische und deutsche Freemium-Dokumentation sowie eine Checkliste für die
  kommerzielle Veröffentlichung. Bevor kostenpflichtige Funktionen erscheinen,
  braucht es einen echten Verkäufer, Lizenz, Rechtstexte, Zahlungsanbieter und
  ein signiertes Berechtigungsmodell.
- Bestehende Profile, Erkennung, Datenschema und Free-Funktionen bleiben unverändert.

# Änderungen – Version 1.4.0 (14. Oktober 2026)

- Katalog von 372 auf **527** Dienste erweitert. Der Katalog prüft eindeutige
  Domains und den Vorrang spezifischer Subdomains; es kamen keine
  Account-Abfragen bei Anbietern hinzu.
- Unterlagen für ein öffentliches Projekt: Katalogrichtlinie,
  Veröffentlichungs-Checkliste, Hilfe, Verhaltenskodex, Issue-Vorlagen und
  Dependabot-Konfiguration.
- Paketmetadaten nennen Projekt, unterstützte Python-Versionen und
  Repository-Adressen. Die Lizenzwahl blieb bewusst dem Inhaber überlassen.
- README für Erstnutzer neu gegliedert: Zweck, Grenzen, Update-Anleitung und
  Projektlinks.
- Bestehende Profile bleiben kompatibel. Für neue Katalogdomains Originalmails
  erneut importieren oder einen ausdrücklich freigegebenen vollständigen IMAP-Scan
  ausführen.

# Änderungen – Version 1.3.0 (14. Oktober 2026)

- Sprachauswahl im Dashboard-Kopf und in offenen Account-Checklisten;
  Browsersprache als Ausgangswert, Auswahl wird lokal gemerkt.
- Beide Sprachen für Navigation, Filter, Kategorien, Erklärungen, Checklisten,
  Datumsangaben, Importe, Einrichtung, Validierung und passwortfreie
  Bitwarden-Notizen.
- Das CLI folgt der Systemsprache; global wählbar mit `--language en|de`.
- Filter, Checklisten, Anmeldeadressen, Exportauswahl und Importfortschritt
  bleiben beim Sprachwechsel erhalten. Jeder Browser wählt unabhängig.
- Vollständige englische und deutsche Anleitungen; gemeinsamer lokaler
  Übersetzungskatalog. Keine Übersetzungsdienste, keine neuen Abhängigkeiten.
- Erkennungsversion bleibt 2; ein erneuter Import aus 1.1/1.2 ist dafür nicht nötig.
- 97 Python-Tests und 14 Browser-Prüfgruppen bestehen mit künstlichen Daten.

# Änderungen – Version 1.2.0 (14. Oktober 2026)

- Englische Oberfläche: Dashboard, Navigation, Checklisten, Filter,
  Scan-Zusammenfassungen, Fehler, Einrichtung, CLI-Eingaben und -Hilfe,
  Erklärungen, Kategorien, Bitwarden-Notizen, Beispiele und Dokumentation.
- Anzeigename **Account Compass** (heute ARGUS); Paket, Befehle, Anbieter-IDs,
  Ordner und Datenbankkennungen blieben damals kompatibel.
- Ältere deutsche Programmhinweise werden auf Englisch angezeigt, ohne
  gespeicherte Daten oder manuelle Bestätigungen zu ändern.
- Englische Datums- und Suchformate. Eigennamen und Nutzertexte bleiben erhalten.
- Die deutschen und englischen Erkennungsregeln sind unverändert. Keine neuen
  Abhängigkeiten; Profile aus 1.1 brauchen dafür keinen neuen Mailimport.
- 86 automatische Tests und acht Browserprüfungen bestehen mit künstlichen Daten.

# Änderungen – Version 1.1.0 (14. Oktober 2026)

- Eine Kontoerstellung wird nicht mehr durch einen Abmeldelink oder ein
  Newsletter-Angebot nach der Hauptnachricht verdeckt. Reine Newsletter-Anmeldungen
  bleiben „Unbekannt“.
- Mehr deutsche und englische Aktivierungs- und Bestätigungsformulierungen;
  verneinte Ereignisse werden verworfen. Betreff und Text werden nicht zu einem
  künstlichen Ereignis verbunden.
- Mehrere eigene Empfänger führen nicht zu einer willkürlichen Adresszuordnung.
- Eine erneute Auswertung aktualisiert den ursprünglichen Fingerabdruck, auch bei
  geändertem Hinweistyp oder neu katalogisierter Domain. Veraltete automatische
  Belege bleiben nicht als zweiter Hinweis bestehen; manuelle Checklisten bleiben.
- Eigene Aliasadressen über das Dashboard oder `add-email` ergänzen. Bestehende
  Aliasse setzen den Scanfortschritt nicht zurück; Demo und persönliche Profile
  bleiben getrennt.
- Dauerhafte Statistik für mehrere Dateien, Importabbruch, Ablauf verlassener
  Importsitzungen, Schutz vor parallelen Importen und erhaltene
  Bitwarden-Auswahl.
- Der Scanstatus unterscheidet Nachrichtenlimit, Unterbrechung, Fehler,
  übersprungene Nachrichten und reine Header-Auswertung. Eine geänderte
  Adressauswahl unterbricht einen laufenden Scan sicher.
- 85 automatische Tests und acht Browserprüfungen bestehen.

# Änderungen – Version 1.0.0 (13. Oktober 2026)

Katalog mit 372 Diensten, lokale Mailbelege, Dashboard und Checklisten, lokale
Dateiimporte, nur lesendes TLS-IMAP, ausdrücklich freigegebene MX-Hinweise und
passwortfreier Bitwarden-Metadatenexport. 56 automatische Tests und sechs
Browser-Prüfgruppen bestehen mit künstlichen Daten.
