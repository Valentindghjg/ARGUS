# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Publisher tool: issue a signed ARGUS Pro entitlement after payment."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_security.licensing import PRO_FEATURES, issue  # noqa: E402
from publisher_files import write_new  # noqa: E402  (script directory)


def iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    write_new(args.output, (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8"), 0o600)
    print("Created a signed Pro license. Send only this license file to the purchaser.")


if __name__ == "__main__":
    main()
