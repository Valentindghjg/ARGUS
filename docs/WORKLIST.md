# Security worklist / Sicherheits-Arbeitsliste

## English

The worklist guides you through discovered accounts and persists locally across
browser and application restarts. It does not scan on a schedule or change any
provider password automatically.

1. Open **Security worklist**. Choose **Secure next account** to start one local
   highest-priority incomplete account, **Build priority worklist** to add up to
   ten more open accounts in deterministic priority order, or select discovered
   accounts and choose **Add selected accounts**. The exact candidates and their
   next local steps are shown before the builder button can be used. The priority
   builder asks for confirmation and preserves existing queue positions. These
   actions never change a checklist, vault item or provider account by themselves.
2. Choose **Continue with next account**. The detail dialog explains the next
   missing step: review, Bitwarden assignment, password change, sign-in test or
   explicit completion. You can also add a discovered account from its dialog.
3. Use **Open Bitwarden preparation** for the current guided account only, or
   **Prepare Bitwarden** for a manual selection. The guided CLI handoff requires
   an additional browser confirmation, an already unlocked official Bitwarden CLI
   and creates one password-free item. Assign an existing vault item instead when
   you already have one.
4. Open the documented password-settings link where available. Otherwise open
   the official homepage and navigate to its security settings yourself. Only
   Google, Apple and GitHub currently have separately documented direct links.
5. Generate and save the new password in Bitwarden, confirm the change at the
   provider, then test sign-in. Mark only the steps you actually completed.
   SSO and passkey accounts do not require a separate password change.
   For the current guided account, **I completed this step** asks for a second
   local confirmation and then records only that matching checklist step.
6. Choose **Mark as done**. While viewing the worklist, the dialog advances to the
   next available account. Required checkboxes alone do not mark an account done.
7. **Pause worklist** preserves your place. **Defer** skips one queued account
   until you restore it. **Tomorrow** and **In one week** record a local resume
   date; ARGUS makes the item ready again when the date is reached while the
   dashboard is open. Use the calendar and **Schedule date** for another date in
   the next 365 days. These options send no notification and contact no service.
   Removing an account removes only its queue membership, not its evidence,
   checklist or vault entry. Pausing this list does not pause a separately
   started mail import.

The list tracks each account identity separately, including several accounts
at the same provider. See [separate accounts](ACCOUNTS.md). Optional scheduled mailbox
scans and the browser companion are separate features: neither changes this
worklist or treats a site visit as account evidence.

## Deutsch

Die Arbeitsliste führt dich durch gefundene Accounts und bleibt lokal über
Browser- und Programmneustarts hinweg erhalten. Sie startet keine zeitgesteuerten
Scans und ändert keine Anbieterpasswörter automatisch.

1. Öffne **Sicherheits-Arbeitsliste**. Mit **Nächsten Account absichern** startest
   du einen einzelnen unvollständigen lokalen Account mit höchster Priorität.
   **Prioritäts-Arbeitsliste erstellen** fügt nach Bestätigung bis zu zehn weitere
   offene Accounts in deterministischer Prioritätsreihenfolge hinzu. Vorher zeigt
   ARGUS die genauen Kandidaten und ihren nächsten lokalen Schritt. Oder wähle
   gefundene Accounts und klicke auf **Ausgewählte Accounts hinzufügen**. Die
   bestehende Reihenfolge bleibt erhalten; keine dieser Aktionen ändert selbst
   Checklisten, Tresoreinträge oder Anbieter-Accounts.
2. Wähle **Mit dem nächsten Account fortfahren**. Im Detaildialog steht der nächste
   offene Schritt: Prüfung, Bitwarden-Zuordnung, Passwortwechsel, Anmeldetest oder
   ausdrücklicher Abschluss. Du kannst einen gefundenen Account auch direkt im
   Dialog zur Liste hinzufügen.
3. **Bitwarden-Vorbereitung öffnen** gilt nur für den aktuell geführten Account;
   **Bitwarden vorbereiten** bleibt für eine manuelle Auswahl. Die geführte
   CLI-Übergabe verlangt eine weitere Browserbestätigung, eine bereits entsperrte
   offizielle Bitwarden-CLI und erstellt einen passwortfreien Eintrag. Nutze
   stattdessen einen vorhandenen Tresoreintrag, wenn du schon einen hast.
4. Öffne den dokumentierten Passwortlink, falls vorhanden. Sonst öffne die
   offizielle Startseite und gehe selbst zu den Sicherheitseinstellungen. Aktuell
   sind nur für Google, Apple und GitHub direkte Links separat dokumentiert.
5. Erzeuge und speichere das neue Passwort in Bitwarden, bestätige den Wechsel
   beim Anbieter und teste die Anmeldung. Hake nur tatsächlich erledigte Schritte
   ab. SSO- und Passkey-Accounts brauchen keinen separaten Passwortwechsel.
   Beim aktuell geführten Account verlangt **Ich habe diesen Schritt erledigt**
   eine weitere lokale Bestätigung und speichert danach nur den passenden
   Checklistenpunkt.
6. Wähle **Als erledigt markieren**. In der Arbeitslistenansicht wechselt der
   Dialog zum nächsten verfügbaren Account. Abgehakte Pflichtschritte allein
   schließen keinen Account automatisch ab.
7. **Arbeitsliste pausieren** behält deinen Platz. **Zurückstellen** überspringt
   einen Account, bis du ihn wieder aufnimmst. **Morgen** und **In einer Woche**
   speichern einen lokalen Wiedervorlagetermin; ARGUS macht den Eintrag wieder
   bereit, sobald dieses Datum bei geöffnetem Dashboard erreicht ist. Wähle für
   ein anderes Datum innerhalb der nächsten 365 Tage den Kalender und **Datum
   planen**. Dabei werden keine Benachrichtigungen versandt oder Dienste
   kontaktiert. Entfernen löscht nur den Eintrag aus der Arbeitsliste; Belege,
   Checkliste und Tresoreintrag bleiben erhalten. Das Pausieren dieser Liste
   pausiert keinen separat gestarteten Mailimport.

Die Arbeitsliste verwaltet jeden Account getrennt, auch mehrere Accounts beim
selben Anbieter. Siehe die [Mehrkonto-Anleitung](ACCOUNTS.md). Optionale geplante
Mail-Scans und der Browser-Begleiter sind
getrennte Funktionen: Sie ändern diese Arbeitsliste nicht und werten einen
Webseitenbesuch nicht als Account-Beleg.
