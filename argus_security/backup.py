# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Local, unencrypted profile backups and verified restores.

A backup is one ZIP file with a manifest, a consistent copy of the database
(SQLite online backup) and, when present, the password-free ``imap.json``.
Secrets never enter a backup: ARGUS keeps none in the profile, and the OS
keyring is not copied. Files are created with private permissions and never
overwritten. The owner chose no ARGUS encryption (no new password system);
disk encryption protects backups like the profile itself.
"""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import zipfile

from . import __version__
from .errors import UserFacingError

FORMAT = "argus-backup"
FORMAT_VERSION = 1
DATABASE = "accounts.sqlite3"
IMAP_CONFIG = "imap.json"
MANIFEST = "manifest.json"
BACKUP_DIR = "backups"
REASONS = ("manual", "pre-migration", "pre-restore")
# Limits keep a damaged or hostile archive from exhausting the disk.
MAX_SIZES = {DATABASE: 1024 * 1024 * 1024, IMAP_CONFIG: 64 * 1024, MANIFEST: 64 * 1024}
KEEP_AUTOMATIC = 5


class BackupError(UserFacingError):
    """A constant, translatable reason why a backup or restore did not happen."""


def _now():
    return datetime.now(timezone.utc)


def _private_dir(path: Path):
    if path.is_symlink():
        raise BackupError("The backup folder must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "posix":
        path.chmod(0o700)


def _sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_only(database: Path, timeout=5):
    """Open a database file without any chance of writing to it."""
    return closing(sqlite3.connect(f"{Path(database).resolve().as_uri()}?mode=ro", uri=True, timeout=timeout))


def schema_version(database: Path):
    """Read the stored schema version without changing the file (None if unknown)."""
    try:
        with _read_only(database) as db:
            row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    except sqlite3.Error:
        return None
    try:
        value = json.loads(row[0]) if row else None
    except (TypeError, ValueError):
        return None
    return value if type(value) is int else None


def _copy_database(source: Path, target: Path):
    """Consistent copy even while another ARGUS process writes (online backup)."""
    with _read_only(source, timeout=15) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)


def default_folder(data_dir: Path):
    return data_dir / BACKUP_DIR


def create_backup(data_dir: Path, *, reason="manual", folder: Path | None = None, label=""):
    """Write one new backup archive and return its path; never overwrite a file."""
    if reason not in REASONS:
        raise ValueError("Invalid backup reason")
    data_dir = Path(data_dir)
    database = data_dir / DATABASE
    if not database.is_file() or database.is_symlink():
        raise BackupError("There is no local profile to back up yet")
    folder = Path(folder) if folder is not None else default_folder(data_dir)
    _private_dir(folder)
    stamp = _now().strftime("%Y%m%dT%H%M%SZ")
    name = f"argus-backup-{stamp}-{reason}{'-' + label if label else ''}-{secrets.token_hex(3)}.zip"
    target = folder / name
    fd, temporary = tempfile.mkstemp(prefix=".argus-db-", dir=folder)
    os.close(fd)
    temporary = Path(temporary)
    try:
        _copy_database(database, temporary)
        files = {DATABASE: temporary}
        imap = data_dir / IMAP_CONFIG
        if imap.is_file() and not imap.is_symlink():
            files[IMAP_CONFIG] = imap
        manifest = {"format": FORMAT, "version": FORMAT_VERSION, "app_version": __version__,
                    "created_at": _now().isoformat(), "reason": reason,
                    "schema_version": schema_version(temporary),
                    "files": {member: {"sha256": _sha256(path), "size": path.stat().st_size}
                              for member, path in files.items()}}
        handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(handle, "wb") as raw, zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2))
                for member, path in files.items():
                    archive.write(path, member)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    except (OSError, sqlite3.Error) as exc:
        raise BackupError("The backup could not be written; nothing was changed") from exc
    finally:
        temporary.unlink(missing_ok=True)
    if reason != "manual":
        _prune_automatic(folder)
    return target


def _prune_automatic(folder: Path):
    """Keep the newest automatic backups; manual backups are never deleted."""
    automatic = sorted(path for path in folder.glob("argus-backup-*.zip")
                       if "-manual" not in path.name and path.is_file() and not path.is_symlink())
    for path in automatic[:-KEEP_AUTOMATIC]:
        path.unlink(missing_ok=True)


def list_backups(data_dir: Path):
    folder = default_folder(Path(data_dir))
    if not folder.is_dir() or folder.is_symlink():
        return []
    result = []
    for path in sorted(folder.glob("argus-backup-*.zip"), reverse=True):
        try:
            manifest = read_manifest(path)
        except BackupError:
            continue
        result.append({"path": str(path), "created_at": manifest["created_at"], "reason": manifest["reason"],
                       "app_version": manifest["app_version"], "schema_version": manifest["schema_version"]})
    return result


def read_manifest(path: Path):
    """Validate an archive's structure and manifest without extracting data."""
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise BackupError("Choose an existing ARGUS backup file")
    try:
        with zipfile.ZipFile(path) as archive:
            members = {info.filename: info for info in archive.infolist()}
            if MANIFEST not in members or DATABASE not in members or set(members) - set(MAX_SIZES):
                raise BackupError("This file is not a valid ARGUS backup")
            if any(info.file_size > MAX_SIZES[name] for name, info in members.items()):
                raise BackupError("This file is not a valid ARGUS backup")
            manifest = json.loads(archive.read(MANIFEST))
    except (OSError, zipfile.BadZipFile, ValueError, UnicodeError) as exc:
        raise BackupError("This file is not a valid ARGUS backup") from exc
    if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT
            or not isinstance(manifest.get("files"), dict) or manifest.get("reason") not in REASONS
            or set(manifest["files"]) != set(members) - {MANIFEST}
            or not all(isinstance(entry, dict) for entry in manifest["files"].values())
            or not isinstance(manifest.get("created_at"), str) or not isinstance(manifest.get("app_version"), str)):
        raise BackupError("This file is not a valid ARGUS backup")
    if manifest.get("version") != FORMAT_VERSION:
        raise BackupError("This backup was made by a newer ARGUS version; update ARGUS first")
    return manifest


def _extract_verified(path: Path, manifest: dict, folder: Path):
    """Extract members into new private files and check every checksum."""
    extracted = {}
    try:
        with zipfile.ZipFile(path) as archive:
            for member, expected in manifest["files"].items():
                fd, name = tempfile.mkstemp(prefix=".argus-restore-", dir=folder)
                extracted[member] = Path(name)
                digest, size = hashlib.sha256(), 0
                with os.fdopen(fd, "wb") as out, archive.open(member) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        size += len(chunk)
                        if size > MAX_SIZES[member]:
                            raise BackupError("This file is not a valid ARGUS backup")
                        digest.update(chunk)
                        out.write(chunk)
                if not isinstance(expected, dict) or digest.hexdigest() != expected.get("sha256") or size != expected.get("size"):
                    raise BackupError("The backup is damaged; its checksums do not match")
    except BaseException:
        for file in extracted.values():
            file.unlink(missing_ok=True)
        raise
    database = extracted[DATABASE]
    try:
        with _read_only(database) as db:
            ok = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            has_meta = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'").fetchone()
    except sqlite3.Error:
        ok = has_meta = False
    if not ok or not has_meta:
        for file in extracted.values():
            file.unlink(missing_ok=True)
        raise BackupError("The backup is damaged; its checksums do not match")
    return extracted


def restore_backup(data_dir: Path, path: Path):
    """Replace the profile with a verified backup; the current state is saved first.

    Stop the dashboard and any scan before restoring. OS-keyring entries are
    not part of a backup, so scheduled scans may need a new approval.
    """
    data_dir = Path(data_dir)
    manifest = read_manifest(path)
    if data_dir.is_symlink():
        raise BackupError("The backup folder must not be a symlink")
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    extracted = _extract_verified(Path(path), manifest, data_dir)
    safety = None
    try:
        if (data_dir / DATABASE).is_file():
            safety = create_backup(data_dir, reason="pre-restore")
        os.replace(extracted.pop(DATABASE), data_dir / DATABASE)
        if IMAP_CONFIG in extracted:
            os.replace(extracted.pop(IMAP_CONFIG), data_dir / IMAP_CONFIG)
        else:
            # The restored profile had no mailbox settings; keep them only in the safety backup.
            (data_dir / IMAP_CONFIG).unlink(missing_ok=True)
    except OSError as exc:
        raise BackupError("The profile is in use; stop the dashboard and scans, then restore again") from exc
    finally:
        for file in extracted.values():
            file.unlink(missing_ok=True)
    if os.name == "posix":
        for name in (DATABASE, IMAP_CONFIG):
            if (data_dir / name).is_file():
                (data_dir / name).chmod(0o600)
    return {"restored": manifest["created_at"], "reason": manifest["reason"],
            "app_version": manifest["app_version"], "safety_backup": str(safety) if safety else None}
