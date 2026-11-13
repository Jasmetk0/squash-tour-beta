"""Real Chromium: following, grouped alerts and persistent read/hide on the actual page.

A real API server and SQLite hold a v87 Run with a played Edition. In the Admin
"Following and alerts" page the Edition winner is followed, one grouped card with
separately sourced items appears, it is marked read and hidden (surviving a page
reload), and unfollowing leaves the career history intact. Saved head and Tour
fingerprint stay unchanged throughout. English and Czech.
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
    root = Path(tempfile.mkdtemp(prefix="follow-alerts-browser-"))
    patch = pytest.MonkeyPatch()
    patch.setattr(population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}))
    patch.setattr(population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}))
    patch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: EAGER)
    try:
        with ApiServer(database_url=f"sqlite:///{root.resolve() / 'follow.sqlite'}") as server:
            repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20)
            pros, _ = _opening_pros(repo)
            view = inspect(server)
            newcomers = sorted({d["player_id"] for w in view["state"]["pre_tour_turn_pro"]["weeks"]
                                for d in w["decisions"]})
            patch.setattr(exhibition_service, "default_turn_pro_model_policy", default_turn_pro_model_policy)
            week = view["state"]["week"]
            execute(server, command(view, "create-edition", name="first:create", data={
                "edition_id": "first", "name": "Followed Edition",
                "week": {**week, "week": week["week"] + 2},
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
            for name in ("after-first", "after-first-2"):
                execute(server, command(inspect(server), "transition", name=name))
                save_tour(server)
            champion = next(p for p in field if career(server, p)[1]["overview"]["titles"] == 1)
            before = inspect(server)
            web_port = 5173
            web = f"http://127.0.0.1:{web_port}"
            with (root / "frontend.log").open("w") as log:
                frontend = subprocess.Popen(
                    ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1",
                     "--port", str(web_port), "--strictPort"],
                    env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    wait_http(web, frontend)
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
                        for language, title, follow_btn, read_btn, hide_btn, read_text, hidden_text, unfollow_btn, show_hidden, restore_btn, nothing in (
                            ("en", "Following and alerts", "Follow", "Mark as read", "Hide", "read", "No alerts", "Unfollow", "Show hidden too", "Restore", "You follow nothing yet."),
                            ("cs", "Sledování a upozornění", "Sledovat", "Označit jako přečtené", "Skrýt", "přečteno", "Žádná upozornění", "Přestat sledovat", "Zobrazit i skrytá", "Obnovit", "Zatím nic nesledujete."),
                        ):
                            context = browser.new_context(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
                            context.add_init_script(f"localStorage.setItem('squash-engine-language-v1','{language}')")
                            page = context.new_page()
                            page.set_default_timeout(60000)
                            errors = []
                            page.on("pageerror", lambda error, target=errors: target.append(str(error)))
                            page.goto(f"{web}/admin/runs/run/following")
                            section = page.get_by_role("region", name=title)
                            expect(section).to_be_visible()
                            expect(section.get_by_role("listitem").filter(has_text=champion)).to_have_count(0)
                            section.get_by_label("ID hráče / kód země" if language == "cs" else "Player ID / country code").fill(champion)
                            section.get_by_role("button", name=follow_btn, exact=True).click()
                            card = section.get_by_label(__import__("re").compile(r"^.+ [0-9a-f]{8}$"))
                            expect(card).to_have_count(1)
                            card.locator("details summary").click()
                            expect(card).to_contain_text("played_edition")
                            section.scroll_into_view_if_needed()
                            section.screenshot(path=str(root / f"follow-{language}.png"))
                            card.get_by_role("button", name=read_btn).click()
                            expect(card).to_contain_text(read_text)
                            page.reload()
                            expect(section.get_by_label(__import__("re").compile(r"^.+ [0-9a-f]{8}$"))).to_contain_text(read_text)
                            section.get_by_label(__import__("re").compile(r"^.+ [0-9a-f]{8}$")).get_by_role("button", name=hide_btn, exact=True).click()
                            expect(section).to_contain_text(hidden_text)
                            page.reload()
                            expect(section).to_contain_text(hidden_text)
                            # Hidden state is persistent: show and restore the card (an explicit step),
                            # then unfollow; career history must stay intact.
                            section.get_by_label(show_hidden).check()
                            section.get_by_role("button", name=restore_btn, exact=True).click()
                            section.get_by_label(show_hidden).uncheck()
                            expect(section.get_by_label(__import__("re").compile(r"^.+ [0-9a-f]{8}$"))).to_have_count(1)
                            section.get_by_role("button", name=unfollow_btn).first.click()
                            expect(section).to_contain_text(nothing)
                            # The follow star in the Saved player profile uses the same Run-level follow.
                            page.goto(f"{web}/admin/runs/run/people/{champion}")
                            star = page.get_by_role("button", name=__import__("re").compile(follow_btn))
                            expect(star).to_have_attribute("aria-pressed", "false")
                            star.click()
                            expect(page.get_by_role("button", name=__import__("re").compile(unfollow_btn))).to_have_attribute("aria-pressed", "true")
                            page.goto(f"{web}/admin/runs/run/following")
                            expect(page.get_by_role("region", name=title)).to_contain_text(champion)
                            page.goto(f"{web}/admin/runs/run/people/{champion}")
                            page.get_by_role("button", name=__import__("re").compile(unfollow_btn)).click()
                            expect(page.get_by_role("button", name=__import__("re").compile(follow_btn))).to_have_attribute("aria-pressed", "false")
                            assert not errors, errors
                            context.close()
                        browser.close()
                finally:
                    stop_process(frontend)
            after = inspect(server)
            for name in ("saved_head_revision_id", "checkpoint_fingerprint", "tour_fingerprint", "draft_version"):
                assert after[name] == before[name], name
            assert career(server, champion)[1]["milestones"]
    finally:
        patch.undo()
    print("Follow alerts browser acceptance passed:", root)


if __name__ == "__main__":
    main()
