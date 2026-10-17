# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""A minimal local history of counts (plan P2).

Once a day ARGUS keeps a handful of counts: clues, found and confirmed
accounts, complete and open accounts, unclear items and open high-priority
accounts. No names, addresses, evidence or message content are kept, and rows
older than about thirteen months are dropped. Comparisons show how the counts
moved over the last week, month and quarter.
"""
from datetime import date, timedelta
import json

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
  day TEXT PRIMARY KEY,
  counts TEXT NOT NULL
);
"""
KEYS = ("clues", "found", "confirmed", "complete", "open", "unclear", "high_priority_open")
WINDOWS = (7, 30, 90)
KEEP_DAYS = 400


def counts(snapshot):
    live = [a for a in snapshot["accounts"] if a["classification"] != "unknown" and a["decision"] != "rejected"]
    return {"clues": snapshot["summary"]["clues"], "found": snapshot["summary"]["found"],
            "confirmed": snapshot["summary"]["confirmed"], "complete": snapshot["result"]["complete"],
            "open": sum(account["progress"] != "complete" for account in live),
            "unclear": len(snapshot["unclear"]), "high_priority_open": snapshot["summary"]["high_priority"]}


def record(db, today_counts, today=None):
    """Keep today's counts; write only when they changed."""
    today = (today or date.today()).isoformat()
    value = json.dumps(today_counts, sort_keys=True)
    row = db.execute("SELECT counts FROM history WHERE day=?", (today,)).fetchone()
    if row is None or row[0] != value:
        db.execute("INSERT INTO history(day,counts) VALUES (?,?) ON CONFLICT(day) DO UPDATE SET counts=excluded.counts",
                   (today, value))
        db.execute("DELETE FROM history WHERE day < ?", ((date.fromisoformat(today) - timedelta(days=KEEP_DAYS)).isoformat(),))


def comparisons(db, today_counts, today=None):
    """For each window, the change against the latest day at least that long ago."""
    today = today or date.today()
    result = []
    for window in WINDOWS:
        row = db.execute("SELECT day, counts FROM history WHERE day <= ? ORDER BY day DESC LIMIT 1",
                         ((today - timedelta(days=window)).isoformat(),)).fetchone()
        if row is None:
            continue
        then = json.loads(row["counts"])
        result.append({"days": window, "since": row["day"],
                       "delta": {key: today_counts[key] - then.get(key, 0) for key in KEYS}})
    return result
