"""Actual Chromium + server worker + MatchEngine + manual final Run Save."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_tour_flow import (
        command,
        create_edition,
        execute,
        inspect,
        save_tour,
        setup,
    )
    from tests.api.test_native_full_simulation_tasks import approve_draw, wait
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium"))
    args = parser.parse_args()
    expect.set_options(timeout=90000)
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "native-task.sqlite"
    if path.exists():
        raise ValueError("Use a fresh isolated browser fixture")
    database = f"sqlite:///{path}"
    result = {}
    started_at = time.monotonic()
    with ApiServer(database_url=database) as server:
        setup(server, RunCalendar(4, 2, 2030, 1), count=4)
        create_edition(server, "worker-cup", size=4)
        for week in (3, 4):
            execute(server, command(inspect(server), "transition", name=f"browser-prepare-{week}"))
            save_tour(server)
        approve_draw(server)
        web = "http://127.0.0.1:5173"
        with (root / "frontend.log").open("w") as log:
            frontend = subprocess.Popen(["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url}, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
                    context = browser.new_context(viewport={"width": 1440, "height": 1100})
                    context.add_init_script("localStorage.setItem('squash-engine-language-v1','en')")
                    page = context.new_page()
                    page.set_default_timeout(90000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    tour = web + "/admin/runs/run/tour/editions?branch=branch"
                    page.goto(tour)
                    panel = page.get_by_role("region", name="Configured native Tour", exact=True)
                    native = page.get_by_role("region", name="Native Full Simulation", exact=True)
                    native.get_by_label("Native simulation operator").fill("Chromium Admin")
                    native.get_by_label("Native simulation reason").fill("Reviewed real worker, points, manual decisions and final closure")
                    native.get_by_role("button", name="Review server simulation", exact=True).click()
                    expect(native.get_by_text("Original Saved source", exact=False)).to_be_visible()
                    native.get_by_role("checkbox").check()
                    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/full-simulation/tasks")) as started:
                        native.get_by_role("button", name="Start as server task", exact=True).click()
                    assert started.value.status == 202, started.value.text()
                    task_id = started.value.json()["task_id"]

                    def task_card(checkpoint):
                        task = wait(server, task_id)
                        assert task["checkpoint"] == checkpoint, task
                        page.goto(web + "/admin/operations")
                        card = page.locator(f'[data-task-id="{task_id}"]')
                        expect(card).to_contain_text(checkpoint)
                        return card

                    def tour_save():
                        page.goto(tour)
                        panel.get_by_label("Confirm Tour Save").check()
                        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/calendar-tour/save")) as saved:
                            panel.get_by_role("button", name="Manual Tour Save", exact=True).click()
                        assert saved.value.status == 201, saved.value.text()

                    def resume(checkpoint):
                        card = task_card(checkpoint)
                        card.get_by_label("Task operator", exact=True).fill("Chromium Admin")
                        card.get_by_label("Task audit reason", exact=True).fill("Reviewed and manually Saved; continue original task")
                        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/continue")) as continued:
                            card.get_by_role("button", name="Explicitly resume server task", exact=True).click()
                        assert continued.value.status == 202, continued.value.text()

                    task_card("native_manual_save_required")
                    assert len(inspect(server)["edition_evidence"]["worker-cup"]["matches"]) == 3
                    tour_save()
                    resume("native_manual_save_required")
                    task_card("native_result_review_required")
                    page.goto(tour)
                    panel.get_by_label("Tour operation reason").fill("Manually reviewed all three actual match results and points")
                    panel.get_by_role("button", name="Review results", exact=True).click()
                    panel.get_by_label("Confirm Tour command").check()
                    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/calendar-tour/execute")) as confirmed:
                        panel.get_by_role("button", name="Execute confirmed operation", exact=True).click()
                    assert confirmed.value.status == 201, confirmed.value.text()
                    tour_save()
                    resume("native_result_review_required")
                    assert not any(r["points"] for r in inspect(server)["state"]["rankings"][-1]["rows"])
                    assert all(r["schema_version"] == "calendar_terminal_edition_result.v1"
                        and "first_publication_week" not in r
                        for r in inspect(server)["edition_evidence"]["worker-cup"]["results"])
                    card = task_card("native_final_closure_review_required")
                    card.get_by_label("Native task control operator").fill("Chromium Admin")
                    card.get_by_label("Native task control reason").fill("Reviewed final Closing Ranking and actual season results")
                    card.get_by_role("button", name="Review final closure", exact=True).click()
                    expect(card.get_by_text("Actually played matches: 3", exact=False)).to_be_visible()
                    expect(card.get_by_role("table", name="Final Closing Ranking")).to_contain_text("100")
                    card.get_by_label("Native closure consent").check()
                    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/closure/approve")) as approved:
                        card.get_by_role("button", name="Approve closure", exact=True).click()
                    assert approved.value.status == 200, approved.value.text()
                    card.get_by_label("Native closure consent").check()
                    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/closure/save")) as final:
                        card.get_by_role("button", name="Manually Save final closure", exact=True).click()
                    assert final.value.status == 201, final.value.text()
                    final_receipt = final.value.json()
                    resume("native_final_closure_review_required")
                    terminal = wait(server, task_id)
                    assert terminal["state"] == "complete", terminal
                    page.goto(web + "/admin/operations")
                    expect(page.locator(f'[data-task-id="{task_id}"]')).to_contain_text("Complete")
                    page.screenshot(path=str(root / "completed-native-task.png"), full_page=True)
                    assert not errors, errors
                    result = {"task_id": task_id, "terminal": terminal, "actual_match_count": 3,
                        "ranking_leader_points": 100, "manual_final_save": final_receipt}
                    browser.close()
            finally:
                stop_process(frontend)
    # Physically reopen the database with a fresh application and worker instance.
    with ApiServer(database_url=database) as restarted:
        terminal = wait(restarted, result["task_id"])
        assert terminal["state"] == "complete"
        assert terminal["original_command"] == result["terminal"]["original_command"]
        assert len(inspect(restarted)["edition_evidence"]["worker-cup"]["matches"]) == 3
        view = inspect(restarted)
        assert view["state"]["week"]["week"] == 4
        assert view["saved_completed_seasons"] == [0]
        from tests.api.test_saved_revision_history_api import _request
        code, summary = _request("GET", restarted.base_url + "/admin/runs/run/branches/branch/calendar-tour/seasons/0")
        assert code == 200, summary
        assert max(r["points"] for r in summary["selected"]["closing_ranking"]["rows"]) == 100
        result["saved_season_summary"] = summary
        result["sqlite_restart_verified"] = True
        with (root / "restarted-frontend.log").open("w") as log:
            frontend = subprocess.Popen(["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": restarted.base_url}, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                wait_http("http://127.0.0.1:5173", frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(executable_path=args.chromium, args=["--no-sandbox"])
                    context = browser.new_context(viewport={"width": 1440, "height": 1100})
                    context.add_init_script("localStorage.setItem('squash-engine-language-v1','en')")
                    page = context.new_page()
                    page.goto("http://127.0.0.1:5173/admin/operations")
                    expect(page.locator(f'[data-task-id="{result["task_id"]}"]')).to_contain_text("Complete")
                    page.screenshot(path=str(root / "restarted-completed-native-task.png"), full_page=True)
                    result["chromium_after_sqlite_restart_verified"] = True
                    browser.close()
            finally:
                stop_process(frontend)
    result["duration_seconds"] = time.monotonic() - started_at
    (root / "evidence.json").write_text(json.dumps(result, indent=2))
    print("Real Chromium native Full Simulation, match/points, manual approvals/Save, final closure and SQLite restart passed.")


if __name__ == "__main__":
    main()
