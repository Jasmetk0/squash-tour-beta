"""Historical Viewer pages: real persisted Saved revisions, HTTP and Chromium.

Positive cases do not mock API responses. Negative cases intercept *only* an
intentionally forged public response to verify fail-closed rendering.
The database is frozen before browser launch and compared byte-for-byte after.
This is a focused W61 legacy Saved read-model test, not W52/W80 acceptance.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from itertools import count
from pathlib import Path
from urllib.parse import quote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
# Existing API test fixtures deliberately use flat "from test_*" imports.
sys.path.insert(0, str(REPO_ROOT / "tests" / "api"))
API_PORT, WEB_PORT = 8037, 5173


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    work = Path(__file__).resolve().parents[2] / "work"
    root = args.root.resolve()
    if root.parent != work.resolve() or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", root.name
    ):
        raise ValueError("Use a new work/<case> directory for this test")
    db = root / "viewer.sqlite"
    if args.serve:
        import uvicorn
        from beta_engine.main import create_app
        uvicorn.run(
            create_app(database_url=f"sqlite:///{db}"),
            host="127.0.0.1", port=API_PORT, log_level="warning",
        )
        return

    from playwright.sync_api import expect, sync_playwright
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
    from tests.api.viewer_saved_revision_helpers import canonical_product_run, save_ranking
    from tests.api.test_player_generation_calendar_gate import _dump
    from tests.api.test_visible_prospects_api import _database_session
    from tests.api.test_viewer_official_ranking_api import _ranking
    from tests.application.test_viewer_people_read_model import _world
    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.application.run_working_draft_service import RunWorkingDraftService
    from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
    from beta_engine.infrastructure.db.initial_world_state import put_initial_world
    from beta_engine.infrastructure.db.player_lifecycle_state import bootstrap_lifecycle
    from beta_engine.infrastructure.db.player_sporting_state import bootstrap_sporting
    from beta_engine.infrastructure.db.models import (
        AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
    )
    from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
    from beta_engine.infrastructure.db.run_package_state import put_run_package_state
    from tests.application.test_viewer_tournament_history_read_model import _state
    from tests.application.test_viewer_tournament_result_read_model import _source

    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    with ApiServer(database_url=f"sqlite:///{db}") as source:
        # Fixture A: real saved initial world (country stats), no forged public rows.
        country_run, country_branch, _ = _create_run(
            source, display_name="Country Stats Browser Acceptance",
        )
        repository = source.app.state.runtime.repository
        world = _world().model_copy(update={"run_id": country_run, "branch_id": country_branch})
        with repository._session_factory.begin() as session:
            put_initial_world(session, world)
            bootstrap_lifecycle(session, world)
            bootstrap_sporting(session, world)
        initial_save = (
            source.base_url + "/admin/players/runs/" + quote(country_run, safe="")
            + "/branches/" + quote(country_branch, safe="") + "/initial-world/save"
        )
        status, preview = _request("GET", initial_save + "/preview")
        assert status == 200 and preview["can_save"], (status, preview)
        status, saved = _request("POST", initial_save, {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
        })
        assert status == 201 and saved["saved_revision"]["revision_id"], (status, saved)
        country_api = f"/viewer/runs/{quote(country_run, safe='')}/countries"
        status, real_countries = _request("GET", source.base_url + country_api)
        assert status == 200 and real_countries["schema_version"] == "viewer_countries.v1", (status, real_countries)
        assert real_countries["country_count"] == 2
        assert {x["country_code"] for x in real_countries["countries"]} == {"CZE", "EGY"}
        assert all("private_rating" not in x for x in real_countries["countries"])

        # Fixture B: a real saved calendar and separately published tournament result.
        tournament_run, tournament_branch, _ = _create_run(
            source, display_name="Tour Archive Browser Acceptance",
        )
        state = _state(run_id=tournament_run, branch_id=tournament_branch)
        with repository._session_factory.begin() as session:
            put_run_package_state(session, state)
        ids = count(1)
        revision = RunWorkingDraftService(
            repository, lambda kind: f"{kind}-historical-browser-{next(ids)}",
        )
        draft = revision.get_viewer_branch_draft(
            run_id=tournament_run, branch_id=tournament_branch,
        )
        revision.save(
            run_id=tournament_run, branch_id=tournament_branch,
            expected_draft_version=draft.draft_version,
        )
        with repository._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(
                    run_id=tournament_run, branch_id=tournament_branch,
                    event_id="event",
                )
            )
        RankingWeekCommandRunner(repository._session_factory).execute(
            RankingBootstrapCommand(
                command_id="historical-browser-ranking-bootstrap",
                run_id=tournament_run,
                branch_id=tournament_branch,
                policy=OfficialRankingPolicy(policy_id="historical-browser-policy"),
                players=(), discipline="none",
            )
        )
        save_ranking(source, tournament_run, tournament_branch)
        tour_root = f"/viewer/runs/{quote(tournament_run, safe='')}"
        status, real_calendar = _request("GET", source.base_url + tour_root + "/calendar")
        assert status == 200, (status, real_calendar)
        status, real_history = _request("GET", source.base_url + tour_root + "/tournaments")
        assert status == 200, (status, real_history)
        assert real_calendar["schema_version"] == "viewer_run_calendar.v1"
        assert real_history["schema_version"] == "viewer_tournament_history.v1"
        assert real_calendar["event_count"] == real_history["tournament_count"] == 2
        assert real_history["published_result_count"] == 1
        assert any(x["result_published"] and x["champion_player_id"] == "A"
                   for x in real_history["tournaments"])

        # Fixture C: two genuinely published Official Ranking snapshots with a
        # later *unpublished* live row. The browser must never see the future.
        ranking_branch, ranking_run = canonical_product_run(source, "no1-browser")
        opening_week, current_week, future_week = (
            RankingWeek(season_index=0, week=n) for n in (1, 2, 3)
        )
        opening = _ranking(
            run_id=ranking_run, branch_id=ranking_branch, week=opening_week,
        )
        current = _ranking(
            run_id=ranking_run, branch_id=ranking_branch,
            week=current_week, previous=opening,
        )
        future = _ranking(
            run_id=ranking_run, branch_id=ranking_branch,
            week=future_week, previous=current,
        )
        with _database_session(db) as session:
            session.add_all([
                PublishedOfficialRankingModel(
                    run_id=ranking_run, branch_id=ranking_branch,
                    week_ordinal=ranking.week.ordinal,
                    snapshot_fingerprint=ranking.fingerprint,
                    payload_json=ranking.model_dump_json(),
                )
                for ranking in (opening, current)
            ])
            session.add(AuthoritativeWorldStateModel(
                run_id=ranking_run, branch_id=ranking_branch,
                current_ordinal=current.week.ordinal,
                ranking_fingerprint=current.fingerprint,
            ))
        save_ranking(source, ranking_run, ranking_branch)
        with _database_session(db) as session:
            session.add(PublishedOfficialRankingModel(
                run_id=ranking_run, branch_id=ranking_branch,
                week_ordinal=future.week.ordinal,
                snapshot_fingerprint=future.fingerprint,
                payload_json=future.model_dump_json(),
            ))
        rank_root = f"/viewer/runs/{quote(ranking_run, safe='')}/rankings"
        status, ranking_history = _request("GET", source.base_url + rank_root + "/history")
        assert status == 200, (status, ranking_history)
        assert ranking_history["publication_count"] == 2
        assert [x["week_ordinal"] for x in ranking_history["publications"]] == [1, 0]
        status, detail = _request("GET", source.base_url + rank_root + "/history/1")
        assert status == 200 and detail["snapshot_fingerprint"] == current.fingerprint
        assert [x["player_id"] for x in detail["rows"]][:1] == [current.rows[0].player_id]
        assert _request("GET", source.base_url + rank_root + "/history/2")[0] == 409

        fixture = {
            "country": {"run": country_run, "branch": country_branch, "snapshot": real_countries},
            "tournament": {
                "run": tournament_run, "branch": tournament_branch,
                "calendar": real_calendar, "history": real_history,
            },
            "ranking": {
                "run": ranking_run, "branch": ranking_branch,
                "metadata": ranking_history, "snapshot": detail,
                "leader": current.rows[0].player_id,
            },
        }
        (root / "fixture.json").write_text(json.dumps(fixture, indent=2))
    before_browser = _dump(db)

    api = f"http://127.0.0.1:{API_PORT}"
    frontend = f"http://127.0.0.1:{WEB_PORT}"
    server_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")
    server = subprocess.Popen(
        [sys.executable, __file__, "--serve", "--root", str(root)],
        stdout=server_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    vite = subprocess.Popen(
        ["npm", "--prefix", "web", "run", "dev", "--",
         "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=frontend_log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    requests: list[tuple[str, str]] = []
    browser_errors: list[str] = []
    blocked: list[str] = []
    screenshots: list[str] = []
    cases: list[str] = []
    try:
        wait_http(api + "/health", server)
        wait_http(frontend, vite)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()

            def new_page(run_id: str):
                context = browser.new_context(viewport={"width": 1440, "height": 980})
                def loopback_only(route):
                    parsed = urlsplit(route.request.url)
                    if parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port in {
                        API_PORT, WEB_PORT,
                    }:
                        route.continue_()
                    else:
                        blocked.append(route.request.url)
                        route.abort()
                context.route("**/*", loopback_only)
                context.add_init_script(
                    "localStorage.setItem('beta_engine:viewer_active_product_run_id', "
                    + json.dumps(run_id) + ");"
                    "if (!localStorage.getItem('squash-engine-language-v1')) "
                    "localStorage.setItem('squash-engine-language-v1','en');"
                )
                page = context.new_page()
                page.on("pageerror", lambda e: browser_errors.append(str(e)))
                page.on("request", lambda req: requests.append((req.method, req.url))
                        if req.url.startswith(api) else None)
                return context, page

            def screenshot(page, name):
                page.screenshot(path=str(root / name), full_page=True)
                screenshots.append(name)

            country_context, page = new_page(country_run)
            page.goto(frontend + "/viewer/stats/country-stats")
            country_table = page.get_by_role("table", name="Public country statistics")
            expect(country_table).to_be_visible(timeout=30000)
            expect(country_table).to_contain_text("CZE")
            expect(country_table).to_contain_text("EGY")
            expect(page.get_by_text("Showing 1–2 of 2")).to_be_visible()
            expect(page.get_by_text("13")).to_have_count(0)
            assert _dump(db) == before_browser
            screenshot(page, "country-stats-real-en.png")
            cases.append("country_stats_real_saved")

            page.goto(frontend + "/viewer/countries/all")
            expect(page.get_by_role("table", name="Verified Saved country directory")).to_be_visible()
            assert _dump(db) == before_browser
            country_context.close()

            tour_context, page = new_page(tournament_run)
            page.goto(frontend + "/viewer/tour/categories")
            expect(page.get_by_role("table", name="Saved tournament category summary")).to_be_visible(timeout=30000)
            table = page.get_by_role("table", name="Selected category tournaments")
            expect(table).to_be_visible()
            expect(table).to_contain_text("Old Open")
            expect(table).to_contain_text("Current Open")
            screenshot(page, "categories-real-en.png")
            cases.append("tournament_categories_real_saved")

            page.goto(frontend + "/viewer/tour/champions")
            champion_table = page.get_by_role("table", name="Published past champions")
            expect(champion_table).to_be_visible(timeout=30000)
            expect(champion_table.get_by_role("link", name="A")).to_be_visible()
            expect(champion_table).to_contain_text("Current Open")
            expect(champion_table).not_to_contain_text("Old Open")
            screenshot(page, "champions-real-en.png")
            cases.append("tournament_champions_real_saved")

            page.goto(frontend + "/viewer/stats/tournament-stats")
            expect(page.get_by_role(
                "table", name="Tournament statistics by season and category",
            )).to_be_visible(timeout=30000)
            expect(page.get_by_text("Calendar events")).to_be_visible()
            screenshot(page, "tournament-stats-real-en.png")
            cases.append("tournament_stats_real_saved")

            page.goto(frontend + "/viewer/stats/title-leaders")
            leaders = page.get_by_role("table", name="Published title leaderboard")
            expect(leaders).to_be_visible(timeout=30000)
            expect(leaders.get_by_role("link", name="A", exact=True)).to_be_visible()
            screenshot(page, "title-leaders-real-en.png")
            cases.append("title_leaders_real_saved")

            # A forged historical response must fail closed. The positive path
            # above and the corrected retry below both use actual SQLite HTTP.
            forged = json.loads(json.dumps(real_history))
            forged["viewer_branch_id"] = "foreign-branch"
            tour_endpoint = tour_root + "/tournaments"
            def forged_history(route):
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(forged))
            tour_context.route("**" + tour_endpoint, forged_history)
            page.goto(frontend + "/viewer/tour/champions")
            expect(page.get_by_role("alert")).to_contain_text("do not have the same verified source")
            expect(page.get_by_role("table")).to_have_count(0)
            tour_context.unroute("**" + tour_endpoint, forged_history)
            page.get_by_role("button", name="Retry read (GET)").click()
            expect(page.get_by_role("table", name="Published past champions")).to_be_visible()
            assert _dump(db) == before_browser
            screenshot(page, "tour-source-guard-recovery-en.png")
            cases.append("tournament_foreign_branch_rejected_and_retried")
            tour_context.close()

            rank_context, page = new_page(ranking_run)
            page.goto(frontend + "/viewer/rankings/no1-history")
            hist_table = page.get_by_role(
                "table", name="Publications for No. 1 verification",
            )
            expect(hist_table).to_be_visible(timeout=30000)
            expect(page.get_by_text("Showing 1–2 of 2")).to_be_visible()
            expect(hist_table.get_by_role("link", name="Open ranking #2")).to_have_count(0)
            assert not any(
                url.endswith("/rankings/history/1") for method, url in requests
                if method == "GET"
            ), "The No.1 page fetched ranking details without user request"
            screenshot(page, "no1-before-inspection-real-en.png")
            page.get_by_role("button", name="Verify No. 1 (GET)").first.click()
            expect(page.get_by_role("link", name=fixture["ranking"]["leader"])).to_be_visible()
            assert sum(url.endswith("/rankings/history/1") for method, url in requests
                       if method == "GET") == 1
            assert not any(url.endswith("/rankings/history/0")
                           for method, url in requests if method == "GET")
            screenshot(page, "no1-proven-real-en.png")
            cases.append("no1_real_published_detail_on_demand")

            # No forged winner may appear when a fingerprint mismatches its
            # independently published history metadata.
            forged_detail = json.loads(json.dumps(detail))
            forged_detail["snapshot_fingerprint"] = "f" * 64
            detail_endpoint = rank_root + "/history/1"
            def forged_ranking(route):
                route.fulfill(status=200, content_type="application/json",
                              body=json.dumps(forged_detail))
            rank_context.route("**" + detail_endpoint, forged_ranking)
            page.reload()
            expect(hist_table).to_be_visible(timeout=30000)
            page.get_by_role("button", name="Verify No. 1 (GET)").first.click()
            expect(page.get_by_role("alert")).to_contain_text("Detail disagrees with history")
            expect(page.get_by_role("link", name=fixture["ranking"]["leader"])).to_have_count(0)
            rank_context.unroute("**" + detail_endpoint, forged_ranking)
            page.get_by_role("button", name="Retry read (GET)").click()
            expect(page.get_by_role("link", name=fixture["ranking"]["leader"])).to_be_visible()
            assert _dump(db) == before_browser
            screenshot(page, "no1-forged-fingerprint-rejected-real-en.png")
            cases.append("no1_fingerprint_mismatch_rejected_and_retried")
            rank_context.close()

            assert not browser_errors, browser_errors
            assert not blocked, blocked
            assert all(method == "GET" for method, _ in requests), requests
            assert _dump(db) == before_browser
            browser.close()
    finally:
        stop_process(vite)
        stop_process(server)
        frontend_log.close()
        server_log.close()

    (root / "evidence.json").write_text(json.dumps({
        "scope": "real persisted Saved legacy W61 projections / actual HTTP + Chromium",
        "test_cases": cases, "run_ids": [country_run, tournament_run, ranking_run],
        "snapshots": screenshots,
        "real_sqlite": True,
        "browser_requests_get_only": True,
        "browser_did_not_mutate_database": True,
        "positive_http_responses_unmodified": True,
        "interception_only_negative_cases": True,
        "private_or_future_sporting_data_not_inferred": True,
        "browser_errors": browser_errors,
        "external_requests": blocked,
    }, indent=2))


if __name__ == "__main__":
    main()
