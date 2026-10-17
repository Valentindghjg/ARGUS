# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Checks before a release (plan G6).

- One version everywhere: the package, the English and the German change log.
- Every module that can reach the network or start another program is declared
  below with what it does. A new connection or permission fails this check
  until it is declared here and named in the release notes.
- The browser companion keeps exactly its declared permissions.
- ``tag NAME`` checks that a release tag names this version.
- ``checksums DIST`` writes SHA256SUMS for the built files.

Usage: python scripts/release_check.py [tag NAME | checksums DIST]
"""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
# Standard-library modules that open connections or start programs, and dynamic imports
# that could load any of them unseen.
REACHING = {"imaplib", "poplib", "smtplib", "ftplib", "nntplib", "telnetlib", "ssl", "socket", "socketserver",
            "http.client", "http.server", "urllib.request", "xmlrpc.client", "xmlrpc.server", "asyncio",
            "subprocess", "multiprocessing", "concurrent.futures", "webbrowser", "importlib"}
# os functions that start programs without any of the modules above.
PROCESS_CALLS = {"system", "popen", "startfile", "posix_spawn", "posix_spawnp", "fork", "forkpty"}
PACKAGES = ("argus_security", "account_finder")
DECLARED = {
    "imap_client.py": "Reads the mailbox over TLS IMAP, only with scan-imap --allow-imap or an approved scheduled scan.",
    "discovery.py": "Asks the DNS resolver for MX records, only with --allow-dns.",
    "bitwarden.py": "Runs the official Bitwarden CLI that you unlocked, only after your confirmation.",
    "server.py": "Serves the dashboard on 127.0.0.1 only and opens it in your browser when you pass --open.",
}
COMPANION_PERMISSIONS = ["activeTab"]
# Any other manifest key (content scripts, optional or host permissions, background) is a new capability.
COMPANION_KEYS = {"manifest_version", "name", "description", "default_locale", "version", "action", "permissions",
                  "content_security_policy"}


def _reaches(name):
    return any(name == entry or name.startswith(entry + ".") for entry in REACHING)


def module_hits(source):
    """What one module's code can use to reach out, by import form and os call."""
    hits, os_names = set(), set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _reaches(alias.name):
                    hits.add(alias.name)
                if alias.name == "os":
                    os_names.add(alias.asname or "os")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                # "from urllib import request" uses urllib.request just like "import urllib.request".
                full = f"{node.module}.{alias.name}"
                if _reaches(node.module) or _reaches(full):
                    hits.add(full if _reaches(full) else node.module)
                elif node.module == "os" and (alias.name in PROCESS_CALLS or alias.name.startswith(("exec", "spawn"))):
                    hits.add(full)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in os_names:
            if node.attr in PROCESS_CALLS or node.attr.startswith(("exec", "spawn")):
                hits.add("os." + node.attr)
        elif isinstance(node, ast.Name) and node.id == "__import__":
            hits.add("__import__")
    return sorted(hits)


def reaching_modules():
    found = {}
    for package in PACKAGES:
        for path in sorted((ROOT / package).rglob("*.py")):
            hits = module_hits(path.read_text(encoding="utf-8"))
            if hits:
                key = path.name if package == "argus_security" else path.relative_to(ROOT).as_posix()
                found[key] = hits
    return found


def package_version():
    return re.search(r'__version__ = "([^"]+)"', (ROOT / "argus_security" / "__init__.py").read_text()).group(1)


def problems():
    issues = []
    version = package_version()
    if f"## {version} " not in (ROOT / "docs" / "CHANGELOG.md").read_text(encoding="utf-8"):
        issues.append(f"docs/CHANGELOG.md has no heading for {version}")
    if f"Version {version}," not in (ROOT / "docs" / "AENDERUNGEN.md").read_text(encoding="utf-8"):
        issues.append(f"docs/AENDERUNGEN.md has no heading for {version}")
    for module, names in reaching_modules().items():
        if module not in DECLARED:
            issues.append(f"{module} can reach out ({', '.join(names)}) but is not declared")
    for module in DECLARED:
        if module not in reaching_modules():
            issues.append(f"{module} is declared but no longer reaches out; remove the declaration")
    manifest = json.loads((ROOT / "browser-companion" / "src" / "manifest.json").read_text(encoding="utf-8"))
    if not companion_declared(manifest):
        issues.append("The browser companion asks for permissions that are not declared")
    return issues


def companion_declared(manifest):
    return manifest.get("permissions", []) == COMPANION_PERMISSIONS and not set(manifest) - COMPANION_KEYS


def write_checksums(folder: Path):
    files = sorted(path for path in folder.iterdir() if path.is_file() and path.name != "SHA256SUMS")
    lines = [f"{sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in files]
    (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["tag"] and len(argv) == 2:
        if argv[1] != f"v{package_version()}":
            print(f"Release check: the tag {argv[1]} does not name version {package_version()}")
            return 1
        return 0
    if argv[:1] == ["checksums"] and len(argv) == 2:
        for line in write_checksums(Path(argv[1])):
            print(line)
        return 0
    issues = problems()
    for issue in issues:
        print("Release check: " + issue)
    if not issues:
        print("Release check passed. Connections and permissions to name in the release notes:")
        for module, text in DECLARED.items():
            print(f"- {module}: {text}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
