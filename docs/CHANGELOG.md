# Change log

## 2.6.1 — Fixes from the review of 2.0–2.6 (not yet tagged)

### Change log, undo, backups and migrations

- A change with more than 1,000 entries (for example a template on many
  accounts) no longer deletes itself and the whole history when the log is
  pruned; it stays undoable.
- Undo restores the sign-in method together with the password step, keeps the
  "new strong clue after your rejection" hint, and after a redo the next undo
  reverts the redo instead of an older change.
- A removed newest clue no longer lends its number to the next one, so a new
  clue after a rejection or an exclusion is always recognised as new.
- Re-importing old clues whose rating is unchanged no longer lists them as
  changed; clues from older rules show as "Older evidence" instead of "No
  evidence".
- Backups include your own catalog additions. A restore never deletes the
  backup it restores from, refuses backups from a newer ARGUS before changing
  anything (backup format 2; format 1 archives still restore), and replaces a damaged profile after saving its raw bytes. A backup
  folder you choose keeps its permissions.
- Two processes opening an old profile at the same time no longer fail during
  the migration. Review dates, due reviews, snoozes, progress days and report
  dates all use your local calendar day. Own templates are saved under one lock.

### Catalog additions, "What's new", worklist order, identity links and sessions

- An own catalog addition that a newer catalog (or a `--providers` file) now
  covers no longer locks the whole profile: it is skipped, shown with a note
  under "Mailbox & Import" and can be removed; its clues wait for a re-import. Malformed
  `--providers` rows are refused with a message instead of a crash. An addition
  can no longer take a sub-domain of a catalog provider.
- "What's new" leaves hidden sender domains alone until a newer clue arrives,
  and groups clues under the account that holds them, not a labelled sibling.
- Moving a worklist task next to equal positions moves it exactly one place,
  and the renumbering is undone with the move.
- A rejected account no longer counts as signing in with another account.
- Clearing a review date that is due counts as reviewing that step today, so a
  review rule proposes the next date from today instead of tomorrow.
- The session report names decisions you made in the session.

### Imports, budgets, the folder watch and the scheduler

- A message whose headers break the email parser counts as one error and is
  listed for `--retry-failed`; it no longer stops the import, and a scheduled
  scan moves past it instead of failing on it every time.
- An unreadable file is skipped and listed for `--retry-failed` instead of
  stopping the import. Directory imports also read files named `.EML`.
- A message or size limit counts only new work: empty, oversized or failing
  items no longer use it up, and a run that fits the limit exactly completes.
  `--recheck` with a limit and `scan-imap --full-scan --limit` are refused,
  because both start at the first message each time and would never move on.
- The folder watch records a failed pass and keeps its interval instead of
  retrying every minute; a pass never undoes a disable or a newly approved
  folder; files after a change of your own addresses are read again; a folder
  with more than 5,000 EML files is reported instead of being re-read forever;
  a file swapped for a link or a pipe is skipped.
- The scheduler starts with the dashboard, so enabling scheduled scans or the
  folder watch in a terminal works without a restart; while paused it checks
  once a minute instead of every second.
- A browser import stopped by the pause is recorded as paused, a scheduled
  scan whose approval ended as cancelled. A schedule from before target binding
  shows "needs approval". Coverage counts messages read again only once.
- The pause takes effect within about a second (it was checked every 25
  messages); the README now says that a revoke is noticed within about
  15 seconds.

### Bitwarden, profiles and move plans

- Two downloads at the same time, or a download next to a direct transfer, can
  no longer both hand out a file: the journal is checked again under its lock
  before a file leaves ARGUS. A file that cannot be written leaves no journal
  entry behind.
- "Already in your vault" accepts only accounts ARGUS found and you did not
  reject, never creates an empty account, and closes an open download entry.
- New `bitwarden-journal list|resolve`, so a terminal-only person can record
  what they found in the vault; the error after a download names it.
- On Windows only the standalone `bw.exe` from PATH is started, never a script
  wrapper or a file in the current folder. The code comment now says that the
  read-only audit shows provider names in the process list.
- `about` and `profiles` never move a pre-rename profile folder or print its
  path. `--profile default` and Windows device names are refused, and a
  mistyped `--profile` no longer creates a new empty profile.
- A move plan keeps an address note you wrote for the same two addresses.
## 2.6.0 — Quality and trust (not yet tagged)

### Plan complete (S21)

- `docs/strategy/README.md` lists every item of the master plan with its
  state, step and place in the code: 60 implemented, two deliberately narrow
  (folder watch, accessibility basics), release signatures still to come and
  the offline license dropped because every feature is free.
- Fresh preview images from the synthetic demo; the browser test hides
  short-lived notices and starts each image at the top of the page.
- A repository test fails on relative Markdown links that point nowhere; one
  stale link in the test report is gone.

### Demo tour, data-minimal bug reports and checked releases (G2, G4, G6)

- The demo overview offers “Try this path”: five steps from what the import
  found through unclear items, the worklist and the Bitwarden handover to a
  progress report. `docs/DEMO.md` and `docs/DEMO_DE.md` describe them.
- `argus about` prints versions, platform and counts for a bug report, never
  addresses, providers, paths or messages. It only reads an existing profile
  and never creates one. The bug report form asks for it, for synthetic steps
  and for a confirmed data check. New FAQ in English and German.
- `scripts/release_check.py` checks one version across the package and both
  change logs, that every module able to reach the network or start a program
  is declared, and that the browser companion keeps only `activeTab`; it also
  checks tag names and writes `SHA256SUMS`. The read-only “Release files”
  workflow runs it on version tags and lists the checksums; it publishes
  nothing. A release notes template always names new connections and
  permissions.

### Coverage, accessibility, a masked view and catalog quality (D4, D6)

- The overview shows what imports cover: sources with runs, messages and last
  date, the period of the clues, months without any clue and own addresses
  without a clue; never a total percentage.
- A skip link, the current page marked for assistive technology, named controls
  everywhere (checked in the browser test) and **Hide personal details**, which
  masks email addresses on screen only.
- New catalog quality tests: unique names and domain roots, known categories,
  clean IDs, no shared senders, HTTPS links on own domains and dated
  password-page sources.

## 2.5.0 — Former Pro features, free (not yet tagged)

### Separate profiles, progress over time and data-minimal reports (P1, P2, P5)

- `--profile NAME` uses a separate named profile folder with its own database,
  settings, catalog additions, backups and approvals; `profiles` lists names
  only. The dashboard shows the profile name.
- One row of counts per day (no names, addresses or evidence; about thirteen
  months) feeds “Progress over time” with week, month and quarter comparisons.
- Progress reports with numbers only, or numbers and tasks; sign-in addresses
  only when explicitly ticked; full preview before saving
  (`report --text|--export`, `GET /api/report`). Schema version 9 adds the
  history table after the automatic backup.

### Plan an address change (A21, P4)

- “Plan an address change” orders every account that signs in with the old
  address: dependent identity accounts first, then by priority. Each item is
  marked changed, skipped or open by hand; plans can be closed. ARGUS changes
  nothing at providers and never moves an account's sign-in identity. Creating
  a plan notes the old address as replaced by the new one.
- New CLI command `move-address create|list|mark|close`; API `POST /api/moves`,
  `/api/moves/item` and `/api/moves/close`. Schema version 10 adds two tables
  after the automatic backup.

### Task templates (A22, P4)

- Templates plan recurring work as plain data: which accounts (categories,
  minimum priority, only confirmed) and what (worklist, review dates for chosen
  steps). Two templates ship with ARGUS; own templates can be saved and deleted.
- A preview names every affected account; applying is one undoable change and
  skips steps that do not apply. New CLI command `template`; API
  `POST /api/templates`, `/api/templates/preview`, `/api/templates/apply` and
  `/api/templates/delete`.

## 2.4.0 — Package E: Bitwarden without surprises (not yet tagged)

### Three equal ways, readiness and one journal (B1, B3, A19)

- “Prepare Bitwarden” offers three equal ways: mark accounts you found in your
  vault yourself (undoable, `bitwarden-assign`), download a password-free file,
  or the optional CLI. Checking existing items reads the vault and needs its own
  tick for that one check.
- Each account shows its readiness (ready, check first, not now) with the
  reasons; ready is no security statement.
- Downloads (dashboard and `bitwarden-export`) are journaled as “downloaded”:
  another download or CLI transfer of that account waits until you record
  whether you imported it. The journal lists every download and transfer with
  its date. An existing export file is reported before anything is journaled.
- New API `POST /api/bitwarden/assign`; snapshot field `bitwarden_readiness`.

## 2.3.0 — Package D: dependable automation (not yet tagged)

### Jobs, activity log and one pause for everything (A24, A25, A27, D5, priority 07)

- Every import, IMAP scan (manual or scheduled) and Bitwarden check or transfer
  is a job with one shared state; a waiting scheduled scan is listed with its
  next time. Jobs that stopped reporting show as interrupted.
- **Pause all automation** (dashboard “Control” or `automation pause`) blocks
  new jobs and stops running ones between two messages; `scan-imap` refuses
  before asking for a password. Scheduled scans wait and keep their checkpoint.
  The overview summary shows the pause until you resume.
- A minimal activity log keeps time, job type, result and counts only, at most
  500 entries for 180 days.
- New CLI command `automation status|pause|resume`; API `GET /api/control` and
  `POST /api/control`. Schema version 7 adds two tables after the automatic
  backup.

### Visible approval, revocation and an offline preview (A23, A26, D5, priority 10)

- Control lists the standing approval for scheduled scans with host, folders,
  limit, interval, approval date and saved checkpoints, never the username. A
  changed target shows as “Needs approval”; the refused run is logged.
- **Revoke approval** (dashboard) ends the approval and removes the keyring
  authorization; it is distinct from the pause. Per-run approvals (manual IMAP,
  Bitwarden transfer, MX lookup) are listed as approved each time.
- `background-imap preview` and `enable` show what an approval covers from local
  data only. Granting, revoking and refusing approvals appear in the activity
  log. New API `POST /api/approvals/revoke`.

### Only what changed, a budget and safe continuation (A13, A14, A15)

- A message already analyzed under the same own addresses, catalog and rules is
  recognized by its content fingerprint and counted as unchanged instead of
  being analyzed again; any change to those conditions analyzes everything
  again. The index stores fingerprints only.
- `import --max-messages` and `--max-megabytes` limit new work per run; such a
  run ends as “limited” with a next step, never as complete. The same import
  continues later, also after an interruption or pause; `--recheck` forces a
  full analysis.
- Schema version 8 adds the index after the automatic backup. Re-imports now
  report `unchanged` where they reported `duplicates` before.

### Repeat, retry and check local imports (A11, A16, P3, priority 13)

- `import --again` repeats the last terminal import with the same source and
  format; a missing source is reported. The dashboard shows the last terminal
  import with its commands. Browser selections are never remembered.
- Empty, oversized or unreadable items are noted locally by their relative path
  or mbox number, and `import --retry-failed` reads only those.
- `import --check` counts messages, size, new, unchanged and oversized items of
  a source without importing or analyzing anything.

### Watch one export folder (A12, priority 14)

- `watch-folder enable PATH` approves exactly one existing local folder; while
  the dashboard runs, new or changed `*.eml` files directly in it are imported
  through the normal import with its index. Subfolders are never read; files are
  never changed. The root, the home folder, hidden folders, links, network paths
  and the profile folder are refused.
- The watch is a permission and a waiting job in Control, a `folder_watch` job
  with activity entries, follows the global pause, handles at most 500 files per
  pass and reports a missing folder. The dashboard names it at start and can stop
  it (`POST /api/watch/disable`).

## 2.2.0 — Package C: local preparation (not yet tagged)

### What's new since your last review (A1–A4, A7, A28, priorities 05 and 06)

- A new “What's new” view lists only clues that are new or rated differently
  since you last marked changes as reviewed, grouped by account; items that need
  a decision come first, and advertising, orders and reset requests are only
  counted. Importing the same email again brings nothing back. Gaps of the last
  import stay visible until reviewed.
- The overview shows one return summary: import gaps and unclear Bitwarden
  transfers first, then new decisions, new clues and reached review dates. An
  import ends with one message instead of several.
- **Mark as reviewed** changes no decision or step and can be undone once. New
  CLI command `whats-new [--mark-reviewed]`; API `POST /api/digest/seen` and
  `POST /api/digest/seen/undo`; snapshot fields `changes` and `return_summary`.
- Schema version 5 adds two revision columns to clues after the automatic
  backup. Clues stored before count as already reviewed.
- Notes in the account list and the unclear view now wrap on narrow screens.

### Explained priorities and identity accounts (D3, A6, A17, B6)

- Every account lists the reasons for its priority. A priority you choose wins;
  “Automatic” returns to the derived one.
- You can note which confirmed account hosts the mailbox of an own address and
  which confirmed account a single sign-on account uses. Such identity accounts
  become “Do first” with the reason shown and lead the worklist suggestions;
  relations to accounts that are no longer confirmed stay listed as inactive.
  ARGUS never infers these relations.
- Worklist suggestions say why (“Why: …”). **Move up** and **Move down** swap
  two tasks and can be undone; adding suggestions never reorders planned tasks.
- New CLI commands `mailbox` and `sign-in-with`; API
  `POST /api/profile/mailboxes`, `POST /api/accounts/{id}/sign-in-with` and the
  worklist action `move`. Schema version 6 adds two tables after the automatic
  backup.

### Sessions, review dates and the checklist by sign-in method (A5, A8, A10, A18, A20)

- The checklist follows the confirmed sign-in method: single sign-on and passkey
  accounts get matching steps, and an account whose sign-in account is not
  complete says so.
- **One task** or **Three tasks** starts a short session without a deadline. Its
  report comes from the steps you recorded since the start; the text file is
  shown in full before saving and holds account names and steps only.
- A review rule (6, 12 or 24 months; important or all completed accounts)
  proposes review dates. Applying them is one undoable change; nothing happens
  automatically.
- Bitwarden notes add the confirmed sign-in method, the confirmed sign-in
  account and a verified password-settings page; unknown values stay out.
- New CLI commands `session` and `review-rule`; API `POST /api/session`,
  `GET /api/session/report`, `POST /api/review-rule` and
  `POST /api/review-rule/apply`.

## 2.1.0 — Package B: explainable, correctable detection (not yet tagged)

### Why a clue counts, what kind it is and how old (E1, E2, priority 03)

- Each clue now stores short rule features instead of any message text: where
  the rule matched (subject or text), whether the mail went directly to your
  address, mailing-list or advertising signs, forwarding, header-only analysis
  and whether the sender domain is in the catalog. The account dialog explains
  them under “Why it counts”.
- Clues are labelled by kind (account event, order or invoice, advertising,
  reset request) and age. Clues older than two years are marked; if all are,
  the account shows that it may have changed or been closed. Old clues are
  never deleted.
- Clues imported before this version gain their explanation when the same
  message is imported again; the profile gets one new column (schema version
  3, with the automatic backup first).

### Unclear items in one list, reversible exclusions, address notes (E3, E4, A9)

- A new “Unclear items” view lists accounts that need a sign-in address,
  services with clues that name no clear account, rejected accounts with new
  evidence and sender domains outside the catalog.
- Sender domains outside the catalog can be hidden with a reason; new clues
  bring them back and “Show again” reverses it. Domains in the catalog cannot be
  hidden; reject the account instead.
- Notes between two own addresses (same mailbox, replaced by) are shown on the
  affected accounts and never merge accounts.
- New CLI commands `unclear`, `exclude` and `relate`; schema version 4 adds two
  tables after the automatic backup.

### Your own catalog additions and visible rule changes (E5, E6)

- “Add to my catalog” in “Unclear items” saves a provider for a sender domain
  outside the catalog in the profile only (`my-providers.json`, private
  permissions). It is validated like the built-in catalog and never looked up
  online; shared sending services are refused and marked in the list.
- A domain added this way stays in the list, marked as now in the catalog,
  until its original emails are imported again; a notice counts these clues.
  Additions without clues, decisions or steps can be removed again.
- A re-import lists clues whose rating changed under the current rules (old and
  new reason and score); the CLI prints the number. Decisions and steps stay.
- New API routes `POST /api/catalog` and `POST /api/catalog/remove`; the
  snapshot carries `catalog` and candidates carry `shared_sender` and
  `catalog_match`.

### Provider proposals and a synthetic benchmark (G3, G5)

- A **Provider proposal** issue form asks for the official website, category,
  each domain root with a reason, public sources with a check date and four
  review criteria, and forbids real emails. The catalog policy now describes
  shared sending services and the dashboard's own additions.
- `python scripts/benchmark.py` runs 27 invented messages through the analysis
  and reports hits, messages kept for review, misses, false alarms and three
  documented limits (forged catalog senders, other languages, unusual
  wording). It is not proof of accuracy on real mailboxes; a test keeps every
  outcome documented.

## 2.0.0 — Package A: clear states and a controllable core (not yet tagged)

See [the security review](SECURITY_REVIEW_2026-10.md) and
[the master plan status](strategy/README.md).

### Breaking: one free edition, standard library only

- Every feature is free (owner decision, master plan step S1). The Plans page,
  `license-status`, `activate-license`, `POST /api/license/activate`, the
  snapshot field `product` and the publisher license scripts are removed.
- ARGUS no longer depends on `cryptography`; it runs on the Python standard
  library. `keyring` stays optional for scheduled scans. A test rejects new
  runtime dependencies.
- A leftover `license.json` in an old profile is ignored and can be deleted.

### Breaking: the project is now ARGUS everywhere

- Package `argus_security` (`python -m argus_security`), distribution
  `argus-account-security` and command `argus`. `python -m account_finder` and
  `account-finder` still work but print a deprecation notice.
- The default profile moves once, atomically, from `~/.local/share/account-finder`
  to `~/.local/share/argus`, with all files and permissions. An explicit
  `--data-dir` is never moved. Keyring entries need no migration.
- New Bitwarden items carry the field `ARGUS-Account-ID`; the read-only audit
  still recognizes the older `Account-Finder-ID`. The dashboard language
  preference moves to a new browser storage key on first use.
- The internal header-only marker keeps its old name, because it is part of
  message fingerprints.

### Platforms

- CI now runs the unit tests and a package installation check on Windows and
  macOS as well as Linux. Browser checks stay on Linux.

### Clear next steps and a precise promise (master plan F4, G1)

- Known problems now come with one concrete next step: missing profile or
  source path, Maildir layout, an existing export file, a busy port or
  database, keyring and IMAP failures, unresolved Bitwarden transfers and
  incomplete checklists. The CLI prints it as "Next step:", and the dashboard
  shows it under the error. Hints are fixed texts and never repeat paths,
  addresses or message content.
- Every scan result lists what to do about its gaps (skipped, unreadable or
  header-only messages, interruptions, limits, changed addresses). The CLI
  keeps JSON on stdout and prints these steps on stderr.
- The browser import lists files it skipped and why (empty, not EML, over
  2 MiB). The file names stay in the browser tab.
- Texts no longer suggest completeness or protection: "Already secured" is now
  "Checklists completed", and the progress panel says that ARGUS cannot find
  every account. Both READMEs state the product promise; a test blocks
  absolute claims.

### Exact Bitwarden preview and an explaining demo (master plan B2, F6)

- Download, direct CLI transfer and the guided step first show exactly the
  items that will be written: name, official website, confirmed sign-in
  address, note and extra fields, and the accounts the journal already records
  as created. The confirmation replaces the former browser prompt and reuses
  the previewed selection and language. `bitwarden-export --preview` prints the
  same and writes no file. Preview, download and transfer share one code path.
- The demo now has two invented own addresses and 18 messages. A guide on the
  overview explains the newsletter, guest order and reset email (clues only),
  two GitHub accounts, single sign-on at Notion and a look-alike sender domain.
  An existing demo folder can be loaded again.

### Profile backup and restore (owner decision, plan "Installation, Migration und Sicherung")

- `argus backup` writes one private ZIP (database via SQLite online backup,
  password-free `imap.json`, manifest with checksums); `--output` chooses a
  folder and `--list` shows backups. Backups are unencrypted by decision: no new
  ARGUS password system.
- `argus restore FILE` shows what it would restore; with `--yes` it verifies
  every checksum and the database integrity, saves the current state first and
  then replaces the profile.
- The profile now records a schema version. Before a newer ARGUS changes an
  older database, it saves an automatic backup (the newest five are kept). If
  that backup fails, nothing is changed. A profile from a newer ARGUS is not
  opened.

### Separate states for evidence, decision and steps (ADR-0001, schema version 2)

- Each account now keeps the person's decision (confirmed, with a date) apart
  from the security steps (identity, vault, password, sign-in test, MFA and
  recovery, each dated). Progress is derived from the steps. Deferring exists
  only in the worklist. New evidence never changes a decision or a step.
- A vault item that ARGUS created without a password counts as "prepared", not
  done; only you mark the vault step done (B4).
- MFA and recovery must be done or marked not applicable before an account is
  complete. Accounts completed in 1.x without the MFA box keep their completion
  with MFA "not applicable".
- Every change to decision, steps and planning is recorded locally (field, old
  and new value, time; at most 1000 entries) as the basis for undo.
- The profile is migrated once, in a single transaction, after an automatic
  backup. The 1.x fields `classification`, `status` and `checklist` remain in
  the API, derived from the new fields, until the next major version.

### Reject, dated reviews and undo (ADR-0001, F5, A9, A10 groundwork)

- An account can be rejected with a reason (not mine, not an account, closed).
  A rejected account leaves lists, the worklist and suggestions; new strong
  evidence only shows a hint and never reverses your decision.
- Each security step can carry a local review date; due reviews are listed per
  account.
- Undo reverts your latest local change, and repeating it goes further back.
  A value you changed again later is never overwritten, and external actions
  (Bitwarden items, scans) are never undone. Worklist actions are part of the
  history.
- New API routes for decisions, steps, undo and history; new CLI commands
  `argus changes` and `argus undo`. The dashboard follows in the next step.

### Dashboard: three marks, decisions, dated steps and undo (D2, A10, F5)

- The account list and dialog show three separate marks: evidence, your
  decision and progress. The meaning of each is explained below the list.
- The dialog asks “Is this your account?” with confirm, reject with a reason
  and undecided, and lists five dated steps. MFA can be marked as not offered or
  not used, and done steps can get a local review date. A prepared vault item is
  labelled as such. The “Mark as done” button is gone: completion follows the
  steps.
- Every decision and step offers Undo in the toast, and “Your recent changes” in
  the worklist lists the history with Undo per change.
- Filters now separate evidence and decision (confirmed by you, evidence only,
  no evidence, rejected) and progress (not started, in progress, complete,
  deferred). “Defer” plans the account in the worklist.

### Three ways in, an honest summary and one next task (F2, F3, D1)

- A new profile shows three separate ways in: the demo, a local import and
  the optional read-only mailbox connection. The first two never use the
  network.
- The overview summarises what ARGUS knows: messages processed, clues, accounts
  with evidence, your decisions, unclear items (identities, clues without a clear
  account, unknown domains) and gaps. It states that this is not a complete list.
- One reasoned next task leads the overview: import, an unfinished import,
  identities to assign, an unclear transfer, a due review, the worklist, accounts
  to decide on or the next account to secure. `argus report` includes both.
- The screenshots in the READMEs now come from this version's demo.

### Security and robustness

- **Approvals are bound to their target (master plan priority 10).** Scheduled
  IMAP scans record a fingerprint of host, port, username, sign-in method and
  folders at `enable`. If `imap.json` differs, a run stops before touching the
  keyring or the network and waits for a new `enable`. Previously a changed host
  received the stored authorization. Schedules from earlier versions need one
  new approval.
- Scheduled IMAP scans renew their lease between messages, so a long scan keeps
  exclusive mailbox access. `disable`, `revoke` or a replacement lease now stops
  a running scan before its next message fetch.
- The dashboard scheduler thread survives database locks and damaged schedules.
  It no longer starts a scan while a browser import is running.
- The dashboard start message now discloses enabled scheduled IMAP scans.
- The dashboard asks for confirmation before permanently binding a sign-in
  address. The direct Bitwarden transfer API requires an explicit
  `confirmed: true`.
- The browser companion labels only HTTPS catalogue domains and their `www.`
  hosts as official. It warns on other subdomains.
- Added 24 missing German messages (license, keyring and scheduler errors) and
  German text for the 4 new messages from this review. A regression test now requires German text for every typed
  user-facing error.
- Added a warning when enabling a schedule with an expiring OAuth2 token.
- `.gitignore` now excludes private key files. Only the public license key is
  packaged, and the key generator refuses to write a private key inside the
  repository.
- Package metadata now declares `MPL-2.0` (PEP 639) and points to the ARGUS
  repository. Dependabot also monitors pip dependencies.
- Corrected documentation that contradicted current behavior, and removed dead
  code.
- Manual `scan-imap` runs and scheduled scans share one cross-process mailbox
  lease; a manual scan is refused before its password prompt while a scheduled
  scan runs.
- Bitwarden item metadata reaches `bw create item` through stdin instead of the
  process list.
- The dashboard now shows specific, fixed rule messages (for example an address
  that already belongs to another account) instead of a generic error; other
  errors stay generic.
- Deferred accounts are no longer suggested by the guided next step.
- The browser companion has a German interface, builds its catalogue through
  the application's validation and is behavior-tested under simulated APIs.
- New profiles no longer create the pre-1.9 tables; older profiles still migrate.
- Every source file carries an MPL-2.0 SPDX header; LICENSING.md covers data,
  documentation and images. Security reports use GitHub private reporting only.
- 22 unused translations removed, with a regression test; German README and
  change log brought to parity; CI tool versions pinned.
- Added end-to-end simulations with a fake IMAP server, fake keyring and
  simulated clock.

## 1.16.0 — Read-only vault audit and guided MFA recovery

- Added an explicitly confirmed, read-only audit for selected accounts through
  an already-unlocked official Bitwarden CLI. It returns only a local
  **found / possible / none** match summary and count; vault names, usernames,
  passwords, CLI output and sessions are never persisted, logged or displayed.
- The guided local worklist now includes an explicit MFA and recovery review
  after sign-in testing. It records only the user's confirmation and never
  contacts a provider or changes a setting.
- Added narrow loopback API, fake-CLI and workflow regression coverage, plus
  English/German dashboard and safety documentation.

## 1.15.0 — Calendar worklist scheduling

- Added a local calendar date picker and **Schedule date** for worklist snoozes
  beyond the preset tomorrow/week choices.
- The strict local action accepts ISO calendar dates from tomorrow through the
  next 365 days and records the resulting UTC resume time without any network
  connection.
- Added unit and browser coverage for the bounded date input and accessible
  calendar control.

## 1.14.0 — Local worklist snoozes

- Added **Tomorrow** and **In one week** to defer a local worklist item until a
  stored resume date. Due items become ready again while ARGUS is open; no
  notification, provider, mailbox or Bitwarden connection is made.
- Added additive SQLite migration for existing worklists and strict local API
  validation for the bounded 1–365 day snooze period.
- Added workflow, migration, loopback API and bilingual browser coverage for
  snoozes and due-item resumption.

## 1.13.0 — Reviewable priority planning

- Added an English/German local preview of the exact accounts that **Build
  priority worklist** would append, including each candidate's next security step.
- The preview uses the same deterministic ranking and ten-account limit as the
  atomic builder, writes no state and never contacts a provider or Bitwarden.
- Added workflow and browser regression coverage for preview contents and the
  translated, no-external-request dashboard flow.

## 1.12.0 — Priority worklist builder

- Added **Build priority worklist**, an explicitly confirmed local action that
  appends up to ten incomplete discovered accounts in deterministic security
  order while preserving existing queue positions.
- The new action has a narrow exact request shape and an atomic SQLite update.
  It never changes account checklists, passwords, providers or Bitwarden items.
- Added English/German UI copy plus workflow and loopback API regression tests
  for ranking, the ten-account limit and progress isolation.

## 1.11.0 — Explicit guided step completion

- Added a guided **I completed this step** action for reviewed accounts,
  password changes and sign-in tests. It records only the user's local
  confirmation for the current account and then advances the displayed step.
- Added browser regression coverage for the confirmation and resulting guided
  transition; no provider page, password, account sibling or vault item changes.

## 1.10.0 — Guided security sessions

- Added **Secure next account**, a local deterministic recommendation that resumes
  ready work or adds one highest-priority incomplete account without changing any
  provider, checklist or vault item.
- Added a step-specific guided card, verified password-settings action and a
  current-account-only Bitwarden CLI handoff with a second explicit confirmation.
- Kept browser companion account isolation intact: a website visit still cannot
  select, confirm or change an ARGUS account.

## 1.9.0 — Separate accounts at one service

- Added stable local account identities with independent checklists, sign-in
  methods, priorities, worklist entries and Bitwarden transfer journals.
- Strong direct evidence is grouped by provider and configured own address;
  forwarded, ambiguous, outdated and weak clues remain unassigned service clues.
  Address changes and aliases still require the user's review.
- Added explicitly confirmed local entries with labels for separate profiles
  that share an address. Bound addresses cannot be reassigned along with their
  completed work. Each selected account prepares one password-free vault item.
- Added transactional profile migration. Legacy progress follows one unambiguous
  or explicitly assigned identity, or remains preserved for review; sibling
  accounts never inherit it. Existing queue positions and interrupted transfers
  retain their account and transfer IDs.
- Dashboard, search, worklist, export and mobile details distinguish identities
  in English and German. `list-accounts` exposes IDs for precise CLI selections.
- Added migration rollback/restart, identity isolation, labeled duplicate and
  per-account CLI handoff regression coverage, plus five new browser check groups.
  Existing profile backups should be kept before upgrading; use version 1.9 or
  newer to work with migrated per-account state.

## 1.8.1 — Concurrent-scan safety fix

- Added an atomic SQLite lease around scheduled IMAP runs. A second dashboard
  using the same profile observes an active run instead of opening another
  mailbox connection; expired leases recover safely after interruption.
- Completion compares the lease ID, so an older worker cannot reactivate a
  schedule after disable/revocation or overwrite a newer worker's result.
- IMAP UID checkpoints now merge individual folder updates atomically instead
  of replacing the full cursor map.

## 1.8.0 — Opt-in background scans and browser companion

- Added an explicitly enabled, in-process scheduler for incremental read-only
  IMAP scans. It runs only while the local dashboard is open and uses the
  existing UID checkpoints, TLS, `EXAMINE` and `BODY.PEEK` path.
- IMAP authorization for scheduled scans is prompted only in a terminal and
  stored only in an OS-protected keyring. ARGUS has no file fallback, rejects
  known plaintext keyring backends, and supports status, pause and revocation.
- Added the dashboard's safe schedule-status display; it never accepts mailbox
  credentials. A missing or failing keyring produces only fixed local errors.
- Added a separate unpacked Chromium Manifest V3 browser companion. It requests
  only `activeTab`, never treats a visit as account evidence, and exposes only
  already verified password-management links from the bundled public catalog.
- Added scheduler, keyring, CLI, dashboard shape and browser-companion static
  regression coverage using synthetic data. No automatic password changes,
  mailbox changes or provider logins were added.

## 1.7.0 — Resumable security worklist and reliable Bitwarden handoff

- Added a persistent, bilingual security worklist with selection, pause/resume,
  deferral, manual completion and guided next steps for passwords, SSO and passkeys.
- Added a durable per-address Bitwarden creation journal and atomic reservations.
  CLI failures and timeouts require explicit vault review before another attempt.
  Successful addresses are excluded from later handoffs and metadata exports.
- Added explicit reconciliation of uncertain transfers, preservation of partial
  successes and protection against simultaneous creation attempts.
- Disabled real Bitwarden CLI transfers in the synthetic demo.
- Added migration, restart, concurrency, timeout, partial-batch, authorization and
  browser coverage using synthetic data and a fake CLI. No automatic provider
  password changes or scheduled background scans are included.

## 1.6.1 — Optional Bitwarden CLI handoff, 14 October 2026

- Added an opt-in dashboard handoff to an already-unlocked official Bitwarden CLI.
  It creates only explicitly selected, password-free metadata items and never
  reads, changes or overwrites existing vault items.
- Added German and English guidance for the local CLI handoff and a secure
  provider-change workflow. Passwords stay in Bitwarden; provider password
  changes still require the user to complete each service’s authentication, MFA
  and confirmation flow.
- Added regression coverage for the password-free CLI payload, required unlocked
  session and dashboard endpoint.

## 1.6.0 — Offline Pro licensing foundation, 14 October 2026

- Added Ed25519-signed, privacy-minimized Pro entitlement verification and local
  activation. The default build has no publisher public key, so it stays Free and
  cannot contact a payment service or activate arbitrary files.
- Added publisher-only key-generation and license-issuance tools. Private keys
  are never generated into, read from or committed by the application itself.
- Added license status and activation commands, a dashboard activation path for a
  future signed build, tests for valid, expired and tampered licenses, and
  commercial integration documentation.
- Licensed the Free edition source code under MPL-2.0 (`LICENSE`, `LICENSING.md`);
  earlier versions were published without a selected license.

## 1.5.0 — Freemium foundation, 14 October 2026

- Added the local **Account Compass Free** edition and a dashboard Plans page
  with a transparent, unavailable Pro preview.
- Product metadata is local and test-covered. The build contains no checkout,
  payment information, telemetry, online account or license activation.
- Added English/German Freemium documentation and a commercial-release checklist
  for the future publisher. It requires a real seller, license, legal terms,
  payment provider and signed entitlement design before paid features ship.
- Existing profiles, account detection, data schema and Free features remain
  unchanged.

## 1.4.0 — Public-release preparation and catalog expansion, 14 October 2026

- Built-in catalog expanded from 372 to **527** provider entries across all
  supported categories. The registry validates unique roots and specific
  subdomain precedence; no provider account queries were added.
- Public project materials: catalog policy, publication checklist, support guide,
  code of conduct, issue routing and Dependabot configuration.
- Package metadata now identifies the project, supported Python versions and
  repository URLs. A license remains an owner decision and is deliberately not
  assumed by this release.
- Readme reorganized for first-time users, with clear purpose, limitations,
  upgrade instructions and public-project links.
- Existing profiles remain compatible. Re-import local source emails or run an
  explicitly authorized full IMAP scan to consider new catalog domains.

## 1.3.0 — German/English interface, 14 October 2026

- Language selectors in the dashboard header and open account checklists;
  automatic browser language and locally remembered choice.
- Both languages for navigation, filters, categories, explanations, checklists,
  dates, imports, setup, validation and password-free Bitwarden notes.
- CLI follows system language with an explicit global `--language en|de` flag.
- Filters, checklist state, sign-in addresses, export selection and import
  progress survive language changes. Browser profiles choose independently.
- Full English and German installation/user guides; shared local translation
  catalog. No translation services or new runtime dependencies.
- Detection version remains 2; no re-import is needed from 1.1/1.2 for this change.
- 97 Python tests and 14 browser groups pass using artificial data only.

### Upgrade from 1.1 or 1.2

Stop the app, protect a backup of the data directory, replace source files and
restart with the same `--data-dir` and custom catalog. The database schema,
evidence, checklists, confirmations and identifiers are preserved. The language
preference belongs to each browser; it contains only `en` or `de`.

## 1.2.0 — English release, 14 October 2026

- English dashboard, navigation, checklists, filters, scan summaries, errors,
  setup guidance, CLI prompts and help, detection explanations, provider categories,
  Bitwarden notes, examples and documentation.
- App display name changed to **Account Compass**; package, command names,
  provider IDs, folder paths and database identifiers remain compatible.
- Legacy German program-generated caveats are displayed in English without
  rewriting stored data or changing manual confirmations.
- English date/search formatting. Official proper names and user-supplied text
  are preserved.
- English and German email detection rules are unchanged. No new runtime
  dependencies. Version 1.1 profiles need no email re-import solely for this change.
- 86 automated tests and eight browser checks pass with synthetic data, including
  preservation of a legacy German explanation and confirmation state.

### Upgrade from 1.1

Stop the dashboard and scanner, make a protected backup of your local data
directory, and replace the source code with version 1.2. Start with the same
`--data-dir` and additional catalog. Existing checklists, known addresses,
priorities, sign-in methods and evidence are preserved. Custom catalog labels are
used verbatim; translate your own labels if desired.

## 1.1.0 — Detection and workflow improvements, 14 October 2026

- Account creation is no longer hidden by an unsubscribe footer or a newsletter
  offer after the main message. Pure newsletter signups remain unknown.
- More English/German activation and verification phrases; negated events are
  rejected. Subject and body are not joined into an artificial event.
- Multiple own recipients do not cause an arbitrary username assignment.
- Reanalysis updates the original fingerprint, including changed clue type or
  newly cataloged domain. Obsolete automatic evidence is not retained as a second
  positive clue. Manual checklist state remains.
- Add own aliases through the dashboard or `add-email`. Existing aliases do not
  reset scan progress; demo and personal profiles stay separate.
- Durable multi-file statistics, import cancellation, expiry of abandoned import
  sessions, parallel-import protection and retained Bitwarden selection.
- Scan status distinguishes a message limit, interruption, errors, skips and
  header-only coverage. Address-scope changes interrupt a running scan safely.
- 85 automated tests and eight browser checks passed in the 1.1 release.

### Upgrade from 1.0

1. Stop the server and scanner and protect a backup of your local data directory.
2. Replace source code, keeping your personal data directory and additional catalog.
3. Start with the same `--data-dir`. The schema is extended automatically;
   checklists, manual confirmations, priorities and sign-in methods remain.
4. Older-rule evidence is marked for reanalysis and does not establish a current
   probable account until checked again. **Unknown never means no account exists.**
5. Re-import original local emails or explicitly authorize an IMAP scan. The rule
   change makes its first scan recheck older messages, without modifying them.

Email bodies are not stored, so old clues cannot be reinterpreted without access
to the original messages. This rule upgrade is separate from the 1.2 language change.

## 1.0.0 — Initial release, 13 October 2026

372-provider catalog, local email evidence, dashboard and checklists, local file
imports, read-only TLS IMAP, opt-in MX hints and password-free Bitwarden metadata
export. 56 automated tests and six browser groups passed with synthetic data.
