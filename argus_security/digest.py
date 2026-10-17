# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""What changed since the person last reviewed (plan A1-A4, A7, A28).

Each stored clue carries the revision at which it arrived and the revision at
which its rating last changed. The person's review mark is one revision
number: clues at or below it were already shown and are not presented again
(A2), and importing the same message again changes nothing. Gaps of the last
import stay visible regardless. Grouping is only a view: it never confirms,
merges or assigns accounts (A3), and marking changes as reviewed never touches
a decision or a step (A1). Everything is derived locally; nothing is sent.
"""
import json

from .analysis import KINDS, LABELS
from .errors import UserFacingError
from .registry import is_shared_sender

SEEN = "changes_seen"
EVIDENCE_HIGH = "evidence_high"
# Items that need a decision come first (A4), most blocking first.
ATTENTION = ("reconsider", "identity", "unassigned", "domain")
SCAN_GAPS = {"partial", "limited", "completed_with_gaps"}


def _meta(db, key, default):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def next_revision(db):
    """Reserve the next revision inside the caller's write transaction."""
    revision = _meta(db, "revision", 0) + 1
    db.execute("INSERT INTO meta VALUES ('revision',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (json.dumps(revision),))
    return revision


def evidence_mark(db):
    """The highest clue id ever stored.

    SQLite gives a new row the current largest id plus one, so after the
    newest clue is removed its id comes back. Decisions and exclusions keep
    this high-water value instead, and new clues are stored above it, so a
    later clue is always recognised as newer (ADR-0001 rule 2, plan A9).
    """
    return max(_meta(db, EVIDENCE_HIGH, 0), db.execute("SELECT COALESCE(MAX(id),0) FROM evidence").fetchone()[0])


def keep_evidence_mark(db):
    """Remember the high-water value before a clue is removed."""
    db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (EVIDENCE_HIGH, json.dumps(evidence_mark(db))))


def review_mark(db):
    mark = _meta(db, SEEN, None)
    return mark if isinstance(mark, dict) else {"revision": 0, "at": None}


def _store_mark(db, mark):
    db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
               (SEEN, json.dumps(mark)))


def acknowledge(db, revision, moment):
    """Mark everything up to ``revision`` (the one the person saw) as reviewed.

    Clues that arrived after that revision stay new. The same revision again
    only moves the time forward, which acknowledges import gaps. The previous
    mark is kept once, so the last acknowledgement can be undone.
    """
    current = review_mark(db)
    if type(revision) is not int or not current["revision"] <= revision <= _meta(db, "revision", 0):
        raise UserFacingError("These changes are no longer current; reload the page")
    # Marking the same revision again (a double click, or a second button) keeps
    # the earlier undo point, so one undo always shows the changes again.
    previous = (current["previous"] if revision == current["revision"] and current.get("previous")
                else {"revision": current["revision"], "at": current["at"]})
    _store_mark(db, {"revision": revision, "at": moment, "previous": previous})


def undo_acknowledge(db):
    previous = review_mark(db).get("previous")
    if not previous:
        raise UserFacingError("There is no review mark to undo")
    _store_mark(db, previous)


def change_digest(snapshot, evidences, mark, current):
    """New and changed clues since the mark, grouped by account, unclear first."""
    since = mark["revision"]
    accounts = snapshot["accounts"]
    # Clues belong to the canonical account of an identity; a labelled sibling holds none.
    by_identity = {(a["provider_id"], a["identity_email"]): a for a in accounts
                   if a["identity_email"] and a.get("canonical", True)}
    by_provider = {}
    for account in accounts:
        by_provider.setdefault(account["provider_id"], account)
    groups, other = {}, {"marketing": 0, "order": 0, "reset": 0}
    # A domain the person hid stays out of the digest until a newer clue brings it back (A9).
    hidden = {entry["domain"] for entry in snapshot.get("exclusions", []) if not entry.get("new_clues")}
    fresh = [e for e in evidences if e["changed_rev"] > since
             and not (e["provider_id"] is None and e["sender_domain"] in hidden)]
    for clue in fresh:
        kind = KINDS.get(clue["signal"], "marketing")
        provider, email = clue["provider_id"], clue["registered_email"]
        if provider is None:
            key = ("domain", clue["sender_domain"])
            base = {"kind": "domain", "domain": clue["sender_domain"], "account_id": None,
                    "shared": is_shared_sender(clue["sender_domain"])}
        elif email and (provider, email) in by_identity:
            account = by_identity[(provider, email)]
            key = ("account", account["id"])
            base = {"kind": "account", "account_id": account["id"]}
        elif kind == "account" and provider in by_provider:
            key = ("unassigned", provider)
            base = {"kind": "unassigned", "account_id": by_provider[provider]["id"]}
        else:
            # Advertising, orders and reset requests say nothing about an account (A28).
            other[kind if kind in other else "marketing"] += 1
            continue
        group = groups.setdefault(key, {**base, "new": 0, "changed": 0, "signals": set()})
        group["new" if clue["created_rev"] > since else "changed"] += 1
        group["signals"].add(clue["signal"])
    by_id = {account["id"]: account for account in accounts}
    result = []
    for group in groups.values():
        account = by_id.get(group["account_id"])
        if group["kind"] == "account":
            reason = ("reconsider" if account["reconsider"] else
                      "identity" if account["identity_review_required"] else None)
        else:
            reason = group["kind"]
        signals = sorted(group["signals"])
        result.append({**group, "signals": signals, "reasons": [LABELS[s] for s in signals if s in LABELS],
                       "attention": reason})
    names = {account["id"]: account["name"].casefold() for account in accounts}
    result.sort(key=lambda g: (ATTENTION.index(g["attention"]) if g["attention"] else len(ATTENTION),
                               names.get(g["account_id"], g.get("domain") or "")))
    scan = snapshot.get("last_scan") if isinstance(snapshot.get("last_scan"), dict) else None
    gaps = None
    # A2: processing gaps stay visible even when nothing new arrived.
    if scan and not scan.get("running") and (scan.get("result") in SCAN_GAPS or scan.get("scope_changed")) \
            and (mark["at"] is None or (scan.get("updated_at") or "") > mark["at"]):
        gaps = {key: scan.get(key) for key in ("result", "skipped", "errors", "headers_only", "scope_changed")}
        gaps["next_steps"] = scan.get("next_steps", [])
    return {"since": mark["at"], "seen": since, "revision": current,
            "new": sum(e["created_rev"] > since for e in fresh),
            "changed": sum(e["created_rev"] <= since for e in fresh),
            "groups": result, "other": other, "gaps": gaps,
            "attention": sum(1 for g in result if g["attention"])}


def return_summary(snapshot):
    """One local overview after a pause instead of many single messages (A7, A28).

    Problems come first and stay visible until they are resolved; the next task
    closes the summary.
    """
    changes = snapshot["changes"]
    items = []
    if changes["gaps"]:
        items.append({"kind": "scan_gaps", "count": None})
    unclear = sum(entry["state"] in {"running", "uncertain"} for entry in snapshot["bitwarden_handoffs"])
    if unclear:
        items.append({"kind": "handoff", "count": unclear})
    if changes["attention"]:
        items.append({"kind": "decide_first", "count": changes["attention"]})
    if changes["new"] or changes["changed"]:
        items.append({"kind": "changes", "count": changes["new"] + changes["changed"]})
    due = sum(bool(account["reviews_due"]) for account in snapshot["accounts"] if account["decision"] != "rejected")
    if due:
        items.append({"kind": "review_due", "count": due})
    return {"since": changes["since"], "items": items}
