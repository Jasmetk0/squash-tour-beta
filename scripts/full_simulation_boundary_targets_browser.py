"""Native canonical Draw/final/source targets with durable server task and closed tab.

The acceptance-only gate delays real writers. Production HTTP creates all inputs
and sporting outputs; no result, source, RNG, or Save is injected.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from admin_first_tournament_smoke import browser_click, setup_run
from full_simulation_server_tasks_browser import serve
from playwright.sync_api import expect, sync_playwright


def acceptance(root, port, base_url, chromium):
    if root.exists():
        raise ValueError("Use a fresh disposable directory")
    root.mkdir(parents=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    api = f"http://127.0.0.1:{port}"
    log = (root / "process.log").open("w")
    process = subprocess.Popen(
        [sys.executable, __file__, "--serve", str(root), "--port", str(port)],
        stdout=log,
        stderr=log,
    )
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError("Backend stopped; inspect process.log")
            try:
                with urlopen(api + "/health", timeout=1):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Backend did not start")
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chromium,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            page.set_default_timeout(30000)
            page.smoke_pending_requests = set()
            page.smoke_dialogs = []
            page.on(
                "request",
                lambda r, target_page=page: target_page.smoke_pending_requests.add(r),
            )
            page.on(
                "requestfinished",
                lambda r, target_page=page: target_page.smoke_pending_requests.discard(
                    r
                ),
            )
            page.on(
                "requestfailed",
                lambda r, target_page=page: target_page.smoke_pending_requests.discard(
                    r
                ),
            )
            page.on("dialog", lambda d: d.accept())
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))

            def request(method, path, body=None, status=200):
                r = context.request.fetch(
                    api + path,
                    method=method,
                    **({"data": body} if body is not None else {}),
                    timeout=60000,
                )
                assert r.status == status, (path, r.status, r.text()[:2000])
                return r.json()

            try:
                run_url = setup_run(page, base_url, artifacts)
                run_id = run_url.split("/admin/runs/", 1)[1]
                branch_id = request("GET", "/run-branches?run_id=" + run_id)[
                    "run_branches"
                ][0]["branch_id"]
                scope = f"/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation"
                evidence_url = (
                    f"/__test/task-evidence?run_id={run_id}&branch_id={branch_id}"
                )
                for button, approval, commit in [
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
                    browser_click(page, button)
                    page.get_by_label(approval, exact=True).check()
                    browser_click(page, commit)
                original = request("GET", evidence_url)
                assert not original["groups"]
                results = []
                for kind, expected_count, language in [
                    ("before_final", 2, "en"),
                    ("after_tournament", 3, "cs"),
                ]:
                    page.goto(run_url + "/simulate?branch=" + branch_id)
                    page.get_by_label("Full Simulation operator", exact=True).fill(
                        "Native target operator"
                    )
                    page.get_by_label("Full Simulation audit reason", exact=True).fill(
                        "Review exact boundary " + kind
                    )
                    page.get_by_role(
                        "button",
                        name="Review authoritative Full Simulation",
                        exact=True,
                    ).click()
                    page.get_by_label("Confirm authoritative simulation").check()
                    request("POST", "/__test/task-gate/arm")
                    with page.expect_response(
                        lambda r: (
                            r.url.endswith("/full-simulation/tasks")
                            and r.request.method == "POST"
                        )
                    ) as start:
                        page.get_by_role(
                            "button", name="Start as server task", exact=True
                        ).click()
                    assert start.value.status == 202, start.value.text()
                    ack = start.value.json()
                    for _ in range(300):
                        if request("GET", "/__test/task-gate")["reached"]:
                            break
                        time.sleep(0.1)
                    else:
                        raise AssertionError("No genuine child reached gate")
                    if language == "cs":
                        page.evaluate(
                            "localStorage.setItem('squash-engine-language-v1','cs')"
                        )
                        page.reload()
                    review = (
                        "Review precise targets"
                        if language == "en"
                        else "Prověřit přesné cíle"
                    )
                    page.get_by_role("button", name=review, exact=True).click()
                    options = request(
                        "GET",
                        scope
                        + "/full-simulation/target-options?command_id="
                        + ack["parent_command_id"],
                    )
                    selected = next(o for o in options["options"] if o["kind"] == kind)
                    page.get_by_label(
                        "Target boundary" if language == "en" else "Cílová hranice",
                        exact=True,
                    ).select_option(selected["selector_fingerprint"])
                    page.get_by_label(
                        "Target operator" if language == "en" else "Operátor cíle",
                        exact=True,
                    ).fill("Native boundary auditor")
                    page.get_by_label(
                        "Target audit reason"
                        if language == "en"
                        else "Důvod změny cíle",
                        exact=True,
                    ).fill("Verify canonical " + kind)
                    page.get_by_label(
                        "I reviewed the exact edition / global slot and schedule."
                        if language == "en"
                        else "Prověřil jsem přesnou edici / globální slot a plán.",
                        exact=True,
                    ).check()
                    with page.expect_response(
                        lambda r: r.url.endswith("/full-simulation/target")
                    ) as applied:
                        page.get_by_role(
                            "button",
                            name="Apply precise target"
                            if language == "en"
                            else "Použít přesný cíl",
                            exact=True,
                        ).click()
                    assert applied.value.status == 200, applied.value.text()
                    assert applied.value.json()["boundary_target"] == selected
                    page.screenshot(
                        path=str(artifacts / (kind + "-review-" + language + ".png")),
                        full_page=True,
                    )
                    if kind == "before_final":
                        before_crash = request("GET", evidence_url)
                        page.close()
                        process.kill()
                        process.wait(timeout=10)
                        process = subprocess.Popen(
                            [
                                sys.executable,
                                __file__,
                                "--serve",
                                str(root),
                                "--port",
                                str(port),
                            ],
                            stdout=log,
                            stderr=log,
                        )
                        for _ in range(200):
                            try:
                                with urlopen(api + "/health", timeout=1):
                                    break
                            except OSError:
                                time.sleep(0.1)
                        else:
                            raise RuntimeError("Recovery backend did not start")
                        # Startup/GET never enqueues sport, even with a stored target.
                        assert request("GET", evidence_url) == before_crash
                        interrupted = request(
                            "GET", scope + "/full-simulation/tasks/" + ack["task_id"]
                        )["tasks"][0]
                        assert interrupted["state"] == "ownership_unverified", (
                            interrupted
                        )
                        request("POST", "/__test/task-gate/expire")
                        page = context.new_page()
                        page.goto(base_url + "/admin/operations")
                        recovery = page.locator(
                            'li[data-task-id="' + ack["task_id"] + '"]'
                        )
                        expect(recovery).to_contain_text(
                            "Interrupted; explicit recovery required"
                        )
                        recovery.get_by_label("Task operator", exact=True).fill(
                            "Native recovery operator"
                        )
                        recovery.get_by_label("Task audit reason", exact=True).fill(
                            "Explicit recovery after genuine process death"
                        )
                        with page.expect_response(
                            lambda r: r.url.endswith("/continue")
                        ) as resumed:
                            recovery.get_by_role(
                                "button",
                                name="Explicitly recover server task",
                                exact=True,
                            ).click()
                        assert resumed.value.status == 202, resumed.value.text()
                        page.close()
                    else:
                        page.close()
                        request("POST", "/__test/task-gate/release")
                    for _ in range(600):
                        task = request(
                            "GET", scope + "/full-simulation/tasks/" + ack["task_id"]
                        )["tasks"][0]
                        if task["state"] in {
                            "target_reached",
                            "failed",
                            "awaiting_operator",
                        }:
                            break
                        time.sleep(0.1)
                    assert task["state"] == "target_reached", task
                    data = request("GET", evidence_url)
                    assert len(data["groups"]) == expected_count
                    assert (
                        data["saved"] == original["saved"]
                        and data["saved_head"] == original["saved_head"]
                    )
                    summary = request(
                        "GET",
                        scope
                        + "/full-simulation/parents/"
                        + ack["parent_command_id"]
                        + "/summary",
                    )
                    trigger = summary["summary"]["target_trigger_evidence"]
                    if kind == "before_final":
                        assert selected["slot_id"] not in data["slots"]
                        assert len(summary["summary"]["completed_tournaments"]) == 0
                    else:
                        assert (
                            trigger["source_fingerprint"]
                            == summary["summary"]["completed_tournaments"][0][
                                "source_fingerprint"
                            ]
                        )
                        assert trigger["edition_id"] == selected["edition_id"]
                    page = context.new_page()
                    page.smoke_pending_requests = set()
                    page.smoke_dialogs = []
                    page.on(
                        "request",
                        lambda r, target_page=page: (
                            target_page.smoke_pending_requests.add(r)
                        ),
                    )
                    page.on(
                        "requestfinished",
                        lambda r, target_page=page: (
                            target_page.smoke_pending_requests.discard(r)
                        ),
                    )
                    page.on(
                        "requestfailed",
                        lambda r, target_page=page: (
                            target_page.smoke_pending_requests.discard(r)
                        ),
                    )
                    page.on("dialog", lambda d: d.accept())
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(base_url + "/admin/operations")
                    cards = page.get_by_role(
                        "region",
                        name="Server simulation tasks"
                        if language == "en"
                        else "Serverové simulační úlohy",
                    )
                    card = cards.locator('li[data-task-id="' + ack["task_id"] + '"]')
                    expect(card).to_contain_text(
                        "Target reached" if language == "en" else "Cíl dosažen"
                    )
                    card.get_by_role("link").click()
                    expect(page).to_have_url(
                        run_url
                        + "/simulate?branch="
                        + branch_id
                        + "&task="
                        + ack["task_id"]
                    )
                    card = page.locator('li[data-task-id="' + ack["task_id"] + '"]')
                    card.get_by_text(
                        "Stored terminal summary" if language == "en"
                        else "Uložený závěrečný souhrn", exact=True
                    ).click()
                    expect(card).to_contain_text(
                        "Selected target reached"
                        if language == "en"
                        else "Dosažen vybraný cíl"
                    )
                    page.screenshot(
                        path=str(artifacts / (kind + "-terminal-" + language + ".png")),
                        full_page=True,
                    )
                    card.screenshot(
                        path=str(artifacts / (kind + "-summary-" + language + ".png"))
                    )
                    assert (
                        request(
                            "GET",
                            scope
                            + "/full-simulation/parents/"
                            + ack["parent_command_id"]
                            + "/summary",
                        )
                        == summary
                    )
                    results.append(
                        {
                            "kind": kind,
                            "task_id": ack["task_id"],
                            "target": selected,
                            "group_count": len(data["groups"]),
                            "summary": summary,
                        }
                    )
                    if language == "cs":
                        page.evaluate(
                            "localStorage.setItem('squash-engine-language-v1','en')"
                        )
                assert not errors, errors
                (artifacts / "acceptance.json").write_text(
                    json.dumps(
                        {
                            "results": results,
                            "saved_unchanged": True,
                            "actual_process_death_and_explicit_target_recovery": True,
                            "browser_errors": errors,
                        },
                        indent=2,
                    )
                )
                print(
                    "PASS: native canonical BEFORE final, AFTER owned closure, closed tab, Task Center, CS/EN and frozen summaries"
                )
            finally:
                context.tracing.stop(path=str(artifacts / "trace.zip"))
                browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--acceptance", type=Path)
    parser.add_argument("--port", type=int, default=8023)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    if args.serve:
        serve(args.serve, args.port)
    else:
        acceptance(args.acceptance, args.port, args.base_url, args.chromium)
