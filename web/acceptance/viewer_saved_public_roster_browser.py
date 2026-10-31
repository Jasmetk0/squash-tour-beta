"""Read-only Saved Viewer player roster browser acceptance.

Positive evidence: actual Saved Product Run, repository capture, HTTP API,
Chromium and persistent SQLite. Only adversarial frontend responses are
intercepted to prove fail-closed rendering of forged public roster fields.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
API_PORT, WEB_PORT = 8027, 5173


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
        raise ValueError("Acceptance fixture must be inside a fresh work/<case> directory")
    if args.serve:
        import uvicorn
        from beta_engine.main import create_app
        uvicorn.run(
            create_app(database_url=f"sqlite:///{root / 'viewer.sqlite'}"),
            host="127.0.0.1", port=API_PORT, log_level="warning",
        )
        return

    from playwright.sync_api import expect, sync_playwright
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
    from tests.application.test_viewer_people_read_model import _world, _lifecycle, _sporting
    from beta_engine.application.run_working_draft_service import RunWorkingDraftService
    from beta_engine.infrastructure.db.initial_world_state import put_initial_world
    from beta_engine.infrastructure.db.player_lifecycle_state import put_lifecycle
    from beta_engine.infrastructure.db.player_sporting_state import put_sporting
    from tests.api.test_player_generation_calendar_gate import _dump

    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    db = root / "viewer.sqlite"
    database_url = f"sqlite:///{db}"
    with ApiServer(database_url=database_url) as source:
        run_id, branch_id, _ = _create_run(source, display_name="Saved Public Roster Browser")
        repo = source.app.state.runtime.repository
        world = _world().model_copy(update={"run_id": run_id, "branch_id": branch_id})
        lifecycle = _lifecycle()[0].model_copy(update={
            "run_id": run_id, "branch_id": branch_id,
            "source_initial_world_fingerprint": world.fingerprint,
            "players": tuple(p for p in _lifecycle()[0].players if p.player_id != "PROSPECT-1"),
        })
        sporting = _sporting()[0].model_copy(update={
            "run_id": run_id, "branch_id": branch_id,
            "source_initial_world_fingerprint": world.fingerprint,
            "players": tuple(p for p in _sporting()[0].players if p.player_id != "PROSPECT-1"),
        })
        with repo._session_factory.begin() as session:
            put_initial_world(session, world)
            put_lifecycle(session, lifecycle)
            put_sporting(session, sporting)
        service = RunWorkingDraftService(
            repo, lambda kind: "public-roster-browser-" + kind
        )
        draft = service.get_viewer_branch_draft(
            run_id=run_id, branch_id=branch_id
        )
        saved = service.save(
            run_id=run_id, branch_id=branch_id,
            expected_draft_version=draft.draft_version,
        )
        assert saved.saved_revision.revision_id
        endpoint = f"/viewer/runs/{quote(run_id, safe='')}/players"
        status, actual = _request("GET", source.base_url + endpoint)
        assert status == 200, (status, actual)
        assert actual["schema_version"] == "viewer_players.v1"
        assert actual["product_run_id"] == run_id
        assert actual["viewer_branch_id"] == branch_id
        assert actual["player_count"] == 2
        assert actual["active_player_count"] == 1
        assert actual["retired_player_count"] == 1
        assert actual["season_index"] == 1 and actual["week"] == 5
        assert all(all(row[k] is None for k in (
            "potential_ovr", "current_form", "match_sharpness", "long_term_fatigue"
        )) for row in actual["players"])
        assert any(row["current_ovr"] == 130 for row in actual["players"])
        assert any(row["current_ovr"] is None for row in actual["players"])
        (root / "published-roster.json").write_text(json.dumps(actual, indent=2))
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
    http_requests: list[tuple[str,str]] = []
    blocked: list[str] = []
    browser_errors: list[str] = []
    try:
        wait_http(api + "/health", server)
        wait_http(frontend, vite)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1400, "height": 960})
            def allow_loopback(route):
                parsed = urlsplit(route.request.url)
                if (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                    and parsed.port in {API_PORT, WEB_PORT}):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()
            context.route("**/*", allow_loopback)
            context.add_init_script(
                "localStorage.setItem('beta_engine:viewer_active_product_run_id',"
                + json.dumps(run_id) + ");"
                "if (!localStorage.getItem('squash-engine-language-v1')) "
                "localStorage.setItem('squash-engine-language-v1', 'en')"
            )
            page = context.new_page()
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            page.on("request", lambda request: http_requests.append((
                request.method, request.url
            )) if request.url.startswith(api) else None)
            page.goto(frontend + "/viewer/players")
            expect(page.get_by_role("table", name="Saved player directory")).to_be_visible(timeout=25000)
            expect(page.get_by_role("table")).to_contain_text("Initial One")
            expect(page.get_by_role("table")).to_contain_text("Initial Two")
            expect(page.get_by_text("Showing 1–2 of 2")).to_be_visible()
            assert _dump(db) == before_browser
            page.screenshot(path=str(root / "saved-roster-valid-en.png"), full_page=True)

            def adversarial(body):
                def replace(route):
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
                return replace

            player = actual["players"][0]
            for field in ("potential_ovr", "current_form", "match_sharpness",
                          "long_term_fatigue"):
                altered = json.loads(json.dumps(actual))
                altered["players"][0][field] = 0
                handler = adversarial(altered)
                context.route("**" + endpoint, handler)
                page.reload()
                expect(page.get_by_role("alert")).to_contain_text(
                    "invalid or foreign source data"
                )
                expect(page.get_by_role("table")).to_have_count(0)
                expect(page.get_by_text("Initial One")).to_have_count(0)
                assert _dump(db) == before_browser
                context.unroute("**" + endpoint, handler)

            for clock in [
                {"tour_entry_season_index": 2, "tour_entry_week": 1},
                {"tour_entry_season_index": 1, "tour_entry_week": 6},
                {"tour_entry_season_index": None, "tour_entry_week": 1},
            ]:
                altered = json.loads(json.dumps(actual))
                altered["players"][0].update(clock)
                handler = adversarial(altered)
                context.route("**" + endpoint, handler)
                page.reload()
                expect(page.get_by_role("alert")).to_contain_text(
                    "invalid or foreign source data"
                )
                expect(page.get_by_role("table")).to_have_count(0)
                assert _dump(db) == before_browser
                context.unroute("**" + endpoint, handler)

            # A corrected, authentic HTTP response may be explicitly retried;
            # the public roster must never show the intercepted partial source.
            handler = adversarial({
                **actual, "players": [
                    {**player, "potential_ovr": 199}, actual["players"][1]
                ]
            })
            context.route("**" + endpoint, handler)
            page.reload()
            expect(page.get_by_role("alert")).to_contain_text("invalid or foreign source data")
            context.unroute("**" + endpoint, handler)
            page.get_by_role("button", name="Retry read (GET)").click()
            expect(page.get_by_role("table", name="Saved player directory")).to_contain_text(
                "Initial One"
            )
            assert _dump(db) == before_browser
            page.screenshot(path=str(root / "saved-roster-retry-en.png"), full_page=True)

            # CS preference switch must preserve source provenance but not cause a Save.
            page.evaluate("localStorage.setItem('squash-engine-language-v1', 'cs')")
            page.reload()
            expect(page.get_by_role("table", name="Uložený seznam hráčů")).to_be_visible()
            expect(page.get_by_text("Zobrazeno 1–2 z 2")).to_be_visible()
            assert _dump(db) == before_browser
            assert not browser_errors, browser_errors
            assert not blocked, blocked
            assert all(method == "GET" for method, _ in http_requests), http_requests
            page.screenshot(path=str(root / "saved-roster-valid-cs.png"), full_page=True)
            (root / "evidence.json").write_text(json.dumps({
                "run_id": run_id, "viewer_branch_id": branch_id,
                "real_saved_revision": True, "real_http_projection": True,
                "real_sqlite": True, "chromium": True, "languages": ["cs","en"],
                "zero_private_fields_rejected": 4,
                "future_or_incomplete_tour_entry_rejected": 3,
                "corrected_get_only_retry": True,
                "no_db_mutation_during_viewer": True,
                "interception_only_for_negative_cases": True,
                "browser_errors": browser_errors, "external_requests": blocked
            }, indent=2))
            browser.close()
    finally:
        stop_process(vite)
        stop_process(server)
        server_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
