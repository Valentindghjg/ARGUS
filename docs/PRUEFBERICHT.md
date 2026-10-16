# Prüfbericht – unveröffentlichte Sicherheitsreview (2026-10)

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
