"""Real Chromium + legacy season Run + SQLite exact-player comparison acceptance.

This gate intentionally tests the older /runs/{run_id}/players read model.
It does NOT prove Product Run/Branch Saved player compatibility or historic H2H.
No route mocking on the positive path; every compared player is persisted in SQLite.
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
API_PORT, WEB_PORT = 8024, 5173

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
        raise ValueError("Use only a fresh work/<case> directory")
    if args.serve:
        import uvicorn
        from beta_engine.main import create_app
        from tests.support.world_packages import materialize_test_world_package
        from beta_engine.domain.countries import CountriesConfig
        countries = root / "countries.json"
        materialize_test_world_package(
            root / "world_packages", CountriesConfig.model_validate(
                json.loads(countries.read_text())
            )
        )
        uvicorn.run(
            create_app(
                database_url=f"sqlite:///{root / 'world.sqlite'}",
                countries_config_path=str(countries),
                manual_player_overrides_config_path=str(root / "overrides.json"),
                world_packages_root=str(root / "world_packages"),
            ),
            host="127.0.0.1", port=API_PORT, log_level="warning",
        )
        return

    from playwright.sync_api import expect, sync_playwright
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_player_career_history_api import (
        ApiServer, COUNTRIES_FIXTURE, _request, _write_fixture,
    )
    from tests.api.test_player_generation_calendar_gate import _dump

    work.mkdir(exist_ok=True)
    root.mkdir(exist_ok=False)
    countries = root / "countries.json"
    overrides = root / "overrides.json"
    db = root / "world.sqlite"
    # The canonical single-country test fixture has only ~34 players, so it
    # cannot prove lookup beyond the 50-row discovery page. Replicate the
    # genuine generator configuration across three distinct countries instead
    # of fabricating player records or mocking API results.
    base_country = COUNTRIES_FIXTURE["countries"][0]
    countries_fixture = {
        **COUNTRIES_FIXTURE,
        "countries": [
            {**base_country, "code": code, "name": name}
            for code, name in (
                ("AAA", "Alpha"), ("BBB", "Beta"), ("CCC", "Gamma")
            )
        ],
    }
    _write_fixture(countries, countries_fixture)
    _write_fixture(overrides, {"overrides": []})
    with ApiServer(
        database_url=f"sqlite:///{db}",
        countries_config_path=str(countries),
        manual_overrides_config_path=str(overrides),
    ) as source:
        run_id = "viewer-exact-comparison"
        status, run = _request(
            "POST", source.base_url + "/runs",
            {"run_id": run_id, "seed": 101, "season": 2027},
        )
        assert status == 201, run
        status, first_page = _request(
            "GET", source.base_url + f"/runs/{run_id}/players?limit=50&offset=0"
        )
        assert status == 200 and first_page["total"] > 50, first_page
        status, second_page = _request(
            "GET", source.base_url + f"/runs/{run_id}/players?limit=50&offset=50"
        )
        assert status == 200 and second_page["players"], second_page
        a, b = first_page["players"][0], second_page["players"][0]
        assert a["player_id"] != b["player_id"]
        originals = []
        for player in (a,b):
            status, detail = _request(
                "GET", source.base_url + "/runs/" + run_id +
                "/players/" + quote(player["player_id"], safe="")
            )
            assert status == 200 and detail["player_id"] == player["player_id"]
            originals.append(detail)
    initial = _dump(db)

    api = f"http://127.0.0.1:{API_PORT}"
    frontend_url = f"http://127.0.0.1:{WEB_PORT}"
    backend_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")

    def start_backend():
        proc = subprocess.Popen(
            [sys.executable, __file__, "--serve", "--root", str(root)],
            stdout=backend_log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(api + "/health", proc)
        return proc

    server = start_backend()
    frontend = subprocess.Popen(
        ["npm", "--prefix", "web", "run", "dev", "--",
         "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=frontend_log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    errors: list[str] = []
    requests: list[tuple[str,str]] = []
    blocked: list[str] = []
    try:
        wait_http(frontend_url, frontend)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1400, "height": 1100})
            def local_only(route):
                p = urlsplit(route.request.url)
                if p.scheme == "http" and p.hostname == "127.0.0.1" and p.port in {
                    API_PORT, WEB_PORT
                }:
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()
            context.route("**/*", local_only)
            context.add_init_script(
                "localStorage.setItem('beta_engine:viewer_active_run_id', "
                + json.dumps(run_id) + ")"
            )
            context.add_init_script(
                "localStorage.setItem('squash-engine-language-v1', 'en')"
            )
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda req: requests.append((req.method, req.url))
                if req.url.startswith(api) else None)
            route = (
                frontend_url + "/viewer/players/compare?playerA=" +
                quote(a["player_id"], safe="") + "&playerB=" +
                quote(b["player_id"], safe="")
            )
            page.goto(route)
            expected_a = page.get_by_label("Player A comparison fields")
            expected_b = page.get_by_label("Player B comparison fields")
            expect(expected_a).to_be_visible(timeout=30000)
            expect(expected_b).to_be_visible(timeout=30000)
            expect(expected_a).to_contain_text(a["player_id"])
            expect(expected_b).to_contain_text(b["player_id"])
            expect(expected_a).to_contain_text(str(originals[0]["overall"]))
            expect(expected_b).to_contain_text(str(originals[1]["overall"]))
            expect(page.get_by_text(
                "These are active-Run player fields, not a historical Saved Branch H2H result."
            )).to_be_visible()
            assert any(
                url.endswith("/runs/" + run_id + "/players/" +
                             quote(b["player_id"], safe=""))
                for method,url in requests if method == "GET"
            ), requests
            assert len([1 for method,_ in requests if method != "GET"]) == 0, requests
            assert _dump(db) == initial, "Viewer comparison wrote to SQLite"
            page.screenshot(path=str(root / "exact-comparison-en.png"), full_page=True)

            # A nonexistent exact ID is not silently replaced by the first
            # matching sample player. Test the real HTTP 404 from the backend.
            bogus = "definitely-not-a-real-player"
            with page.expect_response(lambda response: (
                response.request.method == "GET" and
                response.url.endswith("/players/" + bogus)
            )) as missing:
                page.get_by_label("Second player ID").fill(bogus)
                page.get_by_role("button", name="Compare players").click()
            assert missing.value.status == 404
            expect(page.get_by_role("alert")).to_contain_text(
                "One or both player details could not be retrieved."
            )
            assert _dump(db) == initial
            page.screenshot(path=str(root / "missing-player-en.png"), full_page=True)

            # Correct the query without a page refresh, then switch language.
            page.get_by_label("Second player ID").fill(b["player_id"])
            page.get_by_role("button", name="Compare players").click()
            expect(page.get_by_label("Player B comparison fields")).to_contain_text(
                b["player_id"]
            )
            # Viewer shell may not expose Admin's Language combobox.
            # The supported persisted language preference is the same CS/EN
            # source consumed by LanguageContext on a real page reload.
            page.evaluate(
                "localStorage.setItem('squash-engine-language-v1', 'cs')"
            )
            page.reload()
            expect(page.get_by_text(
                "Jde o atributy aktivního Runu, nikoliv o historické vzájemné zápasy ze Saved Branch."
            )).to_be_visible()
            assert _dump(db) == initial
            page.screenshot(path=str(root / "exact-comparison-cs.png"), full_page=True)
            assert not errors, errors
            assert not blocked, blocked
            assert all(method == "GET" for method, _ in requests), requests
            (root / "evidence.json").write_text(json.dumps({
                "source": "real legacy season Run /runs endpoints + persisted SQLite",
                "run_id": run_id, "total_players": first_page["total"],
                "a": a["player_id"], "b_beyond_first_50": b["player_id"],
                "positive_exact_detail": True, "missing_404": True,
                "languages": ["en","cs"], "sqlite_unchanged": True,
                "no_mutations": True, "browser_errors": errors,
                "untrusted_external_requests": blocked,
            }, indent=2))
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        backend_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
