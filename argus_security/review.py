# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Collected review of unclear items, reversible exclusions and address relations.

Plan E3 (one list instead of scattered decisions), E4 and A9 (exclusions and
documented relations). Nothing here merges accounts or picks an address: an
exclusion only hides clues of one sender domain outside the catalog from the
review, and a relation between two own addresses is a note for the person.
New clues after an exclusion bring the domain back for review.
"""
from .errors import UserFacingError
from .registry import normalize_domain

SCHEMA = """
CREATE TABLE IF NOT EXISTS exclusions (
  domain TEXT PRIMARY KEY,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  evidence_mark INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS address_relations (
  address TEXT NOT NULL,
  other TEXT NOT NULL,
  kind TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(address, other)
);
"""
EXCLUSION_REASONS = ("newsletter", "spam", "not_relevant")
# "same_mailbox": both addresses reach the same inbox (alias or forwarding).
# "replaced_by": the first address was given up in favour of the second.
RELATION_KINDS = ("same_mailbox", "replaced_by")


def exclude_domain(db, domain, reason, moment):
    if reason not in EXCLUSION_REASONS:
        raise UserFacingError("Choose why this sender domain should be hidden")
    domain = normalize_domain(domain) if isinstance(domain, str) else None
    if not domain:
        raise UserFacingError("Invalid domain")
    if not db.execute("SELECT 1 FROM evidence WHERE provider_id IS NULL AND sender_domain=?", (domain,)).fetchone():
        raise UserFacingError("Only sender domains outside the catalog can be hidden")
    mark = db.execute("SELECT COALESCE(MAX(id),0) FROM evidence").fetchone()[0]
    db.execute("""INSERT INTO exclusions(domain,reason,created_at,evidence_mark) VALUES (?,?,?,?)
                  ON CONFLICT(domain) DO UPDATE SET reason=excluded.reason,created_at=excluded.created_at,
                  evidence_mark=excluded.evidence_mark""", (domain, reason, moment, mark))
    return domain


def remove_exclusion(db, domain):
    domain = normalize_domain(domain) if isinstance(domain, str) else None
    if not domain or not db.execute("DELETE FROM exclusions WHERE domain=?", (domain,)).rowcount:
        raise UserFacingError("This sender domain is not hidden")


def relate(db, address, other, kind, owned, moment):
    if kind not in RELATION_KINDS:
        raise UserFacingError("Choose how the two addresses are related")
    if address == other or address not in owned or other not in owned:
        raise UserFacingError("Relate two different addresses of your own")
    db.execute("""INSERT INTO address_relations(address,other,kind,created_at) VALUES (?,?,?,?)
                  ON CONFLICT(address,other) DO UPDATE SET kind=excluded.kind,created_at=excluded.created_at""",
               (address, other, kind, moment))


def remove_relation(db, address, other):
    if not db.execute("DELETE FROM address_relations WHERE address=? AND other=?", (address, other)).rowcount:
        raise UserFacingError("These addresses have no saved relation")


def exclusions(db):
    rows = db.execute("SELECT * FROM exclusions ORDER BY domain").fetchall()
    result = []
    for row in rows:
        clues = db.execute("SELECT COUNT(*), COALESCE(SUM(id > ?),0) FROM evidence WHERE provider_id IS NULL AND sender_domain=?",
                           (row["evidence_mark"], row["domain"])).fetchone()
        result.append({"domain": row["domain"], "reason": row["reason"], "created_at": row["created_at"],
                       "clues": clues[0], "new_clues": clues[1]})
    return result


def relations(db):
    return [{"address": row["address"], "other": row["other"], "kind": row["kind"], "created_at": row["created_at"]}
            for row in db.execute("SELECT * FROM address_relations ORDER BY address, other")]


def unclear_items(snapshot):
    """One list of everything that needs a person's look, most blocking first (E3)."""
    accounts = snapshot["accounts"]
    items = []
    for account in accounts:
        if account["identity_review_required"] and account["decision"] != "rejected":
            items.append({"kind": "identity", "account_id": account["id"], "count": None})
    seen = set()
    for account in accounts:
        if account["unassigned_evidence_count"] and account["provider_id"] not in seen and account["decision"] != "rejected":
            seen.add(account["provider_id"])
            items.append({"kind": "unassigned", "account_id": account["id"], "count": account["unassigned_evidence_count"]})
    for account in accounts:
        if account["reconsider"]:
            items.append({"kind": "reconsider", "account_id": account["id"], "count": None})
    for candidate in snapshot["candidates"]:
        items.append({"kind": "domain", "domain": candidate["domain"], "count": len(candidate["evidence"])})
    for entry in snapshot["exclusions"]:
        if entry["new_clues"]:
            items.append({"kind": "excluded_new", "domain": entry["domain"], "count": entry["new_clues"]})
    return items
