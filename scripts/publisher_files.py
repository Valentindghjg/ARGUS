# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Shared file handling for the offline publisher scripts."""
import os
from pathlib import Path


def write_new(path: Path, content: bytes, mode: int) -> None:
    """Create a new file with ``mode``; never overwrite or follow a symlink."""
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(content)
