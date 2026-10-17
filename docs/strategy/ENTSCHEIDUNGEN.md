# Entscheidungen zum Gesamtplan

Getroffen vom Owner am 16.10.2026, bevor die Umsetzung des
[Gesamtplans](README.md) begann. Sie gelten für alle folgenden Arbeitsschritte.

| Thema | Entscheidung | Folge |
| --- | --- | --- |
| Geplante IMAP-Scans mit gespeicherter Freigabe | **Behalten**, gehärtet, nicht ausgebaut | Zielbindung (Priorität 10) zuerst; kein weiterer Ausbau auf Basis gespeicherter Zugangsdaten |
| Zustandsmodell | [ADR-0001](../architecture/ADR-0001-zustands-und-freigabemodell.md) **angenommen** | Bestätigung getrennt, Verwerfen mit Grund, datierte Schritte mit Wiedervorlage, Tresor zweistufig |
| Pro-Ideen des Plans (P1–P6, A12, A21, A22) | **Alles als Free** umsetzen | Keine Edition „Pro“; alle Funktionen frei unter MPL-2.0 |
| Vorhandene Pro-Grundlage (Lizenzprüfung, Aktivierung, Seite „Pläne“) | **Entfernen** | ARGUS braucht zur Laufzeit keine Fremdbibliothek mehr; P6 „Offline-Lizenz“ entfällt |
| Profil-Sicherung | **Lokale, unverschlüsselte Sicherung** | Automatisch vor Migrationen, dazu `argus backup` und `argus restore` mit Rechten 0600; Schutz durch Datenträgerverschlüsselung; keine eigene Verschlüsselung, also kein neues Passwortsystem |
| Plattformen | **Linux, Windows, macOS** | Unit-Tests in der CI auf allen drei; Browserchecks auf Linux |
| Versionen | **Version je Releasepaket erhöhen, keine Releases** | Tags und GitHub-Releases legt der Owner selbst an |
| Dependabot-PRs | **Mergen bei grüner CI** | Nach Prüfung der Release Notes |
| Arbeitsweise | **Ein PR je Arbeitsschritt**, Merge nach grüner CI | Jeder Schritt ist auf `main` gesichert |
| Blockaden | **Konservativ überspringen** | Die sicherere Variante wählen oder den Punkt auslassen, Grund unten dokumentieren |

## Übersprungene oder angepasste Punkte

Wird während der Umsetzung fortgeschrieben.

- **S2, Pflicht-Checks:** Die neuen Jobs „Unit tests on windows-latest“ und
  „Unit tests on macos-latest“ laufen in jedem PR. Die Branch-Regeln von `main`
  verlangen weiterhin nur die fünf bisherigen Linux-Checks, weil nur der Owner
  sie in den GitHub-Einstellungen ändern kann. Gemergt wird trotzdem erst, wenn
  alle sieben Checks grün sind. Der Owner kann die beiden Jobs unter
  *Settings → Branches* als Pflicht-Checks ergänzen.
- **S2, Standardordner:** Das Standardprofil liegt auf allen Plattformen unter
  `~/.local/share/argus`. Ein plattformtypischer Ordner (etwa `%LOCALAPPDATA%`)
  bräuchte eine weitere Migration und ist kein Punkt des Plans; ein eigener
  Ordner geht mit `--data-dir`.
- **S4, Ablage der Sicherungen:** Standardmäßig liegen Sicherungen im Ordner
  `backups` des Profils, damit sie dieselben privaten Rechte haben. Geht der
  ganze Profilordner verloren, sind sie mit weg; dafür gibt es
  `backup --output`. Automatische Sicherungen werden auf die neuesten fünf
  begrenzt, eigene nie gelöscht.
- **S5, Abbildung der 1.x-Zustände:** Abweichend vom Wortlaut der
  ADR-Migrationstabelle gilt der Identitätsschritt für jeden bisher geprüften
  Account als erledigt, weil die 1.x-Prüfung die Anmeldung einschloss. MFA und
  Wiederherstellung sind Pflicht mit „nicht zutreffend“ als erlaubter Antwort;
  in 1.x ohne MFA abgeschlossene Accounts erhalten „nicht zutreffend“, damit kein
  abgeschlossener Account zurückgestuft und keine Prüfung erfunden wird. Details
  in ADR-0001, Abschnitt 8.
- **S9, Ausschlüsse nur für Domains außerhalb des Katalogs:** Für Katalogdienste
  gibt es das Verwerfen je Account (mit Grund und Rückgängig). Ein Ausschluss
  ganzer Katalogdomains würde echte Accounts verdecken und ist deshalb nicht
  vorgesehen. Hinweise ohne eindeutigen Account lassen sich nicht einem Account
  zuweisen; die Liste führt zum Dienst, wo du eigene Accounts anlegst oder
  zuordnest.
- **S4, Wiederherstellen nur über die CLI:** Das Dashboard nimmt keine
  Sicherungsdateien an. Wiederherstellen ersetzt die Datenbank, was bei
  laufendem Dashboard nicht sicher wäre; die Oberfläche nennt nur die Befehle.
- **S10, eigener Katalog nur im Profil:** Ergänzungen aus dem Dashboard landen
  in `my-providers.json` im Profil, nie im gemeinsamen Katalog; ein Vorschlag für
  alle läuft über die Vorlage im Repository. ARGUS speichert keine Mailinhalte,
  deshalb ordnet eine Ergänzung gespeicherte Hinweise erst beim erneuten Import
  der ursprünglichen E-Mails zu; bis dahin bleibt die Domain sichtbar und
  gekennzeichnet. Entfernen geht nur, solange kein Hinweis, keine Entscheidung
  und kein Schritt auf den Dienst verweist, damit nichts Bestätigtes verwaist.
  Gemeinsam genutzte Versanddienste stehen als feste Liste im Code; sie lassen
  sich weder ergänzen noch einem Dienst zuordnen.
- **S11, „Neu seit…“ hängt an einer ausdrücklichen Durchsicht:** ARGUS merkt
  sich keine Besuche, sondern nur, bis zu welcher Revision du Änderungen als
  gesehen markiert hast. Das ist nachvollziehbar, funktioniert gleich in
  Dashboard und CLI und entsteht nie durch bloßes Öffnen. Die Markierung geht
  nur vorwärts (später eingetroffene Hinweise bleiben neu) und lässt sich einmal
  zurücknehmen; sie gehört nicht ins Änderungsprotokoll, weil sie keine
  Entscheidung ist. Werbung, Bestellungen und Rücksetz-Anfragen werden nur
  gezählt, nicht einzeln vorgelegt. Bei vorhandenen Profilen gelten alle vor
  Schemaversion 5 gespeicherten Hinweise als gesehen, damit nach dem Update
  keine Flut alter Funde erscheint.
- **S12, Identitätsbeziehungen als Notizen der Person:** Postfach- und
  Anmeldebeziehungen werden nur ausdrücklich gesetzt und nur zu Accounts, die du
  bestätigt hast. Wie die Adressnotizen aus S9 stehen sie nicht im
  Änderungsprotokoll, sondern lassen sich direkt entfernen. Wird ein beteiligter
  Account verworfen oder ändert sich die Anmeldeart, bleibt die Notiz als
  inaktiv sichtbar statt still zu verschwinden. Ein Postfach- oder
  Anmelde-Account wird automatisch „Zuerst“; eine eigene Priorität geht immer
  vor. „Nach oben/unten“ tauscht genau zwei Positionen, damit Rückgängig die
  Reihenfolge exakt wiederherstellt.
- **S12, Prüfregel und Sitzungsbericht:** Die Prüfregel setzt nie selbst ein
  Datum, sondern schlägt es vor; übernommen wird es als gewöhnliches,
  rücknehmbares Prüfdatum beim Schritt „Anmeldung geprüft“, weil die erneute
  Prüfung fragt, ob der Account noch existiert und die Anmeldung noch stimmt.
  Liegt das Regeldatum in der Vergangenheit, wird morgen vorgeschlagen. Der
  Sitzungsbericht wird aus dem Zustand der Accounts abgeleitet, nicht
  mitprotokolliert, und folgt damit jedem Rückgängig. Gespeichert wird er nur
  über den Browser nach vollständiger Vorschau; die CLI gibt ihn nur aus.
- **S13, Pause und Vorgangszustände:** Die globale Pause sperrt alle neuen
  Vorgänge, auch selbst gestartete Importe und manuelle Scans, weil der Plan
  „neue Jobs sperren“ verlangt und eine Pause sonst unklar bliebe; die Oberfläche
  nennt den Grund und den Weg zurück. Laufende Vorgänge prüfen die Pause alle 25
  Nachrichten und enden als „pausiert“. Zusätzlich zu den Zuständen aus ADR-0001
  gibt es „uncertain“ für eine Bitwarden-Übertragung mit unklarem Ausgang
  (Priorität 12) und das abgeleitete „unterbrochen“ für Vorgänge, die seit zehn
  Minuten nichts gemeldet haben. Geplante Scans stehen als wartend in der
  Liste statt als Warteschlangen-Datensatz, weil ihr Zeitplan die einzige Quelle
  bleibt.
- **S13, Freigabe-Datensatz:** Die einzige dauerhafte Freigabe in ARGUS ist die
  für geplante Scans. Ihr Datensatz bleibt der bestehende Zeitplan (Ziel-
  Fingerabdruck, Höchstmenge, Abstand, jetzt mit Freigabedatum) statt einer
  zweiten Tabelle, damit es keine zwei Wahrheiten gibt; Profil und Zweck ergeben
  sich aus dem Speicherort und der Art. Alle anderen externen Zugriffe werden je
  Aufruf freigegeben und in der Kontrolle so benannt. Der Widerruf ist im
  Dashboard möglich, weil er nur lokal löscht; eine neue Freigabe braucht
  weiterhin das Terminal, weil dort das Passwort eingegeben wird.
- **S14, Index verarbeiteter Nachrichten:** „Unverändert“ heißt: gleicher
  Inhalts-Fingerabdruck unter gleichen eigenen Adressen, gleichem Katalog und
  gleicher Regelversion. Dateinamen, Größen oder Zeitstempel entscheiden nie.
  Der Index ersetzt die frühere Mehrfachauswertung; „Duplikate“ zählen nur noch
  Nachrichten, die erneut ausgewertet wurden und dasselbe Ergebnis brachten
  (etwa mit `--recheck`). Das Budget zählt nur neue Arbeit, damit ein
  wiederholter Lauf tatsächlich weiterkommt.
- **S15, Ordnerüberwachung ohne Dienst im Hintergrund:** Die Überwachung läuft
  nur im Prozess des Dashboards (wie geplante Scans) und fragt den Ordner in
  festem Abstand ab, statt Betriebssystem-Ereignisse zu nutzen; das hält die
  Laufzeit bei der Standardbibliothek und macht jeden Durchgang als Vorgang
  sichtbar. Größe und Änderungszeit wählen nur Kandidaten vor; ob eine Datei neu
  ist, entscheidet der Inhalts-Fingerabdruck. Freigegeben wird nur im Terminal;
  beendet werden kann auch im Dashboard. Netzwerk-Mounts unter Linux und macOS
  lassen sich ohne Zusatzbibliothek nicht sicher erkennen; abgelehnt werden
  daher UNC- und `//`-Pfade, und die Dokumentation verlangt einen lokalen Ordner.
- **S16, Downloads im Übergabejournal:** Ob eine heruntergeladene Datei
  importiert wurde, kann ARGUS nicht wissen. Ein Download zählt deshalb als
  Übergabe mit offenem Ausgang („heruntergeladen“) und sperrt einen weiteren
  Download oder eine CLI-Übertragung desselben Accounts, bis die Person festhält,
  was sie im Tresor gefunden hat. Das schützt vor dem häufigsten Duplikat (eine
  Datei zweimal importiert), kostet aber einen Klick, wenn eine Datei verloren
  ging. Ein bestätigter Import setzt den Tresor-Schritt wie die CLI auf
  „vorbereitet“, nie auf „erledigt“.
- **S17, Profile als Ordner:** Ein benanntes Profil ist ein eigener Ordner
  unter `argus-profiles` neben dem Standardprofil; es gibt keinen gemeinsamen
  Index und keine profilübergreifende Ansicht, damit die Trennung strikt bleibt.
  Das Standardprofil bleibt, wo es ist. Der Verlauf speichert je Tag nur
  sieben Zahlen; Berichte enthalten Adressen nur nach ausdrücklicher Wahl und
  werden wie der Sitzungsbericht vollständig angezeigt, bevor der Browser sie
  speichert.
- **S18, Umzugsplan und Vorlagen ohne Identitätswechsel:** Ein Umzugsplan
  verschiebt keine Anmeldeidentität, weil eine Identität in ADR-0001 fest an
  ihren Account gebunden ist; der Plan ist eine geordnete Liste mit Häkchen,
  und neue Hinweise an die neue Adresse erscheinen wie gewohnt. Vorlagen kennen
  nur zwei Wirkungen (Arbeitsliste, Prüfdatum) und keine Bedingungslogik, damit
  sie nie zu Skripten werden. P6 (Offline-Lizenz) entfällt nach der
  Entscheidung „alles als Free“.
- **S19, Maskierung nur in der Anzeige:** Die maskierte Ansicht ersetzt
  E-Mail-Adressen beim Darstellen; gespeicherte Daten, Exporte und Berichte
  bleiben unverändert (Berichte haben eigene Datensparsamkeit). Die Wahl liegt im
  Browser-Speicher, weil sie eine Ansichtsvorliebe ist. Barrierefreiheit wird mit
  einer einfachen Regel im Browsertest gesichert (jede sichtbare Schaltfläche und
  jedes Feld braucht einen zugänglichen Namen), nicht mit einem externen
  Prüfwerkzeug, damit die Prüfung ohne zusätzliche Abhängigkeit läuft.
