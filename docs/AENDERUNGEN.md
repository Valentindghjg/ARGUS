# Änderungen – Version 1.6

[English change log](CHANGELOG.md) · [Deutsche Anleitung](../README_DE.md)

- Ed25519-signierte Offline-Prüfung und lokale Aktivierung von Pro-Lizenzen
  ergänzt. Ohne eingebauten Herausgeber-Öffentlichkeitsschlüssel bleibt jede
  Installation Free und kann keine beliebige Datei freischalten.
- Herausgeberwerkzeuge für Schlüsselgenerierung und Lizenz-Ausstellung sowie eine
  technische Dokumentation für den getrennten Zahlungs-/Webhook-Dienst ergänzt.
- Weiterhin kein Checkout, keine Zahlungsdaten, Telemetrie oder Online-Konto in
  der Anwendung. Die bisherigen Free-Funktionen bleiben erhalten.
- 101 Python-Tests und 15 Browser-Prüfgruppen verwenden ausschließlich künstliche
  Daten.

## Update von 1.1 bis 1.3

App beenden, persönliche Daten geschützt sichern, Programmdateien ersetzen und
mit demselben Datenverzeichnis und Katalog starten. Datenbankschema und
Erkennungsregeln bleiben gleich. Die Sprachwahl erfordert keinen neuen Mailimport.
Für die neuen Katalogdomains Originalmails erneut lokal importieren oder einen
IMAP-Scan ausdrücklich freigeben.

## Update von 1.0

Version 1.1 führte neue Erkennungsregeln ein. Alte Belege benötigen die
Originalnachrichten zur erneuten lokalen Bewertung; Mailtexte werden nicht als
Ergebnis gespeichert. Originaldateien erneut importieren oder einen IMAP-Scan
ausdrücklich freigeben. Checklisten und manuelle Bestätigungen bleiben erhalten.
„Unbekannt“ bedeutet nie, dass kein Account existiert.

Die vollständige Versionsgeschichte steht im englischen Änderungsprotokoll.
