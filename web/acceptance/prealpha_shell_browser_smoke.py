"""Real Chromium smoke for pre-alpha shell with production FastAPI and disposable SQLite.

The backend/frontend must already be running locally. No simulated UI data is injected.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    parser.add_argument("--artifacts", type=Path, default=Path("work/prealpha-shell-browser"))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    evidence: dict[str, object] = {}
    chrome = os.environ.get("CHROME_BIN") or "/usr/bin/google-chrome"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chrome,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(viewport={"width": 1440, "height": 980})
        page = context.new_page()
        page.set_default_timeout(30000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 500
            else None,
        )
        # Unsaved-context safeguard prompts are tested; accept a clean Run exit.
        dialogs: list[str] = []

        def accept_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.accept()

        page.on("dialog", accept_dialog)
        try:
            page.goto(base + "/")
            expect(page.get_by_role("heading", name="Squash Engine – Domů")).to_be_visible()
            assert page.url.rstrip("/").endswith("/admin"), page.url
            assert page.get_by_role("combobox", name="Admin active Run").count() == 0
            assert page.get_by_role("combobox", name="Admin active Branch").count() == 0
            assert page.get_by_label("Admin view time").count() == 0
            assert page.locator(".app-shell--admin").count() == 1
            assert page.evaluate(
                "getComputedStyle(document.querySelector('.app-shell--admin')).backgroundColor"
            ) == "rgb(11, 17, 32)"
            expect(
                page.get_by_role("navigation", name="Global Admin navigation").get_by_role(
                    "link", name="Testovací laboratoř"
                )
            ).to_be_visible()
            page.screenshot(path=str(artifacts / "01-global-home.png"), full_page=True)
            evidence["neutral_start"] = True

            page.get_by_role("navigation", name="Global Admin navigation").get_by_role(
                "link", name="Testovací laboratoř"
            ).click()
            expect(page.get_by_role("heading", name="Testovací laboratoř")).to_be_visible()
            for module, suffix in (
                ("Match Test Lab", "match"),
                ("Tournament Test Lab", "tournament"),
                ("Player Test Lab", "player"),
            ):
                expect(page.get_by_role("heading", name=module)).to_be_visible()
                expect(page.locator(f'a[href="/admin/labs/{suffix}"]')).to_be_visible()
            assert page.get_by_role("combobox", name="Admin active Run").count() == 0
            evidence["labs_without_run"] = 3

            page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
            expect(page.get_by_role("heading", name="Test Lab", exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_role("heading", name="Test Lab", exact=True)).to_be_visible()
            assert page.get_by_role("combobox", name="Language / Jazyk").input_value() == "en"
            evidence["language_persisted"] = "en"

            # Browse actual registered World packages, never synthetic hybrids.
            page.goto(base + "/admin/packages")
            expect(page.get_by_role("heading", name="Packages", exact=True)).to_be_visible()
            assert page.get_by_role("combobox", name="Admin active Run").count() == 0
            page.get_by_role("link", name="All packages").click()
            expect(page.get_by_role("heading", name="All packages", exact=True)).to_be_visible()
            worlds_response = page.request.get(args.api_url + "/world/packages")
            assert worlds_response.ok, worlds_response.text()
            worlds = worlds_response.json()["packages"]
            expect(page.locator(".package-index-row")).to_have_count(len({w["world_id"] for w in worlds}))
            if worlds:
                world = worlds[0]
                page.locator(".package-index-row").filter(has_text=world["name"]).first.get_by_role("link", name="Details").click()
                expect(page.get_by_role("heading", name=world["name"])).to_be_visible()
                page.get_by_role("button", name="Contents").click()
                expect(page.get_by_role("heading", name="Countries", exact=False)).to_be_visible()
                page.get_by_role("button", name="Validation").click()
                expect(page.get_by_role("heading", name="Actual validation results")).to_be_visible()
                evidence["world_package_detail"] = world["world_id"]
            page.goto(base + "/admin/packages/category/hybrid")
            expect(page.get_by_role("heading", name="Hybrid", exact=True)).to_be_visible()
            expect(page.get_by_text("No independent registry for this category yet.")).to_be_visible()
            expect(page.locator(".package-index-row")).to_have_count(0)
            evidence["packages_registered"] = len({w["world_id"] for w in worlds})

            page.goto(base + "/admin/runs/new")
            expect(page.get_by_role("heading", name="Create test Run")).to_be_visible()
            page.get_by_label("Unique Run name").fill("Prealpha Shell Browser Run")
            page.get_by_role("button", name="Create isolated Run").click()
            expect(page.get_by_role("combobox", name="Admin active Run")).to_be_visible()
            expect(page.get_by_role("combobox", name="Admin active Branch")).to_be_visible()
            expect(page.get_by_label("Admin view time")).to_be_visible()
            assert "/admin/runs/" in page.url and not page.url.endswith("/new"), page.url
            evidence["created_run_url"] = page.url
            run_id = page.url.split("/admin/runs/", 1)[1].split("/", 1)[0].split("?", 1)[0]
            branch_response = page.request.get(args.api_url + "/run-branches", params={"run_id": run_id})
            assert branch_response.ok, branch_response.text()
            source_branch = branch_response.json()["run_branches"][0]
            assert source_branch["saved_head_revision_id"], source_branch
            fork_response = page.request.post(
                args.api_url + "/run-containers/" + run_id + "/branches",
                data={
                    "source_branch_id": source_branch["branch_id"],
                    "source_saved_revision_id": source_branch["saved_head_revision_id"],
                    "display_name": "Browser Alternative",
                },
            )
            assert fork_response.status == 201, fork_response.text()
            created_branch = fork_response.json()
            assert created_branch["branch_id"] != source_branch["branch_id"]
            expect(
                page.get_by_role("navigation", name="Run Admin navigation").get_by_role(
                    "link", name="History & Branches"
                )
            ).to_be_visible()
            expect(
                page.get_by_role("navigation", name="Run management navigation").get_by_role(
                    "link", name="Run Management"
                )
            ).to_be_visible()
            expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
            expect(page.get_by_role("heading", name="Needs attention")).to_be_visible()
            expect(page.get_by_role("heading", name="World activity")).to_be_visible()
            tracks = page.locator(".run-home-progress__track")
            expect(tracks).to_have_count(2)
            expect(tracks.nth(0).locator("span")).to_have_count(50)
            expect(tracks.nth(1).locator("span")).to_have_count(61)
            assert page.get_by_text("Hratelné zápasy: 0").count() == 0
            expect(page.get_by_role("heading", name="Ranking movement · published weeks")).to_be_visible()
            expect(page.get_by_text("This Branch has no saved Official Ranking publication yet.")).to_be_visible()
            evidence["empty_branch_ranking_not_fabricated"] = True
            evidence["run_home_canonical_segments"] = [50, 61]
            page.screenshot(path=str(artifacts / "02-created-run.png"), full_page=True)

            # Exercise actual API-backed Runs expansion and cross-page Admin Branch selection.
            page.goto(base + "/admin/runs")
            expect(page.get_by_role("heading", name="Runs", exact=True)).to_be_visible()
            row = page.locator(".runs-canonical-row").filter(has_text="Prealpha Shell Browser Run")
            expect(row).to_have_count(1)
            row.get_by_role("button", name="Branches +").click()
            alternative = row.locator(".runs-canonical-branch").filter(has_text="Browser Alternative")
            expect(alternative).to_be_visible()
            expect(alternative.get_by_text("Time unavailable")).to_be_visible()
            alternative.get_by_role("link", name="Open").click()
            branch_selector = page.get_by_role("combobox", name="Admin active Branch")
            expect(branch_selector).to_have_value(created_branch["branch_id"])
            page.reload()
            expect(branch_selector).to_have_value(created_branch["branch_id"])
            unchanged = page.request.get(args.api_url + "/run-containers/" + run_id)
            assert unchanged.ok and unchanged.json()["viewer_branch_id"] == source_branch["branch_id"]
            evidence["chosen_admin_branch_after_reload"] = created_branch["branch_id"]
            evidence["viewer_branch_preserved"] = True

            # Sidebar preferences survive reload and hover expansion overlays the content.
            page.get_by_role("button", name="Unpin sidebar").click()
            page.get_by_role("button", name="Collapse sidebar").click()
            page.reload()
            expect(page.get_by_role("button", name="Expand sidebar")).to_be_visible()
            before = page.locator("main").bounding_box()
            page.locator(".side-nav").hover()
            after = page.locator("main").bounding_box()
            assert before and after and abs(before["x"] - after["x"]) < 1, (before, after)
            evidence["sidebar_hover_without_shift"] = True
            page.get_by_role("button", name="Expand sidebar").click()
            evidence["sidebar_preferences_persisted"] = True

            # The new canonical player detail must not fabricate an identity for
            # a legitimate empty Run; the selected Run and Branch remain intact.
            page.goto(evidence["created_run_url"] + "/people/no-saved-player")
            expect(page.get_by_role("heading", name="no-saved-player")).to_be_visible()
            expect(page.get_by_text("No verified player identity in this Saved Revision. No sporting information is shown.")).to_be_visible()
            assert page.get_by_text("This is not yet a full career profile.", exact=False).count() == 0
            evidence["missing_saved_player_identity_no_fallback"] = True
            page.get_by_role("link", name="← Back to Run Home").click()
            expect(page.get_by_role("heading", name="World activity")).to_be_visible()


            page.get_by_role("navigation", name="Run management navigation").get_by_role(
                "link", name="Run Management"
            ).click()
            expect(page.get_by_role("heading", name="Run Management")).to_be_visible()
            expect(page.get_by_role("heading", name="World and Calendar copies")).to_be_visible()
            evidence["run_management"] = True
            page.screenshot(path=str(artifacts / "03-run-management.png"), full_page=True)

            page.get_by_role("link", name="Squash Engine global Home").click()
            expect(page.get_by_role("heading", name="Squash Engine Home")).to_be_visible()
            assert page.get_by_role("combobox", name="Admin active Run").count() == 0
            assert page.get_by_role("combobox", name="Admin active Branch").count() == 0
            expect(page.get_by_text("Prealpha Shell Browser Run")).to_be_visible()
            assert dialogs, "Leaving a Run must activate the navigation safeguard"
            evidence["returned_global_and_explicit_recent_run"] = True

            page.get_by_role("link", name="Open Run →").first.click()
            expect(page.get_by_role("combobox", name="Admin active Run")).to_be_visible()
            evidence["explicit_reopen"] = True
            assert not errors, errors
            evidence["browser_errors"] = errors
            print("PREALPHA_SHELL_BROWSER_PASSED", json.dumps(evidence), flush=True)
        except Exception:
            page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
            (artifacts / "failure.txt").write_text(page.locator("body").inner_text())
            raise
        finally:
            (artifacts / "evidence.json").write_text(
                json.dumps({"evidence": evidence, "errors": errors, "dialogs": dialogs}, indent=2)
            )
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
