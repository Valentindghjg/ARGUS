# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Persistent, secret-free worklist. Account checklists remain the source of truth."""
from datetime import date, datetime, time, timedelta, timezone
import json

from .errors import UserFacingError


PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2}
CLASSIFICATION_RANK = {"confirmed": 0, "probable": 1}
MAX_PRIORITY_WORKLIST = 10


def utcnow():
    return datetime.now(timezone.utc)


def active_snooze(row, current):
    """Return an unexpired local resume timestamp, never raising on old data."""
    value = row["resume_after"]
    if not value or not row["deferred"]:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed <= current:
        return None
    return value


def expired_snooze(row, current):
    value = row["resume_after"]
    if not value or not row["deferred"]:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None and parsed <= current


def effectively_deferred(row, current):
    return bool(row["deferred"]) and not expired_snooze(row, current)


def custom_snooze_date(value, current):
    if not isinstance(value, str):
        raise UserFacingError("Choose a future local date")
    try:
        selected = date.fromisoformat(value)
    except ValueError as exc:
        raise UserFacingError("Choose a future local date") from exc
    if not current.date() < selected <= current.date() + timedelta(days=365):
        raise UserFacingError("Choose a future local date")
    return datetime.combine(selected, time.min, tzinfo=timezone.utc).isoformat()


def next_step(account):
    if account.get("identity_review_required"):
        return "identify"
    if account["status"] == "done":
        return "done"
    for key, step in (("reviewed", "review"), ("saved_in_bitwarden", "bitwarden"),
                      ("password_changed", "change_password"), ("login_tested", "test_signin"),
                      ("mfa_checked", "mfa")):
        if key == "password_changed" and account["login_method"] != "password":
            continue
        if not account["checklist"][key]:
            return step
    return "finish"


def recommended_accounts(accounts, *, excluded=(), limit=None):
    """Rank local accounts deterministically without changing any state."""
    excluded = set(excluded)
    candidates = [account for account in accounts
                  if account["id"] not in excluded
                  and account["classification"] in CLASSIFICATION_RANK
                  # "skipped" is shown as Deferred: the user chose to postpone it.
                  and account["status"] not in {"done", "skipped"}]
    ranked = sorted(candidates, key=lambda account: (
        PRIORITY_RANK[account["priority"]],
        CLASSIFICATION_RANK[account["classification"]],
        not account.get("identity_review_required", False),
        -account.get("score", 0), account["name"].casefold(), account["id"],
    ))
    return ranked if limit is None else ranked[:limit]


def recommended_account(accounts, *, excluded=()):
    """Choose one local account deterministically without changing any state."""
    ranked = recommended_accounts(accounts, excluded=excluded, limit=1)
    return ranked[0] if ranked else None


def worklist_snapshot(store, accounts):
    accounts = {account["id"]: account for account in accounts}
    current_time = utcnow()
    with store.connect() as db:
        rows = db.execute("SELECT * FROM instance_work_queue ORDER BY position, account_id").fetchall()
        paused = db.execute("SELECT value FROM meta WHERE key='worklist_paused'").fetchone()
        focus = db.execute("SELECT value FROM meta WHERE key='worklist_focus'").fetchone()
    items = [{"id": row["account_id"], "deferred": effectively_deferred(row, current_time),
              "snoozed_until": active_snooze(row, current_time),
              "step": next_step(accounts[row["account_id"]])}
             for row in rows if row["account_id"] in accounts]
    ready = [item["id"] for item in items if not item["deferred"] and item["step"] != "done"]
    focus = json.loads(focus[0]) if focus else None
    current = focus if focus in ready else next(iter(ready), None)
    queued = {item["id"] for item in items}
    priority_preview = recommended_accounts(accounts.values(), excluded=queued,
                                            limit=MAX_PRIORITY_WORKLIST)
    suggested = priority_preview[0] if priority_preview else None
    return {"items": items, "paused": bool(json.loads(paused[0])) if paused else False,
            "current": current, "suggested": suggested["id"] if suggested else None,
            "priority_preview": [account["id"] for account in priority_preview],
            "total": len(items), "done": sum(item["step"] == "done" for item in items),
            "deferred": sum(item["deferred"] and item["step"] != "done" for item in items)}


def change_worklist(store, data):
    action = data.get("action")
    shapes = {"add": {"action", "ids"}, "remove": {"action", "id"},
              "defer": {"action", "id"}, "restore": {"action", "id"},
              "focus": {"action", "id"}, "pause": {"action"}, "resume": {"action"},
              "start": {"action"}, "prioritize": {"action"},
              "snooze": {"action", "id", "days"},
              "snooze_until": {"action", "id", "date"}}
    if not isinstance(action, str) or action not in shapes or set(data) != shapes[action]:
        raise UserFacingError("Invalid worklist action")
    if action == "add":
        ids = data["ids"]
        if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(i, str) for i in ids):
            raise UserFacingError("Select discovered accounts for the worklist")
        accounts = {account["id"]: account for account in store.snapshot()["accounts"]}
        if any(i not in accounts or accounts[i]["classification"] == "unknown" for i in ids):
            raise UserFacingError("Select discovered accounts for the worklist")
        # A single transaction makes additions idempotent even across tabs/processes.
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            position = db.execute("SELECT COALESCE(MAX(position),0) FROM instance_work_queue").fetchone()[0]
            for account_id in dict.fromkeys(ids):
                position += 1
                db.execute("INSERT OR IGNORE INTO instance_work_queue(account_id,position) VALUES (?,?)", (account_id, position))
    elif action in {"pause", "resume"}:
        store.set_meta("worklist_paused", action == "pause")
    elif action == "prioritize":
        # The user explicitly starts this action in the dashboard. It adds only
        # local queue rows; no checklist, vault or provider state is touched.
        accounts = {account["id"]: account for account in store.snapshot()["accounts"]}
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT account_id FROM instance_work_queue ORDER BY position,account_id").fetchall()
            ranked = recommended_accounts(accounts.values(),
                                          excluded=[row["account_id"] for row in rows],
                                          limit=MAX_PRIORITY_WORKLIST)
            position = db.execute("SELECT COALESCE(MAX(position),0) FROM instance_work_queue").fetchone()[0]
            added = []
            for account in ranked:
                position += 1
                db.execute("INSERT INTO instance_work_queue(account_id,position) VALUES (?,?)",
                           (account["id"], position))
                added.append(account["id"])
        return {"ok": True, "added": added}
    elif action == "start":
        accounts = {account["id"]: account for account in store.snapshot()["accounts"]}
        current_time = utcnow()
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT account_id,deferred,resume_after FROM instance_work_queue ORDER BY position,account_id").fetchall()
            ready = [row["account_id"] for row in rows
                     if not effectively_deferred(row, current_time) and row["account_id"] in accounts
                     and next_step(accounts[row["account_id"]]) != "done"]
            current = next(iter(ready), None)
            created = False
            if current is None:
                suggested = recommended_account(accounts.values(), excluded=[row["account_id"] for row in rows])
                if suggested:
                    position = db.execute("SELECT COALESCE(MAX(position),0) FROM instance_work_queue").fetchone()[0] + 1
                    current = suggested["id"]
                    created = True
                    db.execute("INSERT INTO instance_work_queue(account_id,position) VALUES (?,?)", (current, position))
            if current:
                db.execute("INSERT INTO meta VALUES ('worklist_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (json.dumps(current),))
            db.execute("INSERT INTO meta VALUES ('worklist_paused',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (json.dumps(False),))
        return {"ok": True, "current": current, "created": created}
    else:
        account_id = data["id"]
        if not isinstance(account_id, str):
            raise UserFacingError("Invalid worklist account")
        if action == "snooze" and (type(data["days"]) is not int or not 1 <= data["days"] <= 365):
            raise UserFacingError("Choose a valid local snooze period")
        resume_after = custom_snooze_date(data["date"], utcnow()) if action == "snooze_until" else None
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM instance_work_queue WHERE account_id=?", (account_id,)).fetchone():
                raise UserFacingError("Account is not in the worklist")
            if action == "remove":
                db.execute("DELETE FROM instance_work_queue WHERE account_id=?", (account_id,))
            elif action in {"defer", "restore"}:
                db.execute("UPDATE instance_work_queue SET deferred=?,resume_after=NULL WHERE account_id=?",
                           (int(action == "defer"), account_id))
            elif action == "snooze":
                resume_after = (utcnow() + timedelta(days=data["days"])).isoformat()
                db.execute("UPDATE instance_work_queue SET deferred=1,resume_after=? WHERE account_id=?",
                           (resume_after, account_id))
            elif action == "snooze_until":
                db.execute("UPDATE instance_work_queue SET deferred=1,resume_after=? WHERE account_id=?",
                           (resume_after, account_id))
            else:
                db.execute("INSERT INTO meta VALUES ('worklist_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (json.dumps(account_id),))
    return {"ok": True}
