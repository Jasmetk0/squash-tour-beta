"""Real Chromium smoke for pre-alpha shell with production FastAPI and disposable SQLite.

The backend/frontend must already be running locally. No simulated UI data is injected.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from calendar_standalone_match_browser_check import exercise_calendar_match
from calendar_opening_knockout_browser_check import exercise_calendar_knockout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    parser.add_argument("--artifacts", type=Path, default=Path("work/prealpha-shell-browser"))
    parser.add_argument("--population-size", type=int, choices=(64, 1000), default=64,
                        help="64 for shell contracts; 1000 for full checkpoint scale")
    args = parser.parse_args()
    population_size = args.population_size
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
        expect.set_options(timeout=30000)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: errors.append(f"HTTP {response.status}: {response.url}")
            if response.status >= 500
            else None,
        )
        # Unsaved-context safeguard prompts are tested; accept a clean Run exit.
        dialogs: list[str] = []
        dialog_policy = {"accept": True}

        def accept_dialog(dialog):
            dialogs.append(dialog.message)
            if dialog_policy["accept"]:
                dialog.accept()
            else:
                dialog.dismiss()

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
            expect(page.get_by_role("heading", name="Create Run", exact=True)).to_be_visible()
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

            # History & Branches v80: real saved-revision fork, map SELECT is
            # read-only and its reachable ancestor remains owned by source.
            page.goto(base + "/admin/runs/" + run_id + "/branches")
            lineage = page.get_by_label("Saved Branch lineage map")
            expect(lineage).to_be_visible()
            expect(lineage.get_by_role("button", name="View Branch Browser Alternative")).to_be_visible()
            assert source_branch["saved_head_revision_id"] in lineage.inner_text()
            expect(lineage.get_by_text("Saved fork from", exact=False)).to_be_visible()
            active_before = page.get_by_role(
                "combobox", name="Admin active Branch"
            ).input_value()
            lineage.get_by_role("button", name="View Branch Browser Alternative").click()
            expect(page.get_by_role("table", name="Saved Revision history table")).to_be_visible()
            table = page.get_by_role("table", name="Saved Revision history table")
            expect(table.get_by_text(
                source_branch["saved_head_revision_id"], exact=True
            ).first).to_be_visible()
            # The shared ancestor is visible as a genuine reachable revision,
            # not rebound to the fork as original owner.
            assert source_branch["branch_id"] in table.inner_text()
            assert "Shared ancestor" in table.inner_text()
            table.get_by_role("button", name="Revision", exact=False).first.click()
            inspector = page.get_by_label("Saved Revision read-only preview")
            expect(inspector).to_be_visible()
            assert "Read-only preview" in inspector.inner_text()
            inspector.get_by_role("button", name="Close detail").click()
            expect(inspector).to_have_count(0)
            assert page.get_by_role(
                "combobox", name="Admin active Branch"
            ).input_value() == active_before
            after_map = page.request.get(
                args.api_url + "/run-branches", params={"run_id": run_id}
            )
            assert after_map.ok
            assert next(b["saved_head_revision_id"]
                        for b in after_map.json()["run_branches"]
                        if b["branch_id"] == source_branch["branch_id"]) == source_branch["saved_head_revision_id"]
            evidence["history_lineage_browser_read_only"] = True
            page.screenshot(path=str(artifacts / "02b-history-lineage.png"), full_page=True)

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

            # Read-only Run exploration is not an unsaved edit, including filters.
            page.goto(base + "/admin/runs/" + run_id + "/players?branch=" + created_branch["branch_id"])
            expect(page.get_by_role("combobox", name="Admin active Branch")).to_have_value(created_branch["branch_id"])
            expect(page.get_by_role("heading", name="Players", exact=True)).to_be_visible()
            # Verify a genuinely empty Saved Revision, not legacy Run roster.
            expected_head = page.request.get(args.api_url + "/run-containers/" + run_id)
            assert expected_head.ok, expected_head.text()
            saved = page.request.get(
                args.api_url + "/admin/runs/" + run_id + "/branches/"
                + created_branch["branch_id"] + "/saved-players"
            )
            assert saved.status == 409 and saved.json()["detail"]["code"] == "saved_players_inventory_unavailable", saved.text()
            # The fork still points to shared pre-fork ancestry. Until its own
            # materialized Saved HEAD exists, current Branch-owned sporting
            # reads fail closed (never borrow another Branch's authority).
            expect(page.get_by_role("alert").filter(has_text="Saved Players HEAD belongs to another Run / Branch")).to_be_visible()
            # The original owned empty Branch is a genuine empty inventory.
            owned = page.request.get(
                args.api_url + "/admin/runs/" + run_id + "/branches/"
                + source_branch["branch_id"] + "/saved-players"
            )
            assert owned.ok and owned.json()["total"] == 0, owned.text()
            assert owned.json()["source"] == "selected_branch_saved_revision"
            page.get_by_role("textbox", name="Player search").fill("browser-filter-only")
            page.get_by_role("textbox", name="Player country").fill("CZE")
            evidence["canonical_saved_players_empty_and_shared_fork_fail_closed"] = True
            assert page.locator(".app-shell--admin").get_attribute("data-run-form-edited") is None
            page.get_by_role("link", name="Squash Engine global Home").click()
            expect(page.get_by_role("heading", name="Squash Engine Home")).to_be_visible()
            assert not dialogs, "Read-only Run filters must not prompt on clean exit"
            evidence["clean_run_exit_no_unsaved_warning"] = True

            # Actual unsaved source form values must still guard the Run exit.
            page.goto(base + "/admin/runs/" + run_id + "/manage")
            expect(page.get_by_role("heading", name="Run Management")).to_be_visible()
            # The navigation guard is bound to the asynchronously selected Branch.
            # Await hydration before generating local unsaved-form evidence.
            expect(page.get_by_role("combobox", name="Admin active Branch")).not_to_have_value("")
            page.get_by_role("combobox", name="Source kind").select_option("calendar")
            page.get_by_role("textbox", name="Calendar source season").fill("2008-2009")
            expect(page.locator(".app-shell--admin")).to_have_attribute("data-run-form-edited", "true")

            # The Branch dropdown is an imperative context change: cancelling
            # keeps both its selected Branch and the edited source values.
            branch_selector = page.get_by_role("combobox", name="Admin active Branch")
            # The Run/Branch provider hydrates asynchronously after a direct
            # browser navigation. Do not capture an empty loading selection as
            # the authoritative initial Branch for the cancel/approve guard.
            expect(branch_selector).not_to_have_value("")
            initial_branch = branch_selector.input_value()
            assert initial_branch in {
                source_branch["branch_id"], created_branch["branch_id"]
            }, initial_branch
            requested_branch = (
                created_branch["branch_id"]
                if initial_branch != created_branch["branch_id"]
                else source_branch["branch_id"]
            )
            dialog_policy["accept"] = False
            branch_selector.select_option(requested_branch)
            expect(branch_selector).to_have_value(initial_branch)
            expect(page.get_by_role("textbox", name="Calendar source season")).to_have_value("2008-2009")
            assert len(dialogs) == 1 and "Switch Branch" in dialogs[0], dialogs

            # Explicitly approving the very same transition changes only the
            # Admin Branch; its Saved Revision / Viewer pointer is unchanged.
            dialog_policy["accept"] = True
            branch_selector.select_option(requested_branch)
            expect(branch_selector).to_have_value(requested_branch)
            assert len(dialogs) == 2, "A programmatic Branch selection must confirm exactly once"
            evidence["imperative_branch_guard"] = "cancel preserved; approve switched once"
            page.get_by_role("combobox", name="Source kind").select_option("calendar")
            page.get_by_role("textbox", name="Calendar source season").fill("2008-2009")
            expect(page.locator(".app-shell--admin")).to_have_attribute("data-run-form-edited", "true")
            page.get_by_role("link", name="Squash Engine global Home").click()
            expect(page.get_by_role("heading", name="Squash Engine Home")).to_be_visible()
            assert len(dialogs) == 3 and "unsaved Working Draft" in dialogs[2], dialogs
            evidence["real_unsaved_run_form_warning"] = True

            # Actual browser Back must not discard edited Run form values.
            page.goto(base + "/admin/runs/" + run_id)
            page.get_by_role("navigation", name="Run management navigation").get_by_role(
                "link", name="Run Management"
            ).click()
            expect(page.get_by_role("heading", name="Run Management")).to_be_visible()
            page.get_by_role("combobox", name="Source kind").select_option("calendar")
            page.get_by_role("textbox", name="Calendar source season").fill("2012-2013")
            dialog_policy["accept"] = False
            before = len(dialogs)
            with page.expect_event("dialog"):
                page.evaluate("window.history.back()")
            expect(page.get_by_role("heading", name="Run Management")).to_be_visible()
            expect(page.get_by_role("textbox", name="Calendar source season")).to_have_value("2012-2013")
            assert len(dialogs) == before + 1, dialogs
            dialog_policy["accept"] = True
            with page.expect_event("dialog"):
                page.evaluate("window.history.back()")
            expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
            assert len(dialogs) == before + 2, dialogs
            evidence["run_history_cancel_accept"] = True

            # World route must truthfully report missing World on the genuinely
            # empty, saved source Branch, with no simulated countries.
            page.goto(base + "/admin/runs/" + run_id
                      + "/world?branch=" + source_branch["branch_id"])
            expect(page.get_by_role("heading", name="Run World")).to_be_visible()
            expect(page.get_by_role("heading", name="No World assigned yet")).to_be_visible()
            assert page.get_by_role("table", name="Run World countries").count() == 0
            assert page.locator(".app-shell--admin").get_attribute("data-run-form-edited") is None
            evidence["world_empty_run_no_fake_countries"] = True

            # Selectively apply exactly one real World source entity into the
            # alternative Branch, then Save; unselected entities never appear.
            assert worlds, "This acceptance requires a real World source registry"
            world_id = worlds[0]["world_id"]
            page.goto(base + "/admin/packages/world/" + world_id)
            page.get_by_role("link", name="Apply to Run — select contents").click()
            expect(page.get_by_role("heading", name="Apply World Package to Run")).to_be_visible()
            page.get_by_role("combobox", name="Target Run").select_option(run_id)
            page.get_by_role("combobox", name="Target Branch").select_option(created_branch["branch_id"])
            checkboxes = page.locator(".package-apply-items input[type=checkbox]")
            expect(checkboxes.first).to_be_visible()
            checkboxes.first.check()
            expect(page.get_by_text("1 selected", exact=False)).to_be_visible()
            expect(page.locator(".package-apply-diff")).to_have_count(1)
            page.get_by_role("checkbox", name="I reviewed the exact selection, changes and target Branch.").check()
            page.get_by_role("button", name="Confirm into Working Draft").click()
            expect(page.get_by_text("Content staged in Working Draft", exact=False)).to_be_visible()
            state_url = (
                args.api_url + "/admin/runs/" + run_id + "/branches/"
                + created_branch["branch_id"] + "/packages"
            )
            staged = page.request.get(state_url)
            assert staged.ok and len(staged.json()["state"]["entities"]) == 1, staged.text()

            # Global Apply is outside Run scope but its local Save context is
            # protected. Rejecting navigation and target changes must keep it.
            dialog_policy["accept"] = False
            before = len(dialogs)
            with page.expect_event("dialog"):
                page.locator(".package-apply > p > a").first.click()
            expect(page.get_by_role("heading", name="Apply World Package to Run")).to_be_visible()
            expect(page.get_by_role("button", name="Save revision")).to_be_visible()
            assert len(dialogs) == before + 1, dialogs
            with page.expect_event("dialog"):
                page.get_by_role("combobox", name="Target Branch").select_option(source_branch["branch_id"])
            expect(page.get_by_role("combobox", name="Target Branch")).to_have_value(created_branch["branch_id"])
            assert len(dialogs) == before + 2, dialogs

            # Accept leaving. The server draft survives a full route exit
            # and must be explicitly inspected/reopened before manual Save.
            dialog_policy["accept"] = True
            with page.expect_event("dialog"):
                page.locator(".package-apply > p > a").first.click()
            expect(page.get_by_role("heading", name=worlds[0]["name"])).to_be_visible()
            assert len(dialogs) == before + 3, dialogs
            reopened_state = page.request.get(state_url)
            assert reopened_state.ok and reopened_state.json()["fingerprint"] == staged.json()["fingerprint"]
            page.get_by_role("link", name="Apply to Run — select contents").click()
            page.get_by_role("combobox", name="Target Run").select_option(run_id)
            page.get_by_role("combobox", name="Target Branch").select_option(created_branch["branch_id"])
            expect(page.get_by_role("button", name="Reopen Working Draft for manual Save")).to_be_enabled()
            page.get_by_role("button", name="Reopen Working Draft for manual Save").click()
            expect(page.get_by_text("Reopened Working Draft may contain other staged changes", exact=False)).to_be_visible()
            page.get_by_role("button", name="Save revision").click()
            expect(page.get_by_text("New Saved Revision saved.")).to_be_visible()
            page.reload()
            persisted = page.request.get(state_url)
            assert persisted.ok and persisted.json()["fingerprint"] == staged.json()["fingerprint"]
            evidence["selective_world_saved_one_entity"] = world_id
            evidence["global_apply_guard_and_draft_recovery"] = True
            page.screenshot(path=str(artifacts / "04-selective-world-saved.png"), full_page=True)

            # Only an EXPLICIT Save after the fork produces two distinct
            # immutable reachable revisions. Branch creation alone shares one head.
            compare_branch_response = page.request.get(
                args.api_url + "/run-branches", params={"run_id": run_id}
            )
            assert compare_branch_response.ok
            new_compare_head = next(
                b["saved_head_revision_id"]
                for b in compare_branch_response.json()["run_branches"]
                if b["branch_id"] == created_branch["branch_id"]
            )
            assert new_compare_head != source_branch["saved_head_revision_id"]
            # Dedicated master-v80 read-only Compare States A/B, reusing the
            # existing REST comparison and both exact reachable Saved identities.
            compared_before = page.request.get(
                args.api_url + "/run-containers/" + run_id + "/branches/"
                + created_branch["branch_id"] + "/saved-revisions/compare",
                params={
                    "from_revision_id": source_branch["saved_head_revision_id"],
                    "to_revision_id": new_compare_head,
                },
            )
            assert compared_before.ok, compared_before.text()
            compared_data = compared_before.json()
            assert compared_data["branch_id"] == created_branch["branch_id"]
            assert compared_data["from_revision"]["revision_id"] == source_branch["saved_head_revision_id"]
            assert compared_data["to_revision"]["revision_id"] == new_compare_head
            page.goto(
                base + "/admin/runs/" + run_id + "/branches/compare?branch="
                + created_branch["branch_id"] + "&a="
                + source_branch["saved_head_revision_id"] + "&b="
                + new_compare_head
            )
            compare_branch_control = page.get_by_role(
                "combobox", name="Admin active Branch"
            )
            expect(compare_branch_control).not_to_have_value("")
            compare_admin_branch_before = compare_branch_control.input_value()
            selection = page.get_by_label("Compare Saved Revision selection")
            expect(selection.get_by_role("combobox", name="Compare state A")).to_have_value(
                source_branch["saved_head_revision_id"]
            )
            expect(selection.get_by_role("combobox", name="Compare state B")).to_have_value(
                new_compare_head
            )
            compared_panel = page.get_by_label("Compare Saved Revision results")
            expect(compared_panel.get_by_label("Compare Saved Revision totals")).to_be_visible()
            assert compared_data["run_id"] == run_id
            assert source_branch["branch_id"] in compared_panel.inner_text()
            # Independent Season/Edition A/B rows are obtained from each
            # immutable Saved Calendar, not inferred from calendar component hashes.
            canonical_a = page.request.get(
                args.api_url + "/admin/runs/" + run_id + "/branches/"
                + created_branch["branch_id"] + "/tour/calendar",
                params={"revision_id": source_branch["saved_head_revision_id"], "season_index": 0},
            )
            canonical_b = page.request.get(
                args.api_url + "/admin/runs/" + run_id + "/branches/"
                + created_branch["branch_id"] + "/tour/calendar",
                params={"revision_id": new_compare_head, "season_index": 0},
            )
            assert canonical_a.ok and canonical_b.ok, (
                canonical_a.text(), canonical_b.text()
            )
            calendars = [canonical_a.json(), canonical_b.json()]
            assert calendars[0]["saved_revision_id"] == source_branch["saved_head_revision_id"]
            assert calendars[0]["revision_branch_id"] == source_branch["branch_id"]
            assert calendars[1]["saved_revision_id"] == new_compare_head
            assert calendars[1]["revision_branch_id"] == created_branch["branch_id"]
            edition_compare = page.get_by_label("Compare saved season Editions")
            expect(edition_compare.get_by_label("Compare saved Edition totals")).to_be_visible()
            assert all(calendar["season_index"] == 0 for calendar in calendars)
            assert all(calendar["edition_count"] == len(calendar["editions"]) for calendar in calendars)
            assert "parent" not in edition_compare.get_by_role(
                "combobox", name="Compare Edition season"
            ).input_value()
            edition_compare.get_by_role(
                "combobox", name="Compare Edition display filter"
            ).select_option("all")
            # The compared Run is intentionally empty of tournament packages:
            # both real snapshots must report 0, not made-up differences.
            assert sum(calendar["edition_count"] for calendar in calendars) == 0
            expect(edition_compare.get_by_text(
                "No Saved Editions exist in either selected revision for this season."
            )).to_be_visible()
            edition_compare.get_by_role(
                "combobox", name="Compare Edition season"
            ).select_option("1")
            expect(edition_compare.get_by_label("Compare saved Edition totals")).to_be_visible()
            edition_compare.get_by_role(
                "combobox", name="Compare Edition season"
            ).select_option("0")
            evidence["compare_saved_calendar_ab_exact_owner_and_empty_season"] = True
            compared_panel.get_by_role("combobox", name="Compare display filter").select_option("all")
            compared_panel.get_by_role("button", name="Inspect state A read-only").click()
            detail = page.get_by_label("Compare read-only detail")
            expect(detail).to_be_visible()
            expect(detail.get_by_text("hash", exact=False).first).to_be_visible()
            assert source_branch["saved_head_revision_id"] in detail.inner_text()
            detail.get_by_role("button", name="Close Compare detail").click()
            expect(detail).to_have_count(0)
            unchanged_branch = page.request.get(
                args.api_url + "/run-branches", params={"run_id": run_id}
            )
            assert unchanged_branch.ok
            assert next(
                b["saved_head_revision_id"] for b in unchanged_branch.json()["run_branches"]
                if b["branch_id"] == created_branch["branch_id"]
            ) == new_compare_head
            assert page.get_by_role(
                "combobox", name="Admin active Branch"
            ).input_value() == compare_admin_branch_before
            evidence["history_saved_compare_ab_read_only"] = True
            page.screenshot(path=str(artifacts / "02c-saved-compare-ab.png"), full_page=True)


            # An intentionally partial copied World (only one source entity)
            # must not masquerade as a complete country roster. This is a
            # genuinely saved partial Run-owned copy, not a mocked API response.
            page.goto(base + "/admin/runs/" + run_id
                      + "/world?branch=" + created_branch["branch_id"])
            expect(page.get_by_role("heading", name="Run World")).to_be_visible()
            expect(page.get_by_role("alert").filter(
                has_text="Run World metadata is incomplete"
            ).or_(page.get_by_role("alert").filter(
                has_text="Run World contains no materialized countries"
            ))).to_be_visible()
            assert page.get_by_role("table", name="Run World countries").count() == 0
            assert page.locator(".app-shell--admin").get_attribute("data-run-form-edited") is None
            evidence["world_partial_saved_copy_fails_closed"] = True

            # Positive immutable Saved Revision World read, independent of
            # the earlier intentionally partial-world negative test.
            assert any(item["world_id"] == "official_fax_world" for item in worlds)
            page.goto(base + "/admin/runs/new")
            page.get_by_label("Unique Run name").fill("Historical World Browser Acceptance")
            page.get_by_role("button", name="Create isolated Run").click()
            expect(page.get_by_role("heading", name="World and Calendar copies")).to_be_visible()
            history_url = page.url.split("?", 1)[0]
            history_run = history_url.split("/admin/runs/", 1)[1].split("/", 1)[0]
            branch_api = args.api_url + "/run-branches"
            original = page.request.get(branch_api, params={"run_id": history_run})
            assert original.ok, original.text()
            old_head = original.json()["run_branches"][0]["saved_head_revision_id"]
            history_branch = original.json()["run_branches"][0]["branch_id"]
            assert old_head and history_branch

            page.get_by_label("Source kind").select_option("world")
            page.get_by_label("World source").select_option("official_fax_world")
            page.get_by_role("button", name="Preview copy").click()
            page.get_by_label("Confirm source copy").check()
            page.get_by_role("button", name="Confirm copy to Working Draft").click()
            page.get_by_label("Confirm save revision").check()
            page.get_by_role("button", name="Save copied packages").click()
            expect(page.get_by_text(
                "Current Run copy: Present. Draft: clean.", exact=False
            )).to_be_visible()
            saved = page.request.get(branch_api, params={"run_id": history_run})
            assert saved.ok, saved.text()
            newer_head = saved.json()["run_branches"][0]["saved_head_revision_id"]
            assert newer_head and newer_head != old_head
            state_url2 = (args.api_url + "/admin/runs/" + history_run
                          + "/branches/" + history_branch + "/packages")
            saved_state = page.request.get(state_url2)
            assert saved_state.ok and saved_state.json()["state"], saved_state.text()
            world_hash = saved_state.json()["fingerprint"]
            codes = [e["source_entity_id"] for e in saved_state.json()["state"]["entities"]
                     if e["entity_kind"] == "world.country.v1"]
            assert codes, "Copied full World has no real countries"
            page.goto(history_url + "/world?year=2000")
            expect(page.get_by_role("table", name="Run World countries")).to_be_visible()
            page.get_by_role("combobox", name="World Saved Revision").select_option(newer_head)
            expect(page.get_by_role("table", name="Run World countries")).to_be_visible()
            # Use the real in-app country link instead of a cross-document
            # page.goto: an active SPA can have a beforeunload dialog that
            # detaches Chrome's page while Playwright is accepting it.
            page.get_by_role("table", name="Run World countries").locator(
                f'a[href*="/world/countries/{codes[0]}"]'
            ).click()
            expect(page.get_by_role("region", name="Run World country detail")).to_be_visible()
            page.get_by_role("combobox", name="World data year").select_option("2010")
            page.wait_for_function(
                "() => new URLSearchParams(location.search).get('year') === '2010'"
            )
            page.get_by_role("navigation", name="Country detail sections").get_by_role(
                "link", name="Players & Talent"
            ).click()
            page.wait_for_function(
                """revision => {
                    const p = new URLSearchParams(location.search);
                    return p.get('revision') === revision &&
                        p.get('year') === '2010' && p.get('tab') === 'players';
                }""",
                arg=newer_head,
            )
            expect(page.get_by_role("region", name="Historical country roster unavailable")).to_be_visible()
            assert page.get_by_role("table", name="Saved country roster").count() == 0
            page.get_by_role("link", name="Back to countries").click()
            expect(page.get_by_role("table", name="Run World countries")).to_be_visible()
            page.get_by_role("combobox", name="World data year").select_option("2000")
            page.wait_for_function(
                "() => new URLSearchParams(location.search).get('year') === '2000'"
            )
            page.get_by_role("combobox", name="World Saved Revision").select_option(old_head)
            expect(page.get_by_role("alert").filter(
                has_text="The selected Saved Revision has no saved Run World component"
            )).to_be_visible()
            assert page.get_by_role("table", name="Run World countries").count() == 0
            page.get_by_role("combobox", name="World Saved Revision").select_option(newer_head)
            expect(page.get_by_role("table", name="Run World countries")).to_be_visible()
            after_read = page.request.get(state_url2)
            assert after_read.ok and after_read.json()["fingerprint"] == world_hash
            after_head = page.request.get(branch_api, params={"run_id": history_run})
            assert after_head.ok
            assert after_head.json()["run_branches"][0]["saved_head_revision_id"] == newer_head
            evidence["historical_saved_world_browser"] = {
                "run_id": history_run, "country_code": codes[0],
                "old_revision_without_world": old_head, "world_revision": newer_head,
                "no_current_world_or_players_fallback": True,
                "world_and_saved_head_unchanged_on_read": True,
            }

            # Real creation form -> pure preview -> immutable custom clock.
            # This proves planning/persistence, never W52 sporting execution.
            before_runs = page.request.get(args.api_url + "/run-containers").json()
            page.goto(base + "/admin/runs/new")
            page.get_by_label("Unique Run name", exact=True).fill("Earth Calendar Browser Acceptance")
            page.get_by_label("Choose calendar and range", exact=True).check()
            create_run = page.get_by_role("button", name="Create isolated Run", exact=True)
            expect(create_run).to_be_disabled()
            page.get_by_label("Calendar preset", exact=True).select_option("earth")
            page.get_by_label("Start year", exact=True).fill("2030")
            page.get_by_label("Number of seasons", exact=True).fill("3")
            page.get_by_role("button", name="Review calendar", exact=True).click()
            expect(page.get_by_text("Sporting simulation is not available", exact=False)).to_be_visible()
            expect(create_run).to_be_enabled()
            assert page.request.get(args.api_url + "/run-containers").json() == before_runs
            page.get_by_label("Season Week 1 equals Year Week", exact=True).fill("35")
            expect(create_run).to_be_disabled()
            page.get_by_role("button", name="Review calendar", exact=True).click()
            expect(page.locator("strong").filter(has_text="2032/2033")).to_be_visible()
            page.screenshot(path=str(artifacts / "08-custom-calendar-review.png"), full_page=True)
            create_run.click()
            expect(page.get_by_role("heading", name="Earth Calendar Browser Acceptance", exact=True)).to_be_visible()
            custom_url = page.url.split("?", 1)[0]
            custom_id = custom_url.split("/admin/runs/", 1)[1].split("/", 1)[0]
            stored = page.request.get(args.api_url + "/run-containers/" + custom_id).json()
            expected_clock = {"schema_version": "run_calendar.v1", "weeks_per_year": 52,
                              "season_start_year_week": 35, "start_year": 2030, "season_count": 3}
            assert stored["metadata_json"]["run_calendar"] == expected_clock, stored
            assert stored["mapped_simulation_run_count"] == 0, stored
            # V83: actual saved-readiness is not a simulation-start promise.
            status_url = args.api_url + "/admin/runs/" + custom_id + "/branches/"
            status_url += page.request.get(args.api_url + "/run-branches", params={"run_id": custom_id}).json()["run_branches"][0]["branch_id"] + "/home-readiness"
            empty_readiness_response = page.request.get(status_url)
            assert empty_readiness_response.status == 200, empty_readiness_response.text()
            empty_readiness = empty_readiness_response.json()
            assert empty_readiness["source"] == "validated_selected_branch_saved_head"
            assert empty_readiness["simulation_started"] is False
            assert empty_readiness["requires_operation_preflight"] is True
            assert empty_readiness["sporting_calendar_supported_by_legacy_writers"] is False
            assert [(item["code"], item["status"]) for item in empty_readiness["items"]][:3] == [
                ("world", "missing"), ("calendar_package", "missing"), ("population", "missing")
            ]
            expect(page.get_by_text("This Branch readiness", exact=True)).to_be_visible()

            custom_branches = page.request.get(args.api_url + "/run-branches", params={"run_id": custom_id}).json()["run_branches"]
            custom_branch = custom_branches[0]
            saved = page.request.get(args.api_url + "/run-containers/" + custom_id + "/branches/"
                                     + custom_branch["branch_id"] + "/saved-revisions/"
                                     + custom_branch["saved_head_revision_id"])
            assert saved.ok and saved.json()["payload"]["run"]["run_calendar"] == expected_clock, saved.text()
            page.reload()
            tracks = page.locator(".run-home-progress__track")
            expect(tracks.nth(0).locator("span")).to_have_count(3)
            expect(tracks.nth(1).locator("span")).to_have_count(52)
            expect(page.get_by_text("calendar-aware player previews are available", exact=False)).to_be_visible()
            assert page.get_by_role("heading", name="Prepare initial ranking", exact=True).count() == 0
            page.screenshot(path=str(artifacts / "09-custom-calendar-reopened.png"), full_page=True)
            evidence["custom_calendar_creation"] = {"run_id": custom_id, "saved_calendar": expected_clock,
                "preview_did_not_create_run": True, "edits_require_new_preview": True,
                "saved_revision_verified": True, "sporting_execution_claimed": False}

            # Copy a real World into this W52 Run using the existing reviewed
            # copy/explicit Save flow. No generated player is adopted here.
            page.get_by_role("combobox", name="Source kind").select_option("world")
            page.get_by_role("combobox", name="World source").select_option("official_fax_world")
            page.get_by_role("button", name="Preview copy", exact=True).click()
            expect(page.get_by_role("heading", name="Review proposed world copy", exact=True)).to_be_visible()
            page.get_by_label("Confirm source copy", exact=True).check()
            page.get_by_role("button", name="Confirm copy to Working Draft", exact=True).click()
            page.get_by_label("Confirm save revision", exact=True).check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/working-draft/save")) as world_saved:
                page.get_by_role("button", name="Save copied packages", exact=True).click()
            assert world_saved.value.status == 201, world_saved.value.text()
            save_receipt = world_saved.value.json()
            assert save_receipt["working_draft"]["status"] == "clean"
            preview_branch = page.request.get(args.api_url + "/run-branches", params={"run_id": custom_id}).json()["run_branches"][0]
            assert preview_branch["saved_head_revision_id"] == save_receipt["saved_revision"]["revision_id"]
            saved_before_preview = page.request.get(args.api_url + "/run-containers/" + custom_id + "/branches/"
                + preview_branch["branch_id"] + "/saved-revisions/" + preview_branch["saved_head_revision_id"]).json()
            page.reload()
            page.get_by_role("link", name="Generate players →", exact=True).click()
            expect(page.get_by_role("heading", name="Generate players", exact=True)).to_be_visible()
            page.get_by_label("Player count", exact=True).fill(str(population_size))
            assert page.locator(".app-shell--admin").get_attribute("data-run-form-edited") is None
            with page.expect_response(lambda response: response.url.endswith("/calendar-preview")) as generated:
                page.get_by_role("button", name="Generate preview", exact=True).click()
            assert generated.value.status == 200, generated.value.text()
            generated_data = generated.value.json()
            assert generated_data["run_calendar"] == expected_clock
            assert generated_data["adoption_supported"] is False
            assert len(generated_data["result"]["players"]) == population_size
            assert all(player["birth_year_week"] <= 52 and player["created_for_season"] == "2030/2031"
                       for player in generated_data["result"]["players"])
            expect(page.get_by_role("table")).to_be_visible()
            expect(page.get_by_role("row")).to_have_count(51)
            page.get_by_role("button", name="Next", exact=True).click()
            expect(page.get_by_text(f"2 / {(population_size + 49) // 50}", exact=True)).to_be_visible()
            assert page.get_by_role("button", name="Adopt reviewed InitialWorld").count() == 0
            page.screenshot(path=str(artifacts / "10-custom-calendar-player-preview.png"), full_page=True)
            # The real browser preview leaves the Saved owner/hash/content intact.
            saved_after_preview = page.request.get(args.api_url + "/run-containers/" + custom_id + "/branches/"
                + preview_branch["branch_id"] + "/saved-revisions/" + preview_branch["saved_head_revision_id"]).json()
            assert saved_after_preview == saved_before_preview
            page.get_by_label("Seed", exact=True).fill("803")
            expect(page.get_by_role("table")).to_have_count(0)
            assert page.locator(".app-shell--admin").get_attribute("data-run-form-edited") is None
            page.reload()
            expect(page.get_by_role("table")).to_have_count(0)
            evidence["custom_calendar_player_preview"] = {"player_count": population_size, "weeks_per_year": 52,
                "saved_revision_unchanged": True, "preview_only": True, "paging_and_stale_reset": True}

            # The same generator now supports a separately reviewed population
            # adoption. No Save, Tour entry, result or time advance is implicit.
            page.get_by_label("Player count", exact=True).fill(str(population_size))
            page.get_by_role("button", name="Generate preview", exact=True).click()
            expect(page.get_by_role("table")).to_be_visible()
            with page.expect_response(lambda response: response.url.endswith("/calendar-adoption/preview")) as population_review:
                page.get_by_role("button", name="Review adding players", exact=True).click()
            assert population_review.value.status == 200, population_review.value.text()
            proposed = population_review.value.json()
            assert proposed["player_count_before"] == 0 and proposed["player_count_after"] == population_size
            pop_root = args.api_url + "/admin/players/runs/" + custom_id + "/branches/" + preview_branch["branch_id"] + "/initial-world"
            assert page.request.get(pop_root + "/calendar-adoption").status == 404
            expect(page.get_by_role("button", name="Add players to Run", exact=True)).to_be_disabled()
            page.get_by_label("Confirm population adoption", exact=True).check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/calendar-adoption")) as population_added:
                page.get_by_role("button", name="Add players to Run", exact=True).click()
            assert population_added.value.status == 201, population_added.value.text()
            installed_population = population_added.value.json()
            assert installed_population["fingerprint"] == proposed["initial_world_fingerprint"]
            assert installed_population["lifecycle_fingerprint"] == proposed["lifecycle_fingerprint"]
            assert installed_population["state"]["run_calendar"] == expected_clock
            unsaved_branch = page.request.get(args.api_url + "/run-branches", params={"run_id": custom_id}).json()["run_branches"][0]
            assert unsaved_branch["saved_head_revision_id"] == preview_branch["saved_head_revision_id"]
            expect(page.get_by_role("button", name="Save players", exact=True)).to_be_disabled()
            page.get_by_label("Confirm population Save", exact=True).check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/initial-world/save")) as population_saved:
                page.get_by_role("button", name="Save players", exact=True).click()
            assert population_saved.value.status == 201, population_saved.value.text()
            saved_population = population_saved.value.json()["saved_revision"]
            content = saved_population["payload"]["content"]
            assert len(content["initial_world"]["state"]["players"]) == population_size
            assert content["initial_world"]["state"]["schema_version"] == "initial_world_state.v2"
            life = content["player_lifecycle"]["states"][0]
            assert life["week"]["calendar"] == expected_clock and life["initialization_stage"] == "population_only"
            assert all("tour_entry_week" not in player for player in life["players"])
            assert "player_health_state" not in content and "player_sporting" not in content
            expect(page.get_by_text("Population is saved.", exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_role("heading", name="Players added to this Run", exact=True)).to_be_visible()
            expect(page.get_by_text("Population is saved.", exact=True)).to_be_visible()
            assert page.get_by_role("button", name="Generate preview", exact=True).count() == 0
            assert page.request.get(pop_root + "/calendar-adoption").json() == installed_population
            inventory = page.request.get(args.api_url + "/admin/runs/" + custom_id + "/branches/"
                                         + preview_branch["branch_id"] + "/saved-players").json()
            assert inventory["total"] == population_size
            page.screenshot(path=str(artifacts / "11-custom-calendar-population-saved.png"), full_page=True)
            # Separate explicit health baseline; confirmation must not Save implicitly.
            health_root = args.api_url + "/admin/runs/" + custom_id + "/branches/" + preview_branch["branch_id"] + "/player-health"
            page.get_by_role("button", name="Review initial health", exact=True).click()
            expect(page.get_by_role("button", name="Create initial health", exact=True)).to_be_disabled()
            page.get_by_label("Confirm initial health", exact=True).check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/calendar-initial")) as health_created:
                page.get_by_role("button", name="Create initial health", exact=True).click()
            assert health_created.value.status == 201, health_created.value.text()
            initial_health = health_created.value.json()
            assert initial_health["saved_head_revision_id"] == saved_population["revision_id"]
            assert initial_health["draft_status"] == "dirty" and not initial_health["saved"]
            assert initial_health["state"]["week"]["calendar"] == expected_clock
            assert len(initial_health["state"]["players"]) == population_size
            assert all(not p["records"] and not p["permanent_consequences"] for p in initial_health["state"]["players"])
            expect(page.get_by_role("button", name="Save initial health", exact=True)).to_be_disabled()
            page.get_by_label("Confirm health Save", exact=True).check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/player-health/save")) as health_saved:
                page.get_by_role("button", name="Save initial health", exact=True).click()
            assert health_saved.value.status == 201, health_saved.value.text()
            health_revision = health_saved.value.json()["saved_revision"]
            assert health_revision["payload"]["content"]["player_health_state"]["fingerprint"] == initial_health["health_component_fingerprint"]
            expect(page.get_by_text("Initial health is saved.", exact=True)).to_be_visible()
            page.reload()
            expect(page.get_by_text("Initial health is saved.", exact=True)).to_be_visible()
            persisted_health = page.request.get(health_root + "/calendar-initial").json()
            assert persisted_health["saved"] and persisted_health["state"] == initial_health["state"]
            page.screenshot(path=str(artifacts / "13-custom-calendar-initial-health-saved.png"), full_page=True)
            evidence["custom_calendar_initial_health"] = {"players":population_size,"manual_save":True,
                "saved_revision_id":health_revision["revision_id"],"reload_exact":True,"injury_history_created":False}
            page.get_by_role("link", name="Open player list", exact=False).click()
            expect(page.get_by_role("heading", name="Players", exact=True)).to_be_visible()
            expect(page.get_by_text(inventory["players"][0]["display_name"], exact=True)).to_be_visible()
            page.screenshot(path=str(artifacts / "12-custom-calendar-saved-players.png"), full_page=True)
            # Real Product Run player route: inspect -> preview -> approve -> confirm -> separate Save.
            selected_player = inventory["players"][0]
            page.get_by_role("link", name=selected_player["display_name"], exact=True).click()
            page.get_by_role("tab", name="Health", exact=True).click()
            expect(page.get_by_role("heading", name="Canonical Player Health", exact=True)).to_be_visible()
            page.get_by_role("button", name="Edit current Health", exact=True).click()
            page.get_by_label("Edit mode", exact=True).select_option("current_state_correction")
            page.get_by_role("button", name="Add Health record", exact=True).click()
            page.get_by_label("Condition key", exact=True).fill("browser-ankle")
            page.get_by_label("Severity 0–100", exact=True).fill("24")
            page.get_by_label("Affected domains (comma separated)", exact=True).fill("movement")
            page.get_by_label("Recovery estimate min weeks", exact=True).fill("2")
            page.get_by_label("Recovery estimate max weeks", exact=True).fill("6")
            page.get_by_label("Provenance", exact=True).fill("Explicit observed opening-week ankle fact")
            page.get_by_label("Operator label", exact=True).fill("Browser Admin")
            page.get_by_label("Reason", exact=True).fill("Review known health fact with actual Run clock")
            page.get_by_role("checkbox", name="I reviewed the complete current Health profile and this correction.", exact=True).check()
            with page.expect_response(lambda r: r.request.method=="POST" and r.url.endswith("/health/preview")) as event_review:
                page.get_by_role("button", name="Calculate Health preview", exact=True).click()
            assert event_review.value.status==200, event_review.value.text()
            reviewed_health=event_review.value.json()
            assert reviewed_health["after_state"]["schema_version"]=="player_health_calendar_state.v2"
            preview_record=next(p for p in reviewed_health["after_state"]["players"] if p["player_id"]==selected_player["player_id"])["records"][0]
            assert preview_record["onset_week"]=={"calendar":expected_clock,"season_index":0,"week":1}
            assert preview_record["recovery_window_max_weeks"]==6
            health_url=args.api_url+"/admin/runs/"+custom_id+"/branches/"+preview_branch["branch_id"]+"/players/"+selected_player["player_id"]+"/health"
            live_after_preview=page.request.get(health_url).json()
            assert live_after_preview["player"]["records"]==[]
            assert live_after_preview["health_component_fingerprint"]==initial_health["health_component_fingerprint"]
            expect(page.get_by_role("button", name="Confirm reviewed Health edit", exact=True)).to_be_disabled()
            page.get_by_label("Confirm Health changes", exact=True).check()
            with page.expect_response(lambda r:r.request.method=="POST" and r.url.endswith("/health")) as edited:
                page.get_by_role("button", name="Confirm reviewed Health edit", exact=True).click()
            assert edited.value.status==200, edited.value.text()
            branch_before_save=page.request.get(args.api_url+"/run-branches?run_id="+custom_id).json()
            assert next(b for b in branch_before_save["run_branches"] if b["branch_id"]==preview_branch["branch_id"])["saved_head_revision_id"]==health_revision["revision_id"]
            expect(page.get_by_role("button", name="Save Health Revision", exact=True)).to_be_disabled()
            page.get_by_label("Confirm Health Save", exact=True).check()
            with page.expect_response(lambda r:r.request.method=="POST" and r.url.endswith("/player-health/save")) as edited_saved:
                page.get_by_role("button", name="Save Health Revision", exact=True).click()
            assert edited_saved.value.status==201, edited_saved.value.text()
            edited_revision=edited_saved.value.json()["saved_revision"]
            edited_component=edited_revision["payload"]["content"]["player_health_state"]
            assert edited_component["fingerprint"]==reviewed_health["after_component_fingerprint"]
            expect(page.get_by_text("Current Health is already captured by the Saved Revision.",exact=True)).to_be_visible()
            page.reload()
            page.get_by_role("tab",name="Health",exact=True).click()
            expect(page.get_by_text("browser-ankle",exact=True)).to_be_visible()
            health_url=args.api_url+"/admin/runs/"+custom_id+"/branches/"+preview_branch["branch_id"]+"/players/"+selected_player["player_id"]+"/health"
            reloaded_health=page.request.get(health_url).json()
            assert reloaded_health["player"]["records"]==[preview_record]
            assert reloaded_health["health_component_fingerprint"]==edited_component["fingerprint"]
            page.screenshot(path=str(artifacts/"14-custom-calendar-health-edit-saved.png"),full_page=True)
            evidence["custom_calendar_health_edit"]={"manual_save":True,"reload_exact":True,
                "preview_did_not_write":True,"confirmation_did_not_save":True,
                "saved_revision_id":edited_revision["revision_id"],"record":preview_record}
            evidence["custom_calendar_population_adopt_save_reload"] = {"player_count":population_size,
                "saved_revision_id":saved_population["revision_id"],"weeks_per_year":52,
                "adoption_did_not_save":True,"manual_save_verified":True,"population_only":True,
                "saved_inventory_total":inventory["total"],"reload_exact":True}

            # V83: real browser review -> explicit consent -> all-Branch
            # atomic Save on the *same* W52 Run with 1,000 saved players
            # and preserved Health. These remain original opening-week facts.
            old_health_revision_url = (args.api_url + "/run-containers/" + custom_id
                + "/branches/" + preview_branch["branch_id"] + "/saved-revisions/"
                + edited_revision["revision_id"])
            old_health_snapshot = page.request.get(old_health_revision_url).json()
            assert old_health_snapshot["content_hash"] == edited_revision["content_hash"]
            page.goto(base + "/admin/runs/" + custom_id)
            expect(page.get_by_role("heading", name="Extend Run horizon", exact=True)).to_be_visible()
            assert page.get_by_role("button", name="Confirm & Save entire Run").count() == 0
            page.get_by_label("New total season count", exact=True).fill("5")
            with page.expect_response(lambda response: response.request.method == "GET"
                                      and "/calendar/extension-review?" in response.url) as horizon_review_response:
                page.get_by_role("button", name="Review all Branches", exact=True).click()
            assert horizon_review_response.value.status == 200, horizon_review_response.value.text()
            horizon_review = horizon_review_response.value.json()
            assert horizon_review["can_save"], horizon_review
            assert horizon_review["branch_count"] == len(custom_branches) == 1
            assert horizon_review["original_calendar"] == expected_clock
            assert horizon_review["proposed_calendar"]["season_count"] == 5
            assert horizon_review["added_weeks"] == 104
            save_extension = page.get_by_role("button", name="Confirm & Save entire Run", exact=True)
            expect(save_extension).to_be_disabled()
            page.get_by_role("checkbox", name="I confirm extension across every listed Branch and creation of new Saved Revisions.").check()
            with page.expect_response(lambda response: response.request.method == "POST"
                                      and response.url.endswith("/calendar/extension-save")) as horizon_saved:
                save_extension.click()
            assert horizon_saved.value.status == 200, horizon_saved.value.text()
            horizon_receipt = horizon_saved.value.json()
            assert horizon_receipt["saved"] and not horizon_receipt["simulation_started"]
            assert horizon_receipt["branch_count"] == 1
            assert horizon_receipt["previous_calendar"] == expected_clock
            assert horizon_receipt["current_calendar"]["season_count"] == 5
            new_head = horizon_receipt["branches"][0]
            assert new_head["previous_saved_head_revision_id"] == edited_revision["revision_id"]
            expect(page.get_by_text("Run horizon saved successfully", exact=True)).to_be_visible()
            old_after = page.request.get(old_health_revision_url).json()
            assert old_after["revision_id"] == old_health_snapshot["revision_id"]
            assert old_after["content_hash"] == old_health_snapshot["content_hash"]
            assert old_after["payload"] == old_health_snapshot["payload"]
            assert old_after["change_summary"] == old_health_snapshot["change_summary"]
            new_snapshot = page.request.get(
                args.api_url + "/run-containers/" + custom_id + "/branches/"
                + preview_branch["branch_id"] + "/saved-revisions/"
                + new_head["saved_revision_id"]
            ).json()
            assert new_snapshot["payload"]["run"]["run_calendar"] == horizon_receipt["current_calendar"]
            assert new_snapshot["payload"]["run"]["run_calendar_content_origin"] == expected_clock
            assert new_snapshot["payload"]["content"]["initial_world"] == old_health_snapshot["payload"]["content"]["initial_world"]
            assert new_snapshot["payload"]["content"]["player_health_state"] == edited_component
            assert new_snapshot["payload"]["content"]["player_lifecycle"] == old_health_snapshot["payload"]["content"]["player_lifecycle"]
            saved_readiness_response = page.request.get(status_url)
            assert saved_readiness_response.status == 200, saved_readiness_response.text()
            saved_readiness = saved_readiness_response.json()
            assert saved_readiness["saved_revision_id"] == new_head["saved_revision_id"]
            assert saved_readiness["current_calendar"] == horizon_receipt["current_calendar"]
            assert saved_readiness["sporting_calendar_supported_by_legacy_writers"] is False
            assert saved_readiness["simulation_started"] is False
            assert {item["code"]: item["status"] for item in saved_readiness["items"]}["population"] == "saved"
            assert {item["code"]: item["status"] for item in saved_readiness["items"]}["health"] == "saved"
            assert {item["code"]: item["evidence_count"] for item in saved_readiness["items"]}["population"] == population_size
            assert {item["code"]: item["status"] for item in saved_readiness["items"]}["official_ranking"] == "missing"

            # Run metadata and old population stay coherent over restart/reload.
            page.get_by_role("button", name="Reload saved Run", exact=True).click()
            expect(page.locator(".run-home-progress__track").nth(0).locator("span")).to_have_count(5)
            expect(page.locator(".run-home-progress__track").nth(1).locator("span")).to_have_count(52)
            assert page.request.get(health_url).json()["player"]["records"] == [preview_record]
            initial_after_extension = page.request.get(health_root + "/calendar-initial")
            assert initial_after_extension.status == 200, initial_after_extension.text()
            assert initial_after_extension.json()["saved"] is True
            assert initial_after_extension.json()["run_calendar"] == expected_clock
            installed_after_extension = page.request.get(pop_root + "/calendar-adoption")
            assert installed_after_extension.status == 200, installed_after_extension.text()
            assert installed_after_extension.json() == installed_population
            page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
            expect(page.get_by_role("heading", name="Prodloužení horizontu Runu", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Zkontrolovat všechny Branches", exact=True)).to_be_visible()
            page.screenshot(path=str(artifacts / "15-custom-calendar-horizon-extended.png"), full_page=True)
            page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
            evidence["custom_calendar_horizon_extension"] = {
                "reviewed_all_branches": True,
                "explicit_confirm_and_save": True,
                "added_weeks": 104,
                "preserved_initial_population": population_size,
                "old_saved_revision_byte_identical": True,
                "old_health_records_preserved": True,
                "original_calendar_provenance": expected_clock,
                "new_saved_head": new_head["saved_revision_id"],
                "reload_run_seasons": 5,
                "cs_en_admin_flow": True,
                "simulation_started": False,
            }

            # Genuine Run-calendar sporting/browser acceptance on a newly
            # forked historical Saved population. No old branch/head mutation.
            evidence["calendar_native_match_save_replay"] = exercise_calendar_match(
                page, base_url=base, api_url=args.api_url, artifacts=artifacts,
                run_id=custom_id,
                original_branch_id=preview_branch["branch_id"],
                population_revision_id=saved_population["revision_id"],
                original_clock=expected_clock,
            )

            evidence["calendar_native_four_player_knockout"] = exercise_calendar_knockout(
                page, base_url=base, api_url=args.api_url, artifacts=artifacts,
                run_id=custom_id,
                original_branch_id=preview_branch["branch_id"],
                original_clock=expected_clock,
                population_size=population_size,
            )
            assert evidence["calendar_native_four_player_knockout"][
                "reviewed_prepared_points"
            ], "real Saved knockout points were not reviewed/confirmed"
            assert evidence["calendar_native_four_player_knockout"][
                "points_unpublished"
            ], "prepared points must not be represented as Official"
            assert evidence["calendar_native_four_player_knockout"][
                "signed_as_of_scoreboard"
            ], "Signed Saved standings were not read in the real browser"
            assert evidence["calendar_native_four_player_knockout"][
                "exact_calendar_expiry"
            ], "W52 scoreboard expiry was not verified in Chromium"

            page.get_by_role("link", name="Squash Engine global Home").click()
            expect(page.get_by_role("heading", name="Squash Engine Home")).to_be_visible()
            assert page.get_by_role("combobox", name="Admin active Run").count() == 0
            assert page.get_by_role("combobox", name="Admin active Branch").count() == 0
            expect(page.get_by_text("Prealpha Shell Browser Run")).to_be_visible()
            evidence["returned_global_and_explicit_recent_run"] = True

            page.get_by_role("link", name="Open Run →").first.click()
            expect(page.get_by_role("combobox", name="Admin active Run")).to_be_visible()
            evidence["explicit_reopen"] = True
            assert not errors, errors
            evidence["browser_errors"] = errors
            print("PREALPHA_SHELL_BROWSER_PASSED", json.dumps(evidence), flush=True)
        except Exception:
            # Best-effort diagnostics must never hide the original browser failure.
            try:
                page.screenshot(path=str(artifacts / "failure.png"), full_page=True, timeout=5000)
            except Exception as artifact_error:
                (artifacts / "failure-screenshot-error.txt").write_text(
                    f"{type(artifact_error).__name__}: {artifact_error}"
                )
            try:
                (artifacts / "failure.txt").write_text(
                    page.locator("body").inner_text(timeout=5000)
                )
            except Exception as artifact_error:
                (artifacts / "failure-body-error.txt").write_text(
                    f"{type(artifact_error).__name__}: {artifact_error}"
                )
            raise
        finally:
            (artifacts / "evidence.json").write_text(
                json.dumps({"evidence": evidence, "errors": errors, "dialogs": dialogs}, indent=2)
            )
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
