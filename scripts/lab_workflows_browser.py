"""Real Chromium, production Lab APIs and SQLite session/review/restart acceptance."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_rows(path: Path) -> dict:
    """Every non-Lab table stays unchanged during isolated Lab experiments."""
    with sqlite3.connect(path) as db:
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return {
            name: sorted(db.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall(), key=repr)
            for (name,) in tables if name not in {"match_lab_sessions", "tournament_lab_sessions"}
        }


def hold_save_delivery(page, delayed):
    # A factory binds each loop iteration without introducing a second
    # callback argument: Playwright uses that position for Request.
    def handle(route):
        if route.request.method == "PUT":
            delayed.append((route, route.fetch()))
            page.evaluate("window.__labSaveReady = true")
        else:
            route.continue_()

    return handle


def main() -> None:
    from playwright.sync_api import expect, sync_playwright

    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_saved_revision_history_api import (
        ApiServer,
        _create_run,
        _request,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/google-chrome"))
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "labs.sqlite"
    if path.exists():
        raise ValueError("Use a fresh disposable Lab fixture")
    expect.set_options(timeout=30000)
    evidence = {"sessions": {}, "browser_errors": []}
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, original_head = _create_run(server, display_name="Lab isolation target")
        before = run_rows(path)
        with (root / "frontend.log").open("w") as log:
            frontend = subprocess.Popen(
                ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                wait_http("http://127.0.0.1:5173", frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox", "--disable-gpu"])
                    context = browser.new_context(viewport={"width": 1440, "height": 1000})
                    context.add_init_script("localStorage.setItem('squash-engine-language-v1','en')")
                    page = context.new_page()
                    page.on("pageerror", lambda error: (evidence["browser_errors"].append(str(error)), print("Browser error:", str(error), flush=True)))
                    executions = []
                    page.on("request", lambda request: executions.append(request.url)
                            if request.method == "POST" and request.url.endswith("/run") else None)

                    for kind, label, seed_key in (("match", "Match", "seed"), ("tournament", "Tournament", "match_seed")):
                        base = f"{server.base_url}/admin/labs/{kind}"
                        page.goto(f"http://127.0.0.1:5173/admin/labs/{kind}")
                        page.get_by_role("button", name="New Test Session from", exact=False).first.click()
                        editor = page.get_by_label(f"{label} Lab scenario JSON")
                        expect(page.get_by_role("button", name="Run Test Session", exact=True)).to_be_enabled()
                        session_id = page.get_by_label(f"Open {label} Test Session").input_value()
                        scenario = json.loads(editor.input_value())
                        scenario[seed_key] += 1
                        editor.fill(json.dumps(scenario))
                        page.get_by_role("button", name="Save Test Session", exact=True).click()
                        expect(page.get_by_role("button", name="Run Test Session", exact=True)).to_be_enabled()
                        page.get_by_role("button", name="Run Test Session", exact=True).click()
                        expect(page.get_by_role("table", name=f"{label} Lab {'results' if kind == 'match' else 'match results'}", exact=True)).to_be_visible()
                        executed = len(executions)
                        selector = page.get_by_label("Match Lab winner filter" if kind == "match" else "Tournament Lab match status filter")
                        selector.select_option(index=1)
                        selector.select_option("all")
                        assert len(executions) == executed

                        # A real second writer updates the saved session. The
                        # browser's dirty buffer must survive inventory refresh.
                        local = {**scenario, seed_key: scenario[seed_key] + 10}
                        editor.fill(json.dumps(local))
                        status, items = _request("GET", base + "/sessions")
                        assert status == 200
                        stored = next(item for item in items if item["session_id"] == session_id)
                        remote = {**stored["scenario"], seed_key: scenario[seed_key] + 20}
                        status, updated = _request("PUT", base + "/sessions/" + session_id, {
                            "expected_session_fingerprint": stored["session_fingerprint"], "scenario": remote,
                        })
                        assert status == 200, updated
                        page.get_by_role("button", name="Refresh Test Sessions", exact=True).click()
                        expect(page.get_by_role("alert")).to_contain_text("saved Test Session changed")
                        assert json.loads(editor.input_value()) == local
                        expect(page.get_by_role("button", name="Run Test Session", exact=True)).to_be_disabled()
                        expect(page.get_by_role("button", name="Reload saved Test Session", exact=True)).to_be_disabled()
                        page.screenshot(path=str(root / f"{kind}-conflict.png"), full_page=True)
                        page.get_by_role("checkbox", name="Discard local edits when reloading").check()
                        page.get_by_role("button", name="Reload saved Test Session", exact=True).click()
                        assert json.loads(editor.input_value()) == updated["scenario"]

                        # Delay only delivery of a genuine production Save
                        # response; no response or simulation is fabricated.
                        delayed = []

                        hold_save = hold_save_delivery(page, delayed)
                        pattern = f"**/admin/labs/{kind}/sessions/{session_id}"
                        page.route(pattern, hold_save)
                        submitted = {**updated["scenario"], seed_key: scenario[seed_key] + 30}
                        page.evaluate("window.__labSaveReady = false")
                        editor.fill(json.dumps(submitted))
                        page.get_by_role("button", name="Save Test Session", exact=True).click()
                        expect(page.get_by_role("button", name="Saving…" if kind == "tournament" else "Save Test Session", exact=True)).to_be_disabled()
                        # Wait through browser events until the real response
                        # has reached the interception callback.
                        page.wait_for_function("window.__labSaveReady === true")
                        assert len(delayed) == 1
                        newer = {**submitted, seed_key: scenario[seed_key] + 40}
                        editor.fill(json.dumps(newer))
                        delayed[0][0].fulfill(response=delayed[0][1])
                        page.unroute(pattern, hold_save)
                        expect(page.get_by_role("button", name="Save Test Session", exact=True)).to_be_enabled()
                        assert json.loads(editor.input_value()) == newer
                        expect(page.get_by_role("button", name="Run Test Session", exact=True)).to_be_disabled()
                        page.get_by_role("button", name="Save Test Session", exact=True).click()
                        expect(page.get_by_role("button", name="Run Test Session", exact=True)).to_be_enabled()
                        evidence["sessions"][kind] = {"session_id": session_id, "seed_key": seed_key, "seed": newer[seed_key]}

                    page.goto("http://127.0.0.1:5173/admin/labs/player")
                    page.get_by_role("button", name="Run scenario", exact=True).click()
                    expect(page.get_by_role("table", name="Player Lab variant comparison", exact=True)).to_be_visible()
                    executed = len(executions)
                    page.get_by_label("Player Lab variant filter").select_option(index=1)
                    page.get_by_label("Player Lab timeline limit").select_option("10")
                    assert len(executions) == executed
                    page.screenshot(path=str(root / "player-comparison.png"), full_page=True)
                    assert run_rows(path) == before

                    # Only this separately reviewed Apply may change Run data.
                    page.goto("http://127.0.0.1:5173/admin/labs/tournament")
                    source = evidence["sessions"]["tournament"]["session_id"]
                    page.get_by_label("Open Tournament Test Session").select_option(source)
                    page.get_by_label("Tournament Lab target Run ID").fill(run)
                    page.get_by_label("Tournament Lab target Branch ID").fill(branch)
                    page.get_by_label("Tournament Lab target event ID").fill("reviewed-lab-event")
                    page.get_by_role("button", name="Preview Run draft", exact=True).click()
                    apply_button = page.get_by_role("button", name="Apply to Run Working Draft", exact=True)
                    expect(apply_button).to_be_enabled()
                    assert run_rows(path) == before
                    with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/run-draft-apply")) as response:
                        apply_button.click()
                    assert response.value.status == 201, response.value.text()
                    applied = response.value.json()
                    expect(page.get_by_text("Proposal is staged in the target Run Working Draft.", exact=False)).to_be_visible()
                    status, saved = _request("POST", f"{server.base_url}/run-containers/{run}/branches/{branch}/working-draft/save", {
                        "expected_draft_version": applied["working_draft_version"],
                    })
                    assert status == 201, saved
                    assert saved["saved_revision"]["kind"] == "tournament_lab_run_draft"
                    assert saved["saved_revision"]["revision_id"] != original_head
                    assert saved["working_draft"]["status"] == "clean"
                    evidence["saved_proposal"] = saved["saved_revision"]["revision_id"]
                    evidence["run_id"], evidence["branch_id"] = run, branch
                    assert evidence["browser_errors"] == []
                    browser.close()
            finally:
                stop_process(frontend)
        server.server.should_exit = True
        server.thread.join(timeout=30)
        if server.thread.is_alive():
            raise RuntimeError("Lab API did not drain before teardown")

    with ApiServer(database_url=f"sqlite:///{path}") as reopened:
        for kind, item in evidence["sessions"].items():
            status, sessions = _request("GET", f"{reopened.base_url}/admin/labs/{kind}/sessions")
            assert status == 200
            stored = next(row for row in sessions if row["session_id"] == item["session_id"])
            assert stored["scenario"][item["seed_key"]] == item["seed"]
        status, branches = _request("GET", f"{reopened.base_url}/run-branches?run_id={run}")
        assert status == 200
        assert next(row for row in branches["run_branches"] if row["branch_id"] == branch)["saved_head_revision_id"] == evidence["saved_proposal"]
    (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
    print("Real Lab browser, independent sessions, reviewed Apply/Save and SQLite restart PASS")


if __name__ == "__main__":
    main()
