"""Publisher tool: issue a signed ARGUS Pro entitlement after payment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_security.licensing import PRO_FEATURES, issue


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_new(path: Path, content: str):
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def main():
    parser = argparse.ArgumentParser(description="Issue a signed ARGUS Pro license")
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--license-id", default="pro_" + secrets.token_urlsafe(18).replace("-", "_").replace("~", "_"))
    parser.add_argument("--expires-at", help="UTC ISO timestamp ending in Z; omit for a perpetual license")
    parser.add_argument("--feature", action="append", choices=sorted(PRO_FEATURES))
    args = parser.parse_args()
    features = args.feature or sorted(PRO_FEATURES)
    payload = {"license_id": args.license_id, "issued_at": iso_now(),
               "expires_at": args.expires_at, "features": features}
    document = issue(payload, args.private_key.read_bytes())
    write_new(args.output, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print("Created a signed Pro license. Send only this license file to the purchaser.")


if __name__ == "__main__":
    main()
