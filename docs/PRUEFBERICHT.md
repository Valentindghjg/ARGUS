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
