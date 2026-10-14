"""Durable Bitwarden creation attempts. An ambiguous write is never retried blindly."""
import json
import time
import uuid

from .analysis import ANALYSIS_VERSION
from .store import now

LEASE_SECONDS = 60  # Longer than the CLI's 20-second request deadline.


class HandoffError(ValueError):
    pass


def handoff_snapshot(store):
    with store.connect() as db:
        rows = db.execute("SELECT * FROM bitwarden_handoffs ORDER BY updated, id").fetchall()
    moment = time.time()
    return [{"id": row["id"], "provider_id": row["provider_id"], "email": row["email"],
             "state": "uncertain" if row["state"] == "running" and row["lease_until"] <= moment else row["state"],
             "operation_id": row["operation_id"], "vault_item_id": row["vault_item_id"],
             "can_resolve": row["state"] == "uncertain" or (row["state"] == "running" and row["lease_until"] <= moment)}
            for row in rows]


def reserve(store, provider_id, email):
    """Claim one account atomically across processes, before any external write."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM bitwarden_handoffs WHERE provider_id=? AND email=?", (provider_id, email)).fetchone()
        if row and row["state"] == "created":
            return None
        if row and row["state"] != "not_created":
            raise HandoffError("Check the unresolved Bitwarden transfer before trying again.")
        ident, operation = (row["id"] if row else str(uuid.uuid4())), str(uuid.uuid4())
        db.execute("""INSERT INTO bitwarden_handoffs(id,provider_id,email,state,operation_id,lease_until,updated)
                      VALUES (?,?,?,'running',?,?,?) ON CONFLICT(provider_id,email) DO UPDATE SET
                      state='running',operation_id=excluded.operation_id,lease_until=excluded.lease_until,
                      vault_item_id=NULL,updated=excluded.updated""",
                   (ident, provider_id, email, operation, time.time() + LEASE_SECONDS, now()))
    return {"id": ident, "operation_id": operation}


def finish(store, attempt, state, vault_item_id=None):
    if state not in {"created", "uncertain"}:
        raise ValueError("Invalid transfer result")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute("""UPDATE bitwarden_handoffs SET state=?,vault_item_id=?,lease_until=0,updated=?
                                WHERE id=? AND operation_id=? AND state='running'""",
                             (state, vault_item_id, now(), attempt["id"], attempt["operation_id"])).rowcount
        if changed != 1:
            raise HandoffError("Check the unresolved Bitwarden transfer before trying again.")
        if state == "created":
            provider_id = db.execute("SELECT provider_id FROM bitwarden_handoffs WHERE id=?", (attempt["id"],)).fetchone()[0]
            _mark_assigned_if_complete(db, provider_id)


def mark_assigned_if_complete(store, provider_id):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        return _mark_assigned_if_complete(db, provider_id)


def _mark_assigned_if_complete(db, provider_id):
    """Commit final creation and its checklist flag in the same transaction."""
    account_row = db.execute("SELECT checklist,status,manual_email FROM accounts WHERE provider_id=?", (provider_id,)).fetchone()
    expected = {row[0] for row in db.execute("""SELECT registered_email FROM evidence
                WHERE provider_id=? AND rule_version>=? AND registered_email IS NOT NULL""", (provider_id, ANALYSIS_VERSION))}
    if account_row["manual_email"]:
        expected.add(account_row["manual_email"])
    expected = expected or {""}
    created = {row[0] for row in db.execute("SELECT email FROM bitwarden_handoffs WHERE provider_id=? AND state='created'", (provider_id,))}
    if not expected <= created:
        return False
    checklist = json.loads(account_row["checklist"])
    checklist["saved_in_bitwarden"] = True
    status = "in_progress" if account_row["status"] == "pending" else account_row["status"]
    db.execute("UPDATE accounts SET checklist=?,status=?,updated=? WHERE provider_id=?",
               (json.dumps(checklist), status, now(), provider_id))
    return True


def resolve(store, data):
    if (set(data) != {"id", "created", "confirmed"} or not isinstance(data["id"], str)
            or type(data["created"]) is not bool or data["confirmed"] is not True):
        raise ValueError("Confirm the transfer result after checking Bitwarden")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM bitwarden_handoffs WHERE id=?", (data["id"],)).fetchone()
        if not row or row["state"] not in {"running", "uncertain"}:
            raise ValueError("Transfer does not need review")
        if row["state"] == "running" and row["lease_until"] > time.time():
            raise HandoffError("The Bitwarden transfer is still running. Wait before checking its result.")
        db.execute("UPDATE bitwarden_handoffs SET state=?,lease_until=0,updated=? WHERE id=?",
                   ("created" if data["created"] else "not_created", now(), row["id"]))
        if data["created"]:
            _mark_assigned_if_complete(db, row["provider_id"])
    return {"ok": True}
