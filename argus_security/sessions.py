# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Short work sessions and their local report (plan A8, A20).

A session is one or three ready worklist tasks the person chooses to work on
now. It sets no deadline and makes no time estimate. Its report is derived
from the accounts' own steps and decisions since the session started, so it
shows only what the person recorded and follows every undo. The text export
contains account names, step names and dates only: no address, evidence,
password or vault data. It is shown in full before it is saved.
"""
import json

from .errors import UserFacingError
from .i18n import translate

KEY = "work_session"
DECISION_NAMES = {"confirmed": "Confirmed by you", "rejected": "Rejected by you"}
SIZES = (1, 3)
STEP_NAMES = {"identity": "Sign-in checked", "vault": "Stored in Bitwarden", "password": "Unique password",
              "signin_test": "Sign-in tested", "mfa_recovery": "MFA and recovery"}
NEXT_NAMES = {"identify": "Choose the sign-in address", "review": "Decide whether this account is yours",
              "identity": "Sign-in checked", "bitwarden": "Stored in Bitwarden", "change_password": "Unique password",
              "test_signin": "Sign-in tested", "mfa": "MFA and recovery", "done": "Complete"}


def load(db):
    row = db.execute("SELECT value FROM meta WHERE key=?", (KEY,)).fetchone()
    session = json.loads(row[0]) if row else None
    return session if isinstance(session, dict) else None


def start(db, size, workflow, moment):
    if size not in SIZES or type(size) is not int:
        raise UserFacingError("Choose a session with one or three tasks")
    if workflow["paused"]:
        raise UserFacingError("Resume the worklist before starting a session")
    ready = [item["id"] for item in workflow["items"] if not item["deferred"] and item["step"] != "done"]
    if not ready:
        raise UserFacingError("Add accounts to your worklist before starting a session")
    session = {"started_at": moment, "size": size, "accounts": ready[:size]}
    db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (KEY, json.dumps(session)))
    db.execute("INSERT INTO meta VALUES ('worklist_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (json.dumps(ready[0]),))
    return session


def end(db):
    if not db.execute("DELETE FROM meta WHERE key=?", (KEY,)).rowcount:
        raise UserFacingError("There is no session to end")


def report(session, accounts):
    """What happened in the session's accounts since it started, from their own state."""
    if not session:
        return None
    by_id = {account["id"]: account for account in accounts}
    since = session["started_at"]
    rows = []
    for account_id in session["accounts"]:
        account = by_id.get(account_id)
        if account is None:
            continue
        done = [step for step, value in account["steps"].items()
                if value["state"] in {"done", "not_applicable"} and (value["done_at"] or "") >= since]
        rows.append({"id": account_id, "name": account["name"], "label": account.get("label") or "",
                     "decided": bool(account["decided_at"]) and account["decided_at"] >= since,
                     "decision": account["decision"], "done": done, "next_step": account["next_step"]})
    return {"started_at": since, "size": session["size"], "accounts": rows,
            "finished": sum(row["next_step"] == "done" for row in rows),
            "steps_done": sum(len(row["done"]) for row in rows)}


def report_text(summary, language="en"):
    """A short, data-minimal text of the session for the person to keep."""
    def t(message, **values):
        return translate(message, language, **values)
    lines = [t("ARGUS session report"), t("Started: {date}", date=summary["started_at"][:10]),
             t("Finished accounts: {finished} of {total}", finished=summary["finished"], total=len(summary["accounts"])),
             ""]
    for row in summary["accounts"]:
        name = row["name"] + (f" ({row['label']})" if row["label"] else "")
        decided = DECISION_NAMES.get(row["decision"]) if row["decided"] else None
        done = ", ".join(([t(decided)] if decided else []) + [t(STEP_NAMES[step]) for step in row["done"]]) \
            or t("nothing recorded yet")
        following = "Nothing more to do" if row["decision"] == "rejected" else NEXT_NAMES[row["next_step"]]
        lines.append(t("- {name}: done: {done}; next: {next}", name=name, done=done, next=t(following)))
    lines += ["", t("This report lists only steps you recorded in ARGUS. It contains no email addresses, "
                    "evidence or passwords and is not a security guarantee.")]
    return "\n".join(lines) + "\n"
