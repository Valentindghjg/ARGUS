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
import json
import os
from pathlib import Path
import stat
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
    # A mapped network drive resolves to a UNC path on Windows.
    if str(folder).startswith(("\\\\", "//")):
        raise UserFacingError("Choose a local folder; network paths are not watched")
    home = Path.home().resolve()
    profile = Path(data_dir).resolve()
    # samefile also catches another spelling on case-insensitive disks (macOS, Windows).
    if (folder == Path(folder.anchor) or _same(folder, home) or any(_same(folder, parent) for parent in home.parents)
            or any(part.startswith(".") for part in folder.parts[1:])):
        raise UserFacingError("Choose a narrow folder of its own, not the whole disk, your home folder or a hidden folder")
    if folder == profile or profile in folder.parents or folder in profile.parents:
        raise UserFacingError("Choose a folder outside the ARGUS profile")
    return folder


def _same(one, other):
    try:
        return one.samefile(other)
    except OSError:
        return one == other


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
            info = entry.stat(follow_symlinks=False)
            current[entry.name] = [info.st_size, info.st_mtime_ns]
            if known.get(entry.name) != current[entry.name]:
                found.append(entry.name)
    return found, current


def _read(folder, name):
    """One watched file, or None if it cannot be read as a plain file now.

    It is opened without following links and without waiting, and must still be
    a regular file, so a file swapped for a link or a pipe after the folder was
    listed is skipped instead of followed or blocking the scheduler.
    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        handle = os.open(folder / name, flags)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            return None
        with os.fdopen(handle, "rb") as file:
            handle = None
            return file.read(MAX_MESSAGE_BYTES + 1)
    except OSError:
        return None
    finally:
        if handle is not None:
            os.close(handle)


def _finish_pass(store, config, values, remembered=None):
    """Store the pass result only while the same approval is still active.

    A pass that ends after the person disabled the watch or approved another
    folder never brings the old one back (plan A12).
    """
    with store.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT value FROM meta WHERE key=?", (KEY,)).fetchone()
        stored = json.loads(row[0]) if row else None
        if (not isinstance(stored, dict) or not stored.get("enabled") or stored.get("path") != config["path"]
                or stored.get("approved_at") != config.get("approved_at")):
            return False
        db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (KEY, json.dumps({**stored, **values})))
        if remembered is not None:
            db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (STATE, json.dumps(remembered)))
    return True


def run_due(store, now=None):
    """One watch pass if it is enabled and due; returns a short status, never file contents."""
    from .jobs import JobPaused
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
    following = {"last_run_at": now, "next_run_at": now + config["interval_seconds"]}
    if not folder.is_dir() or folder.is_symlink():
        # A missing folder is reported, never searched for elsewhere (plan A15).
        _finish_pass(store, config, {**following, "last_result": "folder_missing"})
        return {"status": "folder_missing"}
    known = store.meta(STATE) or {}
    try:
        changed, current = _changed_files(folder, known)
    except OSError:
        _finish_pass(store, config, {**following, "last_result": "failed"})
        return {"status": "failed"}
    if len(current) > MAX_TRACKED_FILES:
        # Too many files to remember reliably; import the folder once instead (plan A14).
        _finish_pass(store, config, {**following, "last_result": "too_many_files"})
        return {"status": "too_many_files"}
    batch = changed[:MAX_FILES_PER_PASS]
    attempted = []

    def items():
        for name in batch:
            attempted.append(name)
            yield name, _read(folder, name)
    result = {"status": "idle"}
    if batch:
        try:
            stats = scan_messages(store, items(), "eml", trigger="watch", keyed=True)
        except JobPaused:
            # Paused between two files: the rest follows after resuming, nothing is lost.
            _finish_pass(store, config, {"last_result": "paused"},
                         _remember(current, known, attempted[:-1]))
            return {"status": "paused"}
        except Exception:
            # The job is recorded as failed; the pass ends normally, so the interval holds.
            _finish_pass(store, config, {**following, "last_result": "failed"}, _remember(current, known, []))
            return {"status": "failed"}
        if stats["result"] == "partial":
            # Stopped early because the own addresses changed: the file that noticed it
            # and every later one are read again under the new addresses.
            attempted = attempted[:max(0, stats["processed"] - 1)]
        result = {"status": "imported", "processed": stats["processed"], "evidence": stats["evidence"],
                  "unchanged": stats["unchanged"]}
    _finish_pass(store, config, {**following, "last_result": result["status"]}, _remember(current, known, attempted))
    return result


def _remember(current, known, done):
    """Files to treat as seen: unchanged ones and those this pass read; the rest follow next time."""
    return {name: value for name, value in current.items() if known.get(name) == value or name in done}


def next_run_iso(config):
    if not config or not config.get("enabled") or not config.get("next_run_at"):
        return None
    return datetime.fromtimestamp(config["next_run_at"], timezone.utc).isoformat()
