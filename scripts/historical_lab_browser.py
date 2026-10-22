"""Genuine historical Run -> three Labs -> Save -> SQLite reopen browser gate."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_saved_revision_history_api import ApiServer
    from tests.support.historical_lab import cached_history, non_lab_rows

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "labs.sqlite"
    if path.exists():
        raise ValueError("Use a fresh browser evidence directory")
    source, meta = cached_history(args.fixture or root / "fixture")
    with sqlite3.connect(source) as src, sqlite3.connect(path) as dst:
        src.backup(dst)
    before = non_lab_rows(path)
    evidence = {"source": meta, "sessions": {}, "errors": [], "results": {}}
    expect.set_options(timeout=120000)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=args.chromium, args=["--no-sandbox", "--disable-gpu"]
        )
        try:
            for stage in ("import", "restart"):
                with ApiServer(database_url=f"sqlite:///{path}") as server:
                    with (root / f"frontend-{stage}.log").open("w") as log:
                        frontend = subprocess.Popen(
                            [
                                "npm",
                                "--prefix",
                                "web",
                                "run",
                                "dev",
                                "--",
                                "--host",
                                "127.0.0.1",
                                "--port",
                                "5173",
                                "--strictPort",
                            ],
                            env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            start_new_session=True,
                        )
                        try:
                            wait_http("http://127.0.0.1:5173", frontend)
                            context = browser.new_context(
                                viewport={"width": 1440, "height": 1100}
                            )
                            context.add_init_script(
                                "localStorage.setItem('squash-engine-language-v1','en')"
                            )
                            page = context.new_page()
                            page.set_default_timeout(120000)
                            page.on(
                                "pageerror",
                                lambda error: evidence["errors"].append(str(error)),
                            )

                            def choose(lab, revision, page=page):
                                page.get_by_text(
                                    "Choose a saved historical source", exact=True
                                ).click()
                                page.get_by_label(f"{lab} source Run").select_option(
                                    meta["run"]
                                )
                                page.get_by_label(f"{lab} source Branch").select_option(
                                    meta["branch"]
                                )
                                page.get_by_label(
                                    f"{lab} source Saved Revision"
                                ).select_option(revision)

                            for kind in ("player", "match", "tournament"):
                                label = kind.title()
                                page.goto(f"http://127.0.0.1:5173/admin/labs/{kind}")
                                editor = page.get_by_label(f"{label} Lab scenario JSON")
                                if stage == "restart":
                                    page.get_by_label(
                                        f"Open {label} Test Session"
                                    ).select_option(evidence["sessions"][kind])
                                elif kind == "player":
                                    choose("Player Lab", meta["born"])
                                    page.get_by_label("Player Lab import player").fill(
                                        meta["player"]
                                    )
                                    page.get_by_label(
                                        "Player Lab experiment weeks"
                                    ).fill("2")
                                    # Hold delivery of an actual authenticated import, edit during flight.
                                    delayed = []

                                    def hold_delivery(page, delayed):
                                        def on_route(route):
                                            delayed.append(
                                                (route, route.fetch(timeout=120000))
                                            )
                                            page.evaluate(
                                                "window.__historyReady = true"
                                            )

                                        return on_route

                                    hold = hold_delivery(page, delayed)
                                    page.route(
                                        "**/admin/labs/player/import-saved-revision-player",
                                        hold,
                                    )
                                    page.get_by_role(
                                        "button",
                                        name="Import historical Player scenario",
                                        exact=True,
                                    ).click()
                                    page.wait_for_function(
                                        "window.__historyReady === true", timeout=120000
                                    )
                                    edited = json.loads(editor.input_value())
                                    edited["scenario_id"] = "newer-local-edit"
                                    editor.fill(json.dumps(edited))
                                    delayed[0][0].fulfill(response=delayed[0][1])
                                    page.unroute(
                                        "**/admin/labs/player/import-saved-revision-player",
                                        hold,
                                    )
                                    expect(
                                        page.get_by_role(
                                            "button",
                                            name="Import historical Player scenario",
                                            exact=True,
                                        )
                                    ).to_be_enabled()
                                    assert json.loads(editor.input_value()) == edited
                                    page.get_by_role(
                                        "button",
                                        name="Import historical Player scenario",
                                        exact=True,
                                    ).click()
                                    expect(
                                        page.get_by_label(
                                            "Player Lab historical provenance"
                                        )
                                    ).to_contain_text(meta["born"])
                                    scenario = json.loads(editor.input_value())
                                    assert (
                                        scenario["schema_version"]
                                        == "player_test_lab_scenario.v2"
                                    )
                                    assert (
                                        scenario["player"]["player_id"]
                                        == meta["player"]
                                    )
                                    assert (
                                        scenario["start_week"]["calendar"][
                                            "weeks_per_year"
                                        ]
                                        == 52
                                    )
                                    page.get_by_role(
                                        "button",
                                        name="Save Player Test Session",
                                        exact=True,
                                    ).click()
                                    expect(
                                        page.get_by_label("Open Player Test Session")
                                    ).not_to_have_value("")
                                elif kind == "match":
                                    page.get_by_role(
                                        "button",
                                        name="New Test Session from",
                                        exact=False,
                                    ).first.click()
                                    expect(
                                        page.get_by_label("Open Match Test Session")
                                    ).not_to_have_value("")
                                    choose("Match Lab", meta["born"])
                                    for side, player in (
                                        ("player_a", meta["player"]),
                                        ("player_b", meta["opponent"]),
                                    ):
                                        page.get_by_label(
                                            "Match Lab import Player ID"
                                        ).fill(player)
                                        page.get_by_label(
                                            "Match Lab import side"
                                        ).select_option(side)
                                        with page.expect_response(
                                            lambda r: (
                                                r.request.method == "POST"
                                                and r.url.endswith(
                                                    "/import-saved-revision-player"
                                                )
                                            ),
                                            timeout=120000,
                                        ) as response:
                                            page.get_by_role(
                                                "button",
                                                name="Import historical player",
                                                exact=True,
                                            ).click()
                                        assert response.value.status == 200, (
                                            response.value.text()
                                        )
                                        expect(
                                            page.get_by_role(
                                                "button",
                                                name="Import historical player",
                                                exact=True,
                                            )
                                        ).to_be_enabled()
                                    assert (
                                        json.loads(editor.input_value())["context"][
                                            "player_a"
                                        ]["player"]["player_id"]
                                        == meta["player"]
                                    )
                                else:
                                    choose("Tournament Lab", meta["drawn"])
                                    page.get_by_label(
                                        "Tournament Lab import event"
                                    ).fill(meta["event"])
                                    page.get_by_role(
                                        "button",
                                        name="Copy historical tournament",
                                        exact=True,
                                    ).click()
                                    expect(
                                        page.get_by_label(
                                            "Open Tournament Test Session"
                                        )
                                    ).not_to_have_value("")
                                evidence["sessions"][kind] = page.get_by_label(
                                    f"Open {label} Test Session"
                                ).input_value()
                                button = (
                                    "Run scenario"
                                    if kind == "player"
                                    else "Run Test Session"
                                )
                                expect(
                                    page.get_by_role("button", name=button, exact=True)
                                ).to_be_enabled()
                                with page.expect_response(
                                    lambda r: (
                                        r.request.method == "POST"
                                        and r.url.endswith("/run")
                                    ),
                                    timeout=120000,
                                ) as response:
                                    page.get_by_role(
                                        "button", name=button, exact=True
                                    ).click()
                                assert response.value.status == 200, (
                                    response.value.text()
                                )
                                result = response.value.json()
                                if stage == "restart":
                                    assert result == evidence["results"][kind]
                                else:
                                    evidence["results"][kind] = result
                                table = (
                                    "Player Lab variant comparison"
                                    if kind == "player"
                                    else "Match Lab results"
                                    if kind == "match"
                                    else "Tournament Lab match results"
                                )
                                expect(
                                    page.get_by_role("table", name=table, exact=True)
                                ).to_be_visible()
                                page.screenshot(
                                    path=str(root / f"{stage}-{kind}.png"),
                                    full_page=True,
                                )
                                assert non_lab_rows(path) == before
                            context.close()
                        finally:
                            stop_process(frontend)
                    server.server.should_exit = True
                    server.thread.join(timeout=30)
                    if server.thread.is_alive():
                        raise RuntimeError("Historical Lab API did not stop")
                    server.app.state.runtime.repository._session_factory.kw[
                        "bind"
                    ].dispose()
            assert not evidence["errors"], evidence["errors"]
        finally:
            browser.close()
    (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
    print(
        "Historical born native W52 / three Labs / delayed import / Save / restart / exact replay / non-mutation PASS"
    )


if __name__ == "__main__":
    main()
