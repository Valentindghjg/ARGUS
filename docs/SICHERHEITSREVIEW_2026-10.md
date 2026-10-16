# Sicherheitsreview – Oktober 2026 (Basis v1.16.0)

Stand: 2026-10-16 · Basis-Commit `2ec9fb7` · Umfang: vollständiges Repository.
Englische Kurzfassung: [SECURITY_REVIEW_2026-10.md](SECURITY_REVIEW_2026-10.md).

## 1. Auftrag, Grundlage und Abweichungen

Auftrag war eine vollständige, sicherheitsorientierte Review. Geprüft wurden
Zustände, Importe, IMAP, Bitwarden-Grenzen, UI, Übersetzungen, Tests,
Dokumentation, Lizenzierung, GitHub-Reife und toter Code. Konkrete Probleme
sollten innerhalb der Sicherheitsgrenzen behoben und durch Simulationstests
abgesichert werden.

**Abweichung:** Die als Grundlage genannten Dateien `docs/CLAUDE_CODE_HANDOFF.md`
und `docs/strategy/ARGUS_Gesamtplan_Produktstrategie_Automatisierung_DE.pdf`
existieren im Repository nicht – weder auf `main` noch in einem Branch oder in
der Git-Historie. Nach Rücksprache wurden Sicherheitsgrenzen und Testumfang aus
dem Repository abgeleitet: `docs/SECURITY.md`/`SICHERHEIT.md`, `docs/PLAN_DE.md`,
`CONTRIBUTING.md`, `PRIVACY.md` und die CI-Definition `.github/workflows/ci.yml`.
Sollte die Übergabe weitere Grenzen oder Tests enthalten, ist dieser Bericht
dagegen abzugleichen.

### Eingehaltene Sicherheitsgrenzen

| Grenze | Quelle | Einhaltung in dieser Review |
| --- | --- | --- |
| Keine Logins, Passwortänderungen, Resets, Online-Accounts | CONTRIBUTING, SECURITY | Keine Anbieteraktion; nur synthetische Daten |
| DNS/IMAP nur nach ausdrücklicher Freigabe, nur lesend | PLAN_DE, SECURITY | Kein Netzwerkzugriff auf Mailserver; IMAP nur als In-Memory-Fake |
| Keine Zugangsdaten in Konfiguration, API, Logs, Ergebnissen | SECURITY | Keine Secrets angefordert oder gespeichert; Tests prüfen Profildateien |
| Bitwarden: kein Hauptpasswort, keine Änderung bestehender Einträge | SECURITY, BITWARDEN_CLI | Nur gefälschte CLI-Runner; keine echte `bw`-Ausführung |
| Hintergrund-IMAP nur nach Opt-in im Terminal | SECURITY | Nur simulierte Uhr, Fake-Keyring und Fake-IMAP |
| Keine Veröffentlichung | Auftrag | Kein Release, Tag, PR oder Issue; nur Commit auf `main` |

## 2. Ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| `python -m unittest discover -s tests` (Python 3.13) | vorher 166 OK → nachher **177 OK** |
| `node --check` für `app.js` und `popup.js` | OK |
| `browser-companion/tests/validate.py` (verschärft) | OK, 527 Dienste |
| Wheel/Sdist bauen, in sauberer venv installieren, `--help` en/de, `demo`, `report`, `list-accounts` | OK |
| `scripts/browser_smoke.py` (Chromium, Playwright) | 18 Prüfgruppen, 0 Seitenfehler, 0 externe Requests |
| `scripts/browser_multi_account.py` (erweitert) | 5 Prüfgruppen, 0 Seitenfehler, 0 externe Requests |
| MIME-Fuzzing von `analysis.analyze` (30 000 mutierte Nachrichten + 13 gezielte Grenzfälle) | Keine unbehandelten Ausnahmetypen. Rekursion, NUL-Zeichen und exotische Codecs enden als gezählte Fehler. |

Die CI-Matrix (Python 3.11–3.14) wurde lokal nur mit 3.13 ausgeführt. Die
übrigen Versionen deckt GitHub Actions beim Push ab.

## 3. Ergebnisübersicht

Schweregrade: **hoch** = Sicherheitsgrenze praktisch verletzbar; **mittel** =
dokumentierte Zusage nicht eingehalten oder Fehlbedienung mit dauerhafter
Wirkung; **niedrig** = Härtung/Konsistenz; **info** = Hinweis.

| ID | Bereich | Befund | Schwere | Status |
| --- | --- | --- | --- | --- |
| R-01 | Hintergrund-IMAP | Lease (5 min) lief bei langen Läufen ab; ein zweiter Prozess konnte das Postfach parallel öffnen | mittel | **behoben** |
| R-02 | Hintergrund-IMAP | `disable`/`revoke` stoppten einen laufenden Scan nicht | mittel | **behoben** |
| R-03 | Dashboard | Scheduler-Thread konnte bei DB-Sperre/defektem Zeitplan still sterben | mittel | **behoben** |
| R-04 | Dashboard/CLI | Startmeldung „Keine Postfachverbindung aktiv“, obwohl geplante Scans aktiv sein können | mittel | **behoben** |
| R-05 | UI/Zustände | Anmeldeadresse wurde bei einer einzigen Auswahl dauerhaft gebunden, ohne Rückfrage | mittel | **behoben** |
| R-06 | Browser-Begleiter | Fremd-hostbare Subdomains (z. B. `*.substack.com`) und `http:` als „offiziell“ markiert | mittel | **behoben** |
| R-07 | Übersetzungen | 24 sichtbare Meldungen ohne deutschen Text (Lizenz, Schlüsselbund, Scheduler) | mittel | **behoben** |
| R-08 | Bitwarden | Tresor-Schreibendpunkt ohne serverseitige Bestätigung (Audit und geführter Pfad hatten sie) | niedrig | **behoben** |
| R-09 | Hintergrund-IMAP | OAuth2-Access-Tokens laufen ab; geplante Läufe scheitern danach stumm | niedrig | **behoben** (Hinweis) |
| R-10 | Repository | `*.pem`/`*.key` nicht ignoriert; Risiko, einen privaten Signaturschlüssel einzuchecken | niedrig | **behoben** |
| R-11 | UI | Übersetzungslookup traf Prototyp-Schlüssel (`constructor` u. a.) | niedrig | **behoben** |
| R-12 | Import | Irreführender Kommentar und ungenutzter Datei-Handle beim mbox-Import | niedrig | **behoben** |
| R-13 | Begleiter | Treffer hing von Sortierreihenfolge ab; Validator prüfte zu wenig | niedrig | **behoben** |
| R-14 | Bitwarden | `bw create item <base64>` legt Metadaten (Name, Anmeldeadresse) in der Prozessliste offen | niedrig | offen (Empfehlung) |
| R-15 | IMAP | Manueller `scan-imap` nutzt die Scheduler-Lease nicht | niedrig | offen (dokumentiert) |
| R-16 | Server/UI | Spezifische Validierungsfehler werden durch generische Meldungen ersetzt | niedrig | offen (Empfehlung) |
| R-17 | Begleiter | Subdomain-Hinweis und Popup nur auf Englisch | info | offen |
| R-18 | i18n | 22 ungenutzte Übersetzungsschlüssel | info | offen (siehe 6) |

Weitere Befunde aus Dokumentation, Lizenzierung und GitHub-Reife stehen in
Abschnitt 5.

## 4. Befunde im Detail

### R-01 Lease-Ablauf bei langen geplanten Scans – behoben

`RUN_LEASE_SECONDS` betrug 5 Minuten, die Lease wurde aber nie verlängert. Ein
Lauf mit dem erlaubten Maximum von 10 000 Nachrichten dauert bei 0,15 s Pause
pro Nachricht mindestens 25 Minuten. Danach konnte ein zweiter Dashboard-Prozess
desselben Profils die Lease übernehmen und das Postfach parallel öffnen. Die
Sicherheitsdokumentation sagte das Gegenteil zu.

**Fix** (`account_finder/background.py`): Die Service-Klasse gibt dem Runner
einen `keep_alive`-Callback. Er verlängert die Lease zwischen zwei Nachrichten
atomar, höchstens alle 15 s (`LEASE_RENEW_SECONDS`). Der Standard-Runner hüllt
den IMAP-Stream in `_with_keep_alive`. `close()` wird weitergereicht, sodass
IMAP-Abmeldung und Checkpoints unverändert bleiben.

**Test:** `test_long_scan_renews_its_lease_so_a_second_process_cannot_open_the_mailbox`
simuliert 6 × 100 s pro Nachricht. Mit dem alten Code schlägt er fehl.

### R-02 Laufender Scan ignorierte `disable`/`revoke` – behoben

Bisher galt `disable`/`revoke` nur für künftige Läufe. Ein laufender Scan holte
weiter Nachrichten ab. Jetzt stellt `keep_alive` fest, dass der Zeitplan nicht
mehr aktiv ist oder die Run-ID nicht mehr passt. Es wirft dann `ScanCancelled`.
Der Lauf endet vor dem nächsten Abruf als `cancelled`, meldet sich ab und behält
die bereits gespeicherten Belege.

**Tests:** `test_disable_during_scan_stops_before_the_next_fetch_and_keeps_evidence`,
`test_revoke_during_scan_removes_keyring_entry_and_cancels`. Beide schlagen mit
dem alten Code fehl.

### R-03 Scheduler-Thread konnte still sterben – behoben

Fehler wie `sqlite3.OperationalError` aus `_claim_due` wurden im Dashboard-Thread
nicht abgefangen. Ebenso `ValueError` bei einem beschädigten Zeitplan. Danach
liefen keine geplanten Scans mehr, die Oberfläche zeigte aber weiter „aktiviert“.
Die Prüfung `active_import()` lief zudem ohne `import_lock`.

**Fix** (`server.py`, `_background_pass`): Die Prüfung läuft unter dem Lock, und
jeder Durchlauf ist gekapselt. Der nächste Durchlauf versucht es erneut. Es
werden keine Ausnahmetexte offengelegt.

**Tests:** `test_scheduler_pass_survives_unexpected_errors` und
`test_scheduler_pass_waits_for_a_running_browser_import`.

### R-04 Unzutreffende Startmeldung – behoben

`serve` meldete immer „Keine Postfachverbindung aktiv“, auch wenn geplante
IMAP-Scans aktiviert waren und direkt beim Start fällig wurden. Für ein
Sicherheitswerkzeug ist das eine falsche Zusicherung. `startup_notice()` nennt
jetzt den aktiven Zeitplan und `background-imap disable`, auf Englisch und auf
Deutsch.

### R-05 Dauerhafte Adressbindung ohne Rückfrage – behoben

Die Auswahl im Feld „Bekannte Anmeldeadresse zuordnen“ wurde sofort gespeichert.
Der Server lässt danach keine Änderung mehr zu (`store.py`: „cannot be
reassigned“). Ein Fehlklick band den Account also dauerhaft an die falsche
Adresse.

Jetzt fragt `window.confirm` vor dem Speichern nach. Bei Abbruch stellt die
Oberfläche den alten Wert wieder her. Die Browserprüfung deckt beide Pfade ab:
Abbruch lässt den Account unverändert, Bestätigung bindet ihn.

### R-06 Browser-Begleiter: „offiziell“ für fremde Subdomains und HTTP – behoben

Die Suffixprüfung war korrekt: `evil-github.com` ≠ `github.com`. Jede Subdomain
galt aber als „Official ARGUS provider domain“. Das betraf auch Dienste, auf
denen Dritte eigene Seiten hosten: Substack, itch.io, Tumblr, Medium, Typeform.
`http:`-Seiten wurden ebenfalls gekennzeichnet.

Jetzt gilt:

- Nur HTTPS-Seiten werden gekennzeichnet.
- „Offiziell“ heißt nur noch exakt die Katalogdomain oder ihr `www.`-Host.
- Für tiefere Subdomains erscheint ein Warnhinweis, und angezeigt wird die
  Katalogdomain statt des besuchten Hosts.
- Der längste passende Domaineintrag gewinnt, unabhängig von der Reihenfolge im
  Bündel.

Der verifizierte Passwort-Link stammt weiterhin ausschließlich aus dem Katalog.

### R-07 Fehlende deutsche Texte – behoben

Es fehlten 24 deutsche Einträge: 14 Lizenzfehler, 7 Schlüsselbund- und
Zeitplanfehler, die Scheduler-Fehlermeldung, der Lizenzstatus und „Mark account
done“. Sie wurden ergänzt, dazu die neuen Meldungen dieser Review.

**Neuer Test:** `test_user_facing_errors_have_german_entries` prüft per AST jede
typisierte Fehlermeldung (`LicenseError`, `CredentialError`, `MailboxError`,
`BitwardenCliError`, `HandoffError`, `DNSError`) auf einen deutschen Eintrag.

### R-08 Serverseitige Bestätigung für Tresor-Schreibzugriff – behoben

`/api/bitwarden/audit` und `/api/secure-next/bitwarden` verlangten bereits
`confirmed: true`, der schreibende Endpunkt `/api/bitwarden/cli` nicht. Die
Oberfläche fragte zwar per Dialog, die API war aber inkonsistent. Jetzt verlangt
auch dieser Endpunkt `confirmed: true` (strikt `is True`). Ein Test belegt, dass
`None`, `false`, `"true"` und `1` abgelehnt werden und die CLI-Funktion dabei
nie aufgerufen wird.

### R-09 Ablaufende OAuth2-Tokens bei geplanten Scans – Hinweis ergänzt

Kurzlebige XOAUTH2-Access-Tokens laufen meist nach Stunden ab. Ein täglicher Plan
scheitert danach dauerhaft, wenn auch sicher. `background-imap enable` weist bei
`auth=oauth2` jetzt auf beiden Sprachen darauf hin. Eine Token-Erneuerung ist
bewusst nicht eingebaut: Sie bräuchte Refresh-Tokens, und ARGUS speichert laut
PRIVACY.md keine.

### R-10 Private Signaturschlüssel nicht ignoriert – behoben

`scripts/generate_license_keys.py` erzeugt PEM-Dateien. `.gitignore` ignoriert
jetzt `*.pem` und `*.key`, außer dem öffentlichen Schlüssel
`account_finder/data/license_public_key.pem`, der ausgeliefert werden darf.

### R-11 bis R-13 – behoben

- **R-11:** `t()` in `app.js` nutzt `Object.hasOwn`. Kategorien aus einem eigenen
  Katalog wie `constructor` ergeben so keine Funktion mehr statt eines Textes.
- **R-12:** `file_messages(..., "mbox")` öffnete einen ungenutzten Handle. Der
  Kommentar behauptete zudem einen schreibgeschützten Zugriff, den
  `mailbox.mbox` gar nicht verwendet. Das Verhalten war unkritisch, weil nie
  geschrieben, gesperrt oder geflusht wird. Kommentar und Code sind jetzt
  korrekt. Ein Test belegt, dass die Originaldatei byte-, mtime- und
  modusgleich bleibt und keine Lock- oder Nebendateien entstehen.
- **R-13:** `validate.py` prüft zusätzlich: verbotene optionale Berechtigungen,
  `web_accessible_resources`, vollständige Katalogübernahme (527), HTTPS-Websites,
  keine HTML-String-Senken und die HTTPS-Prüfung im Popup.

### R-14 Metadaten in der Prozessliste (offen, Empfehlung)

`bw create item <base64-json>` übergibt die Metadaten als Argument: Anbietername,
Anmeldeadresse, Belegtext, URL. Kein Passwort. Andere lokale Benutzer können
die Argumente auf Linux über `/proc/<pid>/cmdline` lesen. Die offizielle CLI
akzeptiert den kodierten Inhalt auch über stdin. Der Wechsel wurde nicht
umgesetzt, weil er ohne echte Bitwarden-CLI nicht verifizierbar ist; das wäre
eine Anbieteraktion außerhalb der Grenzen.

**Empfehlung:** In einer eigenen Änderung `input=encoded` statt Argument
verwenden und manuell mit einem Test-Tresor prüfen.

### R-15 Manueller Scan ohne Lease (offen, dokumentiert)

`scan-imap` (manuell) und ein geplanter Lauf können gleichzeitig laufen. Folgen:
doppelte Abrufe, die per Fingerprint dedupliziert werden; Checkpoints können
zurückspringen, was erneute Abrufe auslöst, aber keinen Datenverlust; `last_scan`
wird überschrieben. Die Grenzen „nur lesend“ und „keine Secrets“ bleiben gewahrt.
SECURITY/SICHERHEIT weisen jetzt darauf hin.

**Empfehlung:** Den manuellen Scan dieselbe Lease beanspruchen lassen.

### R-16 Generische Fehlermeldungen (offen, Empfehlung)

`PATCH /api/accounts/*` und viele POST-Routen ersetzen jede `ValueError` durch
generische Meldungen. Hilfreiche Hinweise wie „Diese Anmeldeadresse gehört
bereits zu einem separaten Account“ erreichen die Oberfläche nie, obwohl es
deutsche Texte dafür gibt.

**Empfehlung:** Eine Unterklasse `UserFacingError(ValueError)` einführen, analog
zu `HandoffError`, und nur deren feste Texte durchreichen.

## 5. Dokumentation, Lizenzierung, GitHub-Reife

_Wird nach Abschluss der Teilprüfung ergänzt._

## 6. Toter Code und technische Schulden

_Wird nach Abschluss der Teilprüfung ergänzt._

## 7. Geprüft ohne Befund

- **Server:**
  - Bindet nur an `127.0.0.1`.
  - Prüft Host und Origin.
  - Bearer-Token im Speicher, Vergleich mit `hmac.compare_digest`.
  - Strenge CSP, `no-store`, `X-Frame-Options`, COOP/CORP.
  - Größenlimits, kein Chunked-Upload, kein Pfad-Traversal, keine Zugriffslogs.
- **IMAP:**
  - TLS ≥ 1.2 mit Hostname- und Zertifikatsprüfung.
  - `EXAMINE` (`readonly=True`), begrenztes `BODY.PEEK`, kein STORE, EXPUNGE,
    APPEND oder CLOSE.
  - Checkpoints werden erst nach dem Speichern der Belege geschrieben.
  - Feste Fehlermeldungen; Serverantworten erscheinen nie in Ausgaben.
  - Literale über dem Limit werden abgewiesen.
- **Importe:**
  - Symlinks werden übersprungen, Maildir verlangt `cur/` und `new/`.
  - Pro Nachricht gelten 2 MiB, pro Text 100 000 Zeichen und höchstens 100
    MIME-Teile.
  - Weitergeleitete und angehängte Nachrichten werden nicht ausgewertet.
- **Bitwarden:**
  - Exporte und erzeugte Einträge haben leere Passwortfelder.
  - Das Audit gibt nur gefunden / möglich / nichts gefunden mit Anzahl zurück.
  - Die CLI-Ausgabe wird nie angezeigt.
  - Transferjournal: Reservierung vor dem Schreiben; unklare Ergebnisse werden
    nie blind wiederholt.
  - Exporte überschreiben keine vorhandene Datei, die Rechte sind 0600.
- **Zustände:**
  - „Erledigt“ verlangt Prüfung, Bitwarden und Anmeldetest, bei Passwort-Login
    zusätzlich die Passwortänderung.
  - Eine offene Identitätsprüfung blockiert „Erledigt“ und den Export.
  - Ein veralteter Worker kann keinen Zeitplan reaktivieren.
- **Lizenzprüfung:**
  - Ed25519, Signatur über kanonisches JSON, strikte Felder.
  - Ohne mitgelieferten öffentlichen Schlüssel ist die Aktivierung deaktiviert.
- **Discovery:**
  - Offline als Standard; MX nur mit `--allow-dns`.
  - Zufällige TXID; Prüfung der Antwort gegen die Anfrage.
  - Schutz vor Zeigerschleifen.
- **UI:**
  - Keine `innerHTML`-, `eval`- oder `document.write`-Senken; dynamische Inhalte
    nur über `textContent`.
  - Links ausschließlich aus dem validierten HTTPS-Katalog.
  - `localStorage` enthält nur die Sprache.

## 8. Testnachweis der neuen Simulationen

Neue Datei `tests/test_review_simulations.py`. Sie nutzt einen echten Store, den
vorhandenen `FakeIMAP`, einen Fake-Keyring und eine steuerbare Uhr. Es entsteht
keine Netzwerkverbindung.

| Test | Absicherung |
| --- | --- |
| `test_long_scan_renews_its_lease_…` | R-01 |
| `test_disable_during_scan_stops_…` | R-02, Abmeldung und Belegerhalt |
| `test_revoke_during_scan_removes_keyring_entry_…` | R-02, Schlüsselbund geleert |
| `test_secret_never_reaches_profile_files_…` | Kein Secret in irgendeiner Profildatei |
| `test_malformed_message_is_counted_…` | Giftnachricht blockiert keine Folgescans; Checkpoint läuft weiter |
| `test_mbox_import_leaves_the_original_byte_identical` | Original unverändert (R-12) |
| `test_enabling_an_oauth2_schedule_warns_…` | R-09, Token weder ausgegeben noch gespeichert |
| `test_scheduler_pass_survives_unexpected_errors` | R-03 |
| `test_scheduler_pass_waits_for_a_running_browser_import` | R-03 |
| `test_startup_notice_discloses_…` | R-04, beide Sprachen |

Erweitert wurden außerdem:

- `tests/test_server.py` (R-08)
- `tests/test_i18n.py` (R-07)
- `tests/test_background.py`: Runner-Signatur mit `keep_alive`
- `scripts/browser_multi_account.py`: Abbruch und Bestätigung der Adressbindung
- `browser-companion/tests/validate.py` (R-13)
