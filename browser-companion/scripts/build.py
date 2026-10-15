#!/usr/bin/env python3
"""Create a self-contained, unpacked Chromium extension from safe catalogue fields."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "account_finder" / "data" / "providers.json"
COMPANION = ROOT / "browser-companion"


def matches(host: str, root: str) -> bool:
    return host == root or host.endswith("." + root)


def checked_link(value: str, domains: list[str]) -> str:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise ValueError("provider link is not an HTTPS URL")
    host = parts.hostname.lower().rstrip(".")
    if not any(matches(host, domain) for domain in domains):
        raise ValueError("provider link is outside its declared domains")
    return value


def bundle() -> list[dict[str, object]]:
    rows = json.loads(SOURCE.read_text(encoding="utf-8"))["providers"]
    result = []
    for row in rows:
        domains = [str(domain).lower().rstrip(".") for domain in row["domains"]]
        password_url = row.get("password_url")
        if password_url is not None:
            password_url = checked_link(str(password_url), domains)
        result.append({
            "id": row["id"],
            "name": row["name"],
            "website": checked_link(str(row["website"]), domains),
            "domains": domains,
            "password_url": password_url,
        })
    return sorted(result, key=lambda provider: max(map(len, provider["domains"])), reverse=True)


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
