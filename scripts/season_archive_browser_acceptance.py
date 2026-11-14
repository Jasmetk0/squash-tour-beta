"""Real Chromium: seasonal archive and comparison on the actual native Tour page.

Two genuine Signed Seasons (twelve real MatchEngine rally logs) are completed, the
second under another ranking policy. The Admin Tour page must list both seasons and,
after selecting them, show the limited-comparability warning with the exact Best N
values. English and Czech; nothing is written (Saved head and Tour fingerprint equal).
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_tour_flow import inspect
    from tests.api.test_native_season_archive_comparison import complete_two_seasons
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium"))
    args = parser.parse_args()
    expect.set_options(timeout=30000)
    # Evidence goes to a fresh temporary directory; no path is taken from the command line.
    root = Path(tempfile.mkdtemp(prefix="season-archive-browser-"))
    with ApiServer(database_url=f"sqlite:///{root.resolve() / 'seasons.sqlite'}") as server:
        complete_two_seasons(server, change_policy=True)
        before = inspect(server)
        assert before["saved_completed_seasons"] == [0, 1]
        web_port = 5173
        web = f"http://127.0.0.1:{web_port}"
        with (root / "frontend.log").open("w") as log:
            frontend = subprocess.Popen(
                ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1",
                 "--port", str(web_port), "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
                    for language, title, table, warning, best in (
                        ("en", "Season archive and comparison", "Completed season archive",
                         "Limited comparability", "Best N: 1 → 15"),
                        ("cs", "Archiv sezón a porovnání", "Archiv dokončených sezón",
                         "Omezená srovnatelnost", "Best N: 1 → 15"),
                    ):
                        context = browser.new_context(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
                        context.add_init_script(
                            f"localStorage.setItem('squash-engine-language-v1','{language}')"
                        )
                        page = context.new_page()
                        page.set_default_timeout(60000)
                        errors = []
                        page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                        page.goto(f"{web}/admin/runs/run/tour/editions?branch=branch")
                        section = page.get_by_role("region", name=title)
                        expect(section).to_be_visible()
                        archive = section.get_by_role("table", name=table)
                        expect(archive.get_by_role("row")).to_have_count(3)  # header + two seasons
                        selected_label = "Vybraná sezóna" if language == "cs" else "Selected season"
                        compare_label = "Porovnat s" if language == "cs" else "Compare with"
                        search_label = "Hledat v archivu" if language == "cs" else "Search archive"
                        section.get_by_label(selected_label).select_option("1")
                        section.get_by_label(compare_label).select_option("0")
                        expect(section.get_by_role("alert")).to_contain_text(warning)
                        expect(section.get_by_role("alert")).to_contain_text(best)
                        assert section.get_by_role("button", name="Apply").count() == 0
                        # URL selection persists on reload, including the unrelated Branch parameter.
                        assert "branch=branch" in page.url
                        assert "season_selected=1" in page.url and "season_other=0" in page.url
                        page.reload()
                        section = page.get_by_role("region", name=title)
                        expect(section.get_by_label(selected_label)).to_have_value("1")
                        expect(section.get_by_label(compare_label)).to_have_value("0")
                        expect(section.get_by_role("alert")).to_contain_text(warning)

                        # Search changes only the archive display, not the compared seasons or warning.
                        dirty_before_reader_control = page.locator('.app-shell--admin').get_attribute('data-run-form-edited')
                        section.get_by_label(search_label).fill("unmatched-season")
                        # A read-only control must not dirty the Run Working Draft guard.
                        assert page.locator('.app-shell--admin').get_attribute('data-run-form-edited') == dirty_before_reader_control
                        expect(section).to_contain_text(
                            "Žádná sezona neodpovídá hledání." if language == "cs"
                            else "No seasons match the search."
                        )
                        expect(section.get_by_role("alert")).to_contain_text(warning)
                        section.get_by_label(search_label).fill("")
                        expect(section.get_by_role("table", name=table).get_by_role("row")).to_have_count(3)
                        section.get_by_role("button", name="Reset filtrů" if language == "cs" else "Reset filters").click()
                        assert "season_selected" not in page.url
                        assert "branch=branch" in page.url

                        section.scroll_into_view_if_needed()
                        section.screenshot(path=str(root / f"archive-{language}.png"))
                        assert not errors, errors
                        context.close()
                    browser.close()
            finally:
                stop_process(frontend)
        after = inspect(server)
        for field in ("saved_head_revision_id", "checkpoint_fingerprint", "tour_fingerprint", "draft_version"):
            assert after[field] == before[field], field
    print("Season archive browser acceptance passed:", root)


if __name__ == "__main__":
    main()
