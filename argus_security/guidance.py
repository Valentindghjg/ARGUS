# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Concrete next steps for known problems (master plan F4).

Each entry maps the constant text of an error, or one scan outcome, to one
constant, translatable instruction. Hints never contain paths, addresses,
message content or secrets: callers look them up only by the fixed message.
"""

PROFILE_FIRST = ("Start with argus init --email followed by your own address. For a test run, "
                 "use argus demo with a separate --data-dir.")
CHECK_SOURCE_PATH = "Check the path. ARGUS reads only the file or folder you name and never searches your computer."
IDENTIFY_ACCOUNT = "Open the account and choose its sign-in address, or add a separate account for another address."

HINTS = {
    # Local files and import sessions
    "EML path not found": CHECK_SOURCE_PATH,
    "mbox file not found": CHECK_SOURCE_PATH,
    "Maildir requires cur/ and new/": "Choose the Maildir folder that directly contains the cur and new folders.",
    "The destination file already exists and will not be overwritten.":
        "Choose a new file name. Delete older exports after importing them; they contain personal metadata.",
    "Operation interrupted or local file access / port unavailable.":
        "If the dashboard port is in use, add --port with another number. An interrupted import keeps its saved clues; "
        "import the same source again to continue.",
    # Profile set-up
    "Configure your own email addresses with init first": PROFILE_FIRST,
    "Run init or demo first": PROFILE_FIRST,
    "Initialize a personal local profile with init first": PROFILE_FIRST,
    "IMAP requires an initialized personal local profile": PROFILE_FIRST,
    "Background IMAP requires an initialized personal local profile": PROFILE_FIRST,
    "Aliases require an initialized personal profile": PROFILE_FIRST,
    "The demo requires a separate data directory":
        "Start the demo with its own folder, for example --data-dir .local/demo. Your personal profile stays unchanged.",
    # Backups
    "There is no local profile to back up yet": PROFILE_FIRST,
    "The backup could not be written; nothing was changed":
        "Check the free disk space and that the backup folder is writable, then try again.",
    "The backup is damaged; its checksums do not match":
        "Use another backup. ARGUS keeps the latest automatic backups in the backups folder of the profile.",
    "This profile was updated by a newer ARGUS version; update ARGUS first":
        "Or restore a backup from before that update with argus restore.",
    # Local database
    "The local database is temporarily unavailable":
        "Wait a moment and try again. If it keeps happening, close other ARGUS windows or terminals that use this profile.",
    # Mailbox access
    "No readable, selectable IMAP folders were found":
        "Check the folder names with setup-imap, or choose all folders.",
    "Could not read the IMAP folder list":
        "Try again later. Saved progress is preserved; the next scan continues from the last checkpoint.",
    "Could not read the IMAP message list":
        "Try again later. Saved progress is preserved; the next scan continues from the last checkpoint.",
    "The OS keyring is unavailable; background scans cannot safely store IMAP authorization":
        "Use scan-imap for manual scans; they never store the authorization. Scheduled scans need a working system keyring.",
    "The IMAP authorization is missing or invalid":
        "Run background-imap enable again to store a fresh authorization, or use a manual scan-imap.",
    # Bitwarden and accounts
    "The official Bitwarden CLI is not installed or not on PATH.":
        "Install the official Bitwarden CLI, or download the metadata as Bitwarden JSON instead; that needs no CLI.",
    "Check the unresolved Bitwarden transfer before trying again.":
        "Open Prepare Bitwarden, search your vault for the transfer ID shown there and record what you found.",
    "Review this account's sign-in identity before transferring it.": IDENTIFY_ACCOUNT,
    "Review this account's sign-in identity before checking Bitwarden.": IDENTIFY_ACCOUNT,
    "Identify this account before marking it done": IDENTIFY_ACCOUNT,
    "Check the required steps before marking this account done":
        "Required: verified by you, assigned in Bitwarden, sign-in tested and, for password sign-ins, a new password.",
}

SCAN_STEPS = {
    "skipped": "Skipped messages were empty, not EML or larger than 2 MiB. Save large messages without attachments "
               "and import them again.",
    "errors": "Some messages could not be analyzed. Export them again from your email client; ARGUS keeps no "
              "message content.",
    "headers_only": "Large messages were analyzed using headers only, so their clues can be weaker. Review those "
                    "accounts yourself.",
    "partial": "The scan stopped early. Run the same import or scan again; messages already analyzed are recognized "
               "and not counted twice.",
    "limited": "The processing limit was reached, so this is not a complete result. Run the same import or scan "
               "again to continue; messages already processed are skipped.",
    "scope_changed": "Your own addresses changed during the scan. Start it again so every message is checked "
                     "against the current addresses.",
}


def hint_for(message):
    """Return the next step for one constant error text, or None."""
    return HINTS.get(message) if isinstance(message, str) else None


def scan_next_steps(stats):
    """Return the next steps for a scan's gaps, most important first."""
    if not isinstance(stats, dict) or stats.get("running"):
        return []
    steps = []
    if stats.get("scope_changed"):
        steps.append(SCAN_STEPS["scope_changed"])
    elif stats.get("result") == "partial":
        steps.append(SCAN_STEPS["partial"])
    if stats.get("result") == "limited":
        steps.append(SCAN_STEPS["limited"])
    for key in ("skipped", "errors", "headers_only"):
        if type(stats.get(key)) is int and stats[key] > 0:
            steps.append(SCAN_STEPS[key])
    return steps
