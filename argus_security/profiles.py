# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Separate named local profiles (plan P1).

A named profile is its own folder next to the default profile, with its own
database, mailbox settings, catalog additions, backups, approvals and keyring
selectors. Nothing is shared, merged or read across profiles; listing them
only looks at folder names.
"""
from pathlib import Path
import re

from .errors import UserFacingError

FOLDER = "argus-profiles"
NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")


def profile_dir(root: Path, name) -> Path:
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise UserFacingError("Use a profile name with lowercase letters, digits and dashes (at most 40)")
    return root / FOLDER / name


def list_profiles(root: Path, default_dir: Path):
    """Names of existing profiles; their contents are never opened here."""
    names = ["default"] if (default_dir / "accounts.sqlite3").is_file() else []
    folder = root / FOLDER
    if folder.is_dir() and not folder.is_symlink():
        names += sorted(entry.name for entry in folder.iterdir()
                        if entry.is_dir() and not entry.is_symlink() and NAME.fullmatch(entry.name)
                        and (entry / "accounts.sqlite3").is_file())
    return names


def profile_name(data_dir: Path):
    """The name shown in the dashboard: a named profile, or None for the default or a custom folder."""
    data_dir = Path(data_dir)
    return data_dir.name if data_dir.parent.name == FOLDER and NAME.fullmatch(data_dir.name) else None
