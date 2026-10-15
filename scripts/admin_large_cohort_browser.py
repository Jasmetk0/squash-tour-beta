"""Real Chromium → production API → SQLite acceptance for a 1,000-player cohort.

Runs against the existing disposable browser smoke backend; never touches sources.
"""
import argparse
import json
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

# The World/country route may leave background queries active. Assert each
# action's own UI/API result instead of waiting for global network quietness,
# which can hang even after a successful production response.
def browser_click(page, name):
    page.get_by_role("button", name=name, exact=True).click()
from admin_world_country_checks import package_source_digest, verify_positive_world_country


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
    world_source = Path("config/world_packages/official_fax_world")
    world_source_initial_digest = package_source_digest(world_source)

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
        # A new browser context after restart defaults to Czech; pin the
        # acceptance language explicitly instead of assuming session storage.
        page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
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
                page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
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
                # Read actual applied Run World after explicit Save.
                world_fingerprint, _, _ = verify_positive_world_country(
                    page, run_url=run_url, api_url=f"http://127.0.0.1:{port}",
                    country_code="BOG", expected_fingerprint=None,
                    expected_player_ids=None,
                )
                assert package_source_digest(world_source) == world_source_initial_digest
                page.goto(run_url + "/players/generate")

                expect(page.get_by_role("heading", name="Generate players")).to_be_visible()
                page.get_by_label("Number of generated players").fill("1000")
                page.get_by_label("Player generation seed").fill("4207")
                page.get_by_label("InitialWorld audit reason").fill(
                    "Full 1000 player browser/SQLite acceptance")
                # Exercise the real new full-cohort exact quota path, not a mock
                # or weighted best-effort distribution. Remaining 970 must
                # come from countries other than the two fixed countries.
                page.get_by_role("button", name="Add country quota").click()
                quota_section = page.get_by_role("region", name="Exact country quotas")
                rows = quota_section.locator(".form-grid")
                first = rows.nth(0).locator("select").input_value()
                page.get_by_label(f"Exact quota {first}").fill("20")
                page.get_by_role("button", name="Add country quota").click()
                second = rows.nth(1).locator("select").input_value()
                assert first != second, "Quota editor must select distinct countries"
                page.get_by_label(f"Exact quota {second}").fill("10")
                expect(page.get_by_label("Country quota summary")).to_contain_text("970 automatic")
                with page.expect_response(
                    lambda response: response.url.endswith("/world-package/preview")
                    and response.request.method == "POST" and response.status == 200
                ) as response_info:
                    browser_click(page, "Preview generated players")
                reviewed = response_info.value.json()
                countries = Counter(p["country_code"] for p in reviewed["state"]["players"])
                assert len(reviewed["state"]["players"]) == 1000
                assert countries[first] == 20 and countries[second] == 10
                assert sum(n for code, n in countries.items()
                           if code not in (first, second)) == 970
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
                # The adoption status already exists before Save. Wait for the
                # actual committed Save receipt before capturing the read-only
                # Saved HEAD invariant; navigation must not abort the request.
                with page.expect_response(
                    lambda response: response.url.endswith("/initial-world/save")
                    and response.request.method == "POST" and response.status == 201
                ) as save_response:
                    browser_click(page, "Save InitialWorld revision")
                saved_initial = save_response.value.json()
                assert saved_initial["saved_revision"]["revision_id"]
                expect(page.get_by_text(
                    "First-season InitialWorld is saved and recoverable.", exact=False
                )).to_be_visible()
                expect(page.get_by_text("InitialWorld exists: 1000 players", exact=False)).to_be_visible()
                roster_country = max(countries, key=lambda c: (countries[c], c))
                assert countries[roster_country] > 25, "Country paging needs >25 saved players"
                roster_expected = sorted(
                    p["player_id"] for p in reviewed["state"]["players"]
                    if p["country_code"] == roster_country
                )
                # Actual canonical Saved HEAD country API (25 per page), real UI,
                # profile deep-link and opt-in future-player visibility.
                saved_world_fingerprint, country_player_ids, _ = verify_positive_world_country(
                    page, run_url=run_url, api_url=f"http://127.0.0.1:{port}",
                    country_code=roster_country, expected_fingerprint=world_fingerprint,
                    expected_player_ids=roster_expected,
                )
                assert saved_world_fingerprint == world_fingerprint
                assert country_player_ids == roster_expected
                assert package_source_digest(world_source) == world_source_initial_digest
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
                restarted_world_fingerprint, restarted_country_ids, _ = verify_positive_world_country(
                    page, run_url=run_url, api_url=f"http://127.0.0.1:{port}",
                    country_code=roster_country, expected_fingerprint=world_fingerprint,
                    expected_player_ids=roster_expected,
                )
                assert restarted_world_fingerprint == world_fingerprint
                assert restarted_country_ids == country_player_ids
                assert package_source_digest(world_source) == world_source_initial_digest
                assert not errors, errors
                (artifacts / "evidence.json").write_text(json.dumps({
                    "count": len(after), "unique": len(set(after)),
                    "exact_country_quotas": {first: 20, second: 10},
                    "automatic_remainder": 970,
                    "canonical_saved_inventory": True, "ranking_published": True,
                    "reopened_after_backend_restart": True,
                    "positive_world_country_browser": True,
                    "country_saved_roster_code": roster_country,
                    "country_saved_roster_count": len(roster_expected),
                    "country_saved_roster_exact_api_paging": True,
                    "country_saved_roster_persisted_restart": True,
                    "country_saved_profile_link": True,
                    "run_world_and_source_read_only": True,
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
