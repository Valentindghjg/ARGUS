# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Local change log for the person's decisions, steps and planning (ADR-0001, rule 3).

Each entry holds a field name, the old and new value and a time, grouped in a
batch per user action. It never holds message contents, secrets or vault
data. External effects (Bitwarden items, scans) are not part of it and are
never undone. Retention is limited.
"""
import json
import uuid

from .errors import UserFacingError
from .instances import read_steps, timestamp, write_step

KEEP_ENTRIES = 1000


def planning(db, account_id):
    """Axis D of one account, in the form the change log stores."""
    row = db.execute("SELECT * FROM instance_work_queue WHERE account_id=?", (account_id,)).fetchone()
    if row is None:
        return {"queued": False, "position": None, "deferred": False, "resume_after": None}
    return {"queued": True, "position": row["position"], "deferred": bool(row["deferred"]),
            "resume_after": row["resume_after"]}


class ChangeBatch:
    """Collects the changes of one user action inside the caller's transaction."""

    def __init__(self, db, undo_of=None):
        self.db = db
        self.id = str(uuid.uuid4())
        self.undo_of = undo_of
        self.count = 0

    def record(self, account_id, field, old, new):
        if old == new:
            return
        self.db.execute("""INSERT INTO change_log(batch,at,account_id,field,old,new,undo_of)
                           VALUES (?,?,?,?,?,?,?)""",
                        (self.id, timestamp(), account_id, field, json.dumps(old, ensure_ascii=False),
                         json.dumps(new, ensure_ascii=False), self.undo_of))
        self.count += 1

    def close(self):
        """Prune the oldest entries beyond the retention limit."""
        if self.count:
            # Whole batches only, so a remaining batch can always be undone completely.
            self.db.execute("""DELETE FROM change_log WHERE batch IN (
                                 SELECT batch FROM change_log WHERE id <= (
                                   SELECT id FROM change_log ORDER BY id DESC LIMIT 1 OFFSET ?))""", (KEEP_ENTRIES,))
        return self.id if self.count else None


def current_value(db, account_id, field):
    """The present value of one logged field, in the logged form."""
    if field == "planning":
        return planning(db, account_id)
    row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
    if row is None:
        return None
    if field == "decision":
        return {"decision": row["decision"], "reason": row["decision_reason"], "decided_at": row["decided_at"]}
    if field.startswith("step:"):
        return read_steps(db, account_id, row["login_method"]).get(field[5:])
    return None


def apply_value(db, account_id, field, value):
    if field == "decision":
        db.execute("UPDATE account_instances SET decision=?,decision_reason=?,decided_at=?,updated=? WHERE id=?",
                   (value["decision"], value["reason"], value["decided_at"], timestamp(), account_id))
    elif field.startswith("step:"):
        write_step(db, account_id, field[5:], value)
    elif field == "planning":
        if not value["queued"]:
            db.execute("DELETE FROM instance_work_queue WHERE account_id=?", (account_id,))
        else:
            db.execute("""INSERT INTO instance_work_queue(account_id,position,deferred,resume_after) VALUES (?,?,?,?)
                          ON CONFLICT(account_id) DO UPDATE SET position=excluded.position,
                          deferred=excluded.deferred,resume_after=excluded.resume_after""",
                       (account_id, value["position"], int(value["deferred"]), value["resume_after"]))
    else:
        raise ValueError("Unknown change field")


def undo(db, batch=None):
    """Revert one batch, by default the newest one not yet undone, under BEGIN IMMEDIATE.

    Undo is itself a logged batch; undoing that batch restores the change
    again. A field that changed again later blocks the undo, so a newer
    decision is never overwritten silently.
    """
    if batch is None:
        row = db.execute("""SELECT batch FROM change_log WHERE undone_by IS NULL AND undo_of IS NULL
                            ORDER BY id DESC LIMIT 1""").fetchone()
        if row is None:
            raise UserFacingError("There is no local change to undo")
        batch = row["batch"]
    if not isinstance(batch, str):
        raise UserFacingError("There is no local change to undo")
    entries = db.execute("SELECT * FROM change_log WHERE batch=? ORDER BY id", (batch,)).fetchall()
    if not entries or any(entry["undone_by"] for entry in entries):
        raise UserFacingError("There is no local change to undo")
    for entry in entries:
        if current_value(db, entry["account_id"], entry["field"]) != json.loads(entry["new"]):
            raise UserFacingError("This change was changed again later; undo the later change first")
    reverse = ChangeBatch(db, undo_of=batch)
    for entry in reversed(entries):
        old = json.loads(entry["old"])
        apply_value(db, entry["account_id"], entry["field"], old)
        reverse.record(entry["account_id"], entry["field"], json.loads(entry["new"]), old)
    db.execute("UPDATE change_log SET undone_by=? WHERE batch=?", (reverse.id, batch))
    reverse.close()
    return {"undone": batch, "batch": reverse.id, "accounts": sorted({entry["account_id"] for entry in entries})}


def recent(db, limit=20):
    """The newest batches with their entries, for a local history view."""
    batches = [row["batch"] for row in db.execute(
        "SELECT batch, MAX(id) AS last FROM change_log GROUP BY batch ORDER BY last DESC LIMIT ?", (limit,))]
    result = []
    for batch in batches:
        entries = db.execute("SELECT * FROM change_log WHERE batch=? ORDER BY id", (batch,)).fetchall()
        result.append({"batch": batch, "at": entries[-1]["at"], "undo_of": entries[0]["undo_of"],
                       "undone": any(entry["undone_by"] for entry in entries),
                       "changes": [{"account_id": entry["account_id"], "field": entry["field"],
                                    "old": json.loads(entry["old"]), "new": json.loads(entry["new"])}
                                   for entry in entries]})
    return result
