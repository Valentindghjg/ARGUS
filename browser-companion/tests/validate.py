#!/usr/bin/env python3
"""Static validation for the unpacked browser companion build."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "browser-companion" / "scripts" / "build.py"
SRC = ROOT / "browser-companion" / "src"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "extension"
        subprocess.run([sys.executable, str(BUILD), "--output", str(output)], check=True)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        providers = json.loads((output / "providers.json").read_text(encoding="utf-8"))
        require(manifest["manifest_version"] == 3, "Manifest V3 is required")
        require(manifest["permissions"] == ["activeTab"], "Only activeTab may be requested")
        forbidden = {"host_permissions", "optional_permissions", "optional_host_permissions", "background",
                     "content_scripts", "externally_connectable", "nativeMessaging", "web_accessible_resources"}
        require(not (forbidden & set(manifest)), "Prototype must not add background or page/native access")
        catalogue = json.loads((ROOT / "argus_security" / "data" / "providers.json").read_text(encoding="utf-8"))["providers"]
        require(len(providers) == len(catalogue), "Bundled catalogue must contain every provider")
        require(all(row["website"].startswith("https://") for row in providers), "Unsafe website link")
        require(all(set(row) == {"id", "name", "website", "domains", "password_url"} for row in providers), "Unexpected provider fields")
        require(all(not row["password_url"] or row["password_url"].startswith("https://") for row in providers), "Unsafe password link")
        script = (SRC / "popup.js").read_text(encoding="utf-8")
        forbidden_terms = ("document.cookie", "localStorage", "sessionStorage", "nativeMessaging", "fetch(\"http", "XMLHttpRequest")
        require(not any(term in script for term in forbidden_terms), "Popup contains prohibited data/network access")
        require(not any(term in script for term in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(")), "Popup must not build HTML from strings")
        require('parsed.protocol !== "https:"' in script, "Popup must label only HTTPS pages")
    print("Browser companion static checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
