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

Die vollständige Versionsgeschichte steht im englischen Änderungsprotokoll.
