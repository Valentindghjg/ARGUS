# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""What the imports cover, and where they leave gaps (plan D4).

ARGUS can say which sources it read, how many messages they held,
which period its clues span and which own addresses or months have no clue at
all. It cannot know how much of a person's mail or online life that is, so it
never shows a total percentage.

The job list keeps only the newest jobs. Source jobs that leave it are folded
into one row of totals per source (runs, messages, last run: numbers only), so
the counts cover every run, not just the recent ones.
"""
from collections import Counter
import json

SOURCE_KINDS = ("import", "imap_scan", "scheduled_scan", "folder_watch")
SCHEMA = """
CREATE TABLE IF NOT EXISTS source_totals (
  kind TEXT PRIMARY KEY,
  runs INTEGER NOT NULL DEFAULT 0,
  messages INTEGER NOT NULL DEFAULT 0,
  last_run TEXT
);
"""


def _messages(counts):
    # Plain Python instead of SQLite JSON functions, which older builds may lack.
    counts = json.loads(counts)
    processed, unchanged = counts.get("processed", 0), counts.get("unchanged", 0)
    # Messages read again unchanged are not counted twice.
    if type(processed) is int and type(unchanged) is int:
        return max(0, processed - unchanged)
    return 0


def keep_totals(db, rows):
    """Fold source jobs that leave the job list into the lasting totals."""
    for row in rows:
        if row["kind"] in SOURCE_KINDS:
            db.execute("""INSERT INTO source_totals(kind,runs,messages,last_run) VALUES (?,1,?,?)
                          ON CONFLICT(kind) DO UPDATE SET runs=runs+1, messages=messages+excluded.messages,
                          last_run=MAX(COALESCE(last_run, excluded.last_run), excluded.last_run)""",
                       (row["kind"], _messages(row["counts"]), row["started_at"]))


def coverage(db, evidences, own_emails):
    # A source counts every run: the folded totals plus the jobs still listed.
    sources = {row["kind"]: {"kind": row["kind"], "runs": row["runs"], "last_run": row["last_run"],
                             "messages": row["messages"]}
               for row in db.execute("SELECT kind, runs, messages, last_run FROM source_totals")
               if row["kind"] in SOURCE_KINDS}
    for row in db.execute("SELECT kind, started_at, counts FROM jobs ORDER BY started_at"):
        if row["kind"] not in SOURCE_KINDS:
            continue
        entry = sources.setdefault(row["kind"], {"kind": row["kind"], "runs": 0, "last_run": None, "messages": 0})
        entry["runs"] += 1
        entry["last_run"] = max(entry["last_run"] or "", row["started_at"])
        entry["messages"] += _messages(row["counts"])
    dated = sorted(e["date"][:7] for e in evidences if e.get("date"))
    months = Counter(dated)
    gaps = []
    if dated:
        year, month = (int(part) for part in dated[0].split("-"))
        last = dated[-1]
        while f"{year:04d}-{month:02d}" <= last:
            key = f"{year:04d}-{month:02d}"
            if not months.get(key):
                gaps.append(key)
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    with_clues = {e["registered_email"] for e in evidences if e.get("registered_email")}
    return {"sources": [sources[kind] for kind in SOURCE_KINDS if kind in sources],
            "first_clue": dated[0] if dated else None, "last_clue": dated[-1] if dated else None,
            "months_without_clues": gaps[-24:], "months_without_clues_total": len(gaps),
            "addresses_without_clues": sorted(set(own_emails) - with_clues)}
