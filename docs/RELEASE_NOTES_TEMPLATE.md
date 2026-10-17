# ARGUS X.Y.Z

Copy this template for each GitHub release and fill it from `docs/CHANGELOG.md`
and `docs/AENDERUNGEN.md`. Keep every section, also when it says "none".

## In short / Kurz gesagt

- One to three sentences on what changes for users, in English.
- Ein bis drei Sätze, was sich für Nutzende ändert, auf Deutsch.

## New connections and permissions

Name every new or changed way ARGUS reaches the network, starts another program
or asks for a permission, and when it does so. Write "none" if nothing changed.
`python scripts/release_check.py` lists the declared ones and fails when a
module reaches out without a declaration. In this version:

| Module | What it may do | Changed in this release |
|---|---|---|
| `imap_client.py` | Reads the mailbox over TLS IMAP, only with `scan-imap --allow-imap` or an approved scheduled scan. | no |
| `discovery.py` | Asks the DNS resolver for MX records, only with `--allow-dns`. | no |
| `bitwarden.py` | Runs the official Bitwarden CLI that you unlocked, only after your confirmation. | no |
| `server.py` | Serves the dashboard on 127.0.0.1 only and opens it in your browser when you pass `--open`. | no |
| Browser companion | Permission `activeTab` only. | no |

## Data and migrations / Daten und Migrationen

- Database schema: from N to M, or "unchanged". ARGUS saves a local backup
  before it migrates a profile.
- New local files or folders, if any.

## Verify the files / Dateien prüfen

Compare the files with `SHA256SUMS` from this release, for example
`sha256sum --check SHA256SUMS` on Linux or
`Get-FileHash <file> -Algorithm SHA256` in PowerShell. The "Release files"
workflow run for this tag lists the same checksums in its summary; the wheel is
built reproducibly, so a local build of the tag gives the same wheel checksum.

## Limits that stay / Grenzen, die bleiben

Clues in emails are no proof of an account, and an unknown account is not an
absent one. ARGUS changes nothing at providers and never stores passwords.
