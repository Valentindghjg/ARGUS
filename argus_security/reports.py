# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Data-minimal progress reports (plan P5).

"numbers" holds counts and their change over time only. "tasks" adds one line
per account with its name, priority, decision, progress and next step.
Sign-in addresses appear only when the person explicitly includes them;
evidence, message content, notes and vault data never do. The text is shown in
full before it is saved.
"""
from .errors import UserFacingError
from .history import KEYS
from .i18n import translate
from .sessions import NEXT_NAMES

LEVELS = ("numbers", "tasks")
COUNT_LABELS = {"clues": "Clues", "found": "Accounts found", "confirmed": "Confirmed by you",
                "complete": "Complete", "open": "Still open", "unclear": "Unclear items",
                "high_priority_open": "Open with high priority"}
DECISIONS = {"undecided": "Not decided", "confirmed": "Confirmed", "rejected": "Rejected"}
PROGRESS = {"not_started": "Not started", "in_progress": "In progress", "complete": "Complete"}
PRIORITIES = {"critical": "Do first", "high": "High", "normal": "Normal"}


def build(snapshot, level="numbers", include_addresses=False, language="en"):
    if level not in LEVELS or type(include_addresses) is not bool or (include_addresses and level != "tasks"):
        raise UserFacingError("Choose numbers only, or tasks with or without sign-in addresses")

    def t(message, **values):
        return translate(message, language, **values)
    today = snapshot["history"]["today"]
    lines = [t("ARGUS progress report"), t("Created: {date}", date=snapshot["history"]["day"]), ""]
    lines += [f"{t(COUNT_LABELS[key])}: {today[key]}" for key in KEYS]
    for comparison in snapshot["history"]["comparisons"]:
        changes = ", ".join(f"{t(COUNT_LABELS[key])} {value:+d}" for key, value in comparison["delta"].items() if value)
        lines.append(t("Since {date}: {changes}", date=comparison["since"], changes=changes or t("no change")))
    if level == "tasks":
        lines += ["", t("Accounts")]
        accounts = [a for a in snapshot["accounts"] if a["classification"] != "unknown" and a["decision"] != "rejected"]
        for account in accounts:
            name = account["name"] + (f" ({account['label']})" if account.get("label") else "")
            if include_addresses and account.get("identity_email"):
                name += f" <{account['identity_email']}>"
            lines.append(t("- {name}: {priority}; {decision}; {progress}; next: {next}", name=name,
                           priority=t(PRIORITIES[account["priority"]]), decision=t(DECISIONS[account["decision"]]),
                           progress=t(PROGRESS[account["progress"]]), next=t(NEXT_NAMES[account["next_step"]])))
    lines += ["", t("Counts and steps recorded in ARGUS on this computer. ARGUS cannot find every account; "
                    "this report is not a security guarantee.")]
    if not include_addresses:
        lines.append(t("No email addresses, evidence or passwords are included."))
    return "\n".join(lines) + "\n"

