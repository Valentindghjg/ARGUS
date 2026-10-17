# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""A narrow, opt-in watch of one local folder for new EML files (plan A12, priority 14).

The person approves exactly one existing local folder in a terminal. While the
dashboard runs, ARGUS looks at the ``*.eml`` files directly inside it, never in
subfolders, and imports new or changed ones through the normal import with its
processed-message index. It refuses the file-system root, the home folder
itself, hidden folders, symlinks, network paths and the profile folder. The
global pause holds the watch; disabling it from the dashboard stops it for
good. No file is changed, moved or deleted.
"""
from datetime import datetime, timezone
import os
from pathlib import Path
import time

from .analysis import MAX_MESSAGE_BYTES
from .errors import UserFacingError
from .jobs import PAUSE

KEY = "folder_watch"
STATE = "folder_watch_files"
MIN_INTERVAL = 60
MAX_INTERVAL = 24 * 60 * 60
DEFAULT_INTERVAL = 5 * 60
MAX_FILES_PER_PASS = 500
MAX_TRACKED_FILES = 5000


def validate_folder(path, data_dir):
    """Accept only a narrow, local, visible folder; refuse anything broader."""
    text = str(path)
    if text.startswith(("\\\\", "//")):
        raise UserFacingError("Choose a local folder; network paths are not watched")
    candidate = Path(path).expanduser()
    if candidate.is_symlink() or not candidate.is_dir():
        raise UserFacingError("Choose an existing local folder that is not a link")
    folder = candidate.resolve()
    home = Path.home().resolve()
    profile = Path(data_dir).resolve()
    if (folder == Path(folder.anchor) or folder == home or folder in home.parents
            or any(part.startswith(".") for part in folder.parts[1:])):
        raise UserFacingError("Choose a narrow folder of its own, not the whole disk, your home folder or a hidden folder")
    if folder == profile or profile in folder.parents or folder in profile.parents:
        raise UserFacingError("Choose a folder outside the ARGUS profile")
    return folder


def enable(store, path, interval_seconds=DEFAULT_INTERVAL):
    if type(interval_seconds) is not int or not MIN_INTERVAL <= interval_seconds <= MAX_INTERVAL:
        raise UserFacingError("The watch interval must be between 1 minute and 24 hours")
    folder = validate_folder(path, store.data_dir)
    now = time.time()
    store.set_meta(KEY, {"path": str(folder), "enabled": True, "interval_seconds": interval_seconds,
                         "approved_at": now, "next_run_at": now, "last_run_at": None, "last_result": None})
    store.set_meta(STATE, {})
    store.record_activity("approval_granted", "folder_watch")
    return status(store)


def disable(store):
    if not (store.meta(KEY) or {}).get("enabled"):
        raise UserFacingError("No folder is being watched")
    store.set_meta(KEY, {**store.meta(KEY), "enabled": False, "next_run_at": None})
    store.record_activity("approval_revoked", "folder_watch")
    return status(store)


def status(store):
    config = store.meta(KEY)
    if not isinstance(config, dict):
        return None
    return {key: config.get(key) for key in ("path", "enabled", "interval_seconds", "approved_at", "next_run_at",
                                             "last_run_at", "last_result")}


def _changed_files(folder, known):
    """New or changed *.eml files directly in the folder; size and time only pre-select them,
    the content fingerprint of the import decides what is new (plan A13)."""
    found, current = [], {}
    with os.scandir(folder) as entries:
        for entry in sorted(entries, key=lambda item: item.name):
            if not entry.name.lower().endswith(".eml") or entry.is_symlink() or not entry.is_file(follow_symlinks=False):
                continue
            stat = entry.stat(follow_symlinks=False)
            current[entry.name] = [stat.st_size, stat.st_mtime_ns]
            if known.get(entry.name) != current[entry.name]:
                found.append(entry.name)
    return found, current


def run_due(store, now=None):
    """One watch pass if it is enabled and due; returns a short status, never file contents."""
    from .scan import scan_messages
    now = now or time.time()
    config = store.meta(KEY)
    if not isinstance(config, dict) or not config.get("enabled"):
        return {"status": "disabled"}
    if store.meta(PAUSE):
        return {"status": "paused"}
    if config.get("next_run_at") and now < config["next_run_at"]:
        return {"status": "not_due"}
    folder = Path(config["path"])
    following = {**config, "last_run_at": now, "next_run_at": now + config["interval_seconds"]}
    if not folder.is_dir() or folder.is_symlink():
        # A missing folder is reported, never searched for elsewhere (plan A15).
        store.set_meta(KEY, {**following, "last_result": "folder_missing"})
        return {"status": "folder_missing"}
    known = store.meta(STATE) or {}
    changed, current = _changed_files(folder, known)
    batch = changed[:MAX_FILES_PER_PASS]

    def items():
        for name in batch:
            with (folder / name).open("rb") as handle:
                yield name, handle.read(MAX_MESSAGE_BYTES + 1)
    result = {"status": "idle"}
    if batch:
        stats = scan_messages(store, items(), "eml", trigger="watch", keyed=True)
        result = {"status": "imported", "processed": stats["processed"], "evidence": stats["evidence"],
                  "unchanged": stats["unchanged"]}
    # Files beyond this pass's limit stay "changed" and follow in the next pass.
    remembered = {name: value for name, value in current.items() if name not in changed[MAX_FILES_PER_PASS:]}
    if len(remembered) > MAX_TRACKED_FILES:
        remembered = dict(sorted(remembered.items())[-MAX_TRACKED_FILES:])
    store.set_meta(STATE, remembered)
    store.set_meta(KEY, {**following, "last_result": result["status"]})
    return result


def next_run_iso(config):
    if not config or not config.get("enabled") or not config.get("next_run_at"):
        return None
    return datetime.fromtimestamp(config["next_run_at"], timezone.utc).isoformat()
