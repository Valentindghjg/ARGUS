# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Facts for a bug report (plan G4): versions, platform and counts, never content.

Nothing here names an address, a provider, a path or a message. An existing
profile is only read; ``argus about`` never creates, migrates or changes one.
"""
import json
from pathlib import Path
import platform
import sqlite3

from . import __version__
from .background import SCHEDULE_META_KEY
from .backup import read_only, schema_version
from .jobs import paused
from .store import SCHEMA_VERSION
from .watch import KEY as WATCH_KEY

TABLES = {"clues": "evidence", "accounts": "account_instances", "processed_messages": "processed_messages"}


def about(data_dir: Path, profile_kind: str):
    facts = {"argus": __version__, "python": f"{platform.python_implementation()} {platform.python_version()}",
             "system": f"{platform.system()} {platform.release()}", "machine": platform.machine(),
             "sqlite": sqlite3.sqlite_version, "schema": SCHEMA_VERSION, "profile": profile_kind}
    database = Path(data_dir) / "accounts.sqlite3"
    if not database.is_file() or database.is_symlink():
        return {**facts, "profile_data": "none"}
    stored = schema_version(database)
    if stored != SCHEMA_VERSION:
        state = "unreadable" if stored is None else "newer" if stored > SCHEMA_VERSION else "older"
        return {**facts, "profile_schema": stored, "profile_data": state}
    try:
        with read_only(database) as db:
            meta = {key: json.loads(value) for key, value in db.execute(
                "SELECT key, value FROM meta WHERE key IN ('emails','demo',?,?)", (SCHEDULE_META_KEY, WATCH_KEY))}
            counts = {name: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for name, table in TABLES.items()}
            jobs = dict(db.execute("SELECT state, COUNT(*) FROM jobs GROUP BY state ORDER BY state").fetchall())
            automation_paused = bool(paused(db))
    except (sqlite3.Error, ValueError):
        return {**facts, "profile_schema": stored, "profile_data": "unreadable"}
    enabled = lambda key: isinstance(meta.get(key), dict) and meta[key].get("enabled") is True
    return {**facts, "profile_schema": stored, "profile_data": "counts",
            "demo": meta.get("demo") is True, "own_addresses": len(meta.get("emails") or []), **counts,
            "jobs": jobs, "automation_paused": automation_paused,
            "scheduled_scan": enabled(SCHEDULE_META_KEY), "folder_watch": enabled(WATCH_KEY)}
