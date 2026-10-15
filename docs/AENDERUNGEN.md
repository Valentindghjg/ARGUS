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
