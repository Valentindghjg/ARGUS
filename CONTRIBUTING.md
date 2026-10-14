# Contributing / Mitwirken

English and German contributions are welcome. User guides:
[English](README.md) · [Deutsch](README_DE.md).

Use Python 3.11 or newer. The app has no third-party runtime dependencies.
Run it from the source directory with a separate synthetic profile:

```bash
python -m account_finder --data-dir .local/demo demo --serve
python -m unittest discover -s tests -v
```

The optional browser suite requires Playwright and Chromium, as documented in
the user guides. GitHub Actions runs Python regression tests on Linux with
Python 3.11–3.14, package installation checks and German/English browser checks.
Its browser session permits requests only to its temporary loopback server.

Do not commit personal profiles, databases, real email exports, credentials,
Bitwarden metadata downloads or screenshots showing personal accounts. All
fixtures and reproductions must be synthetic. Keep local configuration and
results outside tracked files; `.local/`, `.env*` and `imap.json` are ignored.

Bitte ausschließlich künstliche Beispieldaten verwenden. Keine echten E-Mails,
Account-Listen, Zugangsdaten, Tokens oder Bitwarden-Downloads einchecken.
Verwende getrennte Datenverzeichnisse und prüfe `git diff --cached` vor Commits.

Preserve these behavior guarantees:

- No service login probing, automatic resets or automated password changes.
- Read-only source email access; explicit opt-in for DNS and IMAP connections.
- Local processing, bounded MIME analysis and no credential logging.
- Unknown never means no account exists; only explicit review confirms an account.
- Passwords are generated in Bitwarden; exports contain empty password fields.
- Technical IDs, canonical statuses and stored evidence do not change with locale.

For translations, edit `account_finder/data/translations.json`, preserve named
placeholders and check both directions of language switching. For catalog
extensions, use official domain sources and document verified password links.
Re-import synthetic source messages to test changed detection or catalog entries.

Use an issue to describe a bug or improvement, then keep pull requests focused.
Record relevant tests and limitations in the pull request. Security issues follow
[SECURITY.md](SECURITY.md).
