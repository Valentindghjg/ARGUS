# ADR-0001: Zustands- und Freigabemodell

| | |
| --- | --- |
| Status | **Angenommen** am 2026-10-16 durch den Owner (Antworten in Abschnitt 6). |
| Datum | 2026-10-16 |
| Bezug | [Gesamtplan](../strategy/README.md), Phase 0 und Releasepaket A; Prioritäten 01, 07, 08, 10; Ideen D2, E4, F5, B4, B5, A9, A23–A27 |
| Ersetzt | – |

## 1. Kontext

Der Gesamtplan nennt als erste Entscheidung: „Zuerst verständliche Zustände und
belastbare Identitäten, danach mehr Automatisierung.“ Das Freigabekriterium für
Phase 0 lautet: **Jede Statusaussage und jede Wirkung hat eine eindeutige
Bedeutung.**

Der heutige Code (Stand nach PR #4) erfüllt das noch nicht. Stabile Identitäten
gibt es bereits seit 1.9 (`account_instances`). Die Zustände darauf vermischen
aber drei Fragen, die der Plan trennt:

1. **Was sagen die Belege?** Maschinelle Auswertung, ändert sich bei jedem Import.
2. **Was hat die Person entschieden?** Existiert der Account, gehört er mir?
3. **Wie weit ist die Sicherheitsarbeit?** Bitwarden, Passwort, Anmeldetest, MFA.

Dazu kommen die Planung (Arbeitsliste, Zurückstellen) und externe Vorgänge
(Scans, Bitwarden-Übergaben) mit ihren Freigaben.

## 2. Bestandsaufnahme: heutige Zustände im Code

| Ort | Zustand | Werte | Gesetzt von | Problem |
| --- | --- | --- | --- | --- |
| `account_instances.confirmed` | Existenz bestätigt | 0/1 | **Abgeleitet** aus Checkliste `reviewed` (`store.update_account`) | Entscheidung und Aufgabe sind dasselbe Feld. Wer „geprüft“ abwählt, macht die Existenz unbestätigt. |
| Snapshot `classification` | Einstufung | confirmed / probable / unknown | Mischung aus Nutzerentscheidung und Beleg-Score | Eine Spalte beantwortet zwei Fragen (D2). |
| Snapshot `confidence` | Sicherheit | manually confirmed / high / medium / low / no evidence | Mischung | wie oben |
| Snapshot `reason` | Begründung | Belegtext oder „You confirmed …“ | Mischung | Nach der Bestätigung ist die Belegbegründung nicht mehr sichtbar (E1). |
| `account_instances.status` | Arbeitsstand | pending / in_progress / done / **skipped** | Nutzer und Automatik | `skipped` erscheint als „Zurückgestellt“ und doppelt die Zurückstellung der Arbeitsliste. |
| `checklist` (JSON, 5 Booleans) | Sicherheitsschritte | reviewed, saved_in_bitwarden, password_changed, login_tested, mfa_checked | Nutzer, `saved_in_bitwarden` auch Automatik | Ohne Datum (B5); `reviewed` ist eigentlich die Existenzentscheidung. |
| `saved_in_bitwarden` | Tresor-Schritt | bool | Nutzer **oder** erfolgreiche passwortfreie Übergabe (`handoffs`) | Ein von ARGUS angelegter passwortfreier Eintrag sieht aus wie „gespeichert“ (B4). |
| `identity_review_required` | Migrationssperre | 0/1 | Migration | sinnvoll, aber nur als Sonderfall modelliert |
| `instance_work_queue` | Planung | Position, `deferred`, `resume_after`; Meta `worklist_focus`, `worklist_paused` | Nutzer | Zweite Zurückstellung neben `status=skipped`. |
| Fehlt | Ablehnung | – | – | „Nicht meiner / kein Account“ ist nicht ausdrückbar; Fehlfunde kehren zurück (E4, A9). |
| Fehlt | Rückgängig | – | – | Keine Historie lokaler Entscheidungen (F5, Priorität 08). |
| `instance_bitwarden_handoffs.state` | Übergabe | not_created / running / uncertain / created | Automatik und Nutzer (`resolve`) | gut getrennt; als Vorbild nutzbar |
| Meta `last_scan` | Importlauf | running; Ergebnis completed / completed_with_gaps / partial / limited | Automatik | je Lauf, keine gemeinsame Jobsicht (A24) |
| Meta `background_imap_schedule` | Geplanter Scan | enabled, authorized, target, run/lease, last_result | Nutzer und Automatik | an ein Ziel gebunden (Priorität 10, umgesetzt) |
| Meta `imap_mailbox_lease` | Postfach belegt | Token, Art, Ablauf | Automatik | gut getrennt |

## 3. Entscheidung (Vorschlag)

### 3.1 Fünf unabhängige Achsen pro Account

Jede Achse hat genau einen Eigentümer: **Automatik** oder **Person**. Keine
Achse wird aus einer anderen abgeleitet, außer den Anzeigen in 3.3.

| Achse | Eigentümer | Werte | Bedeutung |
| --- | --- | --- | --- |
| **A. Beleglage** | Automatik, nie gespeichert | `none` · `weak` (< 60) · `probable` (≥ 60) · `stale` (nur ältere Regeln); dazu die Zahl mehrdeutiger Hinweise | Was die lokalen Belege nahelegen. Wird bei jedem Snapshot neu berechnet. |
| **B. Entscheidung** | Person | `undecided` · `confirmed` · `rejected` (+ Grund `not_mine` / `not_an_account` / `closed`), mit `decided_at` | Ob die Person den Account als ihren bestätigt oder verworfen hat. Unabhängig von den Belegen. |
| **C. Sicherheitsschritte** | Person (Vorschläge durch Automatik) | je Schritt `open` · `done` · `not_applicable`, mit `done_at`. Schritte: `identity`, `vault`, `password`, `signin_test`, `mfa_recovery` | Was die Person erledigt hat. `password` ist bei SSO und Passkey `not_applicable`. |
| **D. Planung** | Person | in Arbeitsliste ja/nein · Position · `deferred_until` (Datum oder unbestimmt) · Fokus | Wann daran gearbeitet wird. **Die einzige Art, etwas zurückzustellen.** |
| **E. Externe Vorgänge** | Automatik nach Freigabe | Übergabejournal wie heute; Jobs siehe 3.4 | Was außerhalb von ARGUS geschah oder unklar ist. |

**Tresor-Schritt zweistufig (B4):** `vault` kennt zusätzlich `prepared`, also einen
passwortfreien Eintrag, den ARGUS angelegt hat. `done` setzt nur die Person, wenn
das Passwort tatsächlich in Bitwarden liegt.

### 3.2 Regeln, die das Modell garantiert

1. Eine neue Auswertung ändert nur A, nie B, C oder D. So bleiben Entscheidungen
   über Regeländerungen erhalten; das Gate von Releasepaket B ist damit erfüllt.
2. `rejected` blendet den Account aus Listen, Arbeitsliste und Vorschlägen aus.
   Neue, stärkere Belege zeigen einen Hinweis, entscheiden aber nicht neu (A9).
3. Jede Änderung an B, C und D wird mit altem und neuem Wert und Zeitpunkt
   protokolliert. Daraus entsteht „Rückgängig“ für lokale Änderungen (F5,
   Priorität 08). Externe Vorgänge (E) sind ausdrücklich nicht rückgängig zu machen.
4. Automatik darf C nur **vorschlagen**. Die einzige automatische Änderung ist
   `vault: prepared` nach einer bestätigten Übergabe.
5. Bisher galt `status = skipped`; das entfällt. Zurückstellen gibt es nur noch in D.

### 3.3 Abgeleitete Anzeigen (nicht gespeichert)

| Anzeige | Formel | Ersetzt |
| --- | --- | --- |
| „Fortschritt“ | `not_started` / `in_progress` / `complete(at)`, nur aus C über die anwendbaren Pflichtschritte | `status` pending / in_progress / done |
| „Nächster Schritt“ | erster offener anwendbarer Schritt in C, bei offener Identität `identity` | `next_step()` |
| Kurzstatus in Listen | drei getrennte Marken: Beleg (A), Entscheidung (B), Fortschritt | `classification` + `confidence` |

„Abgeschlossen“ heißt nur: Alle Schritte sind von dir abgehakt. Es heißt nie
„sicher“; der Plan nennt das „keine Sicherheitsgarantie durch einen
Abschlussstatus“.

### 3.4 Aktionsarten und Freigaben

Der Plan ordnet jede Aktion nach ihrer Wirkung ein. Jede Aktion in ARGUS bekommt
genau eine Klasse:

| Klasse | Beispiele heute | Freigabe |
| --- | --- | --- |
| lokal lesen/auswerten | Import, Snapshot, Arbeitsliste anzeigen | keine Rückfrage; die Quelle wählt die Person |
| lokal ändern | Entscheidung, Checkliste, Arbeitsliste | direkt; Sammelaktionen mit Vorschau; rückgängig nach 3.2 Regel 3 |
| extern lesen | MX-Abfrage, manueller IMAP-Scan, Bitwarden-Prüfung, geplanter Scan | je Aufruf oder als **zielgebundene Freigabe** |
| extern schreiben | Bitwarden-Übergabe | je Vorgang mit `confirmed: true`; unklarer Ausgang blockiert |
| ausgeschlossen | Login, Reset, Passwortänderung, Löschen beim Anbieter | technisch nicht vorhanden |

Eine **Freigabe** ist ein Datensatz aus Art, Profil, Zweck, Ziel-Fingerabdruck,
Umfang und Erteilungszeit. Weicht ein Feld ab, gilt die Freigabe nicht; ein
Wiederholen braucht eine neue Freigabe. Die Zielbindung geplanter Scans
(Priorität 10, bereits umgesetzt) ist der erste Fall und wird zum allgemeinen Muster.

Jobs (Import, manueller und geplanter Scan) bekommen einen gemeinsamen Zustand:
`queued` · `running` · `paused` · `completed` · `completed_with_gaps` · `failed` ·
`cancelled` · `needs_approval`. Dazu kommt ein globaler Pausenschalter, der neue
Jobs sperrt und laufende zwischen zwei Nachrichten beendet (A24, A27,
Priorität 07). Die bestehende `keep_alive`-Mechanik trägt das bereits.

## 4. Migration

- **Sicherung zuerst:** Vor der Schemaänderung entsteht über die SQLite-Backup-API
  eine Kopie `accounts.sqlite3.pre-adr1` mit Rechten 0600. Danach wird die
  Wiederherstellung getestet.
- **Abbildung des heutigen Stands:**

| Heute | Neu |
| --- | --- |
| `checklist.reviewed = true` | B = `confirmed` (`decided_at` = `updated`); C `identity` = `done`, falls eine Identität zugeordnet ist |
| `status = skipped` | D `deferred_until` = unbestimmt; Fortschritt neu berechnet |
| `status = done` | alle anwendbaren Schritte `done`, `done_at` = `updated` |
| `saved_in_bitwarden` mit erfolgreichem Journal, Status nicht `done` | `vault` = `prepared` mit Hinweis „bestätige, wenn das Passwort gespeichert ist“ |
| `saved_in_bitwarden` sonst | `vault` = `done` |
| `login_method` sso / passkey | `password` = `not_applicable` |

- **Übergang der API:** Für eine Version liefert der Snapshot `classification`
  und `status` als abgeleitete Kompatibilitätsfelder, danach entfallen sie.

## 5. Konsequenzen

**Vorteile**
- Das Gate von Phase 0 wird prüfbar: Jede Marke hat einen Eigentümer und eine
  Bedeutungszeile.
- E4, A9, F5, B4, B5, D2 und Priorität 08 setzen auf einem Modell auf und
  brauchen keine Sonderfälle.
- Die Änderungszentrale (A1 bis A7) kann Änderungen je Achse melden, etwa „neue
  Belege“ getrennt von „deine Entscheidungen“.

**Kosten und Risiken**
- Schemaänderung mit Migration; Dashboard, Exporte und Tests müssen auf die
  getrennten Felder umgestellt werden.
- `vault: prepared` könnte bei Altprofilen fertige Accounts zurückstufen. Die
  Abbildung oben schützt `done`-Accounts davor.
- Das Änderungsprotokoll ist neue persönliche Metadaten. Es enthält nur
  Feldnamen, Werte und Zeit, nie Mailinhalte, Geheimnisse oder Tresordaten.
  Die Aufbewahrung ist begrenzt (Plan A25).

## 6. Entscheidungen des Owners (16.10.2026)

| Frage | Entscheidung |
| --- | --- |
| „Bestätigt“ von der Checkliste trennen? | **Ja, getrennt.** Bestätigung ist eine eigene Entscheidung mit Datum. |
| Verwerfen mit Grund? | **Ja**, mit Grund (nicht meiner / kein Account / geschlossen), umkehrbar. |
| Datierte Schritte? | **Ja, mit Wiedervorlage** (A10), nur lokal. |
| Tresor-Schritt zweistufig? | **Ja**: vorbereitet (passwortfrei durch ARGUS) / erledigt (durch die Person). |
| Paketierung | Kleine Schritte mit je einem Merge; Versionserhöhung je Releasepaket (Paket A → 2.0.0), Tags und Releases legt der Owner an. |

Weitere Entscheidungen zum Gesamtplan stehen in
[ENTSCHEIDUNGEN.md](../strategy/ENTSCHEIDUNGEN.md).

## 7. Umsetzungsschritte nach Freigabe

1. Schema, Migration mit Sicherung, Kompatibilitätsfelder. Tests: Migration aller
   Altstände, Abbruch während der Migration, Wiederherstellung. **Umgesetzt (S5a),
   siehe Abschnitt 8.**
2. Store/API: getrennte Felder, Änderungsprotokoll und Rückgängig für B, C und D.
   **Umgesetzt (S5b), siehe Abschnitt 8.**
3. Dashboard: drei Marken, Verwerfen und Rückgängig, Bedeutungstabelle in der Hilfe.
4. Jobmodell mit globaler Pause; Freigabe-Datensatz für alle externen Lesezugriffe.
5. Fachliche Testfälle aus dem Plan: Newsletter, SSO, mehrere Identitäten,
   unklare Übergaben, Regeländerung gegen Bestätigung, dreifacher Import.

## 8. Umsetzung

### Schritt 1 (S5a, Schemaversion 2)

- `argus_security/states.py` enthält das Modell an einer Stelle: Achsen, Werte,
  Pflichtschritte, abgeleiteter Fortschritt und die Abbildung der 1.x-Zustände.
- `account_instances` trägt Identität, Attribute und die Entscheidung (B) mit
  `decided_at` und dem Belegstand zum Entscheidungszeitpunkt. `account_steps`
  trägt die Schritte (C) mit `done_at` und `review_after`. Planung (D) bleibt in
  `instance_work_queue`. `change_log` protokolliert B, C und D je Aktion.
- Die Migration baut die 1.x-Tabelle in einer Transaktion um. Vorher entsteht die
  automatische Sicherung aus S4 (`pre-migration-v1-to-v2`), statt einer
  Einzeldatei `accounts.sqlite3.pre-adr1`. Ein Abbruch lässt das 1.x-Profil
  unverändert; die Wiederherstellung der Sicherung ist getestet.
- Der Snapshot liefert die Achsen (`evidence_level`, `decision`, `steps`,
  `progress`, `completed_at`, `deferred`) und für Version 2.x die abgeleiteten
  Felder `classification`, `status`, `checklist`, `confidence` und `reason`.
- Die API nimmt die 1.x-Schlüssel weiter an: `checklist.reviewed` setzt
  Entscheidung und Identitätsschritt, die übrigen Häkchen die Schritte,
  `status: done` prüft nur die Vollständigkeit, `status: skipped` stellt in der
  Arbeitsliste zurück.

**Präzisierungen gegenüber Abschnitt 4** (auch in
[ENTSCHEIDUNGEN.md](../strategy/ENTSCHEIDUNGEN.md)):

- **Identität:** Das 1.x-Häkchen „geprüft“ schloss die Anmeldung ein. Deshalb wird
  `identity` für jeden bisher geprüften Account `done`, auch ohne zugeordnete
  Adresse. Nur eine offene Identitätsprüfung hält den Schritt offen.
- **MFA und Wiederherstellung** sind ein Pflichtschritt, der `done` oder
  `not_applicable` sein kann. „Abgeschlossen“ heißt damit immer, dass jede Frage
  beantwortet ist. Ein in 1.x ohne MFA-Häkchen abgeschlossener Account bekommt
  `not_applicable` statt einer erfundenen Prüfung; ebenso, wenn die alte
  Oberfläche „Als erledigt markieren“ ohne MFA-Häkchen sendet.
- **Kein eigener Abschlussschritt:** Der Fortschritt ist abgeleitet. Der frühere
  Schritt „finish“ der geführten Arbeitsliste entfällt.

### Schritt 2 (S5b)

- `Store.decide` setzt B: bestätigt, offen oder verworfen mit Grund
  (`not_mine`, `not_an_account`, `closed`). Verwerfen nimmt den Account im selben
  Vorgang aus der Arbeitsliste; ein Rückgängig bringt beides zurück. Neue starke
  Belege nach dem Verwerfen setzen nur `reconsider` (Regel 2).
- `Store.set_step` setzt einen Schritt (`open`, `done`, `not_applicable` wo
  erlaubt) oder ein lokales Wiedervorlagedatum (`review_after`, A10). `prepared`
  setzt nur eine bestätigte Bitwarden-Anlage. Fällige Wiedervorlagen stehen im
  Snapshot unter `reviews_due`.
- Alle Arbeitslisten-Aktionen werden als Planungsänderung protokolliert.
- `Store.undo` macht den jüngsten noch nicht zurückgenommenen Vorgang rückgängig,
  wiederholt aufgerufen auch ältere. Ein Rückgängig ist selbst ein Vorgang und
  lässt sich gezielt zurücknehmen. Wurde ein Feld später erneut geändert, wird
  abgelehnt statt überschrieben. Externe Vorgänge (Journal, Tresor) bleiben
  unberührt.
- API: `POST /api/accounts/{id}/decision`, `POST /api/accounts/{id}/steps`,
  `POST /api/undo`, `GET /api/changes`. CLI: `argus changes`, `argus undo`.

