# Häufige Fragen

[English](FAQ.md)

## Findet ARGUS alle meine Accounts?

Nein. ARGUS liest nur die E-Mails, die du importierst oder scannst, und sucht
darin nach Hinweisen wie Willkommens-, Anmelde- oder Passwortänderungs-Mails.
Ein Account ohne solche E-Mail bleibt unbekannt, und unbekannt heißt nicht, dass
es ihn nicht gibt. Deshalb zeigt ARGUS, was deine Importe abdecken, aber nie
einen Gesamtprozentwert.

## Ist ein Hinweis ein Beweis für einen Account?

Nein. Ein Newsletter, eine Gastbestellung oder eine Mail zum Zurücksetzen des
Passworts ist ein Hinweis, kein Account. ARGUS ordnet Accounts als bestätigt,
wahrscheinlich oder unbekannt ein und begründet jede Einordnung; du entscheidest,
was stimmt.

## Meldet sich ARGUS irgendwo an oder ändert etwas bei Anbietern?

Nein. ARGUS versucht keine Anmeldung, ändert keine Passwörter und handelt bei
keinem Anbieter. Arbeitsliste und Aufgabenvorlagen planen nur Schritte, die du
selbst ausführst.

## Braucht oder speichert ARGUS meine Passwörter?

ARGUS speichert nie Passwörter im Profil. Ein manueller IMAP-Scan fragt das
App-Passwort im Terminal ab und vergisst es danach. Ein geplanter IMAP-Scan, den
du freigibst, hält es nur im Schlüsselbund deines Betriebssystems. Bitwarden-
Exporte enthalten Metadaten wie Name, Anmeldeadresse und Links, nie Passwörter.

## Wann verbindet sich ARGUS mit dem Internet?

Nur in diesen Fällen, die du jeweils selbst startest oder freigibst:

- `scan-imap --allow-imap` oder ein freigegebener geplanter Scan liest dein
  Postfach über TLS-IMAP, nur lesend.
- `discover --allow-dns` fragt deinen DNS-Resolver nach MX-Einträgen.
- Die Bitwarden-Schritte starten die offizielle, von dir entsperrte Bitwarden-CLI,
  nach deiner Bestätigung.

Das Dashboard lauscht nur auf 127.0.0.1. Jedes Release nennt neue Verbindungen
und Berechtigungen in seinen Hinweisen; `scripts/release_check.py` schlägt fehl,
wenn ein Modul ohne solche Angabe nach außen gehen könnte.

## Wo liegen meine Daten, und wie ziehe ich sie um?

Das Standardprofil liegt in `~/.local/share/argus`, benannte Profile liegen in
`~/.local/share/argus-profiles`. `argus backup` speichert eine unverschlüsselte
Kopie, `argus restore` stellt sie auf einem anderen Rechner wieder her. Bewahre
Sicherungen privat auf.

## Kann ich alles auf einmal anhalten?

Ja. `argus automation pause` oder die Ansicht „Kontrolle“ hält geplante Scans,
die Ordnerüberwachung und andere Hintergrundarbeit an, bis du fortsetzt.

## Gibt es eine kostenpflichtige Version?

Nein. Alle Funktionen sind unter der MPL-2.0-Lizenz kostenlos. Es gibt keinen
Lizenzschlüssel, kein Konto und keinen Bezahlvorgang.

## Wie melde ich einen Fehler, ohne Daten zu teilen?

Öffne einen Fehlerbericht und füge die Ausgabe von `argus about` ein. Sie zeigt
nur Versionen, System und Zahlen, nie Adressen, Pfade oder Nachrichten.
Beschreibe die Schritte mit erfundenen Nachrichten oder mit der Demo
(`argus --data-dir .local/demo demo`). Hänge nie ein Profil, eine Datenbank,
einen Vault-Export, echte E-Mails oder Zugangsdaten an. Sicherheitsprobleme
meldest du privat, wie in [SECURITY.md](../SECURITY.md) beschrieben.
