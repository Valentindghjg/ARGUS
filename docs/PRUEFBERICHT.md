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
