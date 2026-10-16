#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Create a self-contained, unpacked Chromium extension from safe catalogue fields."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[2]
COMPANION = ROOT / "browser-companion"
sys.path.insert(0, str(ROOT))
from argus_security.registry import Registry  # noqa: E402  (after sys.path setup)


def bundle() -> list[dict[str, object]]:
    """Reuse the application's catalogue validation: HTTPS links inside each
    provider's domains, IDNA-normalized and unambiguous domains."""
    return [{"id": provider.id, "name": provider.name, "website": provider.website,
             "domains": list(provider.domains), "password_url": provider.password_url}
            for provider in Registry().providers.values()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=COMPANION / "dist")
    args = parser.parse_args()
    target = args.output.resolve()
    source = COMPANION / "src"
    if target == source.resolve() or source.resolve() in target.parents:
        raise SystemExit("Output directory must not replace browser-companion/src")
    if target.exists():
        raise SystemExit(
            f"Output directory already exists: {target}. Choose a new empty path or remove this generated directory yourself."
        )
    shutil.copytree(source, target)
    (target / "providers.json").write_text(
        json.dumps(bundle(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(bundle())} provider records in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
