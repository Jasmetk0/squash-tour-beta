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

            page.goto(base + "/admin/runs/new")
            expect(page.get_by_role("heading", name="Create test Run")).to_be_visible()
            page.get_by_label("Unique Run name").fill("Prealpha Shell Browser Run")
            page.get_by_role("button", name="Create isolated Run").click()
            expect(page.get_by_role("combobox", name="Admin active Run")).to_be_visible()
            expect(page.get_by_role("combobox", name="Admin active Branch")).to_be_visible()
            expect(page.get_by_label("Admin view time")).to_be_visible()
            assert "/admin/runs/" in page.url and not page.url.endswith("/new"), page.url
            evidence["created_run_url"] = page.url
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

            # The new canonical player detail must not fabricate an identity for
            # a legitimate empty Run; the selected Run and Branch remain intact.
            page.goto(evidence["created_run_url"] + "/people/no-saved-player")
            expect(page.get_by_role("heading", name="no-saved-player")).to_be_visible()
            expect(page.get_by_text("No verified name for this player ID exists in this Saved Revision.")).to_be_visible()
            expect(page.get_by_text("This is not yet a full career profile.", exact=False)).to_be_visible()
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
