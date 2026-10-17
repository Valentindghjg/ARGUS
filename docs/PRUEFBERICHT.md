# Prüfbericht – Version 2.7.0 (noch ohne Tag)

Dauerhafte Abdeckung: **403 Python-Tests**. Ein neuer Test lässt alle Import-Jobs
aus einer verkürzten Jobliste fallen und prüft, dass Läufe und Nachrichten
weiter zählen, dass eine unverändert erneut gelesene Nachricht einmal zählt und
dass andere Jobarten keine Summen hinterlassen.

# Prüfbericht – Version 2.6.1 (Korrekturen aus dem Review, noch ohne Tag)

Review-Korrekturen, Teil 1: **359 Python-Tests**. Neue Regressionstests
reproduzieren jeden behobenen Fund zuerst: ein Stapel über der Protokollgrenze,
Rückgängig für Anmeldeart und Entscheidung, Wiederherstellen und danach
Rückgängig, wiederverwendete Hinweisnummern, stille Neuimporte, ältere Belege,
der lokale Kalendertag westlich von UTC, die Wiederherstellung aus der ältesten
automatischen Sicherung, ein beschädigtes Profil, eine neuere Sicherung,
Katalogergänzungen in Sicherungen und ein gewählter Sicherungsordner. Ein
Migrationsrennen mit drei Prozessen lief 90-mal ohne Fehler.

Review-Korrekturen, Teil 2: **367 Python-Tests**. Neue Regressionstests prüfen
eine eigene Ergänzung, die ein neuerer Katalog abdeckt, eine Subdomain als
Ergänzung, das Verschieben neben gleichen Positionen samt Rückgängig,
ausgeblendete Domains und benannte Geschwister-Accounts in „Neu seit…“, einen
abgelehnten Single-Sign-on-Account, das Entfernen eines fälligen Prüfdatums und
eine Ablehnung im Sitzungsbericht.

Review-Korrekturen, Teil 3: **378 Python-Tests**. Neue Regressionstests prüfen
eine Nachricht, die den Parser stört, eine unlesbare Datei, `.EML`-Namen, Limits,
die nur neue Arbeit zählen und bei exakter Passung abschließen, den abgelehnten
Vollscan mit Limit, die Abdeckungszahlen, den Planerstart sowie Durchgänge der
Ordnerüberwachung, die scheitern, mittendrin beendet werden, auf eine geänderte
Adressliste treffen oder einen zu großen Ordner finden. Die Reproduktionsskripte
des Prüfers zeigen jetzt das korrigierte Verhalten.

Review-Korrekturen, Teil 4: **388 Python-Tests**. Neue Regressionstests prüfen
zwei gleichzeitige Downloads, eine Datei, die sich nicht schreiben lässt,
„Schon in deinem Tresor“ für unbekannte, abgelehnte und heruntergeladene
Accounts, das Journal im Terminal, die Windows-Suche nach `bw.exe`, einen
Umzugsplan neben einer vorhandenen Adressnotiz, reservierte und vertippte
Profilnamen sowie `about`/`profiles` neben einem Ordner aus der Zeit vor der
Umbenennung.

Review-Korrekturen, Teil 5: **391 Python-Tests** und **44 Browser-Prüfgruppen**.
Neue Tests prüfen eine Vorlage, deren Accounts sich nach der Vorschau geändert
haben, zweimal „Als gesehen markieren“, eine belegte Datenbank bei einer
GET-Anfrage und tief verschachteltes JSON. Der Browser behält eine
ungespeicherte Prüfregel-Auswahl über eine Aktualisierung und prüft, dass der
maskierte Account-Dialog keine Adresse zeigt und einen zugänglichen Namen hat.

Review-Korrekturen, Teil 6: **402 Python-Tests**. Neue Tests prüfen jede
Importform und jeden `os`-Prozessaufruf in der Release-Prüfung, eine neue
Fähigkeit des Browser-Begleiters, JSON auf stdout mit Fortschritt auf stderr,
eine vertippte Quelle und ein falsches Format, einen Retry, der an seinem Limit
endet, die Demo außerhalb des Standardprofils, ungültige Ports, fehlende Dateien
ohne Pfade, `setup-imap` ohne Terminal oder mit vorhandenen Einstellungen, die
Prüfregel, die ihren anderen Teil behält, und deutsche JSON-Texte.

# Prüfbericht – Version 2.6.0 (Qualität und Vertrauen, noch ohne Tag)

Schritt S19: **336 Python-Tests** und **42 Browser-Prüfgruppen**. Neue Tests
prüfen die Abdeckung (Quellen, Zeitraum, Monate ohne Hinweis, Adressen ohne
Hinweis, keine Gesamtquote) und die Regeln der Katalogqualität. Der Browser
maskiert Adressen und hebt das wieder auf, prüft die Markierung der aktuellen
Seite, die Abdeckung, dass jede sichtbare Schaltfläche und jedes Feld einen
zugänglichen Namen hat und dass der Sprunglink zuerst kommt.

Schritt S20: **343 Python-Tests** und **43 Browser-Prüfgruppen**. Neue Tests
prüfen die Release-Prüfung (Versionen, angegebene Verbindungen und Rechte, die
Vorlage für Release-Hinweise, Prüfsummen, ein Workflow, der nur liest),
`argus about` (Zahlen ohne Adressen, Pfade oder Anbieter; die Datenbank bleibt
byte-gleich; ein fehlendes Profil wird nicht angelegt) und das Fehlerformular.
Der Browser folgt den fünf Schritten des Demo-Rundgangs und prüft, dass das
Berichtsfeld den Fokus erhält.

Schritt S21: **344 Python-Tests** und **43 Browser-Prüfgruppen**. Ein neuer
Test prüft, dass jeder relative Markdown-Link in den README-Dateien, `docs/` und
`.github/` auf eine vorhandene Datei zeigt. Die Vorschaubilder wurden aus der
synthetischen Demo neu erzeugt und auf Desktop und Mobil in beiden Sprachen
angesehen.

# Prüfbericht – Version 2.5.0 (frühere Pro-Funktionen, noch ohne Tag)

Schritt S17: **326 Python-Tests** und **39 Browser-Prüfgruppen**. Neue Tests
prüfen getrennte Profilordner, die einander nie lesen, Profilnamen, den Konflikt
`--profile`/`--data-dir`, tägliche Zahlen mit Vergleichen und Bereinigung, die
Spalten der Verlaufstabelle, Berichtsstufen mit und ohne Adressen, ungültige
Kombinationen, die private Exportdatei und die Berichts-API. Der Browser zeigt
einen Fortschrittsbericht ohne Adressen in der Vorschau.

Schritt S18a: **329 Python-Tests** und **40 Browser-Prüfgruppen**. Neue Tests
prüfen die Reihenfolge mit dem Postfach-Account zuerst, Ablehnungen (gleiche,
fremde oder unbenutzte Adresse, ein zweiter offener Plan), das Markieren ohne
Änderung eines Accounts, das Schließen sowie CLI- und API-Formen. Der Browser
erstellt einen Plan, markiert einen Account und schließt ihn.

Schritt S18b: **332 Python-Tests** und **41 Browser-Prüfgruppen**. Neue Tests
prüfen mitgelieferte Vorlagen mit Treffern, Vorschau, Anwenden und Rückgängig,
die Ablehnung ohne Treffer, die Prüfung jedes Vorlagenfelds, eigene Vorlagen mit
übersprungenen nicht zutreffenden Schritten, das Löschen sowie CLI- und
API-Formen. Der Browser zeigt eine Vorlage in der Vorschau, wendet sie an und
nimmt sie zurück.

# Prüfbericht – Version 2.4.0 (Paket E, noch ohne Tag)

Schritt S16: **323 Python-Tests** und **38 Browser-Prüfgruppen**. Neue Tests
prüfen die Bereitschaft (bereit, erst prüfen, jeden sperrenden Grund),
journalgeführte Downloads in Dashboard und CLI, die einen zweiten Download und
eine CLI-Übertragung bis zur Klärung sperren, einen bestätigten Import als
„vorbereitet“, die Prüfung vorhandener Dateien und die rücknehmbare manuelle
Zuordnung über Store, CLI und API. Der Browser klärt eine unklare Übertragung,
sieht einen Download im Journal samt Freigabe und ordnet einen Account ohne
Tresor-Lesen zu und wieder zurück.

# Prüfbericht – Version 2.3.0 (Paket D, noch ohne Tag)

Schritt S13a: **301 Python-Tests** und **35 Browser-Prüfgruppen**. Neue Tests
prüfen Vorgangszustände für Importe, Fehler, Abbrüche und unterbrochene
Vorgänge, Anzahlen und rein numerische Protokolleinträge, die Pause (neue
Vorgänge abgelehnt, laufende Scans zwischen Nachrichten beendet mit erhaltenen
Hinweisen, geplante Scans nicht beansprucht, ein pausierter geplanter Lauf behält
seinen Zeitplan, Bitwarden-Übertragungen gesperrt), Aufbewahrungsgrenzen sowie
CLI- und API-Formen. Der Browser pausiert und setzt in beiden Sprachen fort und
sieht die Pause in der Übersicht.

Schritt S13b: **305 Python-Tests** und **35 Browser-Prüfgruppen**. Neue Tests
prüfen die erfasste Freigabe (Host, Ordner, Höchstmenge, Datum, kein
Benutzername), eine geänderte Ordnerauswahl, die vor jeder Schlüsselbund-Nutzung
abgelehnt und protokolliert wird, den Widerruf samt Entfernen aus dem
Schlüsselbund, die Checkpoint-Vorschau ohne Verbindung in der CLI und die
Kontroll-API, die die Freigabe zeigt und widerruft. Der Browser prüft den Bereich
„Berechtigungen“.

Schritt S14a: **310 Python-Tests** und **35 Browser-Prüfgruppen**. Neue Tests
prüfen das Erkennen am Inhalt ohne zweite Auswertung, die vollständige
Neuauswertung nach neuen Adressen oder Katalogeinträgen, ein Nachrichten- und
ein Größenbudget mit Fortsetzung über mehrere Läufe, das Fortsetzen nach einer
Unterbrechung, den Index nur aus Fingerabdrücken und die CLI-Optionen. Frühere
Tests für Neuimporte erwarten jetzt `unchanged`; Tests, die ältere gespeicherte
Hinweise nachbilden, entfernen auch den Index, weil Profile vor 2.3 keinen haben.

Schritt S14b: **314 Python-Tests** und **36 Browser-Prüfgruppen**. Neue Tests
prüfen das Merken und Wiederholen der letzten Quelle, eine fehlende Quelle, die
Ablehnung von Pfad plus `--again`, das gezielte Nachholen fehlgeschlagener
Elemente (danach keine mehr), nummerierte mbox-Elemente, die Vorprüfung ohne
Vorgänge oder Hinweise und dass das Dashboard nur die Anzahl fehlgeschlagener
Elemente sieht. Der Browser zeigt den letzten Terminal-Import mit Befehlen.

Schritt S15: **318 Python-Tests** und **37 Browser-Prüfgruppen**. Neue Tests
prüfen die Ordnerregeln (Wurzel, Benutzerordner, versteckt, fehlend, Datei,
Profil, übergeordneter Ordner des Profils, Netzwerkpfade, Verknüpfungen,
Abstand), Importe neuer Dateien nur aus dem Ordner selbst, stille Durchgänge,
unveränderte berührte Dateien, die Pause, die Grenze je Durchgang, einen
fehlenden Ordner, das Beenden mit Protokolleinträgen sowie CLI und Kontroll-API.
Der Browser zeigt die Überwachung als Berechtigung und wartenden Vorgang und
beendet sie.

# Prüfbericht – Version 2.2.0 (Paket C, noch ohne Tag)

Schritt S11: **283 Python-Tests** und **32 Browser-Prüfgruppen**. Neue Tests
prüfen neue gegenüber geänderten Hinweisen, stille identische Neuimporte, die
Gruppierung mit Unklarem zuerst, nur gezählte Werbung, Bestellungen und
Rücksetz-Anfragen, die Durchsicht-Markierung (nur vorwärts, einmal zurücknehmen,
spätere Hinweise bleiben neu, Entscheidungen unberührt), sichtbare Importlücken,
die Reihenfolge der Zusammenfassung, ältere Profile, die CLI und strenge
API-Formen. Der Browser öffnet die Zusammenfassung, markiert Änderungen als
gesehen, nimmt das in beiden Sprachen zurück und prüft, dass die Übersicht sie
danach ausblendet.

Schritt S12a: **289 Python-Tests** und **33 Browser-Prüfgruppen**. Neue Tests
prüfen Katalog-Begründungen und die eigene Wahl, Postfach- und
Anmeldebeziehungen (eigene Adressen, bestätigte Accounts, nur Single Sign-on,
keine Kreise, inaktiv nach Verwerfen, Entfernen), Identitätskonten an der Spitze
der Vorschläge mit Gründen, das Tauschen zweier Aufgaben mit Rücknahme sowie
CLI- und API-Formen. Der Browser notiert Anmelde- und Postfach-Account, liest die
Gründe und verschiebt eine Aufgabe mit Rücknahme.

Schritt S12b: **294 Python-Tests** und **34 Browser-Prüfgruppen**. Neue Tests
prüfen die Prüfregel (Eingaben, Umfang, nie ein vergangenes Datum, Monatsenden,
einmal rücknehmbares Übernehmen), Sitzungen (nur bereite Aufgaben, Größen,
Bericht aus erfassten Schritten, keine Adressen im Text, Beenden), nur bestätigte
Exportangaben sowie CLI- und API-Formen. Der Browser prüft die
Single-Sign-on-Checkliste, eine Sitzung mit Berichtsvorschau und Download und das
Übernehmen und Zurücknehmen vorgeschlagener Prüfdaten.

# Prüfbericht – Version 2.1.0 (Paket B, noch ohne Tag)

Schritt S8: **257 Python-Tests** und **28 Browser-Prüfgruppen**. Geprüft werden
Regelmerkmale für Treffer in Betreff und Text, direkte, indirekte und mehrfache
Empfänger, Newsletter, Newsletter-Anmeldungen, Weiterleitungen und unbekannte
Domains; der Snapshot zeigt Art, Alter und Merkmale, die Datenbank enthält keinen
Nachrichtentext; ältere Hinweise erhalten ihre Erklärung beim erneuten Import;
der Browser zeigt die Erklärung in beiden Sprachen.

Schritt S9: **263 Python-Tests** und **30 Browser-Prüfgruppen**. Geprüft werden
die Liste „Unklares“, Ausschlüsse (nur Domains außerhalb des Katalogs, Rückkehr
bei neuen Hinweisen, umkehrbar), Adressnotizen (nur eigene Adressen, keine
Zusammenführung), CLI und API-Formen; der Browser blendet eine Domain aus und
wieder ein und speichert und entfernt eine Notiz.

Schritt S10 (E5, E6): **268 Python-Tests** und **31 Browser-Prüfgruppen**.
Eigene Katalogergänzungen werden auf jede Ablehnung geprüft (gemeinsamer
Versanddienst, Katalogdomain, HTTP- oder fremde Website, Kategorie, Priorität,
Feldform), ohne dass Dateien zurückbleiben, außerdem private Rechte, erneutes
Laden und Regeln fürs Entfernen; Regeländerungen beim erneuten Import nennen alte
und neue Begründung, Entscheidungen bleiben. Der Browser ergänzt einen Dienst nach
einer abgelehnten Website, sieht den Hinweis zum erneuten Import und entfernt ihn.

Schritt S10 (G3, G5): **273 Python-Tests** und **31 Browser-Prüfgruppen**. Der
synthetische Benchmark (27 Fälle) muss jedes dokumentierte Ergebnis treffen, jede
Abweichung zwischen Wirklichkeit und Ergebnis begründen, nur erfundene Adressen
verwenden und sagen, dass er keine echte Genauigkeit beweist; das
Vorschlagsformular bietet genau die Kategorien des Katalogs an. Aktuelles
Ergebnis im künstlichen Satz: von 15 echten Accounts zählen 10 als
wahrscheinlich, 3 bleiben zur Prüfung, 2 werden verfehlt (dokumentierte
Grenzen); von 7 Nicht-Accounts ist 1 ein Fehlalarm (gefälschter Absender,
dokumentierte Grenze).

# Prüfbericht – Version 2.0.0 (Paket A, noch ohne Tag)

Die Änderungen der Sicherheitsreview bestehen **208 Python-Tests** (vorher 166)
und **24 Chromium-Prüfgruppen**, ohne Seitenfehler und ohne externe
Browseranfragen.

Masterplan-Schritt S1 hat den Lizenzcode samt Tests und die Prüfung der Seite
„Editionen“ entfernt. Seitdem: **206 Python-Tests** und **23 Browser-Prüfgruppen**.
Neue Repository-Tests lehnen Laufzeitabhängigkeiten außerhalb der
Standardbibliothek ab und sichern die Regel für Quelldatei-Kopfzeilen.

Schritt S3 (F4, G1): **215 Python-Tests** und **24 Browser-Prüfgruppen**. Neue
Tests prüfen Hinweise zum nächsten Schritt in CLI, API und Dashboard (beide
Sprachen), nächste Schritte nach Scans, die lokale Liste übersprungener Dateien
und eine Sperre gegen absolute Produktversprechen.

Schritt S3 (B2, F6): **221 Python-Tests** und **25 Browser-Prüfgruppen**. Die
Vorschau muss Feld für Feld den geschriebenen Einträgen entsprechen, nichts
schreiben und laut Protokoll angelegte Accounts nennen. Der Browser prüft
Vorschau, Abbrechen und Download sowie die Demo-Erklärung.

Schritt S4: **229 Python-Tests**. Sicherungen werden tatsächlich
wiederhergestellt und mit dem gesicherten Stand verglichen; beschädigte, fremde,
Pfad-ausbrechende und neuere Archive lassen das Profil unberührt; eine Sicherung
bleibt bei gleichzeitigem Schreiben konsistent; ältere Profile werden vor der
Migration einmal gesichert, eine gescheiterte Sicherung stoppt sie, neuere
Profile werden abgelehnt. Die CI sichert und stellt im Paketcheck auf Linux,
Windows und macOS wieder her.

Schritt S5 (Schema und Migration): **236 Python-Tests**. Jeder 1.x-Zustand wird
migriert und gegen die dokumentierte Abbildung geprüft; ein Abbruch mittendrin
lässt das 1.x-Profil unverändert; die automatische Sicherung stellt das
1.x-Profil wieder her, das danach zum selben Ergebnis migriert; neue Belege
ändern nur die Belegachse; jede Änderung wird je Aktion protokolliert, das
Protokoll behält ganze Vorgänge.

Schritt S5 (Entscheidungen und Rückgängig): **247 Python-Tests**. Verwerfen
blendet einen Account überall aus, ein Rückgängig stellt ihn samt
Arbeitslistenzeile wieder her; starke neue Belege lösen nur einen Hinweis aus;
Schritte und Wiedervorlagen werden geprüft und datiert; Rückgängig geht der
Reihe nach zurück, überschreibt keine späteren Änderungen und nimmt nie einen
externen Vorgang zurück; API-Formen und CLI-Befehle sind abgedeckt.

Schritt S6: **247 Python-Tests** und **26 Browser-Prüfgruppen**. Der Browser
bestätigt, verwirft mit Grund und macht über den Hinweis und den Verlauf
rückgängig, geht die geführten Schritte Entscheidung und Anmeldung durch,
schließt einen Account erst ab, wenn jeder Schritt beantwortet ist (MFA als
nicht genutzt), setzt eine Wiedervorlage und prüft beide Sprachen.

Schritt S7: **253 Python-Tests** und **28 Browser-Prüfgruppen**. Die nächste
Aufgabe folgt der dokumentierten Reihenfolge (Import, unterbrochener Import,
Identitäten, unklare Übertragung, fällige Wiedervorlage, Arbeitsliste,
entscheiden, absichern, erledigt); die Zusammenfassung zählt Unklares und
Lücken; ein neues Profil zeigt drei Einstiege; ein Test verlangt für jeden
Dashboard-Text eine deutsche Übersetzung.

Neue Simulationen verbinden einen echten lokalen Store mit einem
Fake-IMAP-Server, einem Fake-Schlüsselbund und einer simulierten Uhr. Sie prüfen:
die Verlängerung der Lease bei langen geplanten Scans, den Abbruch durch
`disable` und `revoke`, dass keine Secrets in Profildateien landen, dass fehlerhafte
Nachrichten keine Folgescans blockieren, dass mbox-Originale byte-identisch
bleiben, die Robustheit des Schedulers und die Startmeldung.

Weitere Prüfungen:

- Die Mehrkonto-Browserprüfung deckt jetzt Abbruch und Bestätigung der dauerhaften
  Adressbindung ab.
- Der Begleiter-Validator prüft alle 527 Dienste und die Kennzeichnung nur für
  HTTPS.
- Das Wheel wurde gebaut und in einer sauberen virtuellen Umgebung getestet.
- 30 000 mutierte MIME-Nachrichten lösten keinen unbehandelten Ausnahmetyp aus.
- Weitere Simulationen prüfen die einmalige Profilverschiebung (auch bei
  gleichzeitiger Verschiebung und bei einem Symlink als Altordner), den veralteten
  Befehls-Alias, die gemeinsame Postfach-Lease von manuellen und geplanten Scans,
  Bitwarden-Daten über die Standardeingabe, Regelmeldungen über die
  Loopback-API, zurückgestellte Accounts im geführten Ablauf und das Fehlen der
  Tabellen aus der Zeit vor 1.9 in neuen Profilen.
- Die Browserprüfung deckt zusätzlich die Übernahme einer gespeicherten
  Sprachwahl aus der Zeit vor der Umbenennung ab.
- Der Begleiter-Validator führt `popup.js` mit simulierten Browser-APIs auf
  Deutsch und Englisch gegen Lookalike-Domains, fremde Subdomains und
  Nicht-HTTPS-Seiten aus.
- Jede Quelldatei trägt die MPL-2.0-SPDX-Kopfzeile, und keine Übersetzung ist
  ungenutzt.
- Simulationen zur Zielbindung (Masterplan, Priorität 10) ändern jedes
  freigegebene Feld (Host, Port, Benutzername, Anmeldeart, Ordner). Danach liest
  ein geplanter Lauf keinen Schlüsselbund-Eintrag und öffnet keine Verbindung.
  Zeitpläne aus der Zeit vor der Bindung und die erneute Freigabe sind
  abgedeckt. Eine Gegenprobe am vorherigen `main` zeigte, dass das gespeicherte
  Geheimnis einen geänderten Host erreichte.

Lokal lief nur Python 3.13; GitHub Actions deckt 3.11–3.14 ab. Es wurden keine
echten Postfächer, Anbieter, Passwörter, Schlüsselbünde oder Bitwarden-Tresore
verwendet.

---

# Prüfbericht – Version 1.16.0

Die Version mit nur lesender Bitwarden-Prüfung und geführter MFA-Prüfung besteht
**166 Python-Tests** und **23 Chromium-Prüfgruppen** ohne Seitenfehler und ohne
externe Browseranfragen. Eine künstliche bereits entsperrte CLI liefert eine
Tresorantwort mit einem synthetischen Passwort; die Tests belegen, dass ARGUS nur
die Trefferübersicht zurückgibt und weder dieses Passwort noch den Sitzungswert
in sein SQLite-Profil schreibt. Loopback-Tests verlangen das genaue Datenformat
und eine eigene Bestätigung. Workflow-Tests prüfen den MFA-/Wiederherstellungs-
Schritt nach dem Anmeldetest. Die statische Begleiter-Prüfung mit 527 Diensten
besteht weiterhin. Es wurden keine echten Postfächer, Anbieter, Passwörter oder
Bitwarden-Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.15.0.

---

# Prüfbericht – Version 1.15.0

Die Version mit Kalender-Wiedervorlage besteht **163 Python-Tests** und **23
Chromium-Prüfgruppen** ohne Seitenfehler und ohne externe Browseranfragen. Neue
Workflow-Tests prüfen den zulässigen Datumsbereich und den exakten UTC-Termin.
Der Browser-Test wählt das früheste Datum im Kalender, plant es und prüft die
synthetische Zurückstellung auf Englisch und Deutsch. Die Mehrkonto-
Browserprüfung und die statische Begleiter-Prüfung mit 527 Diensten bestehen
weiterhin. Das Offline-Wheel wurde als Version 1.15.0 gebaut und in einer
sauberen temporären Umgebung installiert. Es wurden keine echten Postfächer,
Anbieter, Passwörter oder Bitwarden-Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.14.0.

---

# Prüfbericht – Version 1.14.0

Die Version mit lokaler Wiedervorlage besteht **162 Python-Tests** und **23
Chromium-Prüfgruppen** ohne Seitenfehler und ohne externe Browseranfragen. Neue
Workflow-Tests prüfen einen zukünftigen lokalen Termin, die Bereitstellung nach
Fälligkeit ohne Account-Änderung, begrenzte Eingaben und die additive Übernahme
einer älteren Arbeitslisten-Tabelle. Der Browser-Test erstellt einen künstlichen
Aufschub um einen Tag und prüft seine deutsche Anzeige. Die Mehrkonto-
Browserprüfung und die statische Begleiter-Prüfung mit 527 Diensten bestehen
weiterhin. Das Offline-Wheel wurde als Version 1.14.0 gebaut und in einer
sauberen temporären Umgebung installiert. Es wurden keine echten Postfächer,
Anbieter, Passwörter oder Bitwarden-Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.13.0.

---

# Prüfbericht – Version 1.13.0

Die Version mit prüfbarer Prioritätsplanung besteht **160 Python-Tests** und
**23 Chromium-Prüfgruppen** ohne Seitenfehler und ohne externe Browseranfragen.
Der Browser-Test prüft die Vorschau mit zehn Einträgen auf Englisch und ihre
deutsche Übersetzung, bevor eine Arbeitslisten-Aktion möglich ist. Workflow-Tests
belegen dieselben deterministischen Kandidaten wie bei der Sammelaktion ohne
Änderung des Account-Fortschritts. Die Mehrkonto-Browserprüfung und die statische
Begleiter-Prüfung mit 527 Diensten bestehen ebenfalls. Das Offline-Wheel wurde
als Version 1.13.0 gebaut und in einer sauberen temporären Umgebung installiert.
Es wurden keine echten Postfächer, Anbieter, Passwörter oder Bitwarden-Tresore
verwendet.

Der folgende Bericht dokumentiert Version 1.12.0.

---

# Prüfbericht – Version 1.12.0

Die Version mit Prioritäts-Arbeitsliste besteht **160 Python-Tests** und **23
Chromium-Prüfgruppen** ohne Seitenfehler und ohne externe Browseranfragen. Der
neue lokale API-Test akzeptiert nur exakt `{"action":"prioritize"}`. Workflow-
Tests prüfen die deterministische Reihenfolge, die Zehn-Account-Grenze, den
Erhalt bestehender Arbeitslisten-Einträge und unveränderten Account-Fortschritt.
Die statische Begleiter-Prüfung bündelt weiterhin 527 Einträge mit ausschließlich
der Berechtigung `activeTab`. Das Offline-Wheel wurde als Version 1.12.0 gebaut
und in einer sauberen temporären Umgebung installiert. Es wurden keine echten
Postfächer, Anbieter, Passwörter oder Bitwarden-Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.11.0.

---

# Prüfbericht – Version 1.11.0

Die Version mit ausdrücklichem Abschließen besteht **158 Python-Tests** und **23
Chromium-Prüfgruppen**. Der geführte Browserfall bestätigt einen nativen Dialog,
setzt nur den Prüf-Haken des aktuellen Accounts und prüft den folgenden
Bitwarden-Schritt ohne externe Browseranfragen. Es wurden keine echten Postfächer,
Anbieter, Passwörter oder Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.10.0.

---

# Prüfbericht – Version 1.10.0

Die geführte Sicherheitsversion besteht **158 Python-Tests** und **23 Chromium-
Prüfgruppen** (18 Dashboard- und fünf Account-Zuordnungsgruppen), ohne
Seitenfehler und ohne externe Browseranfragen. Die statische Begleiter-Prüfung
bündelt weiterhin 527 Einträge und behält ausschließlich die Berechtigung
`activeTab`.

Neue Fälle prüfen die deterministische lokale Prioritätsauswahl, das Fortsetzen
eines bereiten Arbeitslisten-Eintrags, unveränderte Checklisten beim Start einer
geführten Sitzung und den strengen lokalen Bitwarden-Endpunkt: Er akzeptiert nur
den aktuellen Account und eine zweite ausdrückliche Bestätigung. Der Browserfluss
prüft die Führung auf Englisch und Deutsch. Ein Offline-Wheel wurde gebaut und in
einer sauberen temporären Umgebung installiert. Es wurden keine echten Postfächer,
Anbieter, Passwörter oder Bitwarden-Tresore verwendet.

Der folgende Bericht dokumentiert Version 1.9.0.

---

# Prüfbericht – Version 1.9.0

Die Mehrkonto-Version besteht **155 Python-Tests** und **23 Chromium-
Prüfgruppen** (18 bisherige und fünf neue Gruppen für Account-Zuordnungen).
Beide Browser-Suiten melden keine Seitenfehler und keine externen Anfragen.
Die deutschen Account-Details wurden bei 390 Pixel Ansichtsbreite geprüft.

Neue Fälle prüfen eigene Checklisten, Arbeitslisten und Bitwarden-Einträge für
zwei Adressen beim selben Dienst, ausdrücklich bezeichnete Accounts mit
derselben Adresse, feste Zuordnungen, Unicode-Bezeichnungen, mehrdeutige und
veraltete Belege, Adressauswahl, isolierte Übertragungsfehler und genaue CLI-
Kennungen. Die Migration wird für eindeutige und mehrdeutige Altfortschritte,
erfolgreiche und unklare Übertragungen, Arbeitslisten, wiederholte Starts und
Transaktions-Rollback nach einem künstlichen Abbruch geprüft.

Das Wheel wurde offline gebaut und in einer getrennten temporären Umgebung
installiert; die vorhandene Kryptografie-Abhängigkeit wurde wiederverwendet.
Version, Modulimport, Demo, Account-Liste und Bericht wurden außerhalb des
Quellverzeichnisses geprüft. JavaScript-Syntax, Begleiter-Prüfung, Python-
Kompilierung und Diff-Prüfung bestehen ebenfalls. Alle Nachrichten und
Tresorantworten sind künstlich; echte Postfächer, Anbieterpasswörter und
Bitwarden-Tresore wurden nicht verwendet. Aliase und geänderte Adressen können
denselben historischen Account betreffen und erfordern weiterhin deine Prüfung.
Automatisches Zusammenführen von Accounts ist nicht implementiert.

Die folgenden Berichte dokumentieren frühere Versionen.

---

# Prüfbericht – Version 1.8.1

Die Sicherheitskorrektur für parallele Scans besteht **132 Python-Tests**, die
statische Begleiter-Prüfung, JavaScript-Syntax und den Paket-Wheel-Bau. Neue
gezielte Fälle prüfen atomare prozessübergreifende Leases, sicheren Lease-Ablauf,
die Ablehnung veralteter Abschlüsse, Deaktivierung während eines laufenden Workers
und das atomare Zusammenführen von IMAP-Ordner-Checkpoints. Alle Eingaben nutzen
künstliche Schlüsselbunde, Runner und lokale SQLite-Datenbanken.

Der folgende Bericht dokumentiert die Automatisierungsstufe 1.8.0.

---

# Prüfbericht – Version 1.8.0

Die Stufe mit Hintergrund-Scans und Browser-Begleiter besteht **128 Python-
Tests**, die vorhandenen **18 Chromium-Dashboard-Prüfgruppen**, Python-
Kompilierung, JSON-Prüfung und die isolierte statische Prüfung des Begleiters.
Der Begleiter bündelte 527 Katalogeinträge, fordert nur `activeTab` an und wurde
auf verbotenen Host-/Seiten-/Native-/Netzwerkzugriff geprüft. Der Dashboard-Test
meldete keine Seitenfehler und keine externen Browseranfragen.

Die neuen Tests nutzen einen künstlichen Betriebssystem-Schlüsselbund, einen
Fake für den inkrementellen IMAP-Lauf und ein temporäres Profil. Sie decken den
standardmäßig deaktivierten Zustand, Laufzeit-Netzwerkfreigabe, reine
Keyring-Speicherung, fehlende Geheimnisse und Selektoren im öffentlichen Status,
sicheren Fehler/Backoff, CLI-Aktivierung/Widerruf und die Zeitplanform in der
authentifizierten Loopback-Antwort ab. Es wurden kein echter Schlüsselbund,
kein Postfach, kein Anbieter, kein Bitwarden-Tresor und kein Passwort verwendet.

Der folgende Bericht dokumentiert die frühere Automatisierungsstufe 1.7.

---

# Prüfbericht – Version 1.7.0

Die erste Automatisierungsstufe besteht **119 Python-Tests**, die
JavaScript-Syntaxprüfung und **18 Browser-Prüfgruppen** in Chromium. Geprüft
wurden die deutsche und englische Arbeitsliste mit Wiederaufnahme, Pause,
Schrittanzeige, mobiler Darstellung und Prüfung unklarer Übertragungen sowie die
bestehenden Import- und Exportabläufe. Keine Seitenfehler und **keine externen
Browseranfragen**.

Das Wheel wurde ohne Netzzugriff gebaut, in einer separaten Umgebung installiert
und außerhalb des Quellcodeverzeichnisses geprüft (neue Module, Demo und Bericht).
Die vorhandene Sicherheitsabhängigkeit wurde wiederverwendet. Es wurden keine
echten Postfächer, Bitwarden-Tresore oder Anbieterpasswörter verwendet.

Neue Tests prüfen Schemaergänzung, Neustart, ausdrücklichen Abschluss, SSO und
Passkeys, gleichzeitige Vorgänge, CLI-Zeitüberschreitungen, ungültige Antworten,
teilweise erfolgreiche Aliasübertragungen, manuelle Klärung und API-Zugriffsschutz.
Eine künstliche CLI liefert die Tresorantworten. Echte Synchronisierung und
Passwortwechsel sind damit nicht geprüft. Die Funktion automatisiert die
Arbeitsführung, keine Passwortwechsel und keine zeitgesteuerten Scans.

Der folgende Bericht dokumentiert die frühere Basisversion 1.6.

---

# Prüfbericht – Version 1.6, 14. Oktober 2026

Geprüft auf Linux mit Python 3.12.14 und Chromium. Ausschließlich künstliche
E-Mails, Fake-IMAP und lokale Loopback-Verbindungen. Windows/macOS wurden nicht
separat ausgeführt. [Ausführlicher englischer Bericht](TEST_REPORT.md).

```text
python -m unittest discover -s tests -q
Ran 101 tests
OK
```

101 automatisierte Tests prüfen Erkennung, Katalog, Datenschutz, TLS/IMAP,
Netzwerkfreigaben, Import, Persistenz, Checklisten, API-Schutz und Bitwarden-JSON
mit leeren Passwortfeldern. Die neuen Sprachprüfungen bestätigen dieselben
Ergebnisse in Deutsch und Englisch, unveränderte gespeicherte Belege, beide
E-Mail-Sprachen, lokalisierte Hinweise, CLI und unveränderte technische Kennungen.

Der Browser-Test hat **15 Prüfgruppen** bestanden: lokale Free-Edition und
transparenter Pro-Status in Entwicklung ohne Checkout, Filter, Checklisten, Export, Import,
eigene Adressen, mobile Ansicht, Sprachwechsel in beiden Richtungen, gespeicherte
Sprachwahl, deutsche Exporthinweise, erhaltene Auswahl, Spracherkennung in
getrennten Browserprofilen, Rückfall auf Englisch und gesperrter Browser-Speicher.
Keine Seitenfehler und keine externen Browseranfragen.

Es wurden keine echten Postfächer verbunden, DNS-Abfragen für Nutzer-Domains
ausgeführt oder Bitwarden-Tresore gelesen bzw. verändert. Das fertige Archiv
wird ohne persönliche Datenverzeichnisse oder Datenbanken bereitgestellt.

[Deutsche Desktop-Vorschau](preview/dashboard-de.png) ·
[Deutsche Mobil-Vorschau](preview/mobile-de.png)
