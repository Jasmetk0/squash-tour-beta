"""Real Chromium: native player career (Turn Pro, first recorded title, as-of view).

A real API server and SQLite hold a v87 Run: prospects turn pro in the pre-Tour
exhibition week, four players play a real Edition and the winner's career is opened in
the actual Admin player profile (career tab). The first recorded title must appear
with its source, and an as-of week before the Edition must show neither the result nor
the title. Nothing is written: Saved head and Tour fingerprint are compared.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from beta_engine.application import calendar_sporting_week_service as exhibition_service
    import pytest

    from playwright.sync_api import expect, sync_playwright

    from beta_engine.application import calendar_pre_tour_turn_pro as pre_tour
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api import test_calendar_population_sporting_checkpoint as population
    from tests.api.test_calendar_initial_world_adoption import request as population_request
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup
    from tests.api.test_calendar_tour_player_career_v87 import career
    from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, V87, _opening_pros, _play_edition
    from tests.api.test_player_generation_calendar_gate import _generation
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium"))
    args = parser.parse_args()
    expect.set_options(timeout=30000)
    # Evidence goes to a fresh temporary directory; no path is taken from the command line.
    root = Path(tempfile.mkdtemp(prefix="player-career-browser-"))
    patch = pytest.MonkeyPatch()
    patch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    patch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}),
    )
    patch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: EAGER)
    try:
        with ApiServer(database_url=f"sqlite:///{root.resolve() / 'career.sqlite'}") as server:
            repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20)
            pros, _everyone = _opening_pros(repo)
            view = inspect(server)
            newcomers = sorted({
                d["player_id"] for w in view["state"]["pre_tour_turn_pro"]["weeks"]
                for d in w["decisions"]
            })
            patch.setattr(exhibition_service, "default_turn_pro_model_policy", default_turn_pro_model_policy)
            week = view["state"]["week"]
            edition_week = week["week"] + 2
            execute(server, command(view, "create-edition", name="first:create", data={
                "edition_id": "first", "name": "Career Edition",
                "week": {**week, "week": edition_week},
                "announcement_week": {**week, "week": week["week"] + 1},
                "start_slot": 1, "main_entrant_count": 4, "ranked": True,
                "validity_weeks": week["calendar"]["weeks_per_year"],
                "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
            }))
            save_tour(server)
            for name in ("announce", "open-play-week"):
                execute(server, command(inspect(server), "transition", name=name))
                save_tour(server)
            field = [*newcomers[:2], *sorted(pros)[:2]]
            _play_edition(server, field)
            execute(server, command(inspect(server), "transition", name="after-first"))
            save_tour(server)
            before = inspect(server)
            champion = next(
                p for p in field if career(server, p)[1]["overview"]["titles"] == 1
            )
            edition_ordinal = edition_week - 1
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
                        browser = pw.chromium.launch(
                            executable_path=args.chromium, args=["--no-sandbox"]
                        )
                        for language, title, first, no_inj in (
                            ("en", "Career: timeline and milestones", "First recorded title",
                             "no supported source"),
                            ("cs", "Kariéra: časová osa a milníky", "První zaznamenaný titul",
                             "podporovaný zdroj"),
                        ):
                            context = browser.new_context(
                                viewport={"width": 1440, "height": 1050}, device_scale_factor=1
                            )
                            context.add_init_script(
                                f"localStorage.setItem('squash-engine-language-v1','{language}')"
                            )
                            page = context.new_page()
                            page.set_default_timeout(60000)
                            errors = []
                            page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                            page.goto(f"{web}/admin/runs/run/people/{champion}?tab=career")
                            section = page.get_by_role("region", name=title)
                            expect(section).to_be_visible()
                            expect(section).to_contain_text(first)
                            expect(section).to_contain_text("played_edition")
                            expect(section).to_contain_text(no_inj)
                            if language == "en":
                                section.get_by_label("View as of week (ordinal)").fill(
                                    str(edition_ordinal - 1)
                                )
                                section.get_by_role("button", name="Apply").click()
                                # A read-only control must not dirty the Run Working Draft guard.
                                assert page.locator('.app-shell--admin').get_attribute('data-run-form-edited') != 'true'
                                expect(section).to_contain_text(
                                    f"Shown as of week no. {edition_ordinal - 1}"
                                )
                                expect(section).not_to_contain_text("First recorded title")
                                expect(section).not_to_contain_text("played_edition")
                                # The selected historical ordinal is a linkable, reloadable view.
                                assert f"career_asof={edition_ordinal - 1}" in page.url
                                page.reload()
                                section = page.get_by_role("region", name=title)
                                expect(section).to_contain_text(
                                    f"Shown as of week no. {edition_ordinal - 1}"
                                )
                                expect(section).not_to_contain_text("played_edition")
                                # Search and sorting only affect timeline rows, not recorded overview.
                                overview = section.locator("dl").inner_text()
                                section.get_by_label("Search entries").fill("no-such-event")
                                expect(section).to_contain_text("No entries match the filters.")
                                assert section.locator("dl").inner_text() == overview
                                section.get_by_label("Search entries").fill("")
                                section.get_by_label("Order").select_option("desc")
                                assert "career_order=desc" in page.url
                                page.go_back()
                                expect(section.get_by_label("Order")).to_have_value("asc")
                                page.go_forward()
                                expect(section.get_by_label("Order")).to_have_value("desc")
                                page.reload()
                                expect(section.get_by_label("Order")).to_have_value("desc")
                                section.get_by_role("button", name="Reset filters").click()
                                assert "career_asof" not in page.url
                                expect(section).to_contain_text("played_edition")
                            section.scroll_into_view_if_needed()
                            section.screenshot(path=str(root / f"career-{language}.png"))
                            assert not errors, errors
                            context.close()
                        browser.close()
                finally:
                    stop_process(frontend)
            after = inspect(server)
            for field_name in ("saved_head_revision_id", "checkpoint_fingerprint",
                               "tour_fingerprint", "draft_version"):
                assert after[field_name] == before[field_name], field_name
    finally:
        patch.undo()
    print("Player career browser acceptance passed:", root)


if __name__ == "__main__":
    main()
