"""Persistent, secret-free worklist. Account checklists remain the source of truth."""
import json


def next_step(account):
    if account["status"] == "done":
        return "done"
    for key, step in (("reviewed", "review"), ("saved_in_bitwarden", "bitwarden"),
                      ("password_changed", "change_password"), ("login_tested", "test_signin")):
        if key == "password_changed" and account["login_method"] != "password":
            continue
        if not account["checklist"][key]:
            return step
    return "finish"


def worklist_snapshot(store, accounts):
    accounts = {account["id"]: account for account in accounts}
    with store.connect() as db:
        rows = db.execute("SELECT * FROM work_queue ORDER BY position, provider_id").fetchall()
        paused = db.execute("SELECT value FROM meta WHERE key='worklist_paused'").fetchone()
        focus = db.execute("SELECT value FROM meta WHERE key='worklist_focus'").fetchone()
    items = [{"id": row["provider_id"], "deferred": bool(row["deferred"]),
              "step": next_step(accounts[row["provider_id"]])}
             for row in rows if row["provider_id"] in accounts]
    ready = [item["id"] for item in items if not item["deferred"] and item["step"] != "done"]
    focus = json.loads(focus[0]) if focus else None
    return {"items": items, "paused": bool(json.loads(paused[0])) if paused else False,
            "current": focus if focus in ready else next(iter(ready), None),
            "total": len(items), "done": sum(item["step"] == "done" for item in items),
            "deferred": sum(item["deferred"] and item["step"] != "done" for item in items)}


def change_worklist(store, data):
    action = data.get("action")
    shapes = {"add": {"action", "ids"}, "remove": {"action", "id"},
              "defer": {"action", "id"}, "restore": {"action", "id"},
              "focus": {"action", "id"}, "pause": {"action"}, "resume": {"action"}}
    if not isinstance(action, str) or action not in shapes or set(data) != shapes[action]:
        raise ValueError("Invalid worklist action")
    if action == "add":
        ids = data["ids"]
        if not isinstance(ids, list) or not ids or len(ids) > len(store.registry.providers) or any(not isinstance(i, str) for i in ids):
            raise ValueError("Select discovered accounts for the worklist")
        accounts = {account["id"]: account for account in store.snapshot()["accounts"]}
        if any(i not in accounts or accounts[i]["classification"] == "unknown" for i in ids):
            raise ValueError("Select discovered accounts for the worklist")
        # A single transaction makes additions idempotent even across tabs/processes.
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            position = db.execute("SELECT COALESCE(MAX(position),0) FROM work_queue").fetchone()[0]
            for provider_id in dict.fromkeys(ids):
                position += 1
                db.execute("INSERT OR IGNORE INTO work_queue(provider_id,position) VALUES (?,?)", (provider_id, position))
    elif action in {"pause", "resume"}:
        store.set_meta("worklist_paused", action == "pause")
    else:
        provider_id = data["id"]
        if not isinstance(provider_id, str):
            raise ValueError("Invalid worklist account")
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM work_queue WHERE provider_id=?", (provider_id,)).fetchone():
                raise ValueError("Account is not in the worklist")
            if action == "remove":
                db.execute("DELETE FROM work_queue WHERE provider_id=?", (provider_id,))
            elif action in {"defer", "restore"}:
                db.execute("UPDATE work_queue SET deferred=? WHERE provider_id=?", (int(action == "defer"), provider_id))
            else:
                db.execute("INSERT INTO meta VALUES ('worklist_focus',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (json.dumps(provider_id),))
    return {"ok": True}
