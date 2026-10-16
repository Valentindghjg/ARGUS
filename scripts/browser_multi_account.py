# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Optional browser regression for local identities; synthetic addresses and mail only."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_security.registry import Registry
from argus_security.scan import scan_messages, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import LEGACY_SCHEMA, Store, now


def main():
    parser = argparse.ArgumentParser(description="Browser regression for separate local account identities")
    parser.add_argument("--browser", default=shutil.which("chromium") or shutil.which("google-chrome"))
    parser.add_argument("--screenshots-dir", type=Path)
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        print("This optional test requires Playwright; the application itself does not.")
        return 2
    checks, errors, external, created_requests = [], [], [], []
    first, second = "personal@example.invalid", "work@example.invalid"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        registry = Registry()
        store = Store(root / "profile", registry)
        store.configure([first, second])
        # Recreate an earlier version's reviewed row with no identified address.
        with store.connect() as db:
            db.executescript(LEGACY_SCHEMA)
            db.execute("INSERT INTO accounts(provider_id,confirmed,status,checklist,updated) VALUES (?,?,?,?,?)",
                       ("steam", 1, "in_progress", json.dumps({"reviewed": True}), now()))
            db.execute("DELETE FROM meta WHERE key='account_instances_migrated'")
        store = Store(root / "profile", registry)
        scan_messages(store, [
            synthetic_mail("noreply@github.com", "Your account has been created", "Welcome!", first),
            synthetic_mail("security@github.com", "Your password has been changed", "Changed successfully.", second),
            synthetic_mail("security@github.com", "New sign-in to your account", "A new sign-in.", f"{first}, {second}"),
        ])
        original = {account["identity_email"]: account["id"] for account in store.snapshot()["accounts"]
                    if account["provider_id"] == "github"}
        server = DashboardServer(store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
                context = browser.new_context(viewport={"width":1440,"height":1100}, accept_downloads=True, locale="en-GB")

                def route(request_route):
                    url = request_route.request.url
                    if url.startswith(server.url):
                        if url.endswith("/api/accounts") and request_route.request.method == "POST":
                            created_requests.append(request_route.request.post_data_json)
                        request_route.continue_()
                    else:
                        external.append(url)
                        request_route.abort()

                context.route("**/*", route)
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(server.url, wait_until="networkidle")
                expect(page.locator("#found-count")).to_have_text("3")
                expect(page.locator("#services-found-caption")).to_have_text("2 services found")
                page.locator("#search").fill(second)
                expect(page.locator("#account-rows tr")).to_have_count(1)
                page.locator("#account-rows button").click()
                expect(page.locator("#detail-name")).to_contain_text(second)
                expect(page.locator("#registered-email")).to_have_value(second)
                expect(page.locator("#registered-email")).to_be_disabled()
                expect(page.locator("#identity-caution-note")).to_be_visible()
                expect(page.locator("#shared-evidence-panel")).to_be_visible()
                expect(page.locator("#shared-evidence .evidence-card")).to_have_count(1)
                page.locator("#decide-confirm").click()
                page.locator("#checklist input.step-check").first.check()
                expect(page.locator("#checklist input.step-check").first).to_be_enabled()
                identities = {account["id"]: account for account in store.snapshot()["accounts"]}
                assert identities[original[second]]["decision"] == "confirmed"
                assert identities[original[second]]["steps"]["identity"]["state"] == "done"
                assert identities[original[first]]["decision"] == "undecided"
                checks.append("Search distinguishes identities; review progress is separate; ambiguous clues stay unassigned")

                page.locator("#add-account-panel summary").click()
                page.locator("#new-account-email").select_option(second)
                page.locator("#new-account-label").fill("Second work profile")
                page.locator("#add-account-button").click()
                assert not created_requests, "Confirmation must be required before creating a local record"
                page.locator("#new-account-owned").check()
                page.locator("#add-account-button").click()
                expect(page.locator("#detail-name")).to_contain_text("Second work profile")
                expect(page.locator("#registered-email")).to_have_value(second)
                expect(page.locator("#registered-email")).to_be_disabled()
                expect(page.locator("#found-count")).to_have_text("4")
                assert created_requests == [{"provider_id":"github", "email":second,
                                             "label":"Second work profile", "confirmed":True}]
                siblings = [account for account in store.snapshot()["accounts"] if account["provider_id"] == "github"]
                added = next(account for account in siblings if account["label"] == "Second work profile")
                assert len({account["id"] for account in siblings}) == 3
                assert added["steps"]["vault"]["state"] == "open"
                checks.append("Explicit local-only separate-account form selects its new identity and preserves siblings")

                page.locator("#detail-worklist").click()
                expect(page.locator("#detail-worklist")).to_be_disabled()
                page.locator("#close-dialog").click()
                page.locator('[data-view="workflow"]').click()
                expect(page.locator("#worklist-items")).to_contain_text("Second work profile")
                expect(page.locator("#worklist-items")).to_contain_text(second)
                page.locator('[data-view="bitwarden"]').click()
                for checkbox in page.locator("#export-selection input:not(:disabled)").all():
                    checkbox.uncheck()
                expect(page.locator('#export-selection input[value="steam"]')).to_be_disabled()
                page.locator(f'#export-selection input[value="{added["id"]}"]').check()
                page.locator("#export-button").click()
                expect(page.locator("#preview-items tr")).to_have_count(1)
                expect(page.locator("#preview-items")).to_contain_text(second)
                with page.expect_download() as download_info:
                    page.locator("#preview-confirm").click()
                download_path = root / "metadata.json"
                download_info.value.save_as(download_path)
                exported = json.loads(download_path.read_text(encoding="utf-8"))
                assert len(exported["items"]) == 1
                assert exported["items"][0]["login"]["username"] == second
                assert not exported["items"][0]["login"]["password"]
                checks.append("Worklist and password-free Bitwarden selection target the chosen sibling only")

                page.locator('[data-view="accounts"]').click()
                page.locator("#search").fill("steam")
                page.get_by_role("button", name="Review Steam", exact=True).click()
                expect(page.locator("#identity-review-note")).to_be_visible()
                expect(page.locator("#detail-bitwarden")).to_be_disabled()
                expect(page.locator("#registered-email")).to_be_enabled()
                # Binding is permanent: cancelling the confirmation changes nothing.
                page.once("dialog", lambda dialog: dialog.dismiss())
                page.locator("#registered-email").select_option(first)
                expect(page.locator("#registered-email")).to_have_value("")
                expect(page.locator("#registered-email")).to_be_enabled()
                expect(page.locator("#identity-review-note")).to_be_visible()
                page.once("dialog", lambda dialog: dialog.accept())
                page.locator("#registered-email").select_option(first)
                expect(page.locator("#registered-email")).to_be_disabled()
                expect(page.locator("#identity-review-note")).to_be_hidden()
                expect(page.locator("#checklist input.step-check").first).to_be_checked()
                expect(page.locator("#detail-bitwarden")).to_be_enabled()
                checks.append("Legacy progress stays blocked from Bitwarden until the user explicitly confirms its identity")

                page.locator("#close-dialog").click()
                page.reload(wait_until="networkidle")
                page.locator("#search").fill("Second work profile")
                expect(page.locator("#account-rows tr")).to_have_count(1)
                page.locator("#account-rows button").click()
                page.locator("#detail-language").select_option("de")
                expect(page.locator("#add-account-panel summary")).to_have_text("Weiteren Account bei diesem Dienst hinzufügen")
                page.set_viewport_size({"width":390,"height":844})
                mobile_layout = page.evaluate("""() => ({
                    innerWidth: window.innerWidth,
                    documentWidth: document.documentElement.scrollWidth,
                    bodyWidth: document.body.scrollWidth,
                    overflowing: [...document.querySelectorAll('body *')]
                        .filter(element => {
                            const rect = element.getBoundingClientRect();
                            const style = getComputedStyle(element);
                            return style.position !== 'fixed' && rect.right > window.innerWidth + 1;
                        })
                        .slice(0, 12)
                        .map(element => ({tag: element.tagName, id: element.id, cls: element.className,
                            right: Math.round(element.getBoundingClientRect().right),
                            width: element.clientWidth, scrollWidth: element.scrollWidth,
                            overflowX: getComputedStyle(element).overflowX}))
                })""")
                # The compact navigation deliberately scrolls inside its own strip.  Body width
                # catches page overflow without treating that contained scroll area as one.
                assert mobile_layout["bodyWidth"] <= mobile_layout["innerWidth"], mobile_layout
                dialog_layout = page.locator("#account-dialog").evaluate("""element=>({
                    width:element.clientWidth,scrollWidth:element.scrollWidth,
                    overflow:[...element.querySelectorAll('*')].filter(child=>child.scrollWidth>child.clientWidth+1)
                        .map(child=>({tag:child.tagName,id:child.id,cls:child.className,width:child.clientWidth,scrollWidth:child.scrollWidth,text:child.textContent,whiteSpace:getComputedStyle(child).whiteSpace}))
                })""")
                assert dialog_layout["scrollWidth"] <= dialog_layout["width"], dialog_layout
                if args.screenshots_dir:
                    args.screenshots_dir.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(args.screenshots_dir / "separate-accounts-mobile-de.png"), full_page=True)
                page.locator("#close-dialog").click()
                page.locator('[data-view="workflow"]').click()
                expect(page.locator("#worklist-items")).to_contain_text("Second work profile")
                checks.append("Separate accounts and worklist persist; translated account controls fit a mobile viewport")
                assert not errors, errors
                assert not external, external
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
    print(json.dumps({"checks":checks,"page_errors":errors,"external_requests":len(external)},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
