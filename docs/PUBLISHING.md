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
- The repository includes the exact MPL-2.0 text as `LICENSE`. Every feature is
  free; there is no edition switch, license key or checkout to review.
- Decide whether the current GitHub username, repository name, issues and Actions
  history should be public. Rename or transfer the repository before publishing if
  needed.

## GitHub settings to review manually

1. Set the repository’s description, topics and default branch in **Settings**.
2. In **Actions → General**, keep workflow permissions read-only unless a specific
   workflow needs more. Both workflows, “Checks” and “Release files”, need only
   `contents: read`.
3. In **Branches**, require the “Checks” workflow before merging into `main` if
   you use pull requests. Consider requiring review before merge.
4. In **Security**, enable private vulnerability reporting (required: SECURITY.md
   and CODE_OF_CONDUCT.md name it as the only private channel) and Dependabot alerts
   if they are available for the selected visibility and plan.
5. In **General → Danger Zone**, change visibility to Public only after the
   preceding review. GitHub may show an irreversible-effects confirmation.
6. Create releases only as described below. Do not attach personal databases,
   exports or email files.

## Creating a release by hand

ARGUS never publishes itself, and no workflow can create a release. The
"Release files" workflow builds with read access only. For a tag, a separate
job that runs no project code records a signed build provenance attestation
for the built files (keyless, through Sigstore and the GitHub attestations
API); it is the only job allowed to request a signing identity.

1. Run `python scripts/release_check.py`. It fails when the version differs
   between the package and the two change logs, when a module can reach the
   network or start a program without a declaration, or when the browser
   companion asks for more than `activeTab`.
2. Write the release notes from `docs/RELEASE_NOTES_TEMPLATE.md`. Its section
   "New connections and permissions" is mandatory, also when it says "none".
3. Tag the reviewed commit, for example `git tag v2.6.0`, and push the tag. The
   "Release files" run checks that the tag names the version, builds the files,
   lists their checksums in its summary, keeps them as the `release-files`
   artifact for 30 days and attests their build provenance.
4. Build locally from the same tag:
   `SOURCE_DATE_EPOCH="$(git log -1 --format=%ct)" python -m build`, then
   `python scripts/release_check.py checksums dist`. The wheel checksum must
   match the run summary. The source archive is not byte-identical between two
   builds, so compare the wheel.
5. Create the GitHub release by hand and attach the wheel, the source archive
   and `SHA256SUMS` from the run's `release-files` artifact. Only these exact
   files carry the attestation; a local wheel is byte-identical, a local source
   archive is not. Check one before attaching it:
   `gh attestation verify <file> --repo Valentindghjg/ARGUS --signer-workflow Valentindghjg/ARGUS/.github/workflows/release.yml`.

## What a public user gets

- A local German/English app with every feature free, a 527-provider catalog, tests and CI.
- Synthetic examples only; no user mailbox, password, token or Bitwarden vault.
- A clear limitation: evidence is not account proof and unknown is not absence.

The project is intentionally not a hosted service. Do not expose the loopback
dashboard, publish a personal profile or instruct users to share credentials.
