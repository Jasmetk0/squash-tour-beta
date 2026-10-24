"""Real Chromium post-admission Edition/Entry/play, explicit consent and Save."""

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
    from tests.api.test_calendar_native_birth_week_execution import sign_prospects
    from tests.api.test_calendar_tour_flow import (
        command,
        execute,
        inspect,
        save_tour,
        setup,
    )
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "tour.sqlite").exists():
        raise ValueError("Use a fresh disposable fixture")
    expect.set_options(timeout=30000)
    with ApiServer(database_url=f"sqlite:///{root / 'tour.sqlite'}") as server:
        clock = RunCalendar(52, 1, 2030, 3)
        repo, _ = setup(server, clock, 4)
        sign_prospects(server, repo, clock)
        execute(server, command(inspect(server), "transition", name="browser-admit"))
        birth = save_tour(server)
        web = "http://127.0.0.1:5173"
        with (root / "frontend.log").open("w") as log:
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
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        executable_path=args.chromium, args=["--no-sandbox"]
                    )
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1100}
                    )
                    context.add_init_script(
                        "localStorage.setItem('squash-engine-language-v1','en')"
                    )
                    page = context.new_page()
                    page.set_default_timeout(120000)
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(web + "/admin/runs/run/tour/editions?branch=branch")
                    panel = page.get_by_role("region", name="Configured native Tour")
                    expect(panel).to_have_attribute(
                        "data-saved-head", birth["revision_id"]
                    )
                    evidence = {
                        "birth_saved_head": birth["revision_id"],
                        "operations": [],
                    }

                    def fresh_reason():
                        expect(
                            panel.get_by_label("Tour operation reason")
                        ).to_be_visible()
                        panel.get_by_label("Tour operation reason").fill(
                            "Real post-admission browser authority"
                        )

                    def write(suffix, click):
                        acknowledged = False
                        reads = set()

                        def observe(r):
                            nonlocal acknowledged
                            if r.request.method == "POST" and r.url.endswith(suffix):
                                acknowledged = True

                        def request(r):
                            if (
                                acknowledged
                                and r.method == "GET"
                                and r.url
                                == server.base_url
                                + "/admin/runs/run/branches/branch/calendar-tour"
                            ):
                                reads.add(r)

                        page.on("response", observe)
                        page.on("request", request)
                        try:
                            with page.expect_response(
                                lambda r: r.request in reads
                            ) as loaded:
                                with page.expect_response(
                                    lambda r: (
                                        r.request.method == "POST"
                                        and r.url.endswith(suffix)
                                    )
                                ) as written:
                                    click()
                                assert written.value.status == 201, written.value.text()
                            assert loaded.value.status == 200, loaded.value.text()
                            return written.value.json(), loaded.value.json()
                        finally:
                            page.remove_listener("response", observe)
                            page.remove_listener("request", request)

                    def save():
                        panel.get_by_label("Confirm Tour Save").check()
                        receipt, view = write(
                            "/calendar-tour/save",
                            lambda: panel.get_by_role(
                                "button", name="Manual Tour Save", exact=True
                            ).click(),
                        )
                        head = receipt["saved_revision"]["revision_id"]
                        expect(panel).to_have_attribute("data-active-head", head)
                        expect(panel).to_have_attribute("data-saved-head", head)
                        assert view["saved"]
                        fresh_reason()
                        return head

                    def operation(label, container=None, save_after=True):
                        source = container or panel
                        began = time.monotonic()
                        print(f"Native post-intake: {label} started", flush=True)
                        public = context.request.get(
                            server.base_url + "/viewer/runs/run/calendar-tour"
                        ).json()
                        preview_started = time.monotonic()
                        with page.expect_response(
                            lambda r: (
                                r.request.method == "POST"
                                and r.url.endswith("/calendar-tour/preview")
                            )
                        ) as review:
                            source.get_by_role("button", name=label, exact=True).click()
                        assert review.value.status == 200, review.value.text()
                        preview_seconds = time.monotonic() - preview_started
                        commit_started = time.monotonic()
                        panel.get_by_label("Confirm Tour command").check()
                        receipt, view = write(
                            "/calendar-tour/execute",
                            lambda: panel.get_by_role(
                                "button", name="Execute confirmed operation", exact=True
                            ).click(),
                        )
                        commit_seconds = time.monotonic() - commit_started
                        assert not view["saved"]
                        assert (
                            context.request.get(
                                server.base_url + "/viewer/runs/run/calendar-tour"
                            ).json()
                            == public
                        )
                        save_started = time.monotonic()
                        if save_after:
                            save()
                        save_seconds = (
                            time.monotonic() - save_started if save_after else None
                        )
                        evidence["operations"].append(
                            {
                                "operation": label,
                                "receipt": receipt["command_id"],
                                "preview_seconds": preview_seconds,
                                "commit_and_inspection_seconds": commit_seconds,
                                "save_and_inspection_seconds": save_seconds,
                                "total_seconds": time.monotonic() - began,
                            }
                        )
                        (root / "evidence.json").write_text(
                            json.dumps(evidence, indent=2)
                        )
                        print(
                            f"Native post-intake: {label} completed in {time.monotonic() - began:.2f}s",
                            flush=True,
                        )

                    fresh_reason()
                    panel.get_by_text("New Tournament Edition", exact=True).click()
                    panel.get_by_label("Tour Edition ID", exact=True).fill(
                        "native-browser"
                    )
                    panel.get_by_label("Tour Edition name", exact=True).fill(
                        "After admission"
                    )
                    panel.get_by_label("Tour Edition week", exact=True).fill("5")
                    panel.get_by_label("Tour Edition size", exact=True).select_option(
                        "4"
                    )
                    operation("Review new Edition")
                    operation("Review Week Transition")
                    operation("Review Week Transition")
                    edition = panel.get_by_role(
                        "region", name="Edition native-browser", exact=True
                    )
                    options = (
                        edition.get_by_label("Tour applicants native-browser")
                        .locator("option")
                        .evaluate_all("(xs)=>xs.map(x=>x.value)")
                    )
                    entrants = ["born-native-15"] + [
                        pid for pid in options if pid != "born-native-15"
                    ][:3]
                    edition.get_by_label(
                        "Tour applicants native-browser"
                    ).select_option(entrants)
                    operation("Review applications", edition, False)
                    operation("Review approval", edition, False)
                    operation("Review draw", edition)
                    # New Editions use two shared slots for the actual
                    # semifinals and final, including the admitted player.
                    operation("Review Next Slot")
                    operation("Review Next Slot")
                    operation("Review results", edition)
                    operation("Review Week Transition")
                    view = inspect(server)
                    assert "born-native-15" in {
                        r["player_id"] for r in view["state"]["rankings"][-1]["rows"]
                    }
                    evidence["saved_head"] = view["saved_head_revision_id"]
                    evidence["tour_fingerprint"] = view["tour_fingerprint"]
                    evidence["entrant_ids"] = entrants
                    page.screenshot(path=str(root / "post-intake.png"), full_page=True)
                    assert not errors, errors
                    (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
                    browser.close()
            finally:
                stop_process(frontend)


if __name__ == "__main__":
    main()
