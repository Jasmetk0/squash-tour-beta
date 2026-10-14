"""Native Admin setup -> real Full Simulation pause/retry/Task Center/resume.

No sporting outputs are inserted or mocked. A test-only gate holds the next
writer before BEGIN IMMEDIATE, after a genuine MatchEngine child committed.
Only the acceptance server installs gate/evidence routes. Browser polling is
read-only observation of synchronous HTTP invocations, not a task worker.
"""
from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import quote
from urllib.request import urlopen

import uvicorn
from playwright.sync_api import expect, sync_playwright

from admin_first_tournament_smoke import browser_click, create_smoke_app, setup_run

# Share transaction coordination and evidence reads with the HTTP acceptance.
# This import is acceptance-only; the production app never imports tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests/application"))
from tests.support.full_simulation_http_flow import TransactionGate, routes, snapshot
from beta_engine.infrastructure.db.engine import DatabaseSettings, create_session_factory, create_sqlite_engine


def serve(root, port):
    app = create_smoke_app(root)
    factory = create_session_factory(create_sqlite_engine(DatabaseSettings(
        url=f"sqlite:///{root / 'browser.sqlite'}")))
    gate = TransactionGate(factory)
    routes._driver = gate.driver

    @app.post("/__test/full-simulation/gate/{action}")
    def control_gate(action: str, after_groups: int = 0):
        if action == "arm":
            gate.arm(after_groups=after_groups)
        elif action == "release":
            gate.release.set()
        else:
            raise ValueError("Unknown test gate action")
        return {"reached": gate.reached.is_set()}

    @app.get("/__test/full-simulation/gate")
    def inspect_gate():
        return {"reached": gate.reached.is_set()}

    @app.get("/__test/full-simulation/evidence")
    def evidence(run_id: str, branch_id: str):
        return snapshot(factory, run_id, branch_id)

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def acceptance(root, *, port, base_url, chromium):
    if (root / "browser.sqlite").exists():
        raise ValueError("Use a fresh disposable acceptance directory")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))
    root.mkdir(parents=True, exist_ok=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    api = f"http://127.0.0.1:{port}"
    log = (root / "server.log").open("w")
    process = subprocess.Popen([sys.executable, __file__, "--serve", str(root),
        "--port", str(port)], stdout=log, stderr=log)
    try:
        for _ in range(180):
            if process.poll() is not None:
                raise RuntimeError("Acceptance backend stopped; inspect server.log")
            try:
                with urlopen(api + "/health", timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("Acceptance backend did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.set_default_timeout(30000)
            page.smoke_pending_requests = set()
            page.smoke_dialogs = []
            page.on("request", lambda r: page.smoke_pending_requests.add(r))
            page.on("requestfinished", lambda r: page.smoke_pending_requests.discard(r))
            page.on("requestfailed", lambda r: page.smoke_pending_requests.discard(r))
            page.on("dialog", lambda d: d.accept())
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def request(method, path, body=None, status=200):
                response = context.request.fetch(api + path, method=method,
                    **({"data": body} if body is not None else {}), timeout=60000)
                assert response.status == status, (path, response.status, response.text()[:1600])
                return response.json()

            try:
                run_url = setup_run(page, base_url, artifacts)
                run_id = run_url.split("/admin/runs/", 1)[1]
                branches = request("GET", "/run-branches?run_id=" + quote(run_id, safe=""))["run_branches"]
                branch_id = branches[0]["branch_id"]
                simulation = f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
                evidence_url = f"/__test/full-simulation/evidence?run_id={run_id}&branch_id={branch_id}"
                # Native Entry -> Draw -> Week Schedule, stopping before sport starts.
                for button, approval in [
                    ("Preview actual Entry Field", "Approve reviewed Entry Field"),
                    ("Review first Draw Input", "Approve Draw Input"),
                    ("Review initial bracket generation", "Approve initial bracket generation"),
                    ("Preview complete Week Schedule", "Approve full Week Schedule"),
                ]:
                    browser_click(page, button)
                    page.get_by_label(approval, exact=True).check()
                    browser_click(page, {
                        "Preview actual Entry Field": "Commit reviewed Entry Field",
                        "Review first Draw Input": "Commit reviewed Draw Input",
                        "Review initial bracket generation": "Generate reviewed initial Draw",
                        "Preview complete Week Schedule": "Commit reviewed Week Schedule",
                    }[button])
                original = request("GET", evidence_url)
                assert original["groups"] == {}
                page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
                page.get_by_label("Full Simulation operator", exact=True).fill("Original browser operator")
                page.get_by_label("Full Simulation audit reason", exact=True).fill("Original immutable browser intent")
                browser_click(page, "Review authoritative Full Simulation")
                page.get_by_label("Confirm authoritative simulation").check()
                request("POST", "/__test/full-simulation/gate/arm")
                # This click starts a synchronous production HTTP invocation.
                page.get_by_role("button", name="Simulate reviewed authoritative Full Simulation", exact=True).click()
                for _ in range(300):
                    if request("GET", "/__test/full-simulation/gate")["reached"]:
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("No real committed sporting child reached the test gate")
                committed = request("GET", evidence_url)
                assert committed["groups"]
                pending = request("GET", simulation + "/full-simulation/pending")["operations"][0]
                command = pending["command"]
                parent_id = command["command_id"]
                other = request("POST", "/run-containers", {"display_name": "Competing browser Run"}, status=201)
                other_scope = f"/admin/runs/{other['run_id']}/branches/{other['viewer_branch_id']}/authoritative-simulation"
                rejected = request("POST", other_scope + "/simulate-full-simulation", command, status=409)
                assert "global execution lease" in rejected["detail"]["message"]
                other_evidence = request("GET", f"/__test/full-simulation/evidence?run_id={other['run_id']}&branch_id={other['viewer_branch_id']}")
                assert other_evidence["groups"] == other_evidence["commands"] == {}

                page.get_by_role("button", name="Request safe pause", exact=True).click()
                page.get_by_label("Full Simulation control operator").fill("Browser controller")
                page.get_by_label("Full Simulation control audit reason").fill("Pause during real sporting work")
                lost = []
                def lose_response(route):
                    lost.append(route.request.post_data_json)
                    response = route.fetch()
                    assert response.status == 200  # actual production SQLite commit
                    route.abort("failed")  # discard only the HTTP answer
                control_url = "**/full-simulation/control"
                page.route(control_url, lose_response)
                page.get_by_role("button", name="Request pause", exact=True).click()
                expect(page.get_by_role("group", name="Full Simulation pause or resume").get_by_role("alert")).to_be_visible()
                page.unroute(control_url, lose_response)
                with page.expect_response(lambda r: r.url.endswith("/full-simulation/control")) as replay_response:
                    page.get_by_role("button", name="Request pause", exact=True).click()
                replay = replay_response.value.json()
                assert replay["replayed"] is True and len(lost) == 1
                assert replay["control_command_id"] == lost[0]["control_command_id"]
                assert replay["target_command_id"] == parent_id
                request("POST", "/__test/full-simulation/gate/release")
                expect(page.get_by_role("list", name="Resumable Full Simulation parents")).to_contain_text("Paused", timeout=30000)
                paused = request("GET", evidence_url)
                assert paused["groups"] == committed["groups"]
                assert paused["saved"] == original["saved"]
                assert request("POST", simulation + "/simulate-full-simulation", command, status=201)["checkpoint"] == "operator_paused"
                assert request("GET", evidence_url) == paused
                page.screenshot(path=str(artifacts / "paused-en.png"), full_page=True)
                # Reconnect in a new page through the global Task Center.
                page.close()
                page = context.new_page()
                page.set_default_timeout(30000)
                page.on("dialog", lambda d: d.accept())
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url + "/admin/operations")
                page.get_by_role("combobox", name="Language / Jazyk").select_option("cs")
                inventory = page.get_by_role("list", name="Centrum simulací")
                expect(inventory).to_contain_text(parent_id)
                expect(inventory).to_contain_text("Pozastaveno")
                link = page.get_by_role("link", name="Otevřít detail a ovládání")
                assert link.get_attribute("href") == f"/admin/runs/{run_id}/simulate?branch={quote(branch_id, safe='')}"
                link.click()
                expect(page.get_by_role("button", name="Povolit pokračování", exact=True)).to_be_visible()
                assert page.url.endswith(f"/simulate?branch={quote(branch_id, safe='')}")
                page.get_by_role("button", name="Povolit pokračování", exact=True).click()
                page.get_by_label("Operátor ovládání Full Simulation").fill("Browser reconnect operator")
                page.get_by_label("Důvod ovládání Full Simulation do auditu").fill("Continue the original parent")
                page.screenshot(path=str(artifacts / "resume-cs.png"), full_page=True)
                page.get_by_role("button", name="Povolit pokračování původního příkazu", exact=True).click()
                prepare = page.get_by_role("button", name="Připravit pokračování stejné Full Simulation", exact=True)
                expect(prepare).to_be_enabled()
                prepare.click()
                page.get_by_label("Confirm authoritative simulation").check()
                # Bound the proof by a second genuine operator pause after all
                # three matches, before the much larger remaining season work.
                request("POST", "/__test/full-simulation/gate/arm?after_groups=2")
                with page.expect_response(lambda r: r.url.endswith("/simulate-full-simulation")) as resumed_response:
                    page.get_by_role("button", name="Simulate reviewed authoritative Full Simulation", exact=True).click()
                    for _ in range(300):
                        if request("GET", "/__test/full-simulation/gate")["reached"]:
                            break
                        page.wait_for_timeout(100)
                    else:
                        raise AssertionError("Resume did not commit the remaining real matches")
                    page.get_by_role("button", name="Pozastavit bezpečně", exact=True).click()
                    page.get_by_label("Operátor ovládání Full Simulation").fill("Browser controller")
                    page.get_by_label("Důvod ovládání Full Simulation do auditu").fill("Bound acceptance after three actual matches")
                    page.get_by_role("button", name="Požádat o pauzu", exact=True).click()
                    expect(page.get_by_role("group", name="Pozastavení nebo pokračování Full Simulation")).to_have_count(0)
                    request("POST", "/__test/full-simulation/gate/release")
                assert resumed_response.value.status == 201, resumed_response.value.text()
                continued = request("GET", evidence_url)
                assert len(continued["groups"]) == 3 > len(committed["groups"])
                assert all(continued["groups"][k] == v for k, v in committed["groups"].items())
                assert all(continued["slots"][k] == v for k, v in committed["slots"].items())
                parent = continued["commands"][parent_id]
                assert parent["fingerprint"] == paused["commands"][parent_id]["fingerprint"]
                assert parent["result"]["resume_command"] == command
                assert [e["action"] for e in parent["result"]["control_events"]] == ["pause", "resume", "pause"]
                assert continued["saved_head"] == original["saved_head"]
                assert continued["saved"] == original["saved"]
                assert request("POST", simulation + "/simulate-full-simulation", command, status=201)
                assert request("GET", evidence_url) == continued
                # Exercise the new terminal stop through actual CS Admin controls.
                page.goto(base_url + f"/admin/runs/{run_id}/simulate?branch={quote(branch_id, safe='')}")
                stop_button = page.get_by_role("button", name="Ukončit simulaci", exact=True)
                expect(stop_button).to_be_visible()
                stop_button.click()
                page.get_by_label("Operátor ovládání Full Simulation").fill("Browser stopping operator")
                page.get_by_label("Důvod ovládání Full Simulation do auditu").fill("Finish controlled three-match evidence")
                terminal = page.get_by_role("button", name="Ukončit původní simulaci", exact=True)
                expect(terminal).to_be_disabled()
                page.get_by_role("checkbox", name="Potvrzuji ukončení této simulace; dokončené výsledky zůstanou zachované a Save je ruční.").check()
                with page.expect_response(lambda r: r.url.endswith("/full-simulation/control")) as stopped_response:
                    terminal.click()
                assert stopped_response.value.status == 200
                assert stopped_response.value.json()["control_state"] == "stopped"
                terminal_snapshot = request("GET", evidence_url)
                assert terminal_snapshot["groups"] == continued["groups"]
                assert terminal_snapshot["slots"] == continued["slots"]
                assert terminal_snapshot["saved"] == original["saved"]
                assert terminal_snapshot["saved_head"] == original["saved_head"]
                assert terminal_snapshot["commands"][parent_id]["status"] == "stopped"
                assert [event["action"] for event in terminal_snapshot["commands"][parent_id]["result"]["control_events"]] == [
                    "pause", "resume", "pause", "stop"]
                assert request("GET", simulation + "/full-simulation/pending")["operations"] == []
                final_retry = request("POST", simulation + "/simulate-full-simulation", command, status=201)
                assert final_retry["status"] == "stopped" and final_retry["checkpoint"] == "operator_stopped"
                assert request("GET", evidence_url) == terminal_snapshot
                page.screenshot(path=str(artifacts / "stopped-cs.png"), full_page=True)
                assert errors == []
                (artifacts / "evidence.json").write_text(json.dumps({
                    "run_id": run_id, "branch_id": branch_id, "parent_command": command,
                    "lost_control_request": lost[0], "replayed_control_response": replay,
                    "before": original, "paused": paused, "continued": continued,
                    "stopped": terminal_snapshot, "terminal_retry": final_retry,
                    "competing_run_rejection": rejected, "browser_errors": errors,
                    "boundary": "Test-only gate before next SQLite writer; actual MatchEngine outputs, HTTP and browser controls",
                }, indent=2))
                print("REAL FULL SIMULATION PAUSE / LOST RESPONSE / TASK CENTER / SAME-PARENT RESUME / SAFE STOP PASSED", flush=True)
            except Exception:
                page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
                (artifacts / "failure.txt").write_text(page.locator("body").inner_text())
                raise
            finally:
                request("POST", "/__test/full-simulation/gate/release")
                context.tracing.stop(path=str(artifacts / "browser-trace.zip"))
                context.close()
                browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()  # disposable acceptance process only
            process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", type=Path)
    mode.add_argument("--acceptance", type=Path)
    parser.add_argument("--port", type=int, default=8020)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    if args.serve:
        serve(args.serve.resolve(), args.port)
    else:
        acceptance(args.acceptance.resolve(), port=args.port,
            base_url=args.base_url, chromium=args.chromium)
