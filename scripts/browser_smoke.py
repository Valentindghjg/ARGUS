# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Optional browser QA with synthetic data only. Requires Playwright + Chromium."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argus_security.registry import Registry
from argus_security.scan import load_demo, synthetic_mail
from argus_security.server import DashboardServer
from argus_security.store import Store


def main():
    parser = argparse.ArgumentParser(description="Browser smoke test with synthetic emails")
    parser.add_argument("--browser", default=shutil.which("chromium") or shutil.which("google-chrome"))
    parser.add_argument("--screenshots-dir", type=Path)
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError:
        print("This optional test requires Playwright; the application itself does not.")
        return 2
    checks, errors, external = [], [], []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = Store(root / "demo", Registry())
        load_demo(store)
        server = DashboardServer(store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
                context = browser.new_context(viewport={"width":1440,"height":1100}, accept_downloads=True, locale="en-GB")
                def route(request_route):
                    url = request_route.request.url
                    if url.startswith(server.url):
                        request_route.continue_()
                    else:
                        external.append(url)
                        request_route.abort()
                context.route("**/*", route)
                page = context.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(server.url, wait_until="networkidle")
                expect(page.locator("#found-count")).to_have_text("12")
                expect(page.locator("#account-rows tr")).to_have_count(12)
                expect(page.locator("html")).to_have_attribute("lang", "en")
                expect(page.locator("#page-title")).to_have_text("Your accounts, in one place.")
                checks.append("English desktop dashboard, statistics and demo notice")
                if args.screenshots_dir:
                    args.screenshots_dir.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(args.screenshots_dir / "dashboard.png"), full_page=True)

                page.locator('[data-view="workflow"]').click()
                expect(page.locator('#guided-priority-preview')).to_be_visible()
                expect(page.locator('#guided-priority-items article')).to_have_count(10)
                expect(page.locator('#guided-build-worklist')).to_be_enabled()
                page.locator('#worklist-selection input[value="discord"]').check()
                page.locator('#worklist-selection input[value="steam"]').check()
                page.evaluate("refresh()")
                expect(page.locator('#worklist-selection input[value="steam"]')).to_be_checked()
                page.locator('#worklist-add').click()
                expect(page.locator('#worklist-items article')).to_have_count(2)
                picker = page.locator('#worklist-items article').nth(1).locator('.snooze-date')
                expect(picker).to_have_attribute('min')
                picker.fill(picker.get_attribute('min'))
                page.locator('#worklist-items article').nth(1).get_by_role('button',name='Schedule date',exact=True).click()
                expect(page.locator('#worklist-items article').nth(1)).to_contain_text('Snoozed until')
                page.locator('#worklist-pause').click()
                expect(page.locator('#worklist-badge')).to_have_text('Paused')
                expect(page.locator('#worklist-continue')).to_be_disabled()
                page.reload(wait_until='networkidle')
                page.locator('[data-view="workflow"]').click()
                expect(page.locator('#worklist-badge')).to_have_text('Paused')
                expect(page.locator('#worklist-items article')).to_have_count(2)
                page.locator('#language').select_option('de')
                expect(page.locator('#guided-priority-preview')).to_contain_text('Vorgeschlagene Prioritäts-Arbeitsliste')
                expect(page.locator('#worklist-items article').nth(1)).to_contain_text('zurückgestellt')
                expect(page.locator('#worklist-pause')).to_have_text('Arbeitsliste fortsetzen')
                page.locator('#worklist-pause').click()
                expect(page.locator('#guided-current-card')).to_contain_text('Discord')
                expect(page.locator('#guided-status')).to_have_text('Aktion erforderlich')
                page.locator('#guided-current-open').click()
                expect(page.locator('#account-dialog')).to_be_visible()
                expect(page.locator('#detail-next-step')).to_have_text('Prüfe diesen Account und bestätige, dass er existiert.')
                expect(page.locator('#guided-detail-copy')).to_contain_text('eigenen Prüfung')
                expect(page.locator('#detail-worklist')).to_be_disabled()
                page.locator('#detail-language').select_option('en')
                expect(page.locator('#detail-next-step')).to_have_text('Review this account and confirm it exists.')
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#guided-complete-step').click()
                expect(page.locator('#checklist input').first).to_be_checked()
                expect(page.locator('#detail-next-step')).to_have_text('Assign an existing Bitwarden item or prepare a missing one.')
                expect(page.locator('#guided-prepare-bitwarden')).to_be_visible()
                page.locator('#close-dialog').click()
                if args.screenshots_dir:
                    page.screenshot(path=str(args.screenshots_dir / 'worklist.png'), full_page=True)
                checks.append('Persistent bilingual security worklist, pause, resume and guided next step')
                page.locator('[data-view="dashboard"]').click()

                page.locator("#search").fill("steam")
                expect(page.locator("#account-rows tr")).to_have_count(1)
                page.locator("#search").fill("")
                page.locator("#category").select_option("Finance")
                expect(page.locator("#account-rows tr")).to_have_count(2)
                page.locator("#category").select_option("")
                page.locator("#classification").select_option("unknown")
                expect(page.locator("#account-rows tr")).to_have_count(len(store.registry.providers) - 12)
                page.locator("#classification").select_option("found")
                checks.append("Search, category filters and unknown providers")

                page.locator("#category").select_option("Finance")
                page.locator("#language").select_option("de")
                expect(page.locator("html")).to_have_attribute("lang", "de")
                expect(page.locator("#page-title")).to_have_text("Deine Accounts, an einem Ort.")
                expect(page.locator("#category option:checked")).to_have_text("Finanzen")
                expect(page.locator("#account-rows tr")).to_have_count(2)
                expect(page.locator("#category")).to_have_value("Finance")
                page.locator("#category").select_option("")
                if args.screenshots_dir:
                    page.screenshot(path=str(args.screenshots_dir / "dashboard-de.png"), full_page=True)
                page.reload(wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", "de")
                expect(page.locator("#language")).to_have_value("de")
                page.locator("#language").select_option("en")
                expect(page.locator("#page-title")).to_have_text("Your accounts, in one place.")
                checks.append("Language switching preserves filters; choice remembered after reload")

                page.get_by_role("button",name="Review Steam",exact=True).click()
                expect(page.locator("#finish-account")).to_be_disabled()
                def check(index):
                    expect(page.locator("#checklist input").nth(index)).to_be_enabled()
                    page.locator("#checklist input").nth(index).check()
                    expect(page.locator("#checklist input").nth(index)).to_be_enabled()
                check(0)
                expect(page.locator("#detail-meta .chip")).to_have_text("Confirmed")
                expect(page.locator("#registered-email")).to_have_value("demo@example.invalid")
                expect(page.locator("#registered-email")).to_be_disabled()
                page.locator("#detail-language").select_option("de")
                expect(page.locator("#account-dialog")).to_be_visible()
                expect(page.locator("#checklist input").first).to_be_checked()
                expect(page.locator("#detail-meta .chip")).to_have_text("Bestätigt")
                expect(page.locator("#detail-meta")).to_contain_text("Von dir als vorhanden bestätigt")
                expect(page.locator("#registered-email")).to_have_value("demo@example.invalid")
                expect(page.locator("#checklist")).to_contain_text("Account geprüft und vorhanden")
                page.locator("#detail-language").select_option("en")
                expect(page.locator("#detail-meta .chip")).to_have_text("Confirmed")
                expect(page.locator("#checklist")).to_contain_text("I verified that this account exists")
                checks.append("Open checklist switches both ways without changing confirmation or sign-in address")
                page.locator("#close-dialog").click()

                page.locator('[data-view="bitwarden"]').click()
                expect(page.locator('#export-selection input[value="steam"]')).to_be_checked()
                expect(page.locator('#export-selection input[value="github"]')).to_have_count(0)
                expect(page.locator("#bitwarden-cli-button")).to_contain_text("unlocked Bitwarden CLI")
                expect(page.locator("#bitwarden-cli-button")).to_be_disabled()
                from argus_security.handoffs import reserve, finish
                attempt = reserve(store, 'instagram', 'demo@example.invalid')
                finish(store, attempt, 'uncertain')
                page.evaluate('refresh()')
                expect(page.locator('#handoff-review')).to_be_visible()
                expect(page.locator('#handoff-items')).to_contain_text(attempt['operation_id'])
                page.locator('#language').select_option('de')
                expect(page.locator('#handoff-review')).to_contain_text('Unterbrochene Übertragung prüfen')
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#handoff-items button').nth(1).click()
                expect(page.locator('#handoff-review')).to_be_hidden()
                page.locator('#language').select_option('en')
                checks.append('Ambiguous transfer review, explicit reconciliation and real-vault demo protection')
                page.locator('#export-selection input[value="discord"]').check()
                page.evaluate("refresh()")
                expect(page.locator('#export-selection input[value="discord"]')).to_be_checked()
                for checkbox in page.locator("#export-selection input").all():
                    checkbox.uncheck()
                page.locator("#export-button").click()
                expect(page.locator("#error")).to_contain_text("Select the accounts")
                page.locator("#language").select_option("de")
                expect(page.locator("#error")).to_be_visible()
                expect(page.locator("#error")).to_contain_text("Wähle zuerst die Accounts")
                page.locator("#language").select_option("en")
                expect(page.locator("#error")).to_contain_text("Select the accounts")
                page.locator('#export-selection input[value="steam"]').check()
                page.locator("#language").select_option("de")
                expect(page.locator('#export-selection input[value="steam"]')).to_be_checked()
                with page.expect_download() as download_info:
                    page.locator("#export-button").click()
                download_path = root / "metadata.json"
                download_info.value.save_as(download_path)
                exported = json.loads(download_path.read_text(encoding="utf-8"))
                assert len(exported["items"]) == 1
                assert exported["items"][0]["login"]["password"] == ""
                assert exported["items"][0]["login"]["username"] == "demo@example.invalid"
                assert "Beleg:" in exported["items"][0]["notes"]
                page.locator("#language").select_option("en")
                expect(page.locator('#export-selection input[value="steam"]')).to_be_checked()
                checks.append("Password-free Bitwarden download; assigned entries excluded")
                checks.append("German Bitwarden notes; export selection preserved across language changes")

                page.locator('[data-view="accounts"]').click()
                page.get_by_role("button",name="Review Steam",exact=True).click()
                for index in [1,2,3]:
                    check(index)
                expect(page.locator("#finish-account")).to_be_enabled()
                page.locator("#finish-account").click()
                expect(page.locator("#finish-account")).to_have_text("Already done")
                page.locator("#close-dialog").click()
                page.reload(wait_until="networkidle")
                expect(page.locator("#done-count")).to_have_text("2")
                checks.append("Checklists, manual confirmation and persistence after reload")

                raw = synthetic_mail("notify@tiktok.com", "Your account has been created", "Your account has been created. <img src='https://external.example/pixel'>")
                eml = root / "synthetic.eml"
                eml.write_bytes(raw)
                page.locator('[data-view="setup"]').click()
                held_requests = []
                held_once = [False]
                def hold_first_import(request_route):
                    if not held_once[0]:
                        held_once[0] = True
                        held_requests.append(request_route)
                    else:
                        request_route.continue_()
                page.route("**/api/import", hold_first_import)
                page.locator("#email-files").set_input_files(str(eml))
                expect(page.locator("#import-status")).to_contain_text("0/1 messages processed")
                page.locator("#language").select_option("de")
                expect(page.locator("#import-status")).to_contain_text("0/1 Nachrichten verarbeitet")
                expect(page.locator("#scan-badge")).to_have_text("Läuft")
                expect(page.locator("#email-files")).to_be_disabled()
                expect(page.locator("#cancel-import")).to_be_visible()
                expect(page.locator("#add-alias-button")).to_be_disabled()
                assert held_requests
                held_requests.pop().continue_()
                expect(page.locator("#import-status")).to_contain_text("1/1 Nachrichten verarbeitet")
                expect(page.locator("#scan-badge")).to_have_text("Abgeschlossen")
                page.locator("#language").select_option("en")
                page.unroute("**/api/import", hold_first_import)
                expect(page.locator("#import-status")).to_contain_text("1/1 messages processed")
                expect(page.locator("#found-count")).to_have_text("13")
                checks.append("Language switches during an active import without losing progress or releasing locks")
                checks.append("Entirely local EML import")

                zoom = root / "zoom.eml"
                zoom.write_bytes(synthetic_mail("notify@zoom.us","Your account has been created",""))
                invalid = root / "invalid.txt"
                invalid.write_text("synthetic non-mail", encoding="utf-8")
                page.locator("#email-files").set_input_files([str(eml),str(zoom),str(invalid)])
                expect(page.locator("#import-status")).to_contain_text("3/3 messages processed")
                expect(page.locator("#found-count")).to_have_text("14")
                expect(page.locator("#cancel-import")).not_to_be_visible()
                page.reload(wait_until="networkidle")
                expect(page.locator("#scan-summary")).to_contain_text("3/3 messages processed")
                expect(page.locator("#scan-badge")).to_have_text("Completed with gaps")
                checks.append("Batch import: duplicates, skipped file and statistics after reload")

                # Synthetic personal-profile scenario; never enter real addresses here.
                store.set_meta("demo",False)
                page.reload(wait_until="networkidle")
                page.locator('[data-view="setup"]').click()
                page.locator("#alias-email").fill("second@example.invalid")
                page.locator("#alias-owned").check()
                page.locator("#add-alias-button").click()
                expect(page.locator("#profile-email")).to_contain_text("second@example.invalid")
                expect(page.locator("#alias-message")).to_contain_text("Your checklists were preserved")
                expect(page.locator("#done-count")).to_have_text("2")
                checks.append("Own alias added; checklists and export selection preserved")

                page.set_viewport_size({"width":390,"height":844})
                expect(page.locator("#page-title")).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                if args.screenshots_dir:
                    page.screenshot(path=str(args.screenshots_dir / "mobile.png"), full_page=True)
                checks.append("Mobile layout without horizontal page overflow")
                page.locator("#language").select_option("de")
                expect(page.locator("#page-title")).to_have_text("Beginne mit deinem Postfach.")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                expect(page.locator("#alias-message")).to_contain_text("Deine Checklisten wurden erhalten")
                if args.screenshots_dir:
                    page.screenshot(path=str(args.screenshots_dir / "mobile-de.png"), full_page=True)
                checks.append("German mobile layout and translated alias/import messages")
                page.locator('[data-view="workflow"]').click()
                expect(page.locator('#worklist-items article')).to_have_count(2)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                if args.screenshots_dir:
                    page.screenshot(path=str(args.screenshots_dir / 'worklist-mobile-de.png'), full_page=True)
                checks.append('German security worklist fits the mobile viewport')

                for browser_locale, expected_language, blocked_storage in [("de-DE", "de", False),("fr-FR", "en", False),("de-DE", "de", True)]:
                    other = browser.new_context(locale=browser_locale)
                    other.route("**/*", route)
                    if blocked_storage:
                        other.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
                    localized_page = other.new_page()
                    localized_page.on("pageerror", lambda e: errors.append(str(e)))
                    localized_page.goto(server.url,wait_until="networkidle")
                    expect(localized_page.locator("html")).to_have_attribute("lang",expected_language)
                    expect(localized_page.locator("#found-count")).to_have_text("14")
                    expect(localized_page.locator("#language")).to_have_value(expected_language)
                    localized_page.locator("#language").select_option("en")
                    expect(localized_page.locator("#page-title")).to_have_text("Your accounts, in one place.")
                    other.close()
                checks.append("Independent browser language detection, unsupported-language fallback and blocked preference storage")

                # A preference saved before the ARGUS rename is honoured once and moved.
                legacy = browser.new_context(locale="en-GB")
                legacy.route("**/*", route)
                legacy.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('account-finder.language','de');sessionStorage.setItem('seeded','1');}")
                legacy_page = legacy.new_page()
                legacy_page.on("pageerror", lambda e: errors.append(str(e)))
                legacy_page.goto(server.url, wait_until="networkidle")
                expect(legacy_page.locator("html")).to_have_attribute("lang", "de")
                legacy_page.locator("#language").select_option("de")
                stored = legacy_page.evaluate("[localStorage.getItem('argus.language'), localStorage.getItem('account-finder.language')]")
                assert stored == ["de", None], stored
                legacy.close()
                checks.append("Pre-rename language preference is honoured and moved to the ARGUS key")
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
