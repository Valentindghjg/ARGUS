# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""A plan for moving accounts from one own address to another (plan A21, P4).

ARGUS lists the accounts that sign in with the old address and orders them:
accounts others depend on first (they receive resets for the rest), then by
priority. The person changes the address at each provider and marks the item
here; ARGUS never changes anything at a provider and never moves an account's
sign-in identity by itself. Creating a plan also notes that the old address was
replaced by the new one.
"""
import uuid

from .errors import UserFacingError
from .review import relate

SCHEMA = """
CREATE TABLE IF NOT EXISTS move_plans (
  id TEXT PRIMARY KEY,
  old_address TEXT NOT NULL,
  new_address TEXT NOT NULL,
  created_at TEXT NOT NULL,
  closed_at TEXT
);
CREATE TABLE IF NOT EXISTS move_items (
  plan_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  state TEXT NOT NULL DEFAULT 'open',
  changed_at TEXT,
  PRIMARY KEY(plan_id, account_id)
);
"""
ITEM_STATES = ("open", "changed", "skipped")
RANK = {"critical": 0, "high": 1, "normal": 2}


def order(accounts, old):
    """Accounts that sign in with the old address, identity accounts and high priority first."""
    moving = [a for a in accounts if a["identity_email"] == old and a["decision"] != "rejected"]
    return sorted(moving, key=lambda a: (-a.get("dependents", 0), RANK[a["priority"]],
                                         a["decision"] != "confirmed", a["name"].casefold(), a["id"]))


def create(db, accounts, old, new, owned, moment):
    if old == new or old not in owned or new not in owned:
        raise UserFacingError("Choose two different addresses of your own")
    if db.execute("SELECT 1 FROM move_plans WHERE old_address=? AND closed_at IS NULL", (old,)).fetchone():
        raise UserFacingError("There is already an open plan for this address")
    items = order(accounts, old)
    if not items:
        raise UserFacingError("No account signs in with this address")
    plan_id = str(uuid.uuid4())
    db.execute("INSERT INTO move_plans(id,old_address,new_address,created_at) VALUES (?,?,?,?)",
               (plan_id, old, new, moment))
    for position, account in enumerate(items, start=1):
        db.execute("INSERT INTO move_items(plan_id,account_id,position) VALUES (?,?,?)", (plan_id, account["id"], position))
    # The relation note from plan E4 explains the plan on both addresses' accounts.
    relate(db, old, new, "replaced_by", owned, moment)
    return plan_id


def mark(db, plan_id, account_id, state, moment):
    if state not in ITEM_STATES:
        raise UserFacingError("Mark the item as changed, skipped or open")
    plan = db.execute("SELECT * FROM move_plans WHERE id=?", (plan_id,)).fetchone()
    if plan is None or plan["closed_at"]:
        raise UserFacingError("This plan is closed or no longer exists")
    changed = db.execute("UPDATE move_items SET state=?,changed_at=? WHERE plan_id=? AND account_id=?",
                         (state, moment if state != "open" else None, plan_id, account_id)).rowcount
    if not changed:
        raise UserFacingError("This account is not part of the plan")


def close(db, plan_id, moment):
    if not db.execute("UPDATE move_plans SET closed_at=? WHERE id=? AND closed_at IS NULL", (moment, plan_id)).rowcount:
        raise UserFacingError("This plan is closed or no longer exists")


def plans(db):
    result = []
    for plan in db.execute("SELECT * FROM move_plans ORDER BY created_at DESC"):
        items = [{"account_id": row["account_id"], "position": row["position"], "state": row["state"],
                  "changed_at": row["changed_at"]}
                 for row in db.execute("SELECT * FROM move_items WHERE plan_id=? ORDER BY position", (plan["id"],))]
        result.append({"id": plan["id"], "old": plan["old_address"], "new": plan["new_address"],
                       "created_at": plan["created_at"], "closed_at": plan["closed_at"], "items": items,
                       "done": sum(item["state"] != "open" for item in items)})
    return result
