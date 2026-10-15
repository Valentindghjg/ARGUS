"""Persistent, secret-free worklist. Account checklists remain the source of truth."""
import json


PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2}
CLASSIFICATION_RANK = {"confirmed": 0, "probable": 1}
MAX_PRIORITY_WORKLIST = 10


def next_step(account):
    if account.get("identity_review_required"):
        return "identify"
    if account["status"] == "done":
        return "done"
    for key, step in (("reviewed", "review"), ("saved_in_bitwarden", "bitwarden"),
                      ("password_changed", "change_password"), ("login_tested", "test_signin")):
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
                  and account["status"] != "done"]
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
    with store.connect() as db:
        rows = db.execute("SELECT * FROM instance_work_queue ORDER BY position, account_id").fetchall()
        paused = db.execute("SELECT value FROM meta WHERE key='worklist_paused'").fetchone()
        focus = db.execute("SELECT value FROM meta WHERE key='worklist_focus'").fetchone()
    items = [{"id": row["account_id"], "deferred": bool(row["deferred"]),
              "step": next_step(accounts[row["account_id"]])}
             for row in rows if row["account_id"] in accounts]
    ready = [item["id"] for item in items if not item["deferred"] and item["step"] != "done"]
    focus = json.loads(focus[0]) if focus else None
    current = focus if focus in ready else next(iter(ready), None)
    queued = {item["id"] for item in items}
    suggested = recommended_account(accounts.values(), excluded=queued)
    return {"items": items, "paused": bool(json.loads(paused[0])) if paused else False,
            "current": current, "suggested": suggested["id"] if suggested else None,
            "total": len(items), "done": sum(item["step"] == "done" for item in items),
            "deferred": sum(item["deferred"] and item["step"] != "done" for item in items)}


def change_worklist(store, data):
    action = data.get("action")
    shapes = {"add": {"action", "ids"}, "remove": {"action", "id"},
              "defer": {"action", "id"}, "restore": {"action", "id"},
              "focus": {"action", "id"}, "pause": {"action"}, "resume": {"action"},
              "start": {"action"}, "prioritize": {"action"}}
    if not isinstance(action, str) or action not in shapes or set(data) != shapes[action]:
        raise ValueError("Invalid worklist action")
    if action == "add":
        ids = data["ids"]
        if not isinstance(ids, list) or not ids or len(ids) > 10_000 or any(not isinstance(i, str) for i in ids):
            raise ValueError("Select discovered accounts for the worklist")
        accounts = {account["id"]: account for account in store.snapshot()["accounts"]}
        if any(i not in accounts or accounts[i]["classification"] == "unknown" for i in ids):
            raise ValueError("Select discovered accounts for the worklist")
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
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute("SELECT account_id,deferred FROM instance_work_queue ORDER BY position,account_id").fetchall()
            ready = [row["account_id"] for row in rows
                     if not row["deferred"] and row["account_id"] in accounts
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
            raise ValueError("Invalid worklist account")
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM instance_work_queue WHERE account_id=?", (account_id,)).fetchone():
                raise ValueError("Account is not in the worklist")
            if action == "remove":
                db.execute("DELETE FROM instance_work_queue WHERE account_id=?", (account_id,))
            elif action in {"defer", "restore"}:
                db.execute("UPDATE instance_work_queue SET deferred=? WHERE account_id=?", (int(action == "defer"), account_id))
            else:
                db.execute("INSERT INTO meta VALUES ('worklist_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (json.dumps(account_id),))
    return {"ok": True}
