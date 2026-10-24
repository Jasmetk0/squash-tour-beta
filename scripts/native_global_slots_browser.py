"""Real Chromium/Admin/MatchEngine/SQLite overlapping slots and physical restart."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_calendar_tour_flow import inspect
    from tests.api.test_saved_revision_history_api import ApiServer, _free_port

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--width", type=int, default=52)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "global-slots.sqlite"
    if database.exists():
        raise ValueError("Use a fresh isolated browser directory")
    if args.source:
        with (
            sqlite3.connect(args.source) as source,
            sqlite3.connect(database) as target,
        ):
            source.backup(target)
    started = time.monotonic()
    errors = []
    expect.set_options(timeout=90000)

    @contextmanager
    def browser_session(pw, server, language):
        port = _free_port()
        web = f"http://127.0.0.1:{port}"
        with (root / f"frontend-{language}.log").open("w") as log:
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
                    str(port),
                    "--strictPort",
                ],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            browser = None
            try:
                wait_http(web, frontend)
                browser = pw.chromium.launch(
                    executable_path=args.chromium, args=["--no-sandbox"]
                )
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                context.add_init_script(
                    f"localStorage.setItem('squash-engine-language-v1',{json.dumps(language)})"
                )
                page = context.new_page()
                page.set_default_timeout(90000)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(web + "/admin/runs/run/tour/editions?branch=branch")
                panel = page.get_by_role(
                    "region", name="Configured native Tour", exact=True
                )
                expect(panel.get_by_label("Tour operation reason")).to_be_visible()
                panel.get_by_label("Tour operation reason").fill(
                    "Actual overlapping slot / manual Save / physical restart"
                )
                yield page, panel
            finally:
                if browser:
                    browser.close()
                stop_process(frontend)

    def accept(page, panel, review_label, *, region=None):
        (region or panel).get_by_role("button", name=review_label, exact=True).click()
        panel.get_by_label("Confirm Tour command").check()
        with page.expect_response(
            lambda r: (
                r.request.method == "POST" and r.url.endswith("/calendar-tour/execute")
            )
        ) as result:
            panel.get_by_role(
                "button",
                name="Execute confirmed operation"
                if "Review" in review_label
                else "Provést potvrzenou operaci",
                exact=True,
            ).click()
        assert result.value.status == 201, result.value.text()
        return result.value.json()

    def manual_save(page, panel, language):
        panel.get_by_label("Confirm Tour Save").check()
        with page.expect_response(
            lambda r: (
                r.request.method == "POST" and r.url.endswith("/calendar-tour/save")
            )
        ) as result:
            panel.get_by_role(
                "button",
                name="Manual Tour Save" if language == "en" else "Ruční Save Tour",
                exact=True,
            ).click()
        assert result.value.status == 201, result.value.text()
        # The selected immutable HEAD changes and triggers the normal scoped read.
        expect(panel.get_by_label("Tour operation reason")).to_be_visible()

    with sync_playwright() as pw:
        with ApiServer(database_url=f"sqlite:///{database}") as server:
            if not args.source:
                ready(server, args.width)
            with browser_session(pw, server, "en") as (page, panel):
                slot = panel.get_by_role(
                    "region", name="Global Simulation Slot", exact=True
                )
                expect(slot).to_contain_text("Remaining: 4")
                selected = inspect(server)["next_slot"]["matches"][-1]["match_id"]
                slot.get_by_label("Global slot match").select_option(selected)
                result = accept(page, panel, "Review Next Match")
                assert result["match_ids"] == [selected]
                expect(slot).to_contain_text("Remaining: 3")
                manual_save(page, panel, "en")
                frozen = inspect(server)["next_slot"]["snapshot_fingerprint"]
                page.screenshot(path=str(root / "partial-saved.png"), full_page=True)
        # Both server/SQLite connections and the real browser are physically closed.
        with ApiServer(database_url=f"sqlite:///{database}") as server:
            assert inspect(server)["next_slot"]["snapshot_fingerprint"] == frozen
            with browser_session(pw, server, "cs") as (page, panel):
                slot = panel.get_by_role(
                    "region", name="Global Simulation Slot", exact=True
                )
                expect(slot).to_contain_text("Zbývá: 3")
                accept(page, panel, "Zkontrolovat Next Slot")
                manual_save(page, panel, "cs")
                expect(slot).to_contain_text("Simulation Slot 5")
                accept(page, panel, "Zkontrolovat Next Slot")
                manual_save(page, panel, "cs")
                for eid in ("parallel-a", "parallel-b"):
                    section = panel.get_by_role(
                        "region", name=f"Edition {eid}", exact=True
                    )
                    accept(page, panel, "Zkontrolovat výsledky", region=section)
                    manual_save(page, panel, "cs")
                accept(page, panel, "Zkontrolovat Week Transition")
                manual_save(page, panel, "cs")
                final = inspect(server)
                assert final["state"]["week"]["week"] == 5
                assert sorted(
                    r["points"] for r in final["state"]["rankings"][-1]["rows"]
                ) == [30, 30, 30, 30, 60, 60, 100, 100]
                assert final["next_slot"] is None and final["saved"]
                page.screenshot(
                    path=str(root / "both-editions-points.png"), full_page=True
                )
    assert not errors, errors
    result = {
        "width": args.width,
        "real_match_count": 6,
        "physical_restart": True,
        "languages": ["en", "cs"],
        "seconds": time.monotonic() - started,
    }
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
