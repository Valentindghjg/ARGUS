# Produktstrategie / Product strategy

*English summary:* The German master plan
[ARGUS_Gesamtplan_Produktstrategie_Automatisierung_DE.pdf](ARGUS_Gesamtplan_Produktstrategie_Automatisierung_DE.pdf)
(16 October 2026) sets the direction: clear states and reliable identities
first, then more local automation. External access and writes need separate,
target-bound approvals. Free stays a complete, safe workflow. The plan is a
strategy paper, not an implementation order. This page tracks how far the code
follows it.

## Einordnung

Der Gesamtplan ist das Ergebnis einer Produktdiskussion. Er ist **kein
Umsetzungsauftrag** und kein technisches Audit. Seine Simulationen sind
gedankliche Ablaufprüfungen; Aufwände, Funktionen und Releases sind
Vorschläge. Der Plan beruhte auf der öffentlichen Projektbeschreibung, nicht auf
dem Quellcode. Der Abgleich unten wurde gegen den Code gemacht.

Leitsatz: *ARGUS automatisiert die Vorarbeit, erklärt die Ergebnisse und hält an
den Stellen an, an denen deine Entscheidung zählt.*

## Verbindliche Grenzen aus dem Plan

- Keine automatischen Passwortänderungen, keine Resets, keine Loginserien,
  keine Umgehung von MFA oder CAPTCHA.
- ARGUS erzeugt, protokolliert und speichert keine Passwörter;
  Wiederherstellungsgeheimnisse gehören nach Bitwarden.
- Keine Mailinhalte an externe KI, keine versteckten oder unbestätigten
  Verbindungen, kein Nachladen und kein automatisches Öffnen von Links.
- Ein Hinweis bestätigt keinen Account. „Unbekannt“ heißt nie „existiert nicht“.
- Nutzerentscheidungen sind von automatischer Evidenz getrennt; externe
  Schreibaktionen sind nicht pauschal rückgängig zu machen.

**Bekannter Konflikt:** Geplante IMAP-Scans (seit 1.8) legen ein App-Passwort
oder Token im Schlüsselbund des Betriebssystems ab. Der Plan führt
unbeaufsichtigten Postfachzugriff als **offene Produktentscheidung**. Der Owner
hat am 16.10.2026 entschieden, die Funktion zu behalten. Sie wurde gehärtet,
aber nicht ausgebaut: Lease, Abbruch und Zielbindung. Sie bleibt optional; der
Hauptnutzen kommt ohne sie aus.

## Umsetzungsstand der 15 Prioritäten

Stand: 16.10.2026, nach der Sicherheitsreview und der Zielbindung.

| Nr. | Priorität | Stand | Im Code |
| --- | --- | --- | --- |
| 01 | Zustände sauber trennen | Entwurf | [ADR-0001](../architecture/ADR-0001-zustands-und-freigabemodell.md) wartet auf Freigabe |
| 02 | Importergebnisse und Grenzen erklären | teilweise | Scanstatistik mit Lücken, Header-only, Limit; noch keine Abdeckungsansicht (D4) |
| 03 | Erkennungsbegründungen | teilweise | Hinweisart, Stärke und Einschränkung pro Beleg; nach einer Bestätigung verdeckt (ADR-0001) |
| 04 | Mehrdeutigkeiten gesammelt prüfen | teilweise | Identitätsprüfung und nicht zugeordnete Belege je Account; keine Sammelliste |
| 05 | Änderungen automatisch zusammenstellen | offen | – |
| 06 | Unverändertes nicht erneut vorlegen | teilweise | Fingerabdruck-Deduplizierung und IMAP-Checkpoints; Oberfläche blendet noch nichts aus |
| 07 | Jobs, Pause, Wiederaufnahme vereinheitlichen | teilweise | Importsitzungen, Leases, Abbruch zwischen Nachrichten; gemeinsames Jobmodell in ADR-0001 |
| 08 | Korrekturen erhalten und rückgängig machen | teilweise | Entscheidungen überstehen Neuauswertung; Rückgängig in ADR-0001 |
| 09 | Nächste Aufgabe begründet vorbereiten | weitgehend | geführter Ablauf, Arbeitsliste, Prioritätsvorschau |
| 10 | Freigaben vor externen Jobs prüfen | **umgesetzt** für geplante Scans | Zielbindung aus Host, Port, Benutzer, Anmeldeart und Ordnern; allgemeines Muster in ADR-0001 |
| 11 | Bitwarden-Vorschau und Übergabestatus | teilweise | Übergabejournal und Status; keine Exportvorschau (B2) |
| 12 | Unklare Schreibausgänge blockieren | umgesetzt | Status `uncertain`, keine blinde Wiederholung, manuelle Klärung |
| 13 | Wiederkehrende lokale Importe vereinfachen | offen | – |
| 14 | Begrenzte Ordnerüberwachung | offen | – |
| 15 | Belegten Pro-Komfortbedarf bedienen | offen | nur Grundlage: signierte Offline-Lizenz |

Außerdem ist F1 (einheitlicher Produktname) mit der Umbenennung auf ARGUS
umgesetzt, inklusive Migration.

## Nächster Schritt

Der Plan beginnt mit **Phase 0**: Statusmodell, Begriffe, Aktionsarten und
Freigaben. Danach folgt **Releasepaket A**. Der Vorschlag dafür steht in
[ADR-0001](../architecture/ADR-0001-zustands-und-freigabemodell.md). Er
enthält fünf offene Fragen an den Owner und wird erst nach dessen Freigabe
umgesetzt.
