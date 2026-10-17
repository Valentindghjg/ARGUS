# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Durable Bitwarden hand-offs over every path. An ambiguous write is never retried blindly.

States per account and sign-in address: ``running`` and ``uncertain`` (a CLI
write in progress or with an unknown result), ``exported`` (a password-free
file was downloaded; whether it was imported is unknown, plan B3),
``created`` and ``not_created``. Each unclear state blocks another download or
transfer until the person checks the vault and records what they found.
"""
import time
import uuid

from .changes import ChangeBatch
from .errors import UserFacingError
from .instances import read_steps, write_step
from .store import now

LEASE_SECONDS = 60  # Longer than the CLI's 20-second request deadline.


class HandoffError(UserFacingError):
    pass


def handoff_snapshot(store):
    with store.connect() as db:
        rows = db.execute("SELECT * FROM instance_bitwarden_handoffs ORDER BY updated, id").fetchall()
    moment = time.time()
    return [{"id": row["id"], "account_id": row["account_id"],
             "provider_id": row["provider_id"], "email": row["email"],
             "state": "uncertain" if row["state"] == "running" and row["lease_until"] <= moment else row["state"],
             "operation_id": row["operation_id"], "vault_item_id": row["vault_item_id"], "updated": row["updated"],
             "can_resolve": row["state"] in {"uncertain", "exported"} or (row["state"] == "running" and row["lease_until"] <= moment)}
            for row in rows]


def record_export(store, items):
    """Plan B3: a downloaded file counts as a hand-off whose import is not yet confirmed."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        for account_id, provider_id, email in items:
            db.execute("""INSERT INTO instance_bitwarden_handoffs(id,account_id,provider_id,email,state,operation_id,lease_until,updated)
                          VALUES (?,?,?,?,'exported',?,0,?) ON CONFLICT(account_id,email) DO UPDATE SET
                          state='exported',operation_id=excluded.operation_id,lease_until=0,vault_item_id=NULL,
                          updated=excluded.updated WHERE instance_bitwarden_handoffs.state='not_created'""",
                       (str(uuid.uuid4()), account_id, provider_id, email, str(uuid.uuid4()), now()))


def reserve(store, account_id, email):
    """Claim one account atomically across processes, before any external write."""
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        account = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
        if (not account or account["identity_review_required"] or
                email != (account["identity_email"] or account["manual_email"] or "")):
            raise HandoffError("Review this account's sign-in identity before transferring it.")
        row = db.execute("SELECT * FROM instance_bitwarden_handoffs WHERE account_id=? AND email=?", (account_id, email)).fetchone()
        if row and row["state"] == "created":
            return None
        if row and row["state"] == "exported":
            raise HandoffError("This account was downloaded for Bitwarden. Record whether you imported it before adding it again.")
        if row and row["state"] != "not_created":
            raise HandoffError("Check the unresolved Bitwarden transfer before trying again.")
        ident, operation = (row["id"] if row else str(uuid.uuid4())), str(uuid.uuid4())
        db.execute("""INSERT INTO instance_bitwarden_handoffs(id,account_id,provider_id,email,state,operation_id,lease_until,updated)
                      VALUES (?,?,?,?,'running',?,?,?) ON CONFLICT(account_id,email) DO UPDATE SET
                      state='running',operation_id=excluded.operation_id,lease_until=excluded.lease_until,
                      vault_item_id=NULL,updated=excluded.updated""",
                   (ident, account_id, account["provider_id"], email, operation, time.time() + LEASE_SECONDS, now()))
    return {"id": ident, "operation_id": operation}


def finish(store, attempt, state, vault_item_id=None):
    if state not in {"created", "uncertain"}:
        raise ValueError("Invalid transfer result")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        changed = db.execute("""UPDATE instance_bitwarden_handoffs SET state=?,vault_item_id=?,lease_until=0,updated=?
                                WHERE id=? AND operation_id=? AND state='running'""",
                             (state, vault_item_id, now(), attempt["id"], attempt["operation_id"])).rowcount
        if changed != 1:
            raise HandoffError("Check the unresolved Bitwarden transfer before trying again.")
        if state == "created":
            account_id = db.execute("SELECT account_id FROM instance_bitwarden_handoffs WHERE id=?", (attempt["id"],)).fetchone()[0]
            _mark_assigned_if_complete(db, account_id)


def mark_assigned_if_complete(store, account_id):
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        return _mark_assigned_if_complete(db, account_id)


def _mark_assigned_if_complete(db, account_id):
    """Mark the vault step "prepared" in the transaction that records the creation.

    This is the only automatic change to a security step (ADR-0001, rule 4): a
    password-free item exists, but only the person can mark the step done once
    the password is stored in Bitwarden.
    """
    account_row = db.execute("SELECT * FROM account_instances WHERE id=?", (account_id,)).fetchone()
    if not account_row or account_row["identity_review_required"]:
        return False
    expected = account_row["identity_email"] or account_row["manual_email"] or ""
    if not db.execute("SELECT 1 FROM instance_bitwarden_handoffs WHERE account_id=? AND email=? AND state='created'",
                      (account_id, expected)).fetchone():
        return False
    vault = read_steps(db, account_id, account_row["login_method"])["vault"]
    if vault["state"] == "open":
        prepared = {**vault, "state": "prepared", "done_at": now()}
        write_step(db, account_id, "vault", prepared)
        batch = ChangeBatch(db)
        batch.record(account_id, "step:vault", vault, prepared)
        batch.close()
        db.execute("UPDATE account_instances SET updated=? WHERE id=?", (now(), account_id))
    return True


def resolve(store, data):
    if (set(data) != {"id", "created", "confirmed"} or not isinstance(data["id"], str)
            or type(data["created"]) is not bool or data["confirmed"] is not True):
        raise UserFacingError("Confirm the transfer result after checking Bitwarden")
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM instance_bitwarden_handoffs WHERE id=?", (data["id"],)).fetchone()
        if not row or row["state"] not in {"running", "uncertain", "exported"}:
            raise UserFacingError("Transfer does not need review")
        if row["state"] == "running" and row["lease_until"] > time.time():
            raise HandoffError("The Bitwarden transfer is still running. Wait before checking its result.")
        db.execute("UPDATE instance_bitwarden_handoffs SET state=?,lease_until=0,updated=? WHERE id=?",
                   ("created" if data["created"] else "not_created", now(), row["id"]))
        if data["created"]:
            _mark_assigned_if_complete(db, row["account_id"])
    return {"ok": True}
