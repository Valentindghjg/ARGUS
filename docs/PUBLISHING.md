# Public-release checklist

This document prepares the repository for public visibility. The repository owner
performs each GitHub setting and publication step; the application does not
publish itself.

## Before changing visibility

- Review `git log --all --stat` and `git grep` for names, email addresses, API
  tokens, IMAP settings, databases, exports and personal screenshots.
- Confirm that `.local/`, `imap.json`, `.env*`, mail exports and Bitwarden JSON
  files are ignored. Do not rely on `.gitignore` for files already committed.
- Run `python -m unittest discover -s tests -v` and the optional browser suite.
- Review README, security guidance and screenshots as a first-time user would.
- The repository includes the exact MPL-2.0 text as `LICENSE`. Confirm that the
  publication model still separates future proprietary Pro code and terms from
  this Free repository.
- For the Freemium product, complete
  [COMMERCIAL_RELEASE.md](COMMERCIAL_RELEASE.md) before offering a paid Pro
  edition. The current dashboard only presents a Pro preview; it has no checkout
  or activation path.
- Decide whether the current GitHub username, repository name, issues and Actions
  history should be public. Rename or transfer the repository before publishing if
  needed.

## GitHub settings to review manually

1. Set the repository’s description, topics and default branch in **Settings**.
2. In **Actions → General**, keep workflow permissions read-only unless a specific
   workflow needs more. This project’s CI needs only `contents: read`.
3. In **Branches**, require the “Checks” workflow before merging into `main` if
   you use pull requests. Consider requiring review before merge.
4. In **Security**, enable private vulnerability reporting and Dependabot alerts
   if they are available for the selected visibility and plan.
5. In **General → Danger Zone**, change visibility to Public only after the
   preceding review. GitHub may show an irreversible-effects confirmation.
6. Create a release from a signed-off tag after publication, for example `v1.6.0`.
   Do not attach personal databases, exports or email files.

## What a public user gets

- A local German/English Free edition, 527-provider catalog, tests and CI.
- Synthetic examples only; no user mailbox, password, token or Bitwarden vault.
- A clear limitation: evidence is not account proof and unknown is not absence.

The project is intentionally not a hosted service. Do not expose the loopback
dashboard, publish a personal profile or instruct users to share credentials.
