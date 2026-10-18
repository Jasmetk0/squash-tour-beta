"""Actual Chromium Tour workflow, manual Saves and physical backend restart.

Fixture preparation uses production population/Health/sporting services on an
isolated editable Run. Every new Tour mutation is then performed through Admin.
No SQL repair, hash rewrite or MatchEngine mock is used.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def wait_http(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Server exited; inspect logs")
        try:
            with urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Server startup timed out")


def stop_process(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
    # npm can exit before its Vite child finishes handling SIGTERM.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("work/native-tour-browser"))
    parser.add_argument("--players", type=int, default=8)
    parser.add_argument("--width", type=int, default=52)
    parser.add_argument("--offset", type=int, default=None)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    parser.add_argument("--api-port", type=int, default=8003)
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--prepared",
        action="store_true",
        help="Use an already prepared, unchanged pre-Tour fixture",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = f"sqlite:///{root / 'tour.sqlite'}"
    if args.serve:
        import uvicorn

        from beta_engine.main import create_app

        uvicorn.run(
            create_app(database_url=db),
            host="127.0.0.1",
            port=args.api_port,
            log_level="warning",
        )
        return
    from playwright.sync_api import expect, sync_playwright

    expect.set_options(timeout=30000)
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from tests.api.test_calendar_tour_flow import setup
    from tests.api.test_saved_revision_history_api import ApiServer

    if (root / "tour.sqlite").exists() and not args.prepared:
        raise RuntimeError("Use a fresh acceptance root")
    started = time.monotonic()
    if not args.prepared:
        with ApiServer(database_url=db) as fixture:
            setup(
                fixture,
                RunCalendar(args.width, args.offset or args.width, 2030, 3),
                args.players,
                initialize=False,
            )
    evidence = {
        "players": args.players,
        "W": args.width,
        "offset": args.offset or args.width,
        "fixture_seconds": time.monotonic() - started,
        "operations": [],
    }
    if not args.prepared:
        (root / "fixture.json").write_text(json.dumps(evidence, indent=2))
    elif (root / "fixture.json").exists():
        fixture = json.loads((root / "fixture.json").read_text())
        if any(fixture[k] != evidence[k] for k in ("players", "W", "offset")):
            raise ValueError("Prepared fixture has another population/calendar scope")
        evidence["fixture_seconds"] = fixture["fixture_seconds"]
    if args.prepare_only:
        return
    api = f"http://127.0.0.1:{args.api_port}"
    web = f"http://127.0.0.1:{args.web_port}"
    api_log = (root / "backend.log").open("w")
    web_log = (root / "frontend.log").open("w")

    def backend():
        p = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--serve",
                "--root",
                str(root),
                "--api-port",
                str(args.api_port),
            ],
            stdout=api_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(api + "/health", p)
        return p

    server = backend()
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
            str(args.web_port),
            "--strictPort",
        ],
        env={**os.environ, "VITE_API_BASE_URL": api},
        stdout=web_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        wait_http(web, frontend)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=args.chromium, args=["--no-sandbox"]
            )
            context = browser.new_context(viewport={"width": 1536, "height": 1100})
            context.add_init_script(
                "localStorage.setItem('squash-engine-language-v1','en')"
            )
            page = context.new_page()
            page.set_default_timeout(120000)
            page.goto(web + "/admin/runs/run/tour/editions?branch=branch")
            panel = page.get_by_role("region", name="Configured native Tour")
            expect(panel.get_by_label("Tour operation reason")).to_be_visible()
            panel.get_by_label("Tour operation reason").fill(
                "Actual browser acceptance over configured Edition and saved players"
            )
            # The pre-Tour fixture already has an immutable Saved HEAD, before
            # any Tour-specific Save populates the receipt evidence.
            evidence["last_saved_head"] = panel.get_attribute("data-saved-head")
            assert evidence["last_saved_head"]

            def check_errors():
                errors = panel.get_by_role("alert")
                if errors.count():
                    raise AssertionError(errors.all_text_contents())

            def save():
                panel.get_by_label("Confirm Tour Save").check()
                with (
                    page.expect_response(
                        lambda r: (
                            r.request.method == "GET"
                            and r.url
                            == api + "/admin/runs/run/branches/branch/calendar-tour"
                        )
                    ) as loaded_context,
                    page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith("/calendar-tour/save")
                        )
                    ) as done,
                ):
                    panel.get_by_role(
                        "button", name="Manual Tour Save", exact=True
                    ).click()
                response = done.value
                assert response.status == 201, response.text()
                saved_head = response.json()["saved_revision"]["revision_id"]
                loaded = loaded_context.value
                assert loaded.status == 200, loaded.text()
                saved_view = loaded.json()
                assert saved_view["saved_head_revision_id"] == saved_head
                evidence["last_saved_head"] = saved_head
                evidence["last_checkpoint_fingerprint"] = saved_view[
                    "checkpoint_fingerprint"
                ]
                evidence["last_tour_fingerprint"] = saved_view["tour_fingerprint"]
                # Saving invalidates the shared Branch HEAD and remounts the panel.
                expect(panel.get_by_label("Tour operation reason")).to_be_visible()
                expect(panel).to_have_attribute("data-active-head", saved_head)
                expect(panel).to_have_attribute("data-saved-head", saved_head)
                expect(
                    panel.get_by_role("button", name="Refresh state")
                ).to_be_enabled()
                panel.get_by_label("Tour operation reason").fill(
                    "Actual browser acceptance over configured Edition and saved players"
                )
                check_errors()

            def operation(label, container=None, *, save_after=True):
                began = time.monotonic()
                source = container or panel
                # Some actual sporting transition previews must rebuild the
                # full signed lineage and all player effects. Observe the
                # production HTTP result, not only a 30-second UI animation.
                # This is an acceptance observation bound, NOT a change to an
                # application/network timeout or permission to skip integrity.
                preview_start = time.monotonic()
                with page.expect_response(
                    lambda r: (
                        r.request.method == "POST"
                        and r.url.endswith("/calendar-tour/preview")
                    ),
                    timeout=180000,
                ) as preview_response:
                    source.get_by_role("button", name=label, exact=True).click()
                preview_http = preview_response.value
                preview_seconds = time.monotonic() - preview_start
                evidence.setdefault("preview_seconds", []).append(
                    {"operation": label, "seconds": preview_seconds}
                )
                if preview_http.status != 200:
                    raise AssertionError(
                        f"{label} preview failed after {preview_seconds:.1f}s "
                        f"with HTTP {preview_http.status}: {preview_http.text()[:1600]}"
                    )
                review = panel.get_by_role("region", name="Tour command review")
                expect(review).to_be_visible()
                panel.get_by_label("Confirm Tour command").check()
                # The authenticated post-command inspection can rebuild a long
                # immutable sporting history. Await its actual response before
                # asserting the Working Draft UI; a 30s auto-retry of a locator
                # alone confuses slow but successful reads with missing controls.
                with (
                    page.expect_response(
                        lambda r: (
                            r.request.method == "GET"
                            and r.url
                            == api + "/admin/runs/run/branches/branch/calendar-tour"
                        )
                    ) as inspected,
                    page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith("/calendar-tour/execute")
                        )
                    ) as done,
                ):
                    panel.get_by_role(
                        "button", name="Execute confirmed operation", exact=True
                    ).click()
                response = done.value
                assert response.status == 201, response.text()
                refreshed = inspected.value
                assert refreshed.status == 200, refreshed.text()
                refreshed_view = refreshed.json()
                assert not refreshed_view["saved"], "The confirmed operation must remain an unsaved Working Draft"
                assert refreshed_view["run_id"] == "run" and refreshed_view["branch_id"] == "branch"
                assert refreshed_view["saved_head_revision_id"] == evidence["last_saved_head"]
                expect(panel.get_by_label("Confirm Tour Save")).to_be_visible()
                if save_after:
                    save()
                evidence["operations"].append(
                    {"operation": label, "seconds": time.monotonic() - began}
                )
                (root / "progress.json").write_text(json.dumps(evidence, indent=2))

            operation("Review Tour initialization")

            def create(name, week):
                details = panel.locator("details").first
                if details.get_attribute("open") is None:
                    details.locator("summary").click()
                panel.get_by_label("Tour Edition ID", exact=True).fill(name)
                panel.get_by_label("Tour Edition name", exact=True).fill(
                    "Browser Tour " + name
                )
                panel.get_by_label("Tour Edition week", exact=True).fill(str(week))
                panel.get_by_label("Tour Edition size", exact=True).select_option("8")
                operation("Review new Edition")

            create("browser-first", 4)
            create("browser-second", 5)
            # Future Edition plans are not public before their actual announcement.
            public = context.request.get(api + "/viewer/runs/run/calendar-tour").json()
            assert not public["editions"]
            operation("Review Week Transition")
            operation("Review Week Transition")

            def play(name):
                edition = panel.get_by_role(
                    "region", name="Edition " + name, exact=True
                )
                options = edition.get_by_label("Tour applicants " + name).locator(
                    "option"
                )
                ids = options.evaluate_all("(xs)=>xs.slice(0,8).map(x=>x.value)")
                edition.get_by_label("Tour applicants " + name).select_option(ids)
                # Production Entry/field/draw authority can be staged as one
                # Working Draft, but the MatchEngine still requires a Saved draw.
                operation("Review applications", edition, save_after=False)
                operation("Review approval", edition, save_after=False)
                operation("Review draw", edition)
                operation("Review play", edition)
                expect(
                    edition.get_by_role("table", name="Played matches " + name).locator(
                        "tbody tr"
                    )
                ).to_have_count(7)
                expect(
                    edition.get_by_role(
                        "table", name="Edition results " + name
                    ).locator("tbody tr")
                ).to_have_count(8)
                operation("Review results", edition)
                edition.get_by_role("button", name="Replay final").click()
                expect(
                    panel.get_by_text("Exact replay: true", exact=True)
                ).to_be_visible()

            play("browser-first")
            operation("Review Week Transition")
            expect(
                panel.get_by_role("heading", name="Official ranking · W5 · Best 15")
            ).to_be_visible()
            first_pid = server.pid
            stop_process(server)
            server = backend()
            assert server.pid != first_pid
            evidence["backend_pids"] = [first_pid, server.pid]
            cold_started = time.monotonic()
            with page.expect_response(
                lambda r: (
                    r.request.method == "GET"
                    and r.url == api + "/admin/runs/run/branches/branch/calendar-tour"
                )
            ) as reloaded:
                page.reload()
            assert reloaded.value.status == 200, reloaded.value.text()
            reopened = reloaded.value.json()
            assert reopened["saved"]
            assert reopened["saved_head_revision_id"] == evidence["last_saved_head"]
            assert (
                reopened["checkpoint_fingerprint"]
                == evidence["last_checkpoint_fingerprint"]
            )
            assert reopened["tour_fingerprint"] == evidence["last_tour_fingerprint"]
            expect(panel.get_by_role("button", name="Refresh state")).to_be_enabled()
            evidence["restart_ready_seconds"] = time.monotonic() - cold_started
            panel.get_by_label("Tour operation reason").fill(
                "Continue the next tournament after a physical backend restart"
            )
            play("browser-second")
            operation("Review Week Transition")
            expect(
                panel.get_by_role("heading", name="Official ranking · W6 · Best 15")
            ).to_be_visible()
            ranking = panel.get_by_role("table").last
            ranking.locator("tbody tr").first.get_by_role("button").click()
            expect(
                panel.get_by_role("complementary", name="Official point contributions")
            ).to_be_visible()
            details = panel.locator("details").last
            if details.get_attribute("open") is None:
                details.locator("summary").click()
            player = panel.get_by_label("Tour player state")
            player.select_option(player.locator("option").nth(1).get_attribute("value"))
            expect(
                panel.get_by_role("table", name="Current 57 attributes").locator(
                    "tbody tr"
                )
            ).to_have_count(57)
            page.screenshot(path=str(root / "official-week6.png"), full_page=True)
            public = context.request.get(api + "/viewer/runs/run/calendar-tour").json()
            assert public["official_ranking"]["week"]["week"] == 6
            assert (
                context.request.get(
                    api + "/viewer/runs/run/calendar-tour?week_ordinal=6"
                ).status
                == 409
            )
            evidence["ranking_rows"] = public["official_ranking"]["rows"]
            evidence["success"] = True
            page.get_by_label("Language / Jazyk").select_option("cs")
            expect(
                panel.get_by_role("heading", name="Oficiální ranking · W6 · Best 15")
            ).to_be_visible()
            page.screenshot(path=str(root / "official-week6-cs.png"), full_page=True)
            evidence["total_seconds"] = time.monotonic() - started
            (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
            browser.close()
    finally:
        for process in (server, frontend):
            stop_process(process)
        api_log.close()
        web_log.close()


if __name__ == "__main__":
    main()
