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

Stand: wird mit jedem Arbeitsschritt aktualisiert, zuletzt S15 (2.3.0).

| Nr. | Priorität | Stand | Im Code |
| --- | --- | --- | --- |
| 01 | Zustände sauber trennen | **umgesetzt** | [ADR-0001](../architecture/ADR-0001-zustands-und-freigabemodell.md): getrennte Achsen, Migration mit Sicherung, drei Marken im Dashboard |
| 02 | Importergebnisse und Grenzen erklären | weitgehend | Scanstatistik mit Lücken und nächsten Schritten (F4), ehrliche Ergebniszusammenfassung (F3); Abdeckungsansicht folgt (D4) |
| 03 | Erkennungsbegründungen | **umgesetzt** | Regelmerkmale, Hinweisart, Alter, Stärke und Einschränkung je Beleg; Belegbegründung bleibt neben der Entscheidung sichtbar |
| 04 | Mehrdeutigkeiten gesammelt prüfen | **umgesetzt** | Sammelliste „Unklares“: Identitäten, Hinweise ohne Account, neue Belege nach Verwerfen, unbekannte Domains |
| 05 | Änderungen automatisch zusammenstellen | **umgesetzt** | „Neu seit…“: neue und anders bewertete Hinweise nach Account gruppiert, Unklares zuerst; Zusammenfassung beim Wiederkommen (A1, A3, A4, A7, A28) |
| 06 | Unverändertes nicht erneut vorlegen | **umgesetzt** | Revision je Hinweis und Durchsicht-Markierung; identische Neuimporte bleiben still, Importlücken bleiben sichtbar (A2) |
| 07 | Jobs, Pause, Wiederaufnahme vereinheitlichen | **umgesetzt** | gemeinsames Jobmodell für Importe, Scans, Ordnerüberwachung und Bitwarden, globale Pause, Kontrollübersicht, Fortsetzen über den Nachrichtenindex |
| 08 | Korrekturen erhalten und rückgängig machen | **umgesetzt** | Entscheidungen überstehen Neuauswertung; Protokoll und Rückgängig für Entscheidung, Schritte und Planung in Dashboard, API und CLI |
| 09 | Nächste Aufgabe begründet vorbereiten | **umgesetzt** | eine begründete nächste Aufgabe in der Übersicht (D1), geführter Ablauf, Arbeitsliste |
| 10 | Freigaben vor externen Jobs prüfen | **umgesetzt** | Zielbindung aus Host, Port, Benutzer, Anmeldeart und Ordnern; sichtbare Freigabe mit Widerruf und Vorschau; übrige externe Zugriffe je Aufruf |
| 11 | Bitwarden-Vorschau und Übergabestatus | weitgehend | Übergabejournal und Status; genaue Vorschau vor jedem Schreiben (B2) |
| 12 | Unklare Schreibausgänge blockieren | umgesetzt | Status `uncertain`, keine blinde Wiederholung, manuelle Klärung |
| 13 | Wiederkehrende lokale Importe vereinfachen | **umgesetzt** | letzte Quelle wiederholen, nur Geändertes, Budget, Fortsetzen, gezielt nachholen, Vorprüfung |
| 14 | Begrenzte Ordnerüberwachung | **umgesetzt** | ein freigegebener lokaler Ordner, nur `*.eml` direkt darin, nur mit laufendem Dashboard, sichtbar und beendbar |
| 15 | Belegten Pro-Komfortbedarf bedienen | entschieden | Alles wird als Free umgesetzt; die Lizenzgrundlage ist entfernt (S1) |

Außerdem ist F1 (einheitlicher Produktname) mit der Umbenennung auf ARGUS
umgesetzt, inklusive Migration.

## Arbeitsplan

Umgesetzt wird in der Reihenfolge des Plans: Stabilisierung, verständlicher
Free-Kern, Erkennung, lokale Automatik, Robustheit, Bitwarden, Qualität. Jeder
Schritt wird als eigener PR erst nach grüner CI gemergt. Grundlage sind die
[Entscheidungen](ENTSCHEIDUNGEN.md) des Owners.

| Schritt | Inhalt | Plan-Punkte | Stand |
| --- | --- | --- | --- |
| S0 | Entscheidungen, ADR-0001 angenommen, Arbeitsplan | – | ✅ |
| S1 | Pro-Grundlage entfernen; Laufzeit nur mit Standardbibliothek | Entscheidung | ✅ |
| S2 | CI auf Linux, Windows und macOS | Installation und Plattformen | ✅ |
| S3 | Fehler mit nächstem Schritt, Exportvorschau, präzises Produktversprechen | F4, F6, B2, G1 | ✅ |
| S4 | Profil-Sicherung und Wiederherstellung | Installation, Migration und Sicherung | ✅ |
| S5 | Zustandsmodell im Store mit Migration und Rückgängig | 01, 08, F5, B4, B5, E4 (Teil) | ✅ |
| S6 | Zustandsmodell im Dashboard | D2, A10 | ✅ |
| S7 | Drei Einstiegswege, ehrliche Ergebniszusammenfassung, klare nächste Aufgabe → **2.0.0** | F2, F3, D1, 02, 09 | ✅ (2.0.0) |
| S8 | Erkennungsbegründungen, Hinweisarten und Alter | E1, E2, 03 | ✅ |
| S9 | Mehrdeutigkeitsliste, Ausschlüsse, Alias-Beziehungen | E3, E4, A9, 04 | ✅ |
| S10 | Unbekannte Domains, eigener Katalog, Regeländerungen, Benchmark → **2.1.0** | E5, E6, G3, G5 | ✅ (2.1.0) |
| S11 | Änderungszentrale und Rückkehr-Zusammenfassung | A1–A4, A7, A28, 05, 06 | ✅ |
| S12 | Passende Checkliste, Arbeitsliste, Sitzungen, Prioritäten, Identitätskonten, Bericht → **2.2.0** | A5, A6, A8, A10, A17, A18, A20, D3, B6 | ✅ (2.2.0) |
| S13 | Jobmodell, globale Pause, Freigaben, Aktivitätsprotokoll, Kontrollübersicht | A23–A27, D5, 07, 10 | ✅ |
| S14 | Importeinstellungen, nur Geändertes, Ressourcenbudget, Fortsetzen, gezielte Fehler, große Archive | A11, A13–A16, P3, 13 | ✅ |
| S15 | Begrenzte Ordnerüberwachung → **2.3.0** | A12, 14 | ✅ (2.3.0) |
| S16 | Bitwarden: Weg ohne Tresorlesen, Duplikatschutz, Übergabebereitschaft → **2.4.0** | B1, B3, A19, 11 | offen |
| S17 | Getrennte Profile, Verlaufsanalyse, datensparsame Berichte | P1, P2, P5 | offen |
| S18 | E-Mail-Umzugsplan und Ablaufvorlagen → **2.5.0** | A21, A22, P4 | offen |
| S19 | Importabdeckung, Barrierefreiheit, Maskierung, Katalogqualität | D4, D6 | offen |
| S20 | Demoablauf, FAQ, vertrauenswürdige Releases → **2.6.0** | G2, G4, G6 | offen |
| S21 | Abschluss: Abdeckung aller Plan-Punkte | – | offen |
