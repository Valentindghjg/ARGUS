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

from .instances import timestamp

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
