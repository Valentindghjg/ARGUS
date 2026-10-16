# Optional Bitwarden CLI handoff / Optionale Bitwarden-CLI-Übergabe

## English

ARGUS can create **selected, password-free metadata items** in Bitwarden through
the official Bitwarden CLI. It can also run an explicitly confirmed, read-only
duplicate audit for selected local accounts. Both actions are optional and local.
ARGUS never asks for, stores or generates your Bitwarden master password.

1. Install the official [Bitwarden CLI](https://bitwarden.com/help/cli/).
2. In your own terminal, log in and unlock Bitwarden:

   ```bash
   bw login
   export BW_SESSION="$(bw unlock --raw)"
   ```

   On Windows PowerShell, use:

   ```powershell
   $env:BW_SESSION = bw unlock --raw
   ```

3. Start ARGUS **from that same terminal session**.
4. In **Prepare Bitwarden**, optionally choose **Check selected accounts in
   unlocked Bitwarden**. Confirm again in the browser. ARGUS runs one official
   `bw list items --search` request for each selected account and returns only
   **found / possible / none** and a count. The CLI response may include vault
   fields, but ARGUS immediately reduces it to that summary and never stores,
   logs or displays item names, usernames or passwords. Review possible matches
   yourself.
5. Select only genuinely missing items, then choose **Add selected items through
   unlocked Bitwarden CLI** and confirm.
6. Use Bitwarden to generate the new password. Open the verified provider
   password-settings link, complete any sign-in or MFA step yourself, then test
   the sign-in and mark the checklist complete.

The transfer creates no password and cannot change a provider password. Provider
websites have different authentication and security flows, so ARGUS does not
bypass MFA, CAPTCHAs, confirmations or password-reset protections.

## Deutsch

ARGUS kann **ausgewählte passwortfreie Metadaten-Einträge** über die offizielle
Bitwarden-CLI in Bitwarden erstellen. Außerdem kann es für ausgewählte lokale
Accounts eine ausdrücklich bestätigte, nur lesende Duplikatprüfung ausführen.
Beides ist optional und lokal. ARGUS fragt niemals nach deinem
Bitwarden-Hauptpasswort, speichert es nicht und erzeugt es nicht.

1. Installiere die offizielle [Bitwarden-CLI](https://bitwarden.com/help/cli/).
2. Melde dich in deinem eigenen Terminal bei Bitwarden an und entsperre es:

   ```bash
   bw login
   export BW_SESSION="$(bw unlock --raw)"
   ```

   Unter Windows PowerShell verwendest du:

   ```powershell
   $env:BW_SESSION = bw unlock --raw
   ```

3. Starte ARGUS **aus derselben Terminal-Sitzung**.
4. Unter **Bitwarden vorbereiten** kannst du optional **Ausgewählte Accounts im
   entsperrten Bitwarden prüfen** wählen und im Browser erneut bestätigen. ARGUS
   führt je ausgewähltem Account `bw list items --search` aus und gibt nur
   **gefunden / möglich / nichts gefunden** mit Anzahl zurück. Die CLI-Antwort
   kann Tresorfelder enthalten, wird aber sofort auf diese Übersicht reduziert;
   Namen, Benutzernamen und Passwörter werden nie gespeichert, geloggt oder
   angezeigt. Mögliche Treffer prüfst du selbst.
5. Wähle anschließend nur tatsächlich fehlende Einträge. Wähle dann
   **Ausgewählte Einträge über die entsperrte Bitwarden-CLI hinzufügen** und
   bestätige den Schritt.
6. Erzeuge das neue Passwort in Bitwarden. Öffne den verifizierten Link zu den
   Passwort-Einstellungen des Anbieters, erledige Anmeldung oder MFA selbst,
   teste danach die Anmeldung und schließe die Checkliste ab.

Die Übergabe erstellt kein Passwort und kann kein Passwort bei einem Anbieter
ändern. Anbieter-Websites haben unterschiedliche Anmelde- und Sicherheitsabläufe;
ARGUS umgeht keine MFA, Captchas, Bestätigungen oder Passwortschutzmechanismen.

## Interrupted transfers (1.7)

A local journal records one creation attempt per provider/address, its transfer
ID and, on success, the new vault item ID. It contains no passwords, session
values, raw CLI output or mail contents. A successful CLI reply must include an
item ID before the account is marked assigned. All known addresses must finish
before a provider's Bitwarden checklist flag is set.

If a request times out or fails, ARGUS stops and shows **Check an interrupted
transfer**. It may already have created the item. Find the provider/address and
`ARGUS-Transfer-ID` in Bitwarden manually. Confirm either that you found the item
or that it was not created. Only the second choice permits another attempt.
After a hard crash, an in-flight attempt becomes reviewable after at most one
minute. Previously created addresses are skipped, including during JSON export.

This prevents blind retries of tracked ARGUS transfers. It does not detect
pre-existing items or items created outside ARGUS; review those manually first.
The synthetic demo disables direct CLI transfers.

An unlocked `BW_SESSION` has broad vault permissions. ARGUS's code only creates
selected metadata items; this is a behavior boundary, not a restricted Bitwarden
credential. Use a short session on your own computer, stop ARGUS after the task,
then lock the CLI with `bw lock` and remove `BW_SESSION` from that terminal.
Bitwarden may synchronize the new items with your configured server as part of
the explicitly requested transfer. The worklist itself makes no network requests.

## Unterbrochene Übertragungen (1.7)

Ein lokales Protokoll speichert pro Anbieter/Adresse einen Erstellungsversuch,
seine Übertragungs-ID und bei Erfolg die neue Tresoreintrags-ID. Passwörter,
Sitzungswerte, rohe CLI-Ausgaben und Mailinhalte werden nicht gespeichert. Erst
nach einer erfolgreichen Antwort mit Eintrags-ID gilt die Adresse als zugeordnet.
Alle bekannten Adressen müssen fertig sein, bevor der Anbieter abgehakt wird.

Bei Zeitüberschreitung oder Fehler stoppt ARGUS und zeigt **Unterbrochene
Übertragung prüfen**. Der Eintrag könnte bereits erstellt worden sein. Suche
Anbieter, Adresse und `ARGUS-Transfer-ID` selbst in Bitwarden. Bestätige entweder,
dass du den Eintrag gefunden hast oder dass er nicht erstellt wurde. Nur die
zweite Auswahl erlaubt einen neuen Versuch. Nach einem harten Programmabbruch
kannst du den laufenden Versuch spätestens nach einer Minute prüfen. Erfolgreiche
Adressen werden auch beim späteren JSON-Export übersprungen.

Das verhindert blinde Wiederholungen protokollierter ARGUS-Übertragungen. Bereits
vorhandene oder außerhalb von ARGUS angelegte Einträge werden nicht erkannt;
prüfe sie vorher selbst. Die künstliche Demo deaktiviert direkte CLI-Übergaben.

Ein entsperrtes `BW_SESSION` besitzt weitreichende Tresorrechte. Der ARGUS-Code
erstellt nur ausgewählte Metadateneinträge; das ist eine Verhaltensgrenze und
keine eingeschränkte Bitwarden-Berechtigung. Verwende eine kurze Sitzung auf
deinem eigenen Computer, beende ARGUS danach, sperre die CLI mit `bw lock` und
entferne `BW_SESSION` aus dem Terminal. Bitwarden kann die neuen Einträge im
Rahmen der ausdrücklich angeforderten Übergabe mit deinem konfigurierten Server
synchronisieren. Die Arbeitsliste selbst sendet keine Netzwerkanfragen.
