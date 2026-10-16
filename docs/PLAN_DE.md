# Technischer Plan

1. **Zuerst lokale Erkennung und Dashboard:** Python 3.11+, Standardbibliothek und
   `cryptography` für die Offline-Lizenzprüfung,
   erweiterbarer JSON-Anbieterkatalog, regelbasierte EML-Auswertung, SQLite und eine
   responsive deutsche Oberfläche. Künstliche Beispieldaten in einer getrennten Demo.
2. **Danach Postfachzugriff:** EML/Maildir/mbox-Import; IMAP über TLS mit geprüften
   Zertifikaten, EXAMINE/read-only und BODY.PEEK. App-Passwort per verdeckter
   Terminaleingabe oder kurzlebiges OAuth2-Token. Keine Zugangsdaten in Konfiguration,
   HTTP-API, Logs oder Ergebnissen; nur ein ausdrücklich aktivierter geplanter Scan
   legt die Freigabe im Schlüsselbund des Betriebssystems ab (ab Version 1.8). Kein STORE, DELETE, EXPUNGE oder Passwort-Reset.
3. **Einrichtung:** optionale, ausdrücklich aktivierte MX-Abfrage ausschließlich
   für die Maildomain. MX beschreibt den Empfangsweg, nicht zwingend den IMAP-Host.
   Vorschläge müssen mit der Dokumentation des tatsächlichen Mailanbieters geprüft
   werden. Keine automatische Verbindung zu einem erratenen Host.
4. **Bewertung:** Absenderdomain mit Labelgrenzen abgleichen, Empfänger prüfen,
   HTML ohne Nachladen lesen, Anhänge und weitergeleitete Nachrichten begrenzen.
   Registrierung, Verifizierung, Passwortänderung und Anmeldung getrennt bewerten.
   Werbung, Gastbestellungen und Reset-Anforderungen sind keine Account-Beweise.
   E-Mail-Belege ergeben höchstens „Wahrscheinlich“. „Bestätigt“ erfordert die
   ausdrückliche lokale Prüfung durch den Nutzer. Scores sind Heuristiken.
5. **Bitwarden:** offizielles JSON-Importformat mit ausschließlich Metadaten und
   leerem Passwortfeld; Auswahl pro Account, separate Mappe, keine Änderung
   bestehender Tresoreinträge durch das Programm. Ab 1.6.1 kann eine entsperrte
   offizielle CLI ausgewählte passwortfreie Einträge anlegen, ab 1.16 erzeugt eine
   ausdrücklich bestätigte, nur lesende Prüfung eine Trefferübersicht. Bereits zugeordnete Einträge ausschließen. Der Nutzer erzeugt
   und speichert Passwörter ausschließlich in Bitwarden. Wiederholter Import kann
   Duplikate erzeugen; Bitwarden ersetzt bestehende Einträge dabei nicht.
6. **Schutz:** standardmäßig kein ausgehendes Netzwerk; Dashboard nur auf
   127.0.0.1, API-Token nur im Sitzungsspeicher, Origin/Host-Prüfung, CSP, keine externen
   Assets. Minimale Belegmetadaten statt Mailtexten, private Datenverzeichnisse und
   Dateirechte. Keine Garantie gegen lokale Malware; Datenträger verschlüsseln.
7. **Prüfung:** automatisierte Regressionen für falsche Treffer, Domain-Spoofing,
   MIME, Deduplizierung, Statuspersistenz, IMAP-Read-only, Fehlerpfade, Bitwarden-
   Format und lokale HTTP-Schutzmaßnahmen. Demo sowie HTTP-/Browser-Prüfung.

Die Anwendung ändert keine Website-Passwörter, erstellt keine Online-Accounts und
kann aus fehlenden Mailbelegen nicht auf das Nichtvorhandensein eines Accounts
schließen. Auch historische Belege beweisen keinen heute aktiven Account.

## Deutsch und Englisch ab Version 1.3

- Ein lokaler Übersetzungskatalog für Dashboard, CLI und Exporthinweise.
- Browsersprache als Ausgangswert, ausdrückliche Auswahl pro Browser; CLI mit
  Systemsprache oder `--language en|de` vor dem Unterbefehl.
- Technische Kennungen bleiben stabil; Übersetzungen ändern keine gespeicherten
  Belege, Checklisten oder Erkennungsregeln.
- Tests für Sprachauswahl, Zustandsbewahrung, beide E-Mail-Sprachen und leere
  Passwortfelder in beiden Exportsprachen.
