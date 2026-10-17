# Eine vollständige Demo in fünf Schritten

[English](DEMO.md)

Die Demo zeigt den ganzen Weg vom Import bis zur Übergabe an Bitwarden, mit 18
erfundenen E-Mails an zwei erfundene Adressen. Sie berührt weder dein Profil
noch dein Postfach oder deinen Vault und verbindet sich nie mit dem Internet.

```bash
python -m argus_security --language de --data-dir .local/demo demo --serve --open
```

Die Demo braucht einen eigenen Ordner; ARGUS lädt sie nicht in ein Profil mit
deinen eigenen Adressen. Die Übersicht zeigt dann „Was diese Demo zeigt“ mit den
schwierigen Fällen und die Liste „Probier diesen Weg“. Jeder Eintrag öffnet die
passende Ansicht.

1. **Neu seit…** Alles, was der Import gefunden hat, ist neu: zu welchen
   Anbietern es Hinweise gibt, welche bestätigt sind und was du zuerst ansehen
   solltest. „Als gesehen markieren“ setzt die Marke; der nächste Import zeigt
   nur, was sich seitdem geändert hat.
2. **Unklares.** Hier steht alles, was ARGUS nicht für dich entscheiden kann:
   Hinweise von Amazon (Gastbestellung), eBay (Passwort zurücksetzen) und
   Zalando (Newsletter) ohne Account, eine Domain außerhalb des Katalogs
   (`new-service.example`) und die ähnlich aussehende Absenderdomain
   `github.com.attacker.example`, die nicht als GitHub gilt.
3. **Sicherheits-Arbeitsliste.** PayPal ist bereits geprüft. Der nächste Schritt
   ist, den Login in Bitwarden zu speichern; die Checkliste erklärt, warum, und
   was als erledigt zählt. GitHub ist abgeschlossen, mit je einem Account pro
   eigener Adresse; Notion meldet sich per Single Sign-on an und hat keinen
   eigenen Passwortschritt.
4. **Bitwarden vorbereiten.** Sieh dir die Übergabe für die Accounts an, die du
   auswählst. Die JSON-Datei enthält Namen, Anmeldeadressen und Links, nie
   Passwörter. In einen Vault wird erst geschrieben, wenn du einen Schritt mit
   der Bitwarden-CLI bestätigst.
5. **Fortschrittsbericht.** Zurück in der Übersicht siehst du einen Bericht nur
   mit Zahlen oder mit einer Zeile pro Aufgabe. Anmeldeadressen stehen nur
   darin, wenn du sie hinzufügst.

Entferne die Demo, indem du `.local/demo` löschst. Für deine eigenen E-Mails
nimm einen anderen Ordner oder das Standardprofil; siehe den README-Abschnitt
„Dein echtes Profil“.
