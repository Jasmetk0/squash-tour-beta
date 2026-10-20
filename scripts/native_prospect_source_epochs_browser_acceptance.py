"""Production Chromium: future prospect generation, consent, manual epoch Save.

Component fixtures are not used for the actual Admin UI/HTTP interaction.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright
    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_native_birth_week_execution import sign_prospects
    from tests.api.test_calendar_tour_flow import (
        command, execute, inspect, save_tour, setup,
    )
    from tests.api.test_saved_revision_history_api import ApiServer
    from beta_engine.infrastructure.db.run_prospect_source_state import (
        load_saved_run_prospect_source,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium"))
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "tour.sqlite").exists():
        raise ValueError("Use a fresh SQLite browser fixture")
    with ApiServer(database_url=f"sqlite:///{root / 'tour.sqlite'}") as server:
        clock = RunCalendar(52, 1, 2030, 3)
        repo, _ = setup(server, clock, 4)
        sign_prospects(server, repo, clock)
        execute(server, command(inspect(server), "transition", name="browser-first-epoch-birth"))
        saved = save_tour(server)
        before = repo.get_branch_saved_revision(revision_id=saved["revision_id"])
        old = load_saved_run_prospect_source(before.payload, run_id="run")
        web = "http://127.0.0.1:5173"
        with (root / "frontend.log").open("w") as log:
            frontend = subprocess.Popen(
                ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        executable_path=args.chromium, args=["--no-sandbox"],
                    )
                    context = browser.new_context(viewport={"width": 1440, "height": 1100})
                    context.add_init_script(
                        "localStorage.setItem('squash-engine-language-v1','en')"
                    )
                    page = context.new_page()
                    page.set_default_timeout(120000)
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(web + "/admin/runs/run/tour/editions?branch=branch")
                    panel = page.get_by_role("region", name="Future prospect source epochs")
                    expect(panel).to_have_attribute("data-saved-head", saved["revision_id"])
                    expect(panel.get_by_text("Next future prospect cohort")).to_be_visible()
                    panel.get_by_label("Future season index (0 = first)").fill("1")
                    panel.get_by_label("Annual base target").fill("14")
                    panel.get_by_label("ISO3 country (optional)").fill("GER")
                    with page.expect_response(
                        lambda response: (
                            response.request.method == "POST"
                            and response.url.endswith("/intake/native-calendar/preview")
                        )
                    ) as res:
                        panel.get_by_role("button", name="1. Review future cohort").click()
                    assert res.value.status == 200, res.value.text()
                    expect(panel.get_by_label("Reviewed immutable prospect cohort")).to_contain_text("New profiles")
                    panel.get_by_label("Confirmation reason (at least 10 characters)").fill(
                        "Real explicit browser future cohort"
                    )
                    panel.locator("input[type=checkbox]").first.check()
                    with page.expect_response(
                        lambda response: (
                            response.request.method == "POST"
                            and response.url.endswith("/intake/native-calendar/materialize")
                        )
                    ) as res:
                        panel.get_by_role("button", name="2. Materialize future prospects").click()
                    assert res.value.status == 201, res.value.text()
                    expect(panel).to_contain_text("New records require manual source Save")
                    assert repo.get_branch_saved_revision(
                        revision_id=saved["revision_id"]
                    ).content_hash == before.content_hash
                    with page.expect_response(
                        lambda response: (
                            response.request.method == "GET"
                            and response.url.endswith("/prospect-source/save/preview")
                        )
                    ) as res:
                        panel.get_by_role("button", name="3. Review source-epoch Save").click()
                    assert res.value.status == 200, res.value.text()
                    expect(panel.get_by_label("Reviewed prospect source Save")).to_contain_text("Total prospects")
                    panel.locator("input[type=checkbox]").last.check()
                    with page.expect_response(
                        lambda response: (
                            response.request.method == "POST"
                            and response.url.endswith("/prospect-source/save")
                        )
                    ) as res:
                        panel.get_by_role("button", name="4. Save immutable source epoch").click()
                    assert res.value.status == 201, res.value.text()
                    revision_id = res.value.json()["saved_revision"]["revision_id"]
                    component = load_saved_run_prospect_source(
                        repo.get_branch_saved_revision(revision_id=revision_id).payload,
                        run_id="run",
                    )
                    assert component.schema_version == "run_prospect_source_epochs.v2"
                    assert component.for_week(2).fingerprint == old.fingerprint
                    assert component.for_week(3).fingerprint != old.fingerprint
                    assert repo.verify_branch_saved_revision_hash(revision_id=revision_id)
                    assert not errors, errors
                    page.screenshot(path=str(root / "future-source-epoch.png"), full_page=True)
                    browser.close()
                    print("Real Chromium future cohort review, materialization, immutable epoch Save passed.", flush=True)
            finally:
                stop_process(frontend)


if __name__ == "__main__":
    main()
