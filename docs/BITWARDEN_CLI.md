# Optional Bitwarden CLI handoff / Optionale Bitwarden-CLI-Übergabe

## English

ARGUS can create **selected, password-free metadata items** in Bitwarden through
the official Bitwarden CLI. This is optional and local. ARGUS never asks for,
stores or generates your Bitwarden master password. It never reads, edits or
overwrites existing vault items.

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
4. In **Prepare Bitwarden**, select only items that do not already exist, then
   choose **Add selected items through unlocked Bitwarden CLI** and confirm.
5. Use Bitwarden to generate the new password. Open the verified provider
   password-settings link, complete any sign-in or MFA step yourself, then test
   the sign-in and mark the checklist complete.

The transfer creates no password and cannot change a provider password. Provider
websites have different authentication and security flows, so ARGUS does not
bypass MFA, CAPTCHAs, confirmations or password-reset protections.

## Deutsch

ARGUS kann **ausgewählte passwortfreie Metadaten-Einträge** über die offizielle
Bitwarden-CLI in Bitwarden erstellen. Das ist optional und lokal. ARGUS fragt
niemals nach deinem Bitwarden-Hauptpasswort, speichert es nicht und erzeugt es
nicht. Bestehende Tresoreinträge werden weder gelesen, geändert noch
überschrieben.

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
4. Wähle unter **Bitwarden vorbereiten** nur Einträge, die noch nicht im Tresor
   bestehen. Wähle dann **Ausgewählte Einträge über die entsperrte Bitwarden-CLI
   hinzufügen** und bestätige den Schritt.
5. Erzeuge das neue Passwort in Bitwarden. Öffne den verifizierten Link zu den
   Passwort-Einstellungen des Anbieters, erledige Anmeldung oder MFA selbst,
   teste danach die Anmeldung und schließe die Checkliste ab.

Die Übergabe erstellt kein Passwort und kann kein Passwort bei einem Anbieter
ändern. Anbieter-Websites haben unterschiedliche Anmelde- und Sicherheitsabläufe;
ARGUS umgeht keine MFA, Captchas, Bestätigungen oder Passwortschutzmechanismen.
