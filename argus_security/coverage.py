# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""What the imports cover, and where they leave gaps (plan D4).

ARGUS can say which sources it read recently, how many messages they held,
which period its clues span and which own addresses or months have no clue at
all. It cannot know how much of a person's mail or online life that is, so it
never shows a total percentage.
"""
from collections import Counter
import json

SOURCE_KINDS = ("import", "imap_scan", "scheduled_scan", "folder_watch")


def coverage(db, evidences, own_emails):
    sources = {}
    # Plain Python instead of SQLite JSON functions, which older builds may lack.
    for row in db.execute("SELECT kind, started_at, counts FROM jobs ORDER BY started_at"):
        if row["kind"] not in SOURCE_KINDS:
            continue
        entry = sources.setdefault(row["kind"], {"kind": row["kind"], "runs": 0, "last_run": None, "messages": 0})
        entry["runs"] += 1
        entry["last_run"] = row["started_at"]
        counts = json.loads(row["counts"])
        processed, unchanged = counts.get("processed", 0), counts.get("unchanged", 0)
        # Messages read again unchanged are not counted twice.
        if type(processed) is int and type(unchanged) is int:
            entry["messages"] += max(0, processed - unchanged)
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
