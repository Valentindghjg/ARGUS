# Änderungen – Version 2.2.0, Paket C: lokale Vorarbeit (noch ohne Tag)

## Neu seit deiner letzten Durchsicht (A1–A4, A7, A28, Prioritäten 05 und 06)

- Die neue Ansicht „Neu seit…“ zeigt nur Hinweise, die seit deiner letzten
  Durchsicht neu sind oder anders bewertet werden, nach Account gruppiert; was
  eine Entscheidung braucht, steht zuerst, Werbung, Bestellungen und
  Rücksetz-Anfragen werden nur gezählt. Dieselbe E-Mail erneut importiert bringt
  nichts zurück. Lücken des letzten Imports bleiben bis zur Durchsicht sichtbar.
- Die Übersicht zeigt eine Zusammenfassung beim Wiederkommen: zuerst
  Importlücken und unklare Bitwarden-Übertragungen, dann neue Entscheidungen,
  neue Hinweise und erreichte Prüfdaten. Ein Import endet mit einer Meldung statt
  mehrerer.
- **Als gesehen markieren** ändert keine Entscheidung und keinen Schritt und
  lässt sich einmal zurücknehmen. Neuer CLI-Befehl `whats-new [--mark-reviewed]`;
  API `POST /api/digest/seen` und `POST /api/digest/seen/undo`; Snapshot-Felder
  `changes` und `return_summary`.
- Schemaversion 5 ergänzt nach der automatischen Sicherung zwei
  Revisionsspalten bei Hinweisen. Vorher gespeicherte Hinweise gelten als
  bereits gesehen.
- Hinweise in der Accountliste und unter „Unklares“ brechen auf schmalen
  Bildschirmen jetzt um.

## Begründete Prioritäten und Identitätskonten (D3, A6, A17, B6)

- Jeder Account nennt die Gründe für seine Priorität. Eine von dir gewählte
  Priorität hat Vorrang; „Automatisch“ stellt die abgeleitete wieder her.
- Du kannst notieren, welcher bestätigte Account das Postfach einer eigenen
  Adresse hostet und mit welchem bestätigten Account sich ein
  Single-Sign-on-Account anmeldet. Solche Identitätskonten werden zu „Zuerst“
  mit sichtbarem Grund und stehen bei den Vorschlägen für die Arbeitsliste vorn;
  Beziehungen zu nicht mehr bestätigten Accounts bleiben als inaktiv sichtbar.
  ARGUS leitet diese Beziehungen nie selbst ab.
- Vorschläge für die Arbeitsliste nennen ihren Grund („Warum: …“). **Nach oben**
  und **Nach unten** tauschen zwei Aufgaben und lassen sich zurücknehmen;
  Vorschläge hinzuzufügen sortiert geplante Aufgaben nie um.
- Neue CLI-Befehle `mailbox` und `sign-in-with`; API
  `POST /api/profile/mailboxes`, `POST /api/accounts/{id}/sign-in-with` und die
  Arbeitslisten-Aktion `move`. Schemaversion 6 ergänzt zwei Tabellen nach der
  automatischen Sicherung.

## Sitzungen, Prüfdaten und Checkliste nach Anmeldeart (A5, A8, A10, A18, A20)

- Die Checkliste folgt der bestätigten Anmeldeart: Single-Sign-on- und
  Passkey-Accounts erhalten passende Schritte, und ein Account, dessen
  Anmelde-Account nicht vollständig ist, sagt das.
- **Eine Aufgabe** oder **Drei Aufgaben** startet eine kurze Sitzung ohne Frist.
  Ihr Bericht stammt aus den Schritten, die du seit dem Start erfasst hast; die
  Textdatei wird vor dem Speichern vollständig gezeigt und enthält nur
  Accountnamen und Schritte.
- Eine Prüfregel (6, 12 oder 24 Monate; wichtige oder alle abgeschlossenen
  Accounts) schlägt Prüfdaten vor. Das Übernehmen ist eine rücknehmbare
  Änderung; automatisch passiert nichts.
- Bitwarden-Notizen ergänzen die bestätigte Anmeldeart, den bestätigten
  Anmelde-Account und eine geprüfte Seite für Passwort-Einstellungen; Unbekanntes
  bleibt weg.
- Neue CLI-Befehle `session` und `review-rule`; API `POST /api/session`,
  `GET /api/session/report`, `POST /api/review-rule` und
  `POST /api/review-rule/apply`.

# Änderungen – Version 2.1.0, Paket B: erklärbare, korrigierbare Erkennung (noch ohne Tag)

## Warum ein Hinweis zählt, welche Art er hat und wie alt er ist (E1, E2, Priorität 03)

- Jeder Hinweis speichert jetzt kurze Regelmerkmale statt Nachrichtentext: wo die
  Regel traf (Betreff oder Text), ob die Mail direkt an deine Adresse ging,
  Verteiler- oder Werbemerkmale, Weiterleitung, Auswertung nur der Kopfzeilen und
  ob die Absenderdomain im Katalog steht. Der Accountdialog erklärt sie unter
  „Warum das zählt“.
- Hinweise sind nach Art (Account-Ereignis, Bestellung oder Rechnung, Werbung,
  Rücksetz-Anfrage) und Alter gekennzeichnet. Hinweise älter als zwei Jahre sind
  markiert; sind es alle, zeigt der Account, dass er sich geändert haben oder
  geschlossen sein kann. Alte Hinweise werden nie gelöscht.
- Vor dieser Version importierte Hinweise erhalten ihre Erklärung, sobald
  dieselbe Nachricht erneut importiert wird; das Profil erhält eine neue Spalte
  (Schemaversion 3, vorher die automatische Sicherung).

## Unklares in einer Liste, umkehrbare Ausschlüsse, Adressnotizen (E3, E4, A9)

- Die neue Ansicht „Unklares“ listet Accounts ohne Anmeldeadresse, Dienste mit
  Hinweisen ohne eindeutigen Account, verworfene Accounts mit neuen Belegen und
  Absenderdomains außerhalb des Katalogs.
- Absenderdomains außerhalb des Katalogs lassen sich mit Grund ausblenden; neue
  Hinweise holen sie zurück, „Wieder anzeigen“ hebt es auf. Domains im Katalog
  lassen sich nicht ausblenden; verwirf dafür den Account.
- Notizen zwischen zwei eigenen Adressen (dasselbe Postfach, ersetzt durch)
  erscheinen bei den betroffenen Accounts und führen nie Accounts zusammen.
- Neue CLI-Befehle `unclear`, `exclude` und `relate`; Schemaversion 4 ergänzt
  zwei Tabellen nach der automatischen Sicherung.

## Eigene Katalogergänzungen und sichtbare Regeländerungen (E5, E6)

- „Zu meinem Katalog hinzufügen“ unter „Unklares“ speichert einen Dienst für eine
  Absenderdomain außerhalb des Katalogs nur im Profil (`my-providers.json`,
  private Rechte). Er wird wie der eingebaute Katalog geprüft und nie online
  nachgeschlagen; gemeinsam genutzte Versanddienste werden abgelehnt und in der
  Liste gekennzeichnet.
- Eine so ergänzte Domain bleibt in der Liste, markiert als jetzt im Katalog, bis
  ihre ursprünglichen E-Mails erneut importiert sind; ein Hinweis zählt diese
  Hinweise. Ergänzungen ohne Hinweise, Entscheidungen oder Schritte lassen sich
  wieder entfernen.
- Ein erneuter Import listet Hinweise, deren Bewertung sich mit den aktuellen
  Regeln geändert hat (alte und neue Begründung und Punktzahl); die CLI nennt die
  Anzahl. Entscheidungen und Schritte bleiben.
- Neue API-Routen `POST /api/catalog` und `POST /api/catalog/remove`; der
  Snapshot enthält `catalog`, Kandidaten enthalten `shared_sender` und
  `catalog_match`.

## Dienstvorschläge und synthetischer Benchmark (G3, G5)

- Das Issue-Formular **Dienst vorschlagen** fragt nach offizieller Website,
  Kategorie, jeder Domainwurzel mit Begründung, öffentlichen Quellen mit
  Prüfdatum und vier Prüfkriterien und schließt echte E-Mails aus. Die
  Katalogrichtlinie beschreibt jetzt gemeinsam genutzte Versanddienste und die
  eigenen Ergänzungen im Dashboard.
- `python scripts/benchmark.py` schickt 27 erfundene Nachrichten durch die
  Auswertung und berichtet Treffer, zur Prüfung Behaltenes, Verfehltes,
  Fehlalarme und drei dokumentierte Grenzen (gefälschte Katalogabsender, andere
  Sprachen, ungewöhnliche Formulierungen). Das beweist keine Genauigkeit bei
  echten Postfächern; ein Test hält jedes Ergebnis dokumentiert.

# Änderungen – Version 2.0.0, Paket A: klare Zustände und kontrollierbarer Kern (noch ohne Tag)

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

## Klare nächste Schritte und ein präzises Versprechen (Masterplan F4, G1)

- Bekannte Probleme nennen jetzt einen konkreten nächsten Schritt: fehlendes
  Profil oder fehlender Quellpfad, Maildir-Aufbau, vorhandene Exportdatei,
  belegter Port oder belegte Datenbank, Schlüsselbund- und IMAP-Fehler, offene
  Bitwarden-Übertragungen und unvollständige Checklisten. Die CLI zeigt ihn als
  „Nächster Schritt:“, das Dashboard unter der Fehlermeldung. Die Hinweise sind
  feste Texte und wiederholen nie Pfade, Adressen oder Mailinhalte.
- Jedes Scan-Ergebnis nennt, was gegen seine Lücken hilft (übersprungene,
  unlesbare oder nur über Kopfzeilen ausgewertete Nachrichten, Abbrüche,
  Limits, geänderte Adressen). Die CLI gibt weiter JSON auf stdout aus und die
  Schritte auf stderr.
- Der Browser-Import listet übersprungene Dateien mit Grund (leer, keine EML,
  über 2 MiB). Die Dateinamen bleiben im Browser-Tab.
- Texte versprechen keine Vollständigkeit oder Sicherheit mehr: Aus „Bereits
  abgesichert“ wird „Checklisten erledigt“, und der Fortschrittsbereich sagt,
  dass ARGUS nicht jeden Account finden kann. Beide READMEs nennen das
  Produktversprechen; ein Test verhindert absolute Aussagen.

## Genaue Bitwarden-Vorschau und eine erklärende Demo (Masterplan B2, F6)

- Download, direkte CLI-Übertragung und der geführte Schritt zeigen zuerst genau
  die Einträge, die geschrieben werden: Name, offizielle Website, bestätigte
  Anmeldeadresse, Notiz und Zusatzfelder sowie die Accounts, die das Protokoll
  schon als angelegt führt. Die Bestätigung ersetzt die bisherige Browser-Abfrage
  und verwendet Auswahl und Sprache der Vorschau. `bitwarden-export --preview`
  zeigt dasselbe und schreibt keine Datei. Vorschau, Download und Übertragung
  teilen sich einen Codepfad.
- Die Demo hat jetzt zwei erfundene eigene Adressen und 18 Nachrichten. Eine
  Erklärung in der Übersicht zeigt Newsletter, Gastbestellung und Rücksetz-Mail
  (nur Hinweise), zwei GitHub-Accounts, Single Sign-on bei Notion und eine
  ähnlich aussehende Absenderdomain. Ein vorhandener Demo-Ordner lässt sich
  erneut laden.

## Profil sichern und wiederherstellen (Owner-Entscheidung, Plan „Installation, Migration und Sicherung“)

- `argus backup` schreibt eine private ZIP-Datei (Datenbank per
  SQLite-Online-Backup, passwortfreie `imap.json`, Manifest mit Prüfsummen);
  `--output` wählt einen Ordner, `--list` zeigt Sicherungen. Sicherungen sind
  bewusst unverschlüsselt: kein neues ARGUS-Passwortsystem.
- `argus restore DATEI` zeigt, was wiederhergestellt würde; mit `--yes` prüft es
  jede Prüfsumme und die Datenbank, sichert den aktuellen Stand und ersetzt dann
  das Profil.
- Das Profil speichert jetzt eine Schemaversion. Bevor ein neueres ARGUS eine
  ältere Datenbank ändert, legt es eine automatische Sicherung an (die neuesten
  fünf bleiben). Scheitert sie, wird nichts geändert. Ein Profil einer neueren
  ARGUS-Version wird nicht geöffnet.

## Getrennte Zustände für Belege, Entscheidung und Schritte (ADR-0001, Schemaversion 2)

- Jeder Account speichert deine Entscheidung (bestätigt, mit Datum) getrennt von
  den Sicherheitsschritten (Identität, Tresor, Passwort, Anmeldetest, MFA und
  Wiederherstellung, jeweils datiert). Der Fortschritt wird aus den Schritten
  abgeleitet. Zurückstellen gibt es nur noch in der Arbeitsliste. Neue Belege
  ändern nie eine Entscheidung oder einen Schritt.
- Ein von ARGUS ohne Passwort angelegter Tresoreintrag gilt als „vorbereitet“,
  nicht als erledigt; erledigt markierst nur du den Tresor-Schritt (B4).
- MFA und Wiederherstellung müssen erledigt oder als nicht zutreffend markiert
  sein, bevor ein Account abgeschlossen ist. In 1.x ohne MFA-Häkchen
  abgeschlossene Accounts bleiben abgeschlossen, mit MFA „nicht zutreffend“.
- Jede Änderung an Entscheidung, Schritten und Planung wird lokal protokolliert
  (Feld, alter und neuer Wert, Zeit; höchstens 1000 Einträge) als Grundlage für
  Rückgängig.
- Das Profil wird einmalig in einer Transaktion migriert, nach einer
  automatischen Sicherung. Die 1.x-Felder `classification`, `status` und
  `checklist` bleiben bis zur nächsten Hauptversion in der API, abgeleitet aus
  den neuen Feldern.

## Verwerfen, datierte Wiedervorlage und Rückgängig (ADR-0001, F5, A9, Grundlage für A10)

- Ein Account lässt sich mit Grund verwerfen (nicht meiner, kein Account,
  geschlossen). Ein verworfener Account verschwindet aus Listen, Arbeitsliste und
  Vorschlägen; neue starke Belege zeigen nur einen Hinweis und kehren deine
  Entscheidung nie um.
- Jeder Sicherheitsschritt kann ein lokales Wiedervorlagedatum tragen; fällige
  Wiedervorlagen werden je Account aufgeführt.
- Rückgängig nimmt deine letzte lokale Änderung zurück, wiederholt auch ältere.
  Ein später erneut geänderter Wert wird nie überschrieben, externe Vorgänge
  (Bitwarden-Einträge, Scans) werden nie zurückgenommen. Arbeitslisten-Aktionen
  gehören zum Verlauf.
- Neue API-Routen für Entscheidungen, Schritte, Rückgängig und Verlauf; neue
  CLI-Befehle `argus changes` und `argus undo`. Das Dashboard folgt im nächsten
  Schritt.

## Dashboard: drei Marken, Entscheidungen, datierte Schritte und Rückgängig (D2, A10, F5)

- Accountliste und Dialog zeigen drei getrennte Marken: Beleg, deine
  Entscheidung und Fortschritt. Ihre Bedeutung steht unter der Liste.
- Der Dialog fragt „Ist das dein Account?“ mit Bestätigen, Verwerfen mit Grund
  und Offen lassen und listet fünf datierte Schritte. MFA lässt sich als nicht
  angeboten oder nicht genutzt markieren, erledigte Schritte können eine lokale
  Wiedervorlage bekommen. Ein vorbereiteter Tresoreintrag ist als solcher
  gekennzeichnet. Der Knopf „Als erledigt markieren“ entfällt: Der Abschluss
  folgt aus den Schritten.
- Jede Entscheidung und jeder Schritt bietet im Hinweis „Rückgängig“ an;
  „Deine letzten Änderungen“ in der Arbeitsliste zeigt den Verlauf mit
  Rückgängig je Änderung.
- Filter trennen jetzt Beleg und Entscheidung (von dir bestätigt, nur Belege,
  keine Belege, verworfen) sowie Fortschritt (nicht begonnen, in Arbeit,
  abgeschlossen, zurückgestellt). „Zurückstellen“ plant den Account in der
  Arbeitsliste ein.

## Drei Einstiege, eine ehrliche Zusammenfassung und eine nächste Aufgabe (F2, F3, D1)

- Ein neues Profil zeigt drei getrennte Einstiege: die Demo, einen lokalen
  Import und die optionale, nur lesende Postfachverbindung. Die ersten beiden
  nutzen nie das Netzwerk.
- Die Übersicht fasst zusammen, was ARGUS weiß: verarbeitete Nachrichten,
  Hinweise, Accounts mit Belegen, deine Entscheidungen, Unklares (Identitäten,
  Hinweise ohne eindeutigen Account, unbekannte Domains) und Lücken. Sie sagt
  ausdrücklich, dass das keine vollständige Liste ist.
- Eine begründete nächste Aufgabe steht oben in der Übersicht: Import,
  unterbrochener Import, zuzuordnende Identitäten, unklare Übertragung, fällige
  Wiedervorlage, Arbeitsliste, zu entscheidende Accounts oder der nächste
  abzusichernde Account. `argus report` enthält beides.
- Die Bilder in den READMEs stammen jetzt aus der Demo dieser Version.

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
