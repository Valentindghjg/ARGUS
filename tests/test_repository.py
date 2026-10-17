# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Repository-wide rules: source headers, a standard-library-only runtime and working doc links."""
import ast
from pathlib import Path
import re
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourceHeaderTests(unittest.TestCase):
    def test_every_source_file_declares_mpl_and_the_copyright_holder(self):
        folders = ("argus_security", "account_finder", "tests", "scripts", "browser-companion")
        missing = []
        for folder in folders:
            for path in (ROOT / folder).rglob("*"):
                if path.suffix not in {".py", ".js", ".html", ".css"} or "dist" in path.parts:
                    continue
                head = path.read_text(encoding="utf-8").split("\n", 4)[:4]
                if not any("SPDX-License-Identifier: MPL-2.0" in line for line in head) or \
                        not any("Copyright (c) 2026 ARGUS contributors" in line for line in head):
                    missing.append(str(path.relative_to(ROOT)))
        self.assertEqual(missing, [])


class StandardLibraryRuntimeTests(unittest.TestCase):
    """The app installs without third-party packages; keyring stays optional."""

    OPTIONAL = {"keyring"}

    def test_package_declares_no_runtime_dependencies(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project.get("dependencies", []), [])

    def test_package_imports_only_the_standard_library(self):
        foreign = []
        for folder in ("argus_security", "account_finder"):
            for path in sorted((ROOT / folder).rglob("*.py")):
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.level == 0:
                        names = [node.module]
                    else:
                        continue
                    for name in names:
                        top = name.split(".")[0]
                        if top not in sys.stdlib_module_names and top not in self.OPTIONAL | {"argus_security"}:
                            foreign.append(f"{path.relative_to(ROOT)}: {name}")
        self.assertEqual(foreign, [])



class DocumentationLinkTests(unittest.TestCase):
    def test_relative_markdown_links_point_to_existing_files(self):
        broken = []
        documents = [*ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / ".github").rglob("*.md")]
        for document in documents:
            for target in re.findall(r"\]\(([^)\s]+)\)", document.read_text(encoding="utf-8")):
                path = target.split("#")[0]
                if path and not re.match(r"^(https?|mailto):", path) and not (document.parent / path).exists():
                    broken.append(f"{document.relative_to(ROOT)}: {target}")
        self.assertEqual(broken, [])


if __name__ == "__main__":
    unittest.main()
