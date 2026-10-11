"""Real Chromium → production API → SQLite acceptance for a 1,000-player cohort.

Runs against the existing disposable browser smoke backend; never touches sources.
"""
import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from admin_first_tournament_smoke import browser_click, browser_settle


def acceptance(root: Path, *, port: int, base_url: str, chromium: str):
    if (root / "browser.sqlite").exists():
        raise ValueError("Large-cohort acceptance requires a new disposable database")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    root.mkdir(parents=True, exist_ok=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    server_log = (root / "server.log").open("w")
    errors = []

    def start():
        proc = subprocess.Popen(
            [sys.executable, "scripts/admin_first_tournament_smoke.py",
             "--serve", str(root), "--port", str(port)],
            stdout=server_log, stderr=server_log,
        )
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("Isolated backend exited; see server.log")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                    if response.status == 200:
                        return proc
            except OSError:
                time.sleep(0.15)
        proc.terminate()
        proc.wait(timeout=15)
        raise RuntimeError("Backend failed startup health probe")

    def open_page(browser):
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(120000)
        page.smoke_pending_requests = set()
        page.on("request", lambda req: page.smoke_pending_requests.add(req))
        page.on("requestfinished", lambda req: page.smoke_pending_requests.discard(req))
        page.on("requestfailed", lambda req: page.smoke_pending_requests.discard(req))
        page.on("dialog", lambda dialog: dialog.accept())
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: errors.append(
            f"HTTP {response.status} {response.url}"
        ) if response.status >= 500 else None)
        return context, page

    def inventory(page, run_url):
        page.goto(run_url + "/players")
        status = page.get_by_role("status").filter(has_text="Total matching players")
        expect(status).to_contain_text("1,000")
        ids = []
        for page_index in range(20):
            expect(page.get_by_text(f"Page {page_index + 1} / 20")).to_be_visible()
            rows = page.locator(".table-responsive tbody tr")
            expect(rows).to_have_count(50)
            ids.extend([
                item.inner_text().strip().removeprefix("·").strip()
                for item in rows.locator("small").all()
            ])
            if page_index < 19:
                page.get_by_role("button", name="Next →", exact=True).click()
        assert len(ids) == len(set(ids)) == 1000, "Canonical inventory lost/duplicated IDs"
        return ids

    process = start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context, page = open_page(browser)
            try:
                page.goto(base_url + "/admin/runs/new")
                page.get_by_label("Unique Run name").fill("Large Cohort Browser Acceptance")
                browser_click(page, "Create isolated Run")
                expect(page.get_by_role("heading", name="World and Calendar copies")).to_be_visible()
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
                run_url = page.url
                page.get_by_label("Source kind").select_option("world")
                page.get_by_label("World source").select_option("official_fax_world")
                browser_click(page, "Preview copy")
                page.get_by_label("Confirm source copy").check()
                browser_click(page, "Confirm copy to Working Draft")
                page.get_by_label("Confirm save revision").check()
                browser_click(page, "Save copied packages")
                expect(page.get_by_text(
                    "Current Run copy: Present. Draft: clean.", exact=False
                )).to_be_visible()

                page.get_by_role("link", name="Generate players →").click()
                expect(page.get_by_role("heading", name="Generate players")).to_be_visible()
                page.get_by_label("Number of generated players").fill("1000")
                page.get_by_label("Player generation seed").fill("4207")
                page.get_by_label("InitialWorld audit reason").fill(
                    "Full 1000 player browser/SQLite acceptance")
                browser_click(page, "Preview generated players")
                expect(page.get_by_text("Review 1000 players")).to_be_visible()
                inspector = page.get_by_role("region", name="Complete generated player preview")
                expect(inspector.locator("tbody tr")).to_have_count(50)
                expect(page.get_by_text("Page 1 / 20", exact=False)).to_be_visible()
                page.get_by_role("button", name="Next preview page →").click()
                expect(page.get_by_text("Page 2 / 20", exact=False)).to_be_visible()
                expect(inspector.locator("tbody tr")).to_have_count(50)
                assert not page.get_by_text(
                    "InitialWorld exists: 1000 players", exact=False
                ).count(), "Preview mutated persisted Run"
                page.get_by_label("Approve InitialWorld adoption").check()
                browser_click(page, "Adopt generated players")
                page.get_by_label("Approve InitialWorld revision save").check()
                browser_click(page, "Save InitialWorld revision")
                expect(page.get_by_text("InitialWorld exists: 1000 players", exact=False)).to_be_visible()
                before = inventory(page, run_url)
                # The existing full ranking workflow exercises the production
                # ranking boundary against all 1,000 saved players.
                page.goto(run_url)
                page.get_by_label("Initial ranking audit reason").fill(
                    "1000-player ranking continuation")
                browser_click(page, "Preview initial ranking")
                page.get_by_label("Approve initial ranking preparation").check()
                browser_click(page, "Confirm initial ranking")
                page.get_by_label("Approve initial ranking save").check()
                browser_click(page, "Save initial ranking revision")
                browser_click(page, "Review initial publication")
                page.get_by_label("Approve initial publication").check()
                browser_click(page, "Publish initial ranking")
                browser_click(page, "Review unsaved published ranking state")
                page.get_by_label("Approve published ranking revision save").check()
                browser_click(page, "Save published ranking revision")
                expect(page.get_by_text("Viewer readback verified:", exact=False)).to_be_visible()
                before_ranked = inventory(page, run_url)
                assert set(before_ranked) == set(before)
                page.screenshot(path=str(artifacts / "large-cohort-before-restart.png"), full_page=True)
                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                process.terminate()
                process.wait(timeout=25)
                process = start()
                context, page = open_page(browser)
                after = inventory(page, run_url)
                assert after == before_ranked, "Saved player identities/order changed after restart"
                assert not errors, errors
                (artifacts / "evidence.json").write_text(json.dumps({
                    "count": len(after), "unique": len(set(after)),
                    "canonical_saved_inventory": True, "ranking_published": True,
                    "reopened_after_backend_restart": True,
                    "same_player_ids_and_order": True, "errors": errors,
                    "run_url": run_url,
                }, indent=2))
                print("1000-PLAYER BROWSER/SQLITE ACCEPTANCE PASSED", flush=True)
            except Exception:
                page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
                (artifacts / "failure.txt").write_text(page.locator("body").inner_text())
                raise
            finally:
                context.tracing.stop(path=str(artifacts / "after-restart.zip"))
                context.close()
                browser.close()
    finally:
        process.terminate()
        process.wait(timeout=25)
        server_log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8018)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    acceptance(args.acceptance.resolve(), port=args.port,
               base_url=args.base_url, chromium=args.chromium)
