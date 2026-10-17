# Produktstrategie / Product strategy

*English summary:* The German master plan
[ARGUS_Gesamtplan_Produktstrategie_Automatisierung_DE.pdf](ARGUS_Gesamtplan_Produktstrategie_Automatisierung_DE.pdf)
(16 October 2026) sets the direction: clear states and reliable identities
first, then more local automation. External access and writes need separate,
target-bound approvals. Free stays a complete, safe workflow. The plan is a
strategy paper, not an implementation order. This page tracks how far the code
follows it. Since step S21 every plan item is implemented, deliberately limited, partly
done or dropped by an owner decision; the
coverage table at the end names where.

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

Stand: abgeschlossen mit S21.

| Nr. | Priorität | Stand | Im Code |
| --- | --- | --- | --- |
| 01 | Zustände sauber trennen | **umgesetzt** | [ADR-0001](../architecture/ADR-0001-zustands-und-freigabemodell.md): getrennte Achsen, Migration mit Sicherung, drei Marken im Dashboard |
| 02 | Importergebnisse und Grenzen erklären | **umgesetzt** | Scanstatistik mit Lücken und nächsten Schritten (F4), ehrliche Ergebniszusammenfassung (F3), Abdeckung mit Quellen, Zeitraum und Lücken ohne Gesamtquote (D4) |
| 03 | Erkennungsbegründungen | **umgesetzt** | Regelmerkmale, Hinweisart, Alter, Stärke und Einschränkung je Beleg; Belegbegründung bleibt neben der Entscheidung sichtbar |
| 04 | Mehrdeutigkeiten gesammelt prüfen | **umgesetzt** | Sammelliste „Unklares“: Identitäten, Hinweise ohne Account, neue Belege nach Verwerfen, unbekannte Domains |
| 05 | Änderungen automatisch zusammenstellen | **umgesetzt** | „Neu seit…“: neue und anders bewertete Hinweise nach Account gruppiert, Unklares zuerst; Zusammenfassung beim Wiederkommen (A1, A3, A4, A7, A28) |
| 06 | Unverändertes nicht erneut vorlegen | **umgesetzt** | Revision je Hinweis und Durchsicht-Markierung; identische Neuimporte bleiben still, Importlücken bleiben sichtbar (A2) |
| 07 | Jobs, Pause, Wiederaufnahme vereinheitlichen | **umgesetzt** | gemeinsames Jobmodell für Importe, Scans, Ordnerüberwachung und Bitwarden, globale Pause, Kontrollübersicht, Fortsetzen über den Nachrichtenindex |
| 08 | Korrekturen erhalten und rückgängig machen | **umgesetzt** | Entscheidungen überstehen Neuauswertung; Protokoll und Rückgängig für Entscheidung, Schritte und Planung in Dashboard, API und CLI |
| 09 | Nächste Aufgabe begründet vorbereiten | **umgesetzt** | eine begründete nächste Aufgabe in der Übersicht (D1), geführter Ablauf, Arbeitsliste |
| 10 | Freigaben vor externen Jobs prüfen | **umgesetzt** | Zielbindung aus Host, Port, Benutzer, Anmeldeart und Ordnern; sichtbare Freigabe mit Widerruf und Vorschau; übrige externe Zugriffe je Aufruf |
| 11 | Bitwarden-Vorschau und Übergabestatus | **umgesetzt** | genaue Vorschau (B2), Bereitschaft je Account (A19), ein Journal über Download und CLI (B3), drei gleichwertige Wege ohne Tresor-Lesen (B1) |
| 12 | Unklare Schreibausgänge blockieren | umgesetzt | Status `uncertain`, keine blinde Wiederholung, manuelle Klärung |
| 13 | Wiederkehrende lokale Importe vereinfachen | **umgesetzt** | letzte Quelle wiederholen, nur Geändertes, Budget, Fortsetzen, gezielt nachholen, Vorprüfung |
| 14 | Begrenzte Ordnerüberwachung | **umgesetzt** | ein freigegebener lokaler Ordner, nur `*.eml` direkt darin, nur mit laufendem Dashboard, sichtbar und beendbar |
| 15 | Belegten Pro-Komfortbedarf bedienen | **umgesetzt als Free** | Profile, Verlauf, Berichte, große Archive, Ordnerüberwachung, Umzugsplan und Vorlagen kostenlos; keine Lizenz (S1, S14, S15, S17, S18) |

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
| S16 | Bitwarden: Weg ohne Tresorlesen, Duplikatschutz, Übergabebereitschaft → **2.4.0** | B1, B3, A19, 11 | ✅ (2.4.0) |
| S17 | Getrennte Profile, Verlaufsanalyse, datensparsame Berichte | P1, P2, P5 | ✅ |
| S18 | E-Mail-Umzugsplan und Ablaufvorlagen → **2.5.0** | A21, A22, P4 | ✅ (2.5.0) |
| S19 | Importabdeckung, Barrierefreiheit, Maskierung, Katalogqualität | D4, D6 | ✅ |
| S20 | Demoablauf, FAQ, vertrauenswürdige Releases → **2.6.0** | G2, G4, G6 | ✅ (2.6.0) |
| S21 | Abschluss: Abdeckung aller Plan-Punkte | – | ✅ |

## Abdeckung aller Plan-Punkte

Stand nach S21: Jeder Punkt des Plans ist umgesetzt, bewusst begrenzt, teilweise
umgesetzt oder per Entscheidung entfallen. „Wo“ nennt den Einstieg im Code oder in der Oberfläche;
die Grenzen aus dem Plan gelten weiter.

### Fundament

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| F1 | Einheitlicher Produktname | umgesetzt | vor S0 | Umbenennung auf ARGUS mit Profil-Migration; Alias `account-finder` bleibt |
| F2 | Drei klare Einstiegswege | umgesetzt | S7 | Übersicht „Wähle deinen Einstieg“: Demo, lokale E-Mails, IMAP |
| F3 | Ehrliche Ergebniszusammenfassung | umgesetzt | S7 | `summary.py`, Übersicht „Was ARGUS bisher weiß“ |
| F4 | Fehler mit nächstem Schritt | umgesetzt | S3 | `guidance.py`, `errors.py`; CLI und Dashboard |
| F5 | Lokale Änderung rückgängig | umgesetzt | S5 | `changes.py`; `changes`/`undo`, Rückgängig im Dashboard |
| F6 | Exportvorschau und synthetische Beispiele | umgesetzt | S3 | `bitwarden-export --preview`, Exportvorschau; Demo mit schwierigen Fällen (`scan.load_demo`) |

### Erkennung

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| E1 | Erkennungsbegründungen | umgesetzt | S8 | `analysis.py` (Regelmerkmale), Belegkarten im Detaildialog |
| E2 | Hinweisarten und Alter trennen | umgesetzt | S8 | Hinweisart, Alter und Stärke je Beleg |
| E3 | Mehrdeutigkeiten bündeln | umgesetzt | S9 | `review.py`, Ansicht „Unklares“, CLI `unclear` |
| E4 | Ausschlüsse und Alias-Beziehungen | umgesetzt | S5, S9 | `exclude`, `relate`; Beziehungen ohne Zusammenlegen von Accounts |
| E5 | Unbekannte Domains und eigener Katalog | umgesetzt | S10 | `catalog.py`, persönlicher Katalog, `/api/catalog` |
| E6 | Regeländerungen nachvollziehbar anwenden | umgesetzt | S10 | Regelversion je Beleg, Hinweis auf geänderte Bewertungen, Entscheidungen bleiben |

### Dashboard

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| D1 | Eine klare nächste Aufgabe | umgesetzt | S7 | `summary.next_task`, Karte „Nächste Aufgabe“ |
| D2 | Drei Zustände statt eines grünen Hakens | umgesetzt | S6 | `states.py` (ADR-0001), drei Marken je Account |
| D3 | Prioritäten erklären und anpassen | umgesetzt | S12 | `identity.explain_priorities`, Reihenfolge in der Arbeitsliste änderbar |
| D4 | Importabdeckung zeigen | umgesetzt | S19 | `coverage.py`, Panel „Was deine Importe abdecken“, ohne Gesamtquote |
| D5 | Zentrale Kontrollübersicht | umgesetzt | S13 | Ansicht „Kontrolle“, `jobs.py` |
| D6 | Barrierefreiheit und Verbergen persönlicher Angaben | umgesetzt (Grundlagen) | S19 | Sprunglink, `aria-current`, Namen für alle Bedienelemente, maskierte Ansicht; kein vollständiges WCAG-Audit |

### Bitwarden

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| B1 | Standardweg ohne Vault-Lesen | umgesetzt | S16 | drei Wege (Datei, CLI, selbst zuordnen) in „Bitwarden vorbereiten“ |
| B2 | Exakte Übergabevorschau | umgesetzt | S3 | `bitwarden.preview_export`, Vorschau-Dialog |
| B3 | Sichtbarer Duplikatschutz | umgesetzt | S16 | `handoffs.py`, ein Journal über Download und CLI |
| B4 | Passwortfreien Eintrag kennzeichnen | umgesetzt | S5 | Tresor-Schritt wird „vorbereitet“, nie „erledigt“ (`instances.py`) |
| B5 | Datierte Sicherheitsbestätigungen | umgesetzt | S5, S12 | `done_at` und Wiedervorlage je Schritt (`states.py`), Regel `review-rule` |
| B6 | Kritische Identitätskonten berücksichtigen | umgesetzt | S12 | `identity.py`: `mailbox`, `sign-in-with`, Priorisierung |

### Automatisierung

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| A1 | Änderungszentrale | umgesetzt | S11 | `digest.py`, Ansicht „Neu seit…“, CLI `whats-new` |
| A2 | Unverändertes erkennen | umgesetzt | S11 | Revision je Hinweis, Durchsicht-Markierung |
| A3 | Neue Funde vorgruppieren | umgesetzt | S11 | Gruppen nach Account in „Neu seit…“ |
| A4 | Unklarheiten zuerst | umgesetzt | S11 | Bereich „Zuerst entscheiden“ in „Neu seit…“ |
| A5 | Passende Checkliste | umgesetzt | S12 | Schritte je Anmeldeart (Passwort, SSO, Passkey) |
| A6 | Arbeitsliste vorbereiten | umgesetzt | S12 | `workflow.py`, Vorschläge mit Begründung |
| A7 | Zusammenfassung beim Wiederkommen | umgesetzt | S11 | `digest.return_summary`, Karte in der Übersicht |
| A8 | Kleine Arbeitssitzungen | umgesetzt | S12 | `sessions.py`, CLI `session` |
| A9 | Fehlfunde unterdrücken | umgesetzt | S9 | umkehrbare Ausschlüsse mit sichtbarem Geltungsbereich |
| A10 | Alte Prüfungen vorlegen | umgesetzt | S6, S12 | Wiedervorlage je Schritt, `reviews.py` |
| A11 | Importeinstellungen merken | umgesetzt | S14 | `import --again`, Hinweis „Letzter lokaler Import“ |
| A12 | Ausgewählten Ordner beobachten | umgesetzt (eng begrenzt) | S15 | `watch.py`: ein Ordner, nur `*.eml`, nur bei laufendem Dashboard |
| A13 | Nur Geändertes verarbeiten | umgesetzt | S14 | Index verarbeiteter Nachrichten (`imports.py`) |
| A14 | Ressourcenbudget | umgesetzt | S14 | `--max-messages`, `--max-megabytes` |
| A15 | Sicher fortsetzen | umgesetzt | S14 | Fortsetzen über den Nachrichtenindex |
| A16 | Fehler gezielt bearbeiten | umgesetzt | S14 | `import --retry-failed`, `--check` |
| A17 | Identitätskonten priorisieren | umgesetzt | S12 | Postfach- und SSO-Accounts zuerst, mit Begründung |
| A18 | Metadaten vorausfüllen | umgesetzt | S12 | bekannte Angaben in Bitwarden-Notizen |
| A19 | Übergabebereitschaft prüfen | umgesetzt | S16 | `bitwarden.readiness` je Account |
| A20 | Sitzungsbericht vorbereiten | umgesetzt | S12 | `sessions.report_text`, Berichtsdialog |
| A21 | E-Mail-Umzugsplan | umgesetzt | S18 | `moves.py`, CLI `move-address` |
| A22 | Sichere Ablaufvorlagen | umgesetzt | S18 | `templates.py`, CLI `template`, Vorschau und Rückgängig |
| A23 | Freigaben vor Start prüfen | umgesetzt | S13 | Zielbindung und sichtbare Freigabe (`background.py`) |
| A24 | Sichtbare Jobwarteschlange | umgesetzt | S13 | Vorgänge und Wartendes in „Kontrolle“ |
| A25 | Minimales Aktivitätsprotokoll | umgesetzt | S13 | 500 Einträge, 180 Tage, ohne Inhalte (`jobs.py`) |
| A26 | Automatikregeln vorschauen | umgesetzt | S13, S18 | `background-imap preview`, Vorlagenvorschau |
| A27 | Gesamte Automatisierung pausieren | umgesetzt | S13 | `automation pause|resume`, Pause in „Kontrolle“ |
| A28 | Zusammenfassen statt stören | umgesetzt | S11 | eine Zusammenfassung statt einzelner Meldungen; Pause bleibt sichtbar |

### Frühere Pro-Ideen (alle kostenlos)

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| P1 | Getrennte lokale Profile | umgesetzt | S17 | `--profile`, `profiles.py` |
| P2 | Lokale Verlaufsanalyse | umgesetzt | S17 | `history.py`, Panel „Fortschritt im Zeitverlauf“ |
| P3 | Große Archive komfortabel verarbeiten | umgesetzt | S14 | Budget, Fortsetzen, nur Geändertes |
| P4 | Umzug und eigene Vorlagen | umgesetzt | S18 | Umzugsplan und eigene Vorlagen |
| P5 | Datensparsame Berichte | umgesetzt | S17 | `reports.py`, `report --text|--export` |
| P6 | Offline-Lizenz und kuratierte Spezialpakete | entfällt | S1 | Entscheidung „alles als Free“; keine Lizenz |

### Community und Sichtbarkeit

| Punkt | Titel | Stand | Schritt | Wo |
| --- | --- | --- | --- | --- |
| G1 | Präzises Produktversprechen | umgesetzt | S3 | README und Dashboard: Hinweise statt Beweise, keine Vollständigkeit |
| G2 | Ein vollständiger Demoablauf | umgesetzt | S20 | „Probier diesen Weg“, `docs/DEMO_DE.md` |
| G3 | Anbieter-Vorlage mit Prüfkriterien | umgesetzt | S10 | `.github/ISSUE_TEMPLATE/provider.yml` |
| G4 | Datensparsame Fehlerberichte und FAQ | umgesetzt | S20 | `argus about`, Fehlerformular, `docs/FAQ_DE.md` |
| G5 | Synthetischer Qualitätsbenchmark | umgesetzt | S10 | `scripts/benchmark.py`, `benchmarks/` |
| G6 | Vertrauenswürdige Releases | umgesetzt | S20, 2.7.0 | Release-Prüfung, Prüfsummen, Release-Hinweise; signierte Herkunftsbestätigung je Tag (`release.yml`, Job `attest`) |
