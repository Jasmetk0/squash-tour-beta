"""Native Chromium + production HTTP/SQLite, page death and actual SIGKILL recovery.

Test-only gates delay genuine writers; never inject sport, Save or RNG outputs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from threading import Event
from urllib.request import urlopen

import uvicorn
from admin_first_tournament_smoke import browser_click, create_smoke_app, setup_run
from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests/application"))
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from tests.support.full_simulation_http_flow import (
    TransactionGate,
    expire,
    routes,
    snapshot,
)


def serve(root, port):
    app = create_smoke_app(root)
    factory = create_session_factory(
        create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{root}/browser.sqlite"))
    )
    gate = TransactionGate(factory)
    routes._driver = gate.driver

    @app.post("/__test/task-gate/{action}")
    def control(action: str, after_groups: int = 0):
        if action == "arm":
            gate.arm(after_groups=after_groups)
        elif action == "advance":
            old = gate.release
            gate.release = Event()
            gate.arm(after_groups=after_groups)
            old.set()
        elif action == "release":
            gate.release.set()
        elif action == "expire":
            expire(factory)
        else:
            raise ValueError(action)
        return {"reached": gate.reached.is_set()}

    @app.get("/__test/task-gate")
    def reached():
        return {"reached": gate.reached.is_set()}

    @app.get("/__test/task-evidence")
    def evidence(run_id: str, branch_id: str):
        return snapshot(factory, run_id, branch_id)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def acceptance(root, port, base_url, chromium):
    if root.exists():
        raise ValueError("Use a fresh disposable directory")
    root.mkdir(parents=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    api = f"http://127.0.0.1:{port}"
    processes = []
    logs = []

    def start_server(directory, server_port):
        log = (directory / "process.log").open("a")
        logs.append(log)
        proc = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--serve",
                str(directory),
                "--port",
                str(server_port),
            ],
            stdout=log,
            stderr=log,
        )
        processes.append(proc)
        for _ in range(200):
            if proc.poll() is not None:
                raise RuntimeError(f"Server exited: {directory}")
            try:
                with urlopen(f"http://127.0.0.1:{server_port}/health", timeout=1):
                    return proc
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("Server did not start")

    process = start_server(root, port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chromium,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.smoke_pending_requests = set()
            page.smoke_dialogs = []
            page.on("request", lambda r: page.smoke_pending_requests.add(r))
            page.on("requestfinished", lambda r: page.smoke_pending_requests.discard(r))
            page.on("requestfailed", lambda r: page.smoke_pending_requests.discard(r))
            page.on("dialog", lambda d: d.accept())
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def request(method, path, body=None, status=200, api_root=api):
                r = context.request.fetch(
                    api_root + path,
                    method=method,
                    **({"data": body} if body is not None else {}),
                    timeout=240000,
                )
                assert r.status == status, (path, r.status, r.text()[:1200])
                return r.json()

            def wait(predicate, label):
                deadline = time.monotonic() + 240
                while time.monotonic() < deadline:
                    value = predicate()
                    if value:
                        return value
                    time.sleep(0.1)
                raise AssertionError(label)

            try:
                run_url = setup_run(page, base_url, artifacts)
                run_id = run_url.split("/admin/runs/", 1)[1]
                branch = request("GET", "/run-branches?run_id=" + run_id)[
                    "run_branches"
                ][0]["branch_id"]
                scope = (
                    f"/admin/runs/{run_id}/branches/{branch}/authoritative-simulation"
                )
                evidence_url = (
                    f"/__test/task-evidence?run_id={run_id}&branch_id={branch}"
                )
                for review, approval, commit in [
                    (
                        "Preview actual Entry Field",
                        "Approve reviewed Entry Field",
                        "Commit reviewed Entry Field",
                    ),
                    (
                        "Review first Draw Input",
                        "Approve Draw Input",
                        "Commit reviewed Draw Input",
                    ),
                    (
                        "Review initial bracket generation",
                        "Approve initial bracket generation",
                        "Generate reviewed initial Draw",
                    ),
                    (
                        "Preview complete Week Schedule",
                        "Approve full Week Schedule",
                        "Commit reviewed Week Schedule",
                    ),
                ]:
                    browser_click(page, review)
                    page.get_by_label(approval, exact=True).check()
                    browser_click(page, commit)
                original = request("GET", evidence_url)
                page.goto(run_url + "/simulate?branch=" + branch)
                page.get_by_label("Full Simulation operator", exact=True).fill(
                    "Native server task operator"
                )
                page.get_by_label("Full Simulation audit reason", exact=True).fill(
                    "Original server owned intent"
                )
                browser_click(page, "Review authoritative Full Simulation")
                page.get_by_label("Confirm authoritative simulation").check()
                # Copy the identical pre-task world for uninterrupted equivalence.
                reference = root.parent / (root.name + "-reference")
                shutil.copytree(
                    root,
                    reference,
                    ignore=shutil.ignore_patterns(
                        "artifacts", "*.log", "*-wal", "*-shm"
                    ),
                )
                with (
                    sqlite3.connect(root / "browser.sqlite") as src,
                    sqlite3.connect(reference / "browser.sqlite") as dest,
                ):
                    src.backup(dest)
                request("POST", "/__test/task-gate/arm")
                lost = []

                def discard(route):
                    if route.request.method != "POST":
                        route.continue_()
                        return
                    lost.append(route.request.post_data_json)
                    r = route.fetch()
                    assert r.status == 202
                    route.abort("failed")

                page.route("**/full-simulation/tasks", discard)
                browser_click(page, "Start as server task")
                expect(
                    page.get_by_role("button", name="Retry same request", exact=True)
                ).to_be_visible()
                page.unroute("**/full-simulation/tasks", discard)
                with page.expect_response(
                    lambda r: (
                        r.request.method == "POST"
                        and r.url.endswith("/full-simulation/tasks")
                    )
                ) as replay:
                    browser_click(page, "Retry same request")
                ack = replay.value.json()
                assert replay.value.status == 202 and len(lost) == 1
                assert ack["request_id"] == lost[0]["request_id"]
                task_id = ack["task_id"]
                parent_id = ack["parent_command_id"]
                print("BROWSER: task start acknowledgement/retry verified", flush=True)
                wait(
                    lambda: request("GET", "/__test/task-gate")["reached"],
                    "first genuine child",
                )
                first = request("GET", evidence_url)
                assert len(first["groups"]) == 1
                command = request("GET", scope + "/full-simulation/tasks/" + task_id)[
                    "tasks"
                ][0]["original_command"]
                page.close()
                request("POST", "/__test/task-gate/advance?after_groups=1")
                wait(
                    lambda: request("GET", "/__test/task-gate")["reached"],
                    "sport after page close",
                )
                after_close = request("GET", evidence_url)
                assert len(after_close["groups"]) == 2
                print(
                    "BROWSER: genuine sporting receipt after original page closed",
                    flush=True,
                )
                page = context.new_page()
                page.on("dialog", lambda d: d.accept())
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(base_url + "/admin/operations")
                tasks = page.get_by_role("region", name="Server simulation tasks")
                expect(tasks).to_contain_text(task_id)
                expect(tasks).to_contain_text(parent_id)
                tasks.get_by_role("link", name="Open exact Run / Branch").click()
                assert "branch=" + branch in page.url and "task=" + task_id in page.url
                page.get_by_role(
                    "button", name="Request safe pause", exact=True
                ).click()
                page.get_by_label("Full Simulation control operator").fill(
                    "Browser task controller"
                )
                page.get_by_label("Full Simulation control audit reason").fill(
                    "Pause second real match"
                )
                page.get_by_role("button", name="Request pause", exact=True).click()
                request("POST", "/__test/task-gate/release")
                wait(
                    lambda: (
                        request("GET", scope + "/full-simulation/tasks/" + task_id)[
                            "tasks"
                        ][0]["state"]
                        == "paused"
                    ),
                    "safe pause",
                )
                tasks = page.get_by_role("region", name="Server simulation tasks")
                expect(tasks).to_contain_text("Safely paused")
                page.screenshot(
                    path=str(artifacts / "task-paused-en.png"), full_page=True
                )
                request("POST", "/__test/task-gate/arm?after_groups=2")
                tasks.get_by_label("Task operator", exact=True).fill(
                    "Browser explicit resumer"
                )
                tasks.get_by_label("Task audit reason", exact=True).fill(
                    "Continue same task and parent"
                )
                tasks.get_by_role(
                    "button", name="Explicitly resume server task"
                ).click()
                wait(
                    lambda: request("GET", "/__test/task-gate")["reached"],
                    "third genuine match before process death",
                )
                before_kill = request("GET", evidence_url)
                assert len(before_kill["groups"]) == 3
                active = request("GET", scope + "/full-simulation/tasks/" + task_id)[
                    "tasks"
                ][0]
                process.kill()
                process.wait(timeout=10)
                print("BROWSER: killed actual active server process", flush=True)
                page.close()
                process = start_server(root, port)
                restarted = request("GET", scope + "/full-simulation/tasks/" + task_id)[
                    "tasks"
                ][0]
                assert restarted["state"] == "ownership_unverified", restarted
                assert restarted["task_id"] == task_id
                assert (
                    request("GET", evidence_url) == before_kill
                )  # startup and GET do no work
                recover = {
                    "request_id": "native-recovery",
                    "action": "recover",
                    "expected_revision": restarted["revision"],
                    "operator_label": "Explicit recovery operator",
                    "audit_reason": "Recover after actual SIGKILL",
                }
                assert request(
                    "POST",
                    scope + "/full-simulation/tasks/" + task_id + "/continue",
                    recover,
                    status=409,
                )
                request("POST", "/__test/task-gate/expire")
                page = context.new_page()
                page.on("dialog", lambda d: d.accept())
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(base_url + "/admin/operations")
                page.get_by_role("combobox", name="Language / Jazyk").select_option(
                    "cs"
                )
                tasks = page.get_by_role("region", name="Serverové simulační úlohy")
                expect(tasks).to_contain_text(task_id)
                expect(tasks).to_contain_text("Přerušeno; nutná výslovná obnova")
                tasks.get_by_label("Operátor úlohy", exact=True).fill(
                    "Native Czech recovery operator"
                )
                tasks.get_by_label("Důvod akce úlohy", exact=True).fill(
                    "Explicit recovery of original durable task"
                )
                tasks.get_by_role(
                    "button", name="Výslovně obnovit serverovou úlohu"
                ).click()
                wait(
                    lambda: (
                        request("GET", scope + "/full-simulation/tasks/" + task_id)[
                            "tasks"
                        ][0]["state"]
                        == "awaiting_operator"
                    ),
                    "real manual checkpoint",
                )
                final = request("GET", evidence_url)
                waiting = request("GET", scope + "/full-simulation/tasks/" + task_id)[
                    "tasks"
                ][0]
                assert (
                    waiting["needs_operator_action"]
                    and waiting["checkpoint"] == "season_transition_save_required"
                )
                assert all(
                    final["groups"][k] == v for k, v in before_kill["groups"].items()
                )
                assert (
                    final["saved"] == original["saved"]
                    and final["saved_head"] == original["saved_head"]
                )
                page.screenshot(
                    path=str(artifacts / "recovered-waiting-cs.png"), full_page=True
                )
                # Fresh server/DB handles and identical canonical inputs, uninterrupted.
                start_server(reference, port + 1)
                ref_api = f"http://127.0.0.1:{port + 1}"
                uninterrupted = request(
                    "POST",
                    scope + "/simulate-full-simulation",
                    command,
                    status=201,
                    api_root=ref_api,
                )
                ref = request("GET", evidence_url, api_root=ref_api)
                assert uninterrupted["checkpoint"] == waiting["checkpoint"]
                assert (
                    ref["groups"] == final["groups"]
                    and ref["slots"] == final["slots"]
                    and ref["saved"] == final["saved"]
                )
                # Finish with the original native safe Stop and frozen summary.
                tasks.get_by_role("link", name="Otevřít přesný Run / větev").click()
                page.get_by_role("button", name="Ukončit simulaci", exact=True).click()
                page.get_by_label("Operátor ovládání Full Simulation").fill(
                    "Native stopper"
                )
                page.get_by_label("Důvod ovládání Full Simulation do auditu").fill(
                    "Complete bounded recovery acceptance"
                )
                page.get_by_label(
                    "Potvrzuji ukončení této simulace; dokončené výsledky zůstanou zachované a Save je ruční."
                ).check()
                page.get_by_role(
                    "button", name="Ukončit původní simulaci", exact=True
                ).click()
                wait(
                    lambda: (
                        request("GET", scope + "/full-simulation/tasks/" + task_id)[
                            "tasks"
                        ][0]["state"]
                        == "stopped"
                    ),
                    "terminal stop",
                )
                summary = request(
                    "GET", scope + "/full-simulation/parents/" + parent_id + "/summary"
                )
                assert summary["available"]
                assert request("GET", evidence_url)["saved"] == original["saved"]
                assert not errors, errors
                (artifacts / "evidence.json").write_text(
                    json.dumps(
                        {
                            "task_id": task_id,
                            "parent_command_id": parent_id,
                            "ack": ack,
                            "closed_page_groups": len(after_close["groups"]),
                            "before_kill": active,
                            "restarted": restarted,
                            "waiting": waiting,
                            "summary": summary,
                            "uninterrupted_equivalent": True,
                            "original": original,
                            "final": final,
                        },
                        indent=2,
                    )
                )
                print(
                    "SERVER TASK BROWSER / ACTUAL PROCESS DEATH / RECOVERY / EQUIVALENCE PASSED"
                )
            finally:
                context.tracing.stop(path=str(artifacts / "trace.zip"))
                browser.close()
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        for log in logs:
            log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", type=Path)
    mode.add_argument("--acceptance", type=Path)
    parser.add_argument("--port", type=int, default=8021)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    if args.serve:
        serve(args.serve.resolve(), args.port)
    else:
        acceptance(args.acceptance.resolve(), args.port, args.base_url, args.chromium)
