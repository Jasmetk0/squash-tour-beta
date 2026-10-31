"""Real Chromium Entry timing review, explicit Confirm/Save and SQLite restart.

The initial Calendar is constructed with the existing production Package HTTP
commands. No ranking publication, eligibility decision or sporting result is
fabricated. This proves future-plan authoring, not automatic Entry eligibility.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--api-port", type=int, default=8018)
    # This is the existing development CORS origin, not an acceptance-only bypass.
    parser.add_argument("--web-port", type=int, default=5173)
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    database = root / "entry.sqlite"
    db = f"sqlite:///{database}"
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

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_run_edition_entry_timing_api import EVENT, PACKAGE, setup
    from tests.api.test_saved_revision_history_api import ApiServer, _request

    if database.exists():
        raise ValueError("Use a fresh disposable acceptance directory")
    expect.set_options(timeout=30000)
    with ApiServer(database_url=db) as fixture:
        rid, bid, _, _, save_url = setup(fixture, clock=RunCalendar.fax_default())
        draft_url = (
            f"{fixture.base_url}/run-containers/{rid}/branches/{bid}/working-draft"
        )
        code, draft = _request("GET", draft_url)
        assert code == 200, draft
        code, saved = _request(
            "POST", save_url, {"expected_draft_version": draft["draft_version"]}
        )
        assert code == 201, saved
        original_head = saved["saved_revision"]["revision_id"]
    fixture.app.state.runtime.repository._engine.dispose()

    api = f"http://127.0.0.1:{args.api_port}"
    web = f"http://127.0.0.1:{args.web_port}"
    entry = f"{api}/admin/runs/{rid}/branches/{bid}/packages/calendar/{PACKAGE}/editions/{EVENT}/entry-timing"
    branch_root = f"{api}/run-containers/{rid}/branches/{bid}"
    path = f"/admin/runs/{rid}/calendar/{EVENT}?branch={bid}&calendar={PACKAGE}"
    writes = []
    errors = []
    evidence = {"run_id": rid, "branch_id": bid, "original_saved_head": original_head}
    backend_log = (root / "backend.log").open("w")
    frontend_log = (root / "frontend.log").open("w")

    def start_backend():
        process = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--serve",
                "--root",
                str(root),
                "--api-port",
                str(args.api_port),
            ],
            stdout=backend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(api + "/health", process)
        return process

    server = start_backend()
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
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        wait_http(web, frontend)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            context.add_init_script(
                "if (!localStorage.getItem('squash-engine-language-v1')) localStorage.setItem('squash-engine-language-v1','en')"
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    writes.append(
                        {
                            "method": request.method,
                            "url": request.url,
                            "body": request.post_data,
                        }
                    )
                    if request.method in ("POST", "PATCH", "DELETE", "PUT")
                    else None
                ),
            )
            page.goto(web + path)
            panel = page.locator("#run-edition-entry-timing")
            try:
                expect(panel).to_be_visible()
            except AssertionError:
                (root / "failed-page.txt").write_text(page.locator("body").inner_text())
                (root / "page-errors.json").write_text(json.dumps(errors))
                page.screenshot(path=str(root / "failed-page.png"), full_page=True)
                raise
            expect(
                panel.get_by_label("Main opening – week", exact=True)
            ).to_be_enabled()
            (root / "initial.txt").write_text(panel.inner_text())
            panel.get_by_label("Main opening – season", exact=True).select_option("0")
            panel.get_by_label("Main opening – week", exact=True).fill("13")
            panel.get_by_label("Confirmation operator", exact=True).fill(
                "Browser operator"
            )
            panel.get_by_label("Confirmation reason (audit)", exact=True).fill(
                "Actual browser Entry timing acceptance"
            )
            panel.get_by_role(
                "button", name="Calculate server preview", exact=True
            ).click()
            expect(
                panel.get_by_role(
                    "heading", name="Server preview – no write", exact=True
                )
            ).to_be_visible()
            assert len(writes) == 1 and writes[0]["url"].endswith(
                "/entry-timing/preview"
            ), writes
            assert _request("GET", entry)[1]["timing"] is None
            assert (
                _request("GET", branch_root + "/working-draft")[1]["status"] == "clean"
            )
            panel.screenshot(path=str(root / "preview-en.png"))
            page.get_by_label("Language / Jazyk").select_option("cs")
            expect(
                panel.get_by_role(
                    "heading", name="Serverový náhled – bez zápisu", exact=True
                )
            ).to_be_visible()
            expect(
                panel.get_by_label("Otevření Main – týden", exact=True)
            ).to_have_value("13")
            assert len(writes) == 1, writes
            page.set_viewport_size({"width": 390, "height": 844})
            panel.screenshot(path=str(root / "preview-cs-mobile.png"))
            overflow = panel.evaluate("""element => ({width: element.clientWidth, scroll: element.scrollWidth,
              children: [...element.querySelectorAll('*')].filter(e => e.getBoundingClientRect().right > element.getBoundingClientRect().right + 1)
                .slice(0, 12).map(e => ({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,100),width:e.clientWidth,scroll:e.scrollWidth}))})""")
            (root / "mobile-dimensions.json").write_text(json.dumps(overflow, indent=2))
            assert overflow["scroll"] <= overflow["width"] + 1, overflow
            page.set_viewport_size({"width": 1440, "height": 1100})
            page.get_by_label("Language / Jazyk").select_option("en")
            # Forward the real Confirm, then drop its reply. Only the transport
            # fails; the actual backend has already committed its single command.
            acknowledged = []

            def lose_first_confirm(route):
                response = route.fetch()
                assert response.status == 200, response.text()
                acknowledged.append(response.json())
                route.abort("failed")

            page.route("**/entry-timing/confirm", lose_first_confirm, times=1)
            panel.get_by_role(
                "button", name="Explicitly confirm into Working Draft", exact=True
            ).click()
            retry = panel.get_by_role(
                "button", name="Retry the exact same command", exact=True
            )
            expect(retry).to_be_enabled()
            assert acknowledged and len(writes) == 2, writes
            assert (
                _request("GET", branch_root + "/working-draft")[1]["status"] == "dirty"
            )
            retry.click()
            expect(
                panel.get_by_role(
                    "button", name="Save Working Draft separately", exact=True
                )
            ).to_be_visible()
            assert len(writes) == 3 and writes[-1]["url"].endswith(
                "/entry-timing/confirm"
            ), writes
            assert writes[1]["body"] == writes[2]["body"], writes
            assert (
                _request("GET", branch_root + "/working-draft")[1]["status"] == "dirty"
            )
            (root / "confirmed.txt").write_text(panel.inner_text())
            # Saving is a second explicit user action; confirmation never saves.
            panel.get_by_role("checkbox").last.check()
            panel.get_by_role(
                "button", name="Save Working Draft separately", exact=True
            ).click()
            expect(
                panel.get_by_text(
                    "Server confirmed the new Saved Revision.", exact=True
                )
            ).to_be_visible()
            assert len(writes) == 4 and writes[-1]["url"].endswith(
                "/working-draft/save"
            ), writes
            code, draft = _request("GET", branch_root + "/working-draft")
            assert code == 200 and draft["status"] == "clean", draft
            saved_head = draft["base_saved_revision_id"]
            assert saved_head != original_head
            expect(panel.get_by_text(saved_head, exact=False)).to_be_visible()
            before_restart = _request("GET", entry)
            assert (
                before_restart[0] == 200
                and before_restart[1]["timing"]["main_open"]["week"] == 13
            )
            code, revision = _request(
                "GET", branch_root + "/saved-revisions/" + saved_head
            )
            assert code == 200, revision
            content = revision["payload"]["content"]["run_package_state"]["state"]
            event = next(
                e for e in content["entities"] if e["source_entity_id"] == EVENT
            )
            assert (
                event["payload"]["event_level_overrides"]["entry_timing"]
                == before_restart[1]["timing"]
            )
            # Both parent HEAD/Draft refreshes have completed by these actual
            # reads. Their staggered completion must not unmount the receipt.
            expect(
                panel.get_by_text(
                    "Server confirmed the new Saved Revision.", exact=True
                )
            ).to_be_visible()
            stop_process(server)
            server = start_backend()
            assert _request("GET", entry) == before_restart
            assert _request("GET", branch_root + "/saved-revisions/" + saved_head) == (
                code,
                revision,
            )
            page.reload()
            expect(panel.get_by_label("Main opening – week", exact=True)).to_have_value(
                "13"
            )
            assert len(writes) == 4, writes
            evidence.update(
                saved_head=saved_head,
                writes=writes,
                errors=errors,
                sqlite_restart=True,
                exact_saved_payload=True,
                languages=["en", "cs"],
                mobile_width=390,
                real_confirm_response_lost_and_exactly_retried=True,
            )
            assert not errors, errors
            (root / "evidence.json").write_text(json.dumps(evidence, indent=2))
            page.screenshot(path=str(root / "reopened-en.png"), full_page=True)
            browser.close()
    finally:
        stop_process(frontend)
        stop_process(server)
        backend_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
