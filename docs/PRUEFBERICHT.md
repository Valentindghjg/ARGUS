# Prüfbericht – Version 1.3, 14. Oktober 2026

Geprüft auf Linux mit Python 3.12.14 und Chromium. Ausschließlich künstliche
E-Mails, Fake-IMAP und lokale Loopback-Verbindungen. Windows/macOS wurden nicht
separat ausgeführt. [Ausführlicher englischer Bericht](TEST_REPORT.md).

```text
python -m unittest discover -s tests -q
Ran 97 tests
OK
```

97 automatisierte Tests prüfen Erkennung, Katalog, Datenschutz, TLS/IMAP,
Netzwerkfreigaben, Import, Persistenz, Checklisten, API-Schutz und Bitwarden-JSON
mit leeren Passwortfeldern. Die neuen Sprachprüfungen bestätigen dieselben
Ergebnisse in Deutsch und Englisch, unveränderte gespeicherte Belege, beide
E-Mail-Sprachen, lokalisierte Hinweise, CLI und unveränderte technische Kennungen.

Der Browser-Test hat **14 Prüfgruppen** bestanden: Filter, Checklisten, Export,
Import, eigene Adressen, mobile Ansicht, Sprachwechsel in beiden Richtungen,
gespeicherte Sprachwahl, deutsche Exporthinweise, erhaltene Auswahl,
Spracherkennung in getrennten Browserprofilen, Rückfall auf Englisch und
gesperrter Browser-Speicher. Keine Seitenfehler und keine externen Browseranfragen.

Es wurden keine echten Postfächer verbunden, DNS-Abfragen für Nutzer-Domains
ausgeführt oder Bitwarden-Tresore gelesen bzw. verändert. Das fertige Archiv
wird ohne persönliche Datenverzeichnisse oder Datenbanken bereitgestellt.

[Deutsche Desktop-Vorschau](preview/dashboard-de.png) ·
[Deutsche Mobil-Vorschau](preview/mobile-de.png)
