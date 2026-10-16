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
| Keine Veröffentlichung | Auftrag | Kein Release, Tag, PR, Issue oder Kommentar; nur Commits auf einem Branch (siehe 9) |

## 2. Ausgeführte Prüfungen

| Prüfung | Ergebnis |
| --- | --- |
| `python -m unittest discover -s tests` (Python 3.13) | vorher 166 OK → nachher **178 OK** |
| `ruff check --select F` (Pyflakes-Regeln) über das ganze Repository | nachher ohne Befund |
| `node --check` für `app.js` und `popup.js` | OK |
| `browser-companion/tests/validate.py` (verschärft) | OK, 527 Dienste |
| Wheel/Sdist bauen, in sauberer venv installieren, `--help` en/de, `demo`, `report`, `list-accounts` | OK; Metadaten jetzt mit `License-Expression: MPL-2.0` und ARGUS-URLs |
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
| R-14 | Bitwarden | `bw create item <base64>` legt Metadaten (Name, Anmeldeadresse) in der Prozessliste offen | niedrig | **behoben** (Nachbesserung, siehe 11) |
| R-15 | IMAP | Manueller `scan-imap` nutzt die Scheduler-Lease nicht | niedrig | **behoben** (siehe 11) |
| R-16 | Server/UI | Spezifische Validierungsfehler werden durch generische Meldungen ersetzt | niedrig | **behoben** (siehe 11) |
| R-17 | Begleiter | Subdomain-Hinweis und Popup nur auf Englisch | info | **behoben** (siehe 11) |
| R-18 | i18n | 22 ungenutzte Übersetzungsschlüssel | info | **behoben** (siehe 11) |
| D-01 | Doku | Aussagen widersprachen dem Code: „keine Laufzeitabhängigkeiten“, „IMAP-Secrets nie gespeichert“, „kein Tresorzugriff“, „ohne bestehende Einträge zu lesen“, „kein Aktivierungspfad“ | mittel | **behoben** |
| D-02 | Paket | `pyproject.toml` verwies auf ein anderes Repository (`account-compass`) | mittel | **behoben** |
| D-03 | Lizenz | Keine Lizenz-Metadaten im Paket (PyPI hätte keine Lizenz gezeigt) | mittel | **behoben** |
| D-04 | Lizenz/Schlüssel | `data/*.pem` wurde gepackt; ein versehentlich abgelegter privater Schlüssel wäre im Wheel gelandet; der Generator schrieb überallhin | mittel | **behoben** |
| D-05 | Doku | Wechsel zu MPL-2.0 und 1.6.1 fehlten im Changelog | niedrig | **behoben** |
| D-06 | GitHub | Dependabot überwachte nur Actions, nicht `cryptography` | niedrig | **behoben** |
| D-07 | Code | Toter Code und ungenutzte Importe; ResourceWarning in einem Test | niedrig | **behoben** |
| D-08 | GitHub | Dependabot-Branches basieren auf einem Stand vor MPL/1.7 | mittel | offen (Owner) |
| D-09 | GitHub | Eine früher entfernte persönliche Domain ist noch in der Git-Historie | mittel | offen (Owner) |
| D-10 | Lizenz | Kein Copyright-Inhaber, keine SPDX-Kopfzeilen; Lizenz für Katalogdaten, Doku und Bilder ungeklärt | niedrig | **behoben** nach Owner-Entscheidung (siehe 11) |
| D-11 | Projekt | Sechs Namen (ARGUS, Account Compass, Account-Finder, …) | niedrig | **behoben** nach Owner-Entscheidung (siehe 11) |
| D-12 | GitHub | Melde- und Kontaktweg hängt an optionalen GitHub-Funktionen | niedrig | **behoben** nach Owner-Entscheidung; Aktivierung in GitHub durch den Owner |
| D-13 | Doku | Lücken zwischen englischer und deutscher Doku, veraltete Screenshots | niedrig | **behoben** bis auf Release-Screenshots (siehe 11) |
| D-14 | `main` | Der Branch `main` ist serverseitig gegen direkte Pushes geschützt | info | siehe 9 |

## 4. Befunde im Detail

### R-01 Lease-Ablauf bei langen geplanten Scans – behoben

`RUN_LEASE_SECONDS` betrug 5 Minuten, die Lease wurde aber nie verlängert. Ein
Lauf mit dem erlaubten Maximum von 10 000 Nachrichten dauert bei 0,15 s Pause
pro Nachricht mindestens 25 Minuten. Danach konnte ein zweiter Dashboard-Prozess
desselben Profils die Lease übernehmen und das Postfach parallel öffnen. Die
Sicherheitsdokumentation sagte das Gegenteil zu.

**Fix** (`background.py`): Die Service-Klasse gibt dem Runner
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
`argus_security/data/license_public_key.pem`, der ausgeliefert werden darf.

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

Version 1.16.0 ist überall konsistent: `pyproject.toml`, `__init__.py`,
Oberfläche und beide READMEs. Der Katalog hat wie angegeben 527 Dienste.
`LICENSE` ist der vollständige MPL-2.0-Text. Die CI ist solide: `contents: read`,
per SHA gepinnte Actions, `persist-credentials: false`, Timeouts und eine Matrix
für 3.11–3.14. `examples/` enthält nur synthetische Empfänger
(`example.invalid`). Ein Scan der gesamten Historie fand keine Schlüssel oder
Tokens.

**Behoben:**

- **D-01:** CONTRIBUTING, PLAN/PLAN_DE, PRIVACY (en/de), FREEMIUM/FREEMIUM_DE
  und PUBLISHING beschreiben jetzt:
  - die Abhängigkeit von `cryptography` und das optionale `keyring`;
  - die Schlüsselbund-Ausnahme für geplante Scans;
  - die Bitwarden-CLI-Übergabe und die nur lesende Prüfung;
  - den deaktivierten Aktivierungspfad.

  Außerdem nennen die READMEs den richtigen Ordnernamen, und das Bug-Template
  verwendet eine aktuelle Beispielversion.
- **D-02/D-03:** In `pyproject.toml` stehen jetzt:
  - `license = "MPL-2.0"` und `license-files` (PEP 639), dafür `setuptools>=77`;
  - Repository-URLs auf `Valentindghjg/ARGUS`.
- **D-04:**
  - Gepackt wird nur noch `data/license_public_key.pem`.
  - `.gitignore` schließt `*.pem` und `*.key` aus, außer dem öffentlichen
    Schlüssel.
  - `scripts/generate_license_keys.py` verweigert einen privaten Schlüssel
    innerhalb des Repositorys.
  - Simulationstest: `test_key_generator_refuses_private_key_inside_the_repository`.
- **D-05:** Der Wechsel zu MPL-2.0 (ab 1.6.0) ist in beiden Changelogs
  vermerkt, 1.6.1 in AENDERUNGEN.
- **D-06:** `dependabot.yml` überwacht zusätzlich das `pip`-Ökosystem.

**Offen, Owner-Entscheidung:**

- **D-08:** Die offenen Dependabot-PRs (checkout 7.0.1, setup-python 7.0.0)
  ändern nur die SHA-Zeilen in `ci.yml` und lassen sich sauber mergen. Ihre CI
  lief aber gegen einen alten Stand. Empfehlung: auf GitHub `@dependabot rebase`
  kommentieren, dann die Release Notes von v6 → v7 prüfen. In dieser Review
  wurde auf GitHub bewusst nichts gepostet.
- **D-09:** Eine in 42a58fc entfernte persönliche Domain steht noch in älteren
  Commits. Ob vor einer Veröffentlichung die Historie umgeschrieben wird,
  entscheidet der Owner.
- **D-10:** Für SPDX-Kopfzeilen (`# SPDX-License-Identifier: MPL-2.0`) muss
  zuerst feststehen, wer als Copyright-Inhaber genannt wird. `LICENSING.md` deckt
  nur „Quellcode“ ab. Lizenz für `providers.json`, `translations.json`, Doku und
  PNGs festlegen. Das Feld `notes` im Katalog („public-domain catalog“) wirkt wie
  eine Gemeinfreiheitserklärung. Rechtlich prüfen.
- **D-11:** ARGUS, Account Compass, Account-Finder, `local-account-finder`,
  `account-finder` und `AccountFinder` vereinheitlichen. Achtung: Der
  Schlüsselbund-Dienstname und das Datenverzeichnis brauchen eine Migration,
  sonst gehen gespeicherte Freigaben und Profile verloren.
- **D-12:** SECURITY.md stützt sich auf „private vulnerability reporting“, falls
  verfügbar, ohne Ausweichkontakt. Auch CODE_OF_CONDUCT nennt keinen Kontakt.
  SUPPORT verweist auf Discussions, die eventuell deaktiviert sind.

**Offen, niedrig (D-13):**

- README_DE fehlen CI-Badge, Vorschau und die Zeilen zu Datenschutz und Support.
- AENDERUNGEN beginnt erst bei 1.6.
- TEST_REPORT nennt für 1.6 zwei verschiedene Gruppenzahlen.
- Die Screenshots in `docs/preview/` stammen aus 1.6.
- In der CI sind `build` und `playwright` nicht exakt gepinnt.
  `cancel-in-progress` bricht auch Läufe auf `main` ab.

## 6. Toter Code und technische Schulden

**Entfernt (D-07):**

- `Store.known_fingerprints` (ohne Aufrufer)
- `Evidence.public` (ohne Aufrufer; `snapshot` bildet dasselbe Label selbst)
- ungenutzte Importe in `cli.py` und `tests/test_server.py`, ungenutztes `as exc`
  in `imap_client.py`, eine ungenutzte Variable in `tests/test_workflow.py`
- die No-op-Zuweisung `secret = "" if "secret" in locals() else ""` in
  `background.py`
- `sqlite3.connect` in `tests/test_improvements.py` wird jetzt geschlossen; die
  ResourceWarning entfällt

**Ursprünglich belassen; Stand nach der Nachbesserung in Abschnitt 11:**

- **Legacy-Tabellen:** `accounts`, `work_queue` und `bitwarden_handoffs` werden
  in jedem neuen Profil angelegt. Gelesen werden sie nur einmal, von
  `migrate_instances`. Nach der Migration bleiben alte Metadaten wie
  `manual_email` darin liegen. Empfehlung: nur noch bei Altprofilen anlegen und
  nach erfolgreicher, gesicherter Migration leeren. Die Migration muss dafür
  gesondert getestet werden.
- **Aliasse:** `BackgroundScanService.start` und `stop` sind Aliasse von
  `configure` und `disable`. Ein Paar genügt.
- **Testhelfer:** `Store.add_evidence` wird nur von Tests genutzt.
- **Doppelter Code:** `write_new` steht doppelt in den beiden Herausgeber-Skripten.
- **Versionsangabe:** Die Version steht an vier Stellen. Empfehlung:
  `dynamic = ["version"]`.
- **Schreibender Lesezugriff:** `Store.snapshot()` schreibt bei jedem GET
  (`BEGIN IMMEDIATE` + `synchronize_instances`). Das ist funktional korrekt,
  aber ein Lesezugriff sollte keine Schreibsperre brauchen.
- **Übersetzungsschlüssel:** 22 Schlüssel werden nicht mehr verwendet (alte
  Fragmente und Formulierungen). Sie bleiben vorerst, weil gespeicherte
  Altwerte sie eventuell noch anzeigen. Vor dem Löschen gegen gespeicherte
  Belege und Caveats prüfen.
- **Statischer Platzhaltertext:** In der Dashboard-Karte „Secure your next
  account“ steht Platzhaltertext ohne `data-i18n`. Das Skript ersetzt ihn sofort,
  sichtbar ist er nur bis zum ersten Laden.
- **Zurückgestellte Accounts:** Mit „skipped“ markierte Accounts können weiter
  als nächster geführter Account vorgeschlagen werden. Das ist eine
  UX-Entscheidung, keine Sicherheitslücke.

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

Außerdem: `tests/test_review_simulations.py::PublisherKeySimulation` (D-04).

## 9. Hinweis zum Abschluss

Gewünscht war ein Commit direkt auf `main`. Der Push wurde vom Server abgelehnt
(`protected branch hook declined`). Die Ergebnisse liegen deshalb auf dem Branch
`claude/security-review-2026-10`. Einen Pull Request legt diese Review nicht an;
das Mergen entscheidet der Owner.

## 10. Empfohlene nächste Schritte

Stand nach der Nachbesserung (Abschnitt 11):

1. Den Branch `claude/security-review-2026-10` prüfen und in `main` übernehmen.
   Die CI mit Python 3.11–3.14 und Browserchecks läuft dann automatisch.
   Wegen der Umbenennung sollte die nächste Version eine neue Hauptversion sein
   (2.0.0).
2. In GitHub unter **Settings → Security** die private Meldefunktion aktivieren.
   SECURITY.md und CODE_OF_CONDUCT.md nennen sie als einzigen privaten Weg.
3. D-08: Auf den beiden Dependabot-PRs `@dependabot rebase` kommentieren, dann
   die Release Notes von v6 → v7 prüfen.
4. D-09: Entscheiden, ob die Git-Historie vor einer Veröffentlichung
   umgeschrieben wird. Das braucht einen Force-Push auf den geschützten Branch
   `main` und gehört nicht in eine automatische Sitzung.
5. Die Bitwarden-Übergabe über die Standardeingabe (R-14) einmal manuell mit
   einem leeren Test-Tresor bestätigen.
6. Beim nächsten Release die Vorschaubilder neu erzeugen; die aktuellen
   Release-Bilder zeigen noch „Account Compass“.
7. Die Übergabe `docs/CLAUDE_CODE_HANDOFF.md` und das Strategie-PDF ins
   Repository legen und diesen Bericht dagegen abgleichen.

## 11. Nachbesserung

Nach der Review wurden auf Wunsch alle offenen Punkte bearbeitet, die sich
innerhalb der Sicherheitsgrenzen beheben ließen. Die Owner-Fragen wurden vorher
geklärt:

| Frage | Entscheidung |
| --- | --- |
| Copyright-Inhaber | „ARGUS contributors“ mit SPDX-Kopfzeile in jeder Quelldatei |
| Lizenz für Daten, Doku, Bilder | Alles MPL-2.0 |
| Projektnamen | Komplett auf ARGUS: Paket `argus_security`, Distribution `argus-account-security`, Befehl `argus` |
| Meldeweg | Nur die private Meldefunktion von GitHub |

### Umbenennung (D-11)

- **Paket und Befehle:** Das Paket heißt `argus_security`; `python -m argus_security`
  und der Befehl `argus` lösen `account_finder` ab. Ein schmales
  Alias-Paket `account_finder` hält `python -m account_finder` und
  `account-finder` mit Hinweis lauffähig. Es soll in einer späteren Version
  entfallen.
- **Distributionsname:** `argus-account-security`, weil `argus` auf PyPI vergeben
  ist. Ein Python-Paket `argus` hätte sich mit dem fremden Paket überschrieben.
- **Profilordner:** Das Standardprofil wandert einmalig und atomar per
  `rename` von `~/.local/share/account-finder` nach `~/.local/share/argus`.
  Dateien und Rechte bleiben gleich. Behandelte Sonderfälle:
  - ein bereits vorhandener neuer Ordner;
  - ein Symlink als Altordner, der nicht verfolgt wird;
  - zwei gleichzeitig startende Prozesse;
  - eine fehlgeschlagene Verschiebung.

  Ein ausdrückliches `--data-dir` wird nie verschoben. Der Dienstname im
  Schlüsselbund hieß bereits „ARGUS IMAP authorization“ und braucht keine
  Migration.
- **Editionen und Lizenz:** Die Editionen heißen ARGUS Free/Pro, die
  Lizenzprodukt-ID ist `argus-pro`. Unter der alten ID war mangels
  öffentlichem Schlüssel noch keine Lizenz ausstellbar.
- **Bitwarden:** Neue Einträge tragen das Feld `ARGUS-Account-ID`, Ordner und
  Notizen beginnen mit „ARGUS“. Die nur lesende Prüfung erkennt weiterhin das
  alte Feld `Account-Finder-ID`.
- **Browser-Sprache:** Der Speicherschlüssel `account-finder.language` wird
  einmal gelesen und durch `argus.language` ersetzt.
- **Bewusst unverändert:** die interne Markierung
  `X-Account-Finder-Headers-Only`. Sie ist Teil des Nachrichten-Fingerabdrucks;
  eine Änderung hätte Belege großer Nachrichten verdoppelt.

### Sicherheitspunkte

- **R-14:**
  - `_run_cli` übergibt Eintragsdaten per `input=` an `bw create item`;
    Statusabfragen erhalten weiterhin `stdin=DEVNULL`.
  - Tests prüfen, dass die Befehlszeile nur `bw create item` enthält.
  - Laut offizieller Doku liest die CLI den kodierten Inhalt von stdin. Eine
    manuelle Bestätigung mit einem Test-Tresor steht noch aus (Schritt 5 in 10).
- **R-15:** Neues Modul `mailbox_lease.py`: eine prozessübergreifende
  Postfach-Lease aus Token, Art und Ablaufzeit. Ihre Grundlage ist die neue,
  gemeinsame Funktion `atomic_meta_update` in `store.py`; der Zeitplan nutzt
  dieselbe Funktion statt eigenem Transaktionscode.
  - Ein manueller Scan nimmt die Lease vor der Passwortabfrage.
  - Ein geplanter Lauf gibt seinen Anspruch unverändert zurück, wenn das
    Postfach belegt ist.
  - Beide verlängern die Lease zwischen Nachrichten und brechen ab, wenn sie
    verloren geht.
  - Abgelaufene oder beschädigte Einträge blockieren nie.
- **R-16:** Neue Klasse `UserFacingError(ValueError)` in `errors.py`.
  `LicenseError`, `HandoffError` und `BitwardenCliError` erben davon.
  - Feste Regelmeldungen aus Store, Arbeitsliste, Bitwarden und Server reicht das
    Dashboard jetzt durch und übersetzt sie.
  - Andere Fehler bleiben allgemein.
  - Ein AST-Test verlangt für jede dieser Meldungen einen konstanten Text mit
    deutschem Eintrag; Nutzerdaten können so nicht hineingeraten.
  - Netzwerkfehler des Browsers erscheinen jetzt als „Lokale Anfrage
    fehlgeschlagen“.
- **R-17:** Der Begleiter nutzt `_locales/en|de` und `chrome.i18n`, also keine
  zusätzliche Berechtigung. Er baut seinen Katalog über die `Registry` der
  Anwendung. `validate.py` führt `popup.js` unter Node mit simulierten
  Browser-APIs aus, auf Deutsch und Englisch, gegen:
  - Lookalike-Domains;
  - fremde Subdomains;
  - `http:`, `file:` und Browserseiten;
  - verschachtelte Katalogdomains.
- **R-18:** Die 22 Schlüssel stammten weder aus gespeicherten Belegen noch aus
  Hinweisen; sie wurden entfernt. Ein neuer Test verhindert ungenutzte Einträge.
  Dabei fiel ein doppelter JSON-Schlüssel („Ready“) auf; er ist ebenfalls
  bereinigt.

### Technische Schulden aus Abschnitt 6

- **Legacy-Tabellen:** Neue Profile legen sie nicht mehr an (`CORE_SCHEMA` und
  `LEGACY_SCHEMA` sind getrennt). `migrate_instances` prüft vorhandene
  Alttabellen selbst, auch unvollständige Altstände. Bestehende Alttabellen
  werden nicht geleert; sie bleiben als Quelle für ein Zurückgehen auf eine
  ältere Version.
- **Aliasse:** `start`/`stop` sind entfernt; `configure`/`disable` bleiben.
- **Doppelter Code:** `write_new` liegt jetzt einmal in
  `scripts/publisher_files.py`.
- **Version:** Es gibt eine einzige Quelle, `argus_security.__version__`.
  `pyproject.toml` liest sie dynamisch, und das Dashboard setzt sie zur Laufzeit
  ein.
- **Platzhaltertexte:** Die Karte „Secure your next account“ hat jetzt
  `data-i18n` und deutsche Texte.
- **Zurückgestellte Accounts:** Status „skipped“ (Anzeige „Zurückgestellt“)
  schlägt der geführte Ablauf nicht mehr vor.
- **Bewusst belassen:**
  - `Store.snapshot()` sperrt beim Lesen für Schreibzugriffe, weil dabei Accounts
    synchronisiert werden. Ein verzögerter Lock-Aufstieg könnte unter Last
    `SQLITE_BUSY` statt eines Wartens auslösen; die Konsistenz geht vor.
  - `Store.add_evidence` bleibt als kleine, getestete API.

### Lizenz, Kontakt und Doku

- **Lizenz:**
  - Alle 51 Quelldateien tragen `SPDX-License-Identifier: MPL-2.0` und
    „Copyright (c) 2026 ARGUS contributors“.
  - Ein Test erzwingt das für neue Dateien.
  - `LICENSING.md` stellt Daten, Doku und Bilder unter MPL-2.0 und grenzt fremde
    Marken ab.
  - Der Katalog heißt nicht mehr „public-domain catalog“.
- **Kontakt:** SECURITY.md und CODE_OF_CONDUCT.md nennen nur noch die private
  Meldefunktion von GitHub. Fehlt sie, gibt es eine Regel ohne Details;
  PUBLISHING.md markiert die Aktivierung als Pflicht.
- **Doku:**
  - README_DE hat jetzt CI-Badge, Vorschau und die Tabellenzeilen zu
    Datenschutz und Hilfe; beide Modultabellen sind vollständig.
  - AENDERUNGEN enthält 1.0–1.5, die 1.6-Zählung im TEST_REPORT ist erläutert.
- **CI:**
  - `build==1.6.1` und `playwright==1.64.0` sind festgelegt.
  - `cancel-in-progress` gilt nur noch für Pull Requests.
  - Der Paket-Smoke-Test prüft zusätzlich die Befehle `argus` und `account-finder`.

### Nachweis

Durchgeführt wurden:

- 202 Python-Tests (vorher 178), auch mit `ResourceWarning` als Fehler
- `ruff check --select F`, ohne Befund
- `node --check` für alle Skripte
- Begleiter-Validierung mit Verhaltenssimulation
- Wheel-Build mit Installation und Smoke-Test in einer sauberen Umgebung
- 24 Chromium-Prüfgruppen (vorher 23), ohne Seitenfehler und ohne externe
  Anfragen; neu ist die Übernahme der alten Sprachwahl

Neue Testdateien:

- `tests/test_rename_migration.py`
- `tests/test_followup_simulations.py`

Erweitert wurden `test_i18n`, `test_instances`, `test_licensing`,
`test_workflow` und `test_store`.

Testschlüssel für die Herausgeber-Werkzeuge entstanden nur im temporären
Scratchpad und wurden gelöscht. Es gab keine echten Postfächer, Tresore,
Anbieter oder Veröffentlichungen.
