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

            # Read-only Run exploration is not an unsaved edit, including filters.
            page.goto(base + "/admin/runs/" + run_id + "/players")
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
            page.get_by_role("combobox", name="Source kind").select_option("calendar")
            page.get_by_role("textbox", name="Calendar source season").fill("2008-2009")
            expect(page.locator(".app-shell--admin")).to_have_attribute("data-run-form-edited", "true")

            # The Branch dropdown is an imperative context change: cancelling
            # keeps both its selected Branch and the edited source values.
            branch_selector = page.get_by_role("combobox", name="Admin active Branch")
            initial_branch = branch_selector.input_value()
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
            page.evaluate("window.history.back()")
            expect(page.get_by_role("heading", name="Run Management")).to_be_visible()
            expect(page.get_by_role("textbox", name="Calendar source season")).to_have_value("2012-2013")
            assert len(dialogs) == before + 1, dialogs
            dialog_policy["accept"] = True
            page.evaluate("window.history.back()")
            expect(page.get_by_role("heading", name="Next steps")).to_be_visible()
            assert len(dialogs) == before + 2, dialogs
            evidence["run_history_cancel_accept"] = True

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
            page.locator(".package-apply > p > a").first.click()
            expect(page.get_by_role("heading", name="Apply World Package to Run")).to_be_visible()
            expect(page.get_by_role("button", name="Save revision")).to_be_visible()
            assert len(dialogs) == before + 1, dialogs
            page.get_by_role("combobox", name="Target Branch").select_option(source_branch["branch_id"])
            expect(page.get_by_role("combobox", name="Target Branch")).to_have_value(created_branch["branch_id"])
            assert len(dialogs) == before + 2, dialogs

            # Accept leaving. The server draft survives a full route exit
            # and must be explicitly inspected/reopened before manual Save.
            dialog_policy["accept"] = True
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
