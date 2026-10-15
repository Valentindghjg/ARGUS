# Security worklist / Sicherheits-Arbeitsliste

## English

The worklist guides you through discovered accounts and persists locally across
browser and application restarts. It does not scan on a schedule or change any
provider password automatically.

1. Open **Security worklist**. Select discovered accounts and choose **Add selected
   accounts**. Candidates appear by security priority; the queue preserves the
   order in which you add them. An account can only appear once.
2. Choose **Continue with next account**. The detail dialog explains the next
   missing step: review, Bitwarden assignment, password change, sign-in test or
   explicit completion. You can also add a discovered account from its dialog.
3. Use **Prepare Bitwarden** inside the dialog to select that account alone for a
   metadata export or the optional CLI handoff. Assign an existing vault item
   instead when you already have one.
4. Open the documented password-settings link where available. Otherwise open
   the official homepage and navigate to its security settings yourself. Only
   Google, Apple and GitHub currently have separately documented direct links.
5. Generate and save the new password in Bitwarden, confirm the change at the
   provider, then test sign-in. Mark only the steps you actually completed.
   SSO and passkey accounts do not require a separate password change.
6. Choose **Mark as done**. While viewing the worklist, the dialog advances to the
   next available account. Required checkboxes alone do not mark an account done.
7. **Pause worklist** preserves your place. **Defer** skips one queued account
   until you restore it. Removing an account removes only its queue membership,
   not its evidence, checklist or vault entry. Pausing this list does not pause a
   separately started mail import.

The list tracks each account identity separately, including several accounts
at the same provider. See [separate accounts](ACCOUNTS.md). Optional scheduled mailbox
scans and the browser companion are separate features: neither changes this
worklist or treats a site visit as account evidence.

## Deutsch

Die Arbeitsliste führt dich durch gefundene Accounts und bleibt lokal über
Browser- und Programmneustarts hinweg erhalten. Sie startet keine zeitgesteuerten
Scans und ändert keine Anbieterpasswörter automatisch.

1. Öffne **Sicherheits-Arbeitsliste**, wähle gefundene Accounts und klicke auf
   **Ausgewählte Accounts hinzufügen**. Vorschläge sind nach Sicherheitspriorität
   sortiert; die Liste behält die Reihenfolge beim Hinzufügen. Jeder Account
   erscheint höchstens einmal.
2. Wähle **Mit dem nächsten Account fortfahren**. Im Detaildialog steht der nächste
   offene Schritt: Prüfung, Bitwarden-Zuordnung, Passwortwechsel, Anmeldetest oder
   ausdrücklicher Abschluss. Du kannst einen gefundenen Account auch direkt im
   Dialog zur Liste hinzufügen.
3. **Bitwarden vorbereiten** im Dialog wählt genau diesen Account für den
   Metadatenexport oder die optionale CLI-Übergabe aus. Nutze stattdessen einen
   vorhandenen Tresoreintrag, wenn du schon einen hast.
4. Öffne den dokumentierten Passwortlink, falls vorhanden. Sonst öffne die
   offizielle Startseite und gehe selbst zu den Sicherheitseinstellungen. Aktuell
   sind nur für Google, Apple und GitHub direkte Links separat dokumentiert.
5. Erzeuge und speichere das neue Passwort in Bitwarden, bestätige den Wechsel
   beim Anbieter und teste die Anmeldung. Hake nur tatsächlich erledigte Schritte
   ab. SSO- und Passkey-Accounts brauchen keinen separaten Passwortwechsel.
6. Wähle **Als erledigt markieren**. In der Arbeitslistenansicht wechselt der
   Dialog zum nächsten verfügbaren Account. Abgehakte Pflichtschritte allein
   schließen keinen Account automatisch ab.
7. **Arbeitsliste pausieren** behält deinen Platz. **Zurückstellen** überspringt
   einen Account, bis du ihn wieder aufnimmst. Entfernen löscht nur den Eintrag
   aus der Arbeitsliste; Belege, Checkliste und Tresoreintrag bleiben erhalten.
   Das Pausieren dieser Liste pausiert keinen separat gestarteten Mailimport.

Die Arbeitsliste verwaltet jeden Account getrennt, auch mehrere Accounts beim
selben Anbieter. Siehe die [Mehrkonto-Anleitung](ACCOUNTS.md). Optionale geplante
Mail-Scans und der Browser-Begleiter sind
getrennte Funktionen: Sie ändern diese Arbeitsliste nicht und werten einen
Webseitenbesuch nicht als Account-Beleg.
