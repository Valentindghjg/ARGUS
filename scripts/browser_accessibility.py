# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""WCAG 2.2 AA audit with axe-core over every view and dialog in German and English (plan D6).

Optional browser QA with synthetic data only. It needs Playwright, Chromium and
the pinned axe-core from scripts/accessibility (``npm ci --prefix
scripts/accessibility``); the application needs none of them. Every violation
fails the run. The output names rules, impact and element selectors, never page
text.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from argus_security.registry import Registry
from argus_security.scan import load_demo
from argus_security.server import DashboardServer
from argus_security.store import Store

AXE = ROOT / "scripts" / "accessibility" / "node_modules" / "axe-core" / "axe.min.js"
# WCAG 2.0, 2.1 and 2.2, levels A and AA. Best-practice rules are not part of the gate.
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
VIEWPORTS = {"desktop": {"width": 1440, "height": 1100}, "mobile": {"width": 390, "height": 844}}
LANGUAGES = ("en", "de")
CATALOG_BUTTON = {"en": "Add to my catalog",
                  "de": json.loads((ROOT / "argus_security" / "data" / "translations.json").read_text(
                      encoding="utf-8"))["de"]["Add to my catalog"]}


class Audit:
    def __init__(self, page, axe_source):
        self.page, self.axe_source = page, axe_source
        self.runs, self.violations, self.incomplete, self.dialogs = [], [], {}, set()

    def __call__(self, state, dialog=None):
        if not self.page.evaluate("typeof axe !== 'undefined'"):
            self.page.evaluate(self.axe_source)
        result = self.page.evaluate("""tags => axe.run(document, {runOnly: {type: 'tag', values: tags},
                                                                   resultTypes: ['violations', 'incomplete']})""", TAGS)
        self.runs.append(state)
        if dialog:
            self.dialogs.add(dialog)
        for rule in result["violations"]:
            self.violations.append({"state": state, "rule": rule["id"], "impact": rule["impact"], "help": rule["help"],
                                    "targets": [node["target"] for node in rule["nodes"]][:10]})
        # "Needs review" results cannot be decided automatically; they are listed, not counted as failures.
        for rule in result["incomplete"]:
            self.incomplete[rule["id"]] = self.incomplete.get(rule["id"], 0) + len(rule["nodes"])


def local_only(base, external):
    """Let only the local dashboard load; anything else is counted and blocked."""
    def route(request_route):
        if request_route.request.url.startswith(base):
            request_route.continue_()
        else:
            external.append(request_route.request.url)
            request_route.abort()
    return route


def language(page, code, expect):
    page.locator("#language").select_option(code)
    expect(page.locator("html")).to_have_attribute("lang", code)


def view(page, name, expect):
    item = page.locator(f'.nav-item[data-view="{name}"]')
    item.click()
    expect(item).to_have_attribute("aria-current", "page")


def dialogs(page, audit, prefix, expect, label):
    """Open each dialog the way a person does, audit it and close it again."""
    view(page, "dashboard", expect)
    def opened(dialog, close):
        expect(page.locator(f"#{dialog}")).to_be_visible()
        audit(f"{prefix}/{dialog}", dialog)
        page.locator(f"#{close}").click()
        expect(page.locator(f"#{dialog}")).to_be_hidden()
    page.locator("#next-task-action").click()
    opened("account-dialog", "close-dialog")
    page.locator("#report-level").select_option("tasks")
    page.locator("#report-create").click()
    opened("report-dialog", "report-cancel")
    view(page, "bitwarden", expect)
    page.locator("#export-selection input").first.check()
    page.locator("#export-button").click()
    opened("export-preview", "preview-cancel")
    view(page, "unclear", expect)
    page.locator("#unclear-items").get_by_role("button", name=label).first.click()
    opened("catalog-dialog", "catalog-cancel")


def main():
    parser = argparse.ArgumentParser(description="WCAG 2.2 AA audit with axe-core and synthetic data")
    parser.add_argument("--browser", default=shutil.which("chromium") or shutil.which("google-chrome"))
    parser.add_argument("--axe", type=Path, default=AXE, help="axe.min.js (default: the pinned test dependency)")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        print("This optional test requires Playwright; the application itself does not.")
        return 2
    if not args.axe.is_file():
        print("axe-core is missing; run: npm ci --prefix scripts/accessibility")
        return 2
    axe_source = args.axe.read_text(encoding="utf-8")
    errors, external, audits, unaudited = [], [], [], set()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        demo = Store(root / "demo", Registry())
        load_demo(demo)
        fresh = Store(root / "fresh", Registry())
        servers = [DashboardServer(demo, 0), DashboardServer(fresh, 0)]
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
                for profile, server in (("demo", servers[0]), ("new", servers[1])):
                    for size, viewport in VIEWPORTS.items():
                        context = browser.new_context(viewport=viewport, locale="en-GB")

                        context.route("**/*", local_only(server.url, external))
                        page = context.new_page()
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        page.goto(server.url, wait_until="networkidle")
                        audit = Audit(page, axe_source)
                        # Views and dialogs come from the page itself, so a new one cannot go unaudited.
                        views = page.eval_on_selector_all(".nav-item[data-view]", "items => items.map(i => i.dataset.view)")
                        for code in LANGUAGES:
                            language(page, code, expect)
                            for name in views:
                                view(page, name, expect)
                                audit(f"{profile}/{size}/{code}/{name}")
                            if profile == "demo":
                                dialogs(page, audit, f"{profile}/{size}/{code}", expect, CATALOG_BUTTON[code])
                        if profile == "demo":
                            every = set(page.eval_on_selector_all("dialog", "items => items.map(i => i.id)"))
                            unaudited.update(every - audit.dialogs)
                        audits.append(audit)
                        context.close()
                browser.close()
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
    violations = [v for audit in audits for v in audit.violations]
    incomplete = {}
    for audit in audits:
        for rule, count in audit.incomplete.items():
            incomplete[rule] = incomplete.get(rule, 0) + count
    print(json.dumps({"standard": "WCAG 2.2 AA (axe-core tags " + ", ".join(TAGS) + ")",
                      "states": sum(len(audit.runs) for audit in audits), "violations": violations,
                      "needs_review": incomplete, "unaudited_dialogs": sorted(unaudited), "page_errors": errors,
                      "external_requests": len(external)}, ensure_ascii=False, indent=2))
    return 1 if violations or errors or external or unaudited else 0


if __name__ == "__main__":
    raise SystemExit(main())
