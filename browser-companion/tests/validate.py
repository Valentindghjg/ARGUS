#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Static validation for the unpacked browser companion build."""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "browser-companion" / "scripts" / "build.py"
SRC = ROOT / "browser-companion" / "src"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def simulate(extension: Path) -> None:
    """Run popup.js with simulated chrome.* APIs for typical and hostile URLs."""
    urls = ["https://github.com/settings", "https://www.github.com/", "https://evil-github.com/",
            "https://someone.substack.com/p/login", "http://github.com/", "file:///etc/passwd",
            "https://firebase.google.com/", "chrome://settings"]
    results = {}
    for language in ("en", "de"):
        run = subprocess.run(["node", str(ROOT / "browser-companion" / "tests" / "popup_harness.js"),
                              str(extension), language, *urls], check=True, capture_output=True, text=True, timeout=60)
        results[language] = {row["url"]: row for row in json.loads(run.stdout)}
    messages = {language: {key: value["message"] for key, value in
                           json.loads((extension / "_locales" / language / "messages.json").read_text(encoding="utf-8")).items()}
                for language in ("en", "de")}
    for language, rows in results.items():
        text = messages[language]
        require(rows["https://github.com/settings"]["state"] == text["official"], "Exact catalogue domain must be official")
        require(rows["https://github.com/settings"]["domain"] == "github.com", "Show the catalogue domain")
        require(rows["https://www.github.com/"]["state"] == text["official"], "www host counts as official")
        require(rows["https://evil-github.com/"]["state"] == text["notInCatalogue"], "Suffix lookalikes must not match")
        require(rows["https://someone.substack.com/p/login"]["state"] == text["subdomain"], "User subdomains are never official")
        require(rows["https://someone.substack.com/p/login"]["domain"] == "substack.com", "Show the catalogue domain")
        require(rows["http://github.com/"]["state"] == text["notHttps"], "Plain HTTP is never labelled")
        require(rows["file:///etc/passwd"]["state"] == text["notHttps"], "Local files are never labelled")
        require(rows["chrome://settings"]["state"] == text["notHttps"], "Browser pages are never labelled")
        require(rows["https://firebase.google.com/"]["provider"] != "", "Nested catalogue domains still match")
        require(rows["https://github.com/settings"]["heading"] == text["heading"], "Static text must be localized")
        require(all(row["lang"] == language for row in rows.values()), "Document language follows the browser")
    require(results["de"]["https://github.com/settings"]["state"] != results["en"]["https://github.com/settings"]["state"],
            "German messages must be used for a German browser")


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "extension"
        subprocess.run([sys.executable, str(BUILD), "--output", str(output)], check=True)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        providers = json.loads((output / "providers.json").read_text(encoding="utf-8"))
        require(manifest["manifest_version"] == 3, "Manifest V3 is required")
        require(manifest["permissions"] == ["activeTab"], "Only activeTab may be requested")
        require(manifest.get("default_locale") == "en", "English must be the default locale")
        locales = {language: json.loads((output / "_locales" / language / "messages.json").read_text(encoding="utf-8"))
                   for language in ("en", "de")}
        require(set(locales["en"]) == set(locales["de"]), "English and German messages must match")
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
        page = (SRC / "popup.html").read_text(encoding="utf-8")
        used = set(re.findall(r'data-i18n="([A-Za-z0-9_]+)"', page))
        used |= set(re.findall(r'(?:message|showUnknown)\("([A-Za-z0-9_]+)"\)', script))
        used |= set(re.findall(r'"__MSG_([A-Za-z0-9_]+)__"', (SRC / "manifest.json").read_text(encoding="utf-8")))
        used |= {"official", "subdomain"}
        require(used <= set(locales["en"]), "Unknown message keys: " + ", ".join(sorted(used - set(locales["en"]))))
        require(set(locales["en"]) <= used, "Unused message keys: " + ", ".join(sorted(set(locales["en"]) - used)))
        simulate(output)
    print("Browser companion static and behavior checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
