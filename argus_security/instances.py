# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Stable local account identities, with conservative migration of older inventories.

The tables follow ADR-0001: an account row holds identity, attributes and the
person's decision; ``account_steps`` holds the security steps; the work queue
holds planning; ``change_log`` records every change to decision, steps and
planning so it can be undone.
"""
from datetime import datetime, timezone
import json
import uuid

from .analysis import ANALYSIS_VERSION, english_caveat, normalize_email
from .states import default_steps, from_legacy


ACCOUNT_TABLE = """
CREATE TABLE IF NOT EXISTS account_instances (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  identity_email TEXT,
  canonical INTEGER NOT NULL DEFAULT 1,
  label TEXT NOT NULL DEFAULT '',
  identity_review_required INTEGER NOT NULL DEFAULT 0,
  priority_override TEXT,
  login_method TEXT NOT NULL DEFAULT 'password',
  manual_email TEXT,
  decision TEXT NOT NULL DEFAULT 'undecided',
  decision_reason TEXT,
  decided_at TEXT,
  decided_evidence_id INTEGER,
  updated TEXT NOT NULL
)"""
ACCOUNT_INDEXES = (
    "CREATE INDEX IF NOT EXISTS instances_provider ON account_instances(provider_id)",
    """CREATE UNIQUE INDEX IF NOT EXISTS instances_canonical_email
       ON account_instances(provider_id,identity_email)
       WHERE canonical=1 AND identity_email IS NOT NULL""",
)
SCHEMA = ACCOUNT_TABLE + ";\n" + ";\n".join(ACCOUNT_INDEXES) + """;
CREATE TABLE IF NOT EXISTS account_steps (
  account_id TEXT NOT NULL,
  step TEXT NOT NULL,
  state TEXT NOT NULL,
  done_at TEXT,
  review_after TEXT,
  PRIMARY KEY(account_id, step)
);
CREATE TABLE IF NOT EXISTS instance_work_queue (
  account_id TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  deferred INTEGER NOT NULL DEFAULT 0,
  resume_after TEXT
);
CREATE TABLE IF NOT EXISTS instance_bitwarden_handoffs (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  provider_id TEXT NOT NULL,
  email TEXT NOT NULL,
  state TEXT NOT NULL,
  operation_id TEXT NOT NULL,
  lease_until REAL NOT NULL DEFAULT 0,
  vault_item_id TEXT,
  updated TEXT NOT NULL,
  UNIQUE(account_id,email)
);
CREATE TABLE IF NOT EXISTS change_log (
  id INTEGER PRIMARY KEY,
  batch TEXT NOT NULL,
  at TEXT NOT NULL,
  account_id TEXT NOT NULL,
  field TEXT NOT NULL,
  old TEXT,
  new TEXT,
  undo_of TEXT,
  undone_by TEXT
);
CREATE INDEX IF NOT EXISTS change_log_batch ON change_log(batch);
"""


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def owned_emails(db):
    row = db.execute("SELECT value FROM meta WHERE key='emails'").fetchone()
    return set(json.loads(row[0])) if row else set()


def direct_identity(evidence, owned):
    """Only a current, strong, unambiguous own recipient can bind an identity."""
    if evidence["rule_version"] < ANALYSIS_VERSION or evidence["score"] < 60:
        return None
    email = evidence["registered_email"]
    if not email:
        return None
    try:
        email = normalize_email(email)
    except (TypeError, ValueError):
        return None
    caveat = english_caveat(evidence["caveat"]) or ""
    if (email not in owned or "Forwarding / recipient association uncertain" in caveat
            or "Multiple own recipients; sign-in address uncertain" in caveat):
        return None
    return email


def read_steps(db, account_id, login_method="password"):
    steps = default_steps(login_method)
    for row in db.execute("SELECT * FROM account_steps WHERE account_id=?", (account_id,)):
        if row["step"] in steps:
            steps[row["step"]] = {"state": row["state"], "done_at": row["done_at"], "review_after": row["review_after"]}
    return steps


def write_step(db, account_id, step, value):
    """Store one step; the plain default (open, no dates) needs no row."""
    if value["state"] == "open" and not value.get("done_at") and not value.get("review_after"):
        db.execute("DELETE FROM account_steps WHERE account_id=? AND step=?", (account_id, step))
        return
    db.execute("""INSERT INTO account_steps(account_id,step,state,done_at,review_after) VALUES (?,?,?,?,?)
                  ON CONFLICT(account_id,step) DO UPDATE SET state=excluded.state,done_at=excluded.done_at,
                  review_after=excluded.review_after""",
               (account_id, step, value["state"], value.get("done_at"), value.get("review_after")))


def has_progress(db, state):
    """True once a person decided or did anything for this account."""
    if (state["decision"] != "undecided" or state["priority_override"] is not None
            or state["login_method"] != "password" or bool(state["manual_email"])):
        return True
    return db.execute("SELECT 1 FROM account_steps WHERE account_id=? AND state IN ('done','prepared')",
                      (state["id"],)).fetchone() is not None


def insert_instance(db, provider_id, email=None, *, ident=None, canonical=True, label="", review=False,
                    manual=False, decision="undecided", decided_at=None, steps=None, login_method="password",
                    priority_override=None, manual_email=None, updated=None):
    if ident is None:
        ident = provider_id if not db.execute("SELECT 1 FROM account_instances WHERE id=?", (provider_id,)).fetchone() else str(uuid.uuid4())
    db.execute("""INSERT INTO account_instances
      (id,provider_id,identity_email,canonical,label,identity_review_required,priority_override,
       login_method,manual_email,decision,decided_at,updated)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
        ident, provider_id, email, int(canonical), label, int(review), priority_override,
        login_method, email if manual else manual_email, decision, decided_at, updated or timestamp(),
    ))
    for step, value in (steps or default_steps(login_method)).items():
        write_step(db, ident, step, value)
    return ident


def synchronize_instances(db, registry, provider_ids=None):
    """Add identities for direct proof without ever copying an existing decision or step."""
    owned = owned_emails(db)
    grouped = {}
    for row in db.execute("SELECT * FROM evidence WHERE provider_id IS NOT NULL"):
        if row["provider_id"] in registry.providers and (provider_ids is None or row["provider_id"] in provider_ids):
            grouped.setdefault(row["provider_id"], []).append(dict(row))
    for provider_id, evidence in grouped.items():
        identities = sorted({email for item in evidence if (email := direct_identity(item, owned))})
        states = [dict(row) for row in db.execute("SELECT * FROM account_instances WHERE provider_id=?", (provider_id,))]
        for email in identities:
            if db.execute("SELECT 1 FROM account_instances WHERE provider_id=? AND identity_email=? AND canonical=1", (provider_id, email)).fetchone():
                continue
            # An untouched provider placeholder has no identity or progress to transfer.
            placeholder = next((state for state in states if state["canonical"] and state["identity_email"] is None
                                and not state["label"] and not state["identity_review_required"] and not has_progress(db, state)
                                and not db.execute("SELECT 1 FROM instance_bitwarden_handoffs WHERE account_id=?", (state["id"],)).fetchone()), None)
            if placeholder:
                db.execute("UPDATE account_instances SET identity_email=?,updated=? WHERE id=?", (email, timestamp(), placeholder["id"]))
                placeholder["identity_email"] = email
            else:
                ident = insert_instance(db, provider_id, email)
                states.append(dict(db.execute("SELECT * FROM account_instances WHERE id=?", (ident,)).fetchone()))
        if not states:
            insert_instance(db, provider_id)
        elif identities:
            # Old progress without an address is retained for an explicit human decision.
            for state in states:
                if state["identity_email"] is None and has_progress(db, state):
                    db.execute("UPDATE account_instances SET identity_review_required=1 WHERE id=?", (state["id"],))


def defer_in_queue(db, account_id):
    """1.x "skipped" becomes an open-ended deferral in the worklist (ADR-0001, rule 5)."""
    if db.execute("SELECT 1 FROM instance_work_queue WHERE account_id=?", (account_id,)).fetchone():
        db.execute("UPDATE instance_work_queue SET deferred=1 WHERE account_id=?", (account_id,))
    else:
        position = db.execute("SELECT COALESCE(MAX(position),0) FROM instance_work_queue").fetchone()[0] + 1
        db.execute("INSERT INTO instance_work_queue(account_id,position,deferred) VALUES (?,?,1)", (account_id, position))


def rebuild_from_v1(db):
    """Move a 1.9-1.16 account table to the ADR-0001 shape, under BEGIN IMMEDIATE.

    The caller has saved a backup first. Every 1.x row keeps its id, identity,
    attributes and handoff journal; its checklist and status become decision,
    steps and planning (see states.from_legacy).
    """
    rows = [dict(row) for row in db.execute("SELECT * FROM account_instances").fetchall()]
    created = {(row["account_id"], row["email"]) for row in
               db.execute("SELECT account_id,email FROM instance_bitwarden_handoffs WHERE state='created'")}
    db.execute("DROP INDEX IF EXISTS instances_provider")
    db.execute("DROP INDEX IF EXISTS instances_canonical_email")
    db.execute("ALTER TABLE account_instances RENAME TO account_instances_v1")
    db.execute(ACCOUNT_TABLE)
    for statement in ACCOUNT_INDEXES:
        db.execute(statement)
    for row in rows:
        email = row["identity_email"] or row["manual_email"] or ""
        decision, decided_at, steps = from_legacy(row, (row["id"], email) in created)
        insert_instance(db, row["provider_id"], row["identity_email"], ident=row["id"], canonical=row["canonical"],
                        label=row["label"], review=row["identity_review_required"], decision=decision,
                        decided_at=decided_at, steps=steps, login_method=row["login_method"],
                        priority_override=row["priority_override"], manual_email=row["manual_email"],
                        updated=row["updated"])
        if row["status"] == "skipped":
            defer_in_queue(db, row["id"])
    db.execute("DROP TABLE account_instances_v1")


def migrate_instances(db, registry):
    """Run once under BEGIN IMMEDIATE; all pre-1.9 rows remain as migration sources."""
    if db.execute("SELECT 1 FROM meta WHERE key='account_instances_migrated'").fetchone():
        return
    owned = owned_emails(db)
    # New profiles have none of the pre-1.9 tables; older ones may lack some.
    legacy = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    evidence = {}
    for row in db.execute("SELECT * FROM evidence WHERE provider_id IS NOT NULL"):
        if email := direct_identity(row, owned):
            evidence.setdefault(row["provider_id"], set()).add(email)
    queued = {row[0] for row in db.execute("SELECT provider_id FROM work_queue")} if "work_queue" in legacy else set()
    transferred = ({(row["provider_id"], row["email"]) for row in
                    db.execute("SELECT provider_id,email FROM bitwarden_handoffs WHERE state='created'")}
                   if "bitwarden_handoffs" in legacy else set())
    for row in (db.execute("SELECT * FROM accounts").fetchall() if "accounts" in legacy else []):
        state = dict(row)
        provider_id = state["provider_id"]
        legacy_progress = (bool(state["confirmed"]) or state["status"] != "pending"
                           or any(json.loads(state["checklist"]).values())
                           or state["priority_override"] is not None
                           or state["login_method"] != "password" or bool(state["manual_email"]))
        if provider_id not in registry.providers or (not legacy_progress and provider_id not in queued):
            continue
        manual = state["manual_email"]
        try:
            manual = normalize_email(manual) if manual else None
        except (TypeError, ValueError):
            manual = None
        manual = manual if manual in owned else None
        addresses = evidence.get(provider_id, set())
        email = manual or (next(iter(addresses)) if len(addresses) == 1 else None)
        if not legacy_progress and addresses:
            email = sorted(addresses)[0]
        review = legacy_progress and email is None
        decision, decided_at, steps = from_legacy({**state, "identity_review_required": review},
                                                  (provider_id, email or "") in transferred)
        insert_instance(db, provider_id, email, ident=provider_id, review=review, decision=decision,
                        decided_at=decided_at, steps=steps, login_method=state["login_method"],
                        priority_override=state["priority_override"], manual_email=manual,
                        updated=state["updated"])
        if state["status"] == "skipped":
            defer_in_queue(db, provider_id)
    synchronize_instances(db, registry)
    for row in (db.execute("SELECT * FROM work_queue").fetchall() if "work_queue" in legacy else []):
        if row["provider_id"] not in registry.providers:
            continue
        if not db.execute("SELECT 1 FROM account_instances WHERE id=?", (row["provider_id"],)).fetchone():
            insert_instance(db, row["provider_id"], ident=row["provider_id"])
        db.execute("INSERT OR IGNORE INTO instance_work_queue(account_id,position,deferred) VALUES (?,?,?)",
                   (row["provider_id"], row["position"], row["deferred"]))
    for row in (db.execute("SELECT * FROM bitwarden_handoffs").fetchall() if "bitwarden_handoffs" in legacy else []):
        provider_id, email = row["provider_id"], row["email"]
        if provider_id not in registry.providers:
            continue
        state = db.execute("SELECT id FROM account_instances WHERE provider_id=? AND identity_email=? AND canonical=1", (provider_id, email)).fetchone() if email else None
        if state is None and email not in owned:
            state = db.execute("SELECT id FROM account_instances WHERE provider_id=? AND identity_email IS NULL AND canonical=1", (provider_id,)).fetchone()
        if state is None:
            ident = insert_instance(db, provider_id, email if email in owned else None,
                                    review=email not in owned)
        else:
            ident = state["id"]
            if email not in owned:
                db.execute("UPDATE account_instances SET identity_review_required=1 WHERE id=?", (ident,))
        db.execute("""INSERT OR IGNORE INTO instance_bitwarden_handoffs
          (id,account_id,provider_id,email,state,operation_id,lease_until,vault_item_id,updated)
          VALUES (?,?,?,?,?,?,?,?,?)""", (row["id"], ident, provider_id, email, row["state"], row["operation_id"],
                                           row["lease_until"], row["vault_item_id"], row["updated"]))
    # A successful historical transfer belongs to its exact new identity, even
    # when a sibling's old transfer failed: the item exists without a password,
    # so the vault step is prepared, never done (ADR-0001, B4).
    for row in db.execute("""SELECT a.id FROM account_instances a WHERE a.identity_review_required=0
                            AND EXISTS (SELECT 1 FROM instance_bitwarden_handoffs h
                                        WHERE h.account_id=a.id AND h.state='created'
                                        AND h.email=COALESCE(a.identity_email,a.manual_email,''))""").fetchall():
        current = db.execute("SELECT state FROM account_steps WHERE account_id=? AND step='vault'", (row["id"],)).fetchone()
        if current is None or current["state"] == "open":
            write_step(db, row["id"], "vault", {"state": "prepared", "done_at": timestamp(), "review_after": None})
    db.execute("INSERT INTO meta(key,value) VALUES ('account_instances_migrated','true')")
