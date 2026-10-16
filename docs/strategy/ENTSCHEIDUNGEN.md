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
