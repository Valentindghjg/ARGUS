"""Stable local account identities, with conservative migration of older inventories."""
from datetime import datetime, timezone
import json
import uuid

from .analysis import ANALYSIS_VERSION, english_caveat, normalize_email


SCHEMA = """
CREATE TABLE IF NOT EXISTS account_instances (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  identity_email TEXT,
  canonical INTEGER NOT NULL DEFAULT 1,
  label TEXT NOT NULL DEFAULT '',
  identity_review_required INTEGER NOT NULL DEFAULT 0,
  confirmed INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  checklist TEXT NOT NULL DEFAULT '{}',
  priority_override TEXT,
  login_method TEXT NOT NULL DEFAULT 'password',
  manual_email TEXT,
  updated TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS instances_provider ON account_instances(provider_id);
CREATE UNIQUE INDEX IF NOT EXISTS instances_canonical_email
  ON account_instances(provider_id,identity_email)
  WHERE canonical=1 AND identity_email IS NOT NULL;
CREATE TABLE IF NOT EXISTS instance_work_queue (
  account_id TEXT PRIMARY KEY,
  position INTEGER NOT NULL,
  deferred INTEGER NOT NULL DEFAULT 0
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


def has_progress(state):
    return (bool(state["confirmed"]) or state["status"] != "pending"
            or any(json.loads(state["checklist"]).values())
            or state["priority_override"] is not None
            or state["login_method"] != "password" or bool(state["manual_email"]))


def insert_instance(db, provider_id, email=None, *, state=None, ident=None,
                    canonical=True, label="", review=False, manual=False):
    if ident is None:
        ident = provider_id if not db.execute("SELECT 1 FROM account_instances WHERE id=?", (provider_id,)).fetchone() else str(uuid.uuid4())
    state = state or {}
    db.execute("""INSERT INTO account_instances
      (id,provider_id,identity_email,canonical,label,identity_review_required,
       confirmed,status,checklist,priority_override,login_method,manual_email,updated)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        ident, provider_id, email, int(canonical), label, int(review),
        int(state.get("confirmed", False)), state.get("status", "pending"),
        state.get("checklist", "{}"), state.get("priority_override"),
        state.get("login_method", "password"),
        email if manual else state.get("manual_email"), state.get("updated", timestamp()),
    ))
    return ident


def synchronize_instances(db, registry, provider_ids=None):
    """Add identities for direct proof without ever copying an existing checklist."""
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
                                and not state["label"] and not state["identity_review_required"] and not has_progress(state)
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
                if state["identity_email"] is None and has_progress(state):
                    db.execute("UPDATE account_instances SET identity_review_required=1 WHERE id=?", (state["id"],))


def migrate_instances(db, registry):
    """Run once under BEGIN IMMEDIATE; all older rows remain as migration sources."""
    if db.execute("SELECT 1 FROM meta WHERE key='account_instances_migrated'").fetchone():
        return
    owned = owned_emails(db)
    evidence = {}
    for row in db.execute("SELECT * FROM evidence WHERE provider_id IS NOT NULL"):
        if email := direct_identity(row, owned):
            evidence.setdefault(row["provider_id"], set()).add(email)
    queued = {row[0] for row in db.execute("SELECT provider_id FROM work_queue")}
    for row in db.execute("SELECT * FROM accounts").fetchall():
        state = dict(row)
        provider_id = state["provider_id"]
        if provider_id not in registry.providers or (not has_progress(state) and provider_id not in queued):
            continue
        manual = state["manual_email"]
        try:
            manual = normalize_email(manual) if manual else None
        except (TypeError, ValueError):
            manual = None
        manual = manual if manual in owned else None
        addresses = evidence.get(provider_id, set())
        email = manual or (next(iter(addresses)) if len(addresses) == 1 else None)
        if not has_progress(state) and addresses:
            email = sorted(addresses)[0]
        state["manual_email"] = manual
        insert_instance(db, provider_id, email, state=state, ident=provider_id,
                        review=has_progress(state) and email is None)
    synchronize_instances(db, registry)
    for row in db.execute("SELECT * FROM work_queue").fetchall():
        if row["provider_id"] not in registry.providers:
            continue
        if not db.execute("SELECT 1 FROM account_instances WHERE id=?", (row["provider_id"],)).fetchone():
            insert_instance(db, row["provider_id"], ident=row["provider_id"])
        db.execute("INSERT OR IGNORE INTO instance_work_queue VALUES (?,?,?)", (row["provider_id"], row["position"], row["deferred"]))
    for row in db.execute("SELECT * FROM bitwarden_handoffs").fetchall():
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
    # when a sibling's old transfer failed. Do not require users to export it a
    # second time simply because the former provider-wide flag was still false.
    for row in db.execute("""SELECT a.* FROM account_instances a WHERE a.identity_review_required=0
                            AND EXISTS (SELECT 1 FROM instance_bitwarden_handoffs h
                                        WHERE h.account_id=a.id AND h.state='created'
                                        AND h.email=COALESCE(a.identity_email,a.manual_email,''))""").fetchall():
        checklist = json.loads(row["checklist"])
        checklist["saved_in_bitwarden"] = True
        db.execute("UPDATE account_instances SET checklist=?,status=? WHERE id=?",
                   (json.dumps(checklist), "in_progress" if row["status"] == "pending" else row["status"], row["id"]))
    db.execute("INSERT INTO meta(key,value) VALUES ('account_instances_migrated','true')")
