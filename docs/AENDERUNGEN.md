# Änderungen – Version 1.3

[English change log](CHANGELOG.md) · [Deutsche Anleitung](../README_DE.md)

- Deutsch und Englisch auswählbar, auch in einer geöffneten Checkliste.
- Browsersprache als Startwert; eigene Auswahl lokal gemerkt. CLI folgt der
  Systemsprache oder `--language de|en` vor dem Unterbefehl.
- Navigation, Kategorien, Filter, Erklärungen, Checklisten, Einrichtungshinweise,
  Importstatus und Bitwarden-Hinweise in beiden Sprachen.
- Filter, Checklisten, Bestätigungen, Anmeldeadressen, Exportauswahl und laufender
  Import bleiben beim Wechsel erhalten.
- 97 Python-Tests und 14 Browser-Prüfgruppen mit ausschließlich künstlichen Daten.

## Update von 1.1 oder 1.2

App beenden, persönliche Daten geschützt sichern, Programmdateien ersetzen und
mit demselben Datenverzeichnis und Katalog starten. Datenbankschema und
Erkennungsregeln bleiben gleich. Die Sprachwahl erfordert keinen neuen Mailimport.

## Update von 1.0

Version 1.1 führte neue Erkennungsregeln ein. Alte Belege benötigen die
Originalnachrichten zur erneuten lokalen Bewertung; Mailtexte werden nicht als
Ergebnis gespeichert. Originaldateien erneut importieren oder einen IMAP-Scan
ausdrücklich freigeben. Checklisten und manuelle Bestätigungen bleiben erhalten.
„Unbekannt“ bedeutet nie, dass kein Account existiert.

Die vollständige Versionsgeschichte steht im englischen Änderungsprotokoll.
