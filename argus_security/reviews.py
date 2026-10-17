# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""The person's own rule for checking completed accounts again (plan A10).

The rule only proposes a review date for completed accounts that have none;
the person applies it, one account or all at once, as ordinary undoable step
changes. The date is a reminder, not a finding: an account's age alone says
nothing about its security.
"""
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
import json

from .errors import UserFacingError

RULE = "review_rule"
MONTHS = (6, 12, 24)
SCOPES = ("important", "all")
# The account-level review is attached to the identity step: "does this account
# still exist, and is its sign-in still mine?"
REVIEW_STEP = "identity"


def set_rule(db, months, scope):
    """Save the rule, or switch it off with months None."""
    if months is None:
        db.execute("DELETE FROM meta WHERE key=?", (RULE,))
        return None
    if months not in MONTHS or scope not in SCOPES or type(months) is not int:
        raise UserFacingError("Choose 6, 12 or 24 months and which accounts the rule covers")
    rule = {"months": months, "scope": scope}
    db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (RULE, json.dumps(rule)))
    return rule


def load_rule(db):
    row = db.execute("SELECT value FROM meta WHERE key=?", (RULE,)).fetchone()
    rule = json.loads(row[0]) if row else None
    return rule if isinstance(rule, dict) and rule.get("months") in MONTHS and rule.get("scope") in SCOPES else None


def add_months(day, months):
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def proposals(accounts, rule, today=None):
    """Suggested review dates for completed accounts in scope without any review date."""
    if not rule:
        return {}
    today = today or datetime.now(timezone.utc).date()
    result = {}
    for account in accounts:
        if (account["progress"] != "complete" or not account["completed_at"] or account["decision"] == "rejected"
                or (rule["scope"] == "important" and account["priority"] == "normal")
                or any(step["review_after"] for step in account["steps"].values())):
            continue
        completed = datetime.fromisoformat(account["completed_at"]).date()
        result[account["id"]] = max(add_months(completed, rule["months"]), today + timedelta(days=1)).isoformat()
    return result
