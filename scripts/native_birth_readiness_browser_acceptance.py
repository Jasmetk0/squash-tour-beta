"""Real Chromium: read-only readiness, confirmed birth, explicit Save and Viewer."""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_native_birth_week_execution import sign_prospects
    from tests.api.test_calendar_tour_flow import setup
    from tests.api.test_saved_revision_history_api import ApiServer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    expect.set_options(timeout=30000)
    root = args.root or Path(tempfile.mkdtemp(prefix="native-birth-browser-"))
    root.mkdir(parents=True, exist_ok=True)
    if (root / "tour.sqlite").exists():
        raise ValueError("Use a fresh isolated browser fixture")
    with ApiServer(
        database_url=f"sqlite:///{root.resolve() / 'tour.sqlite'}"
    ) as server:
        clock = RunCalendar(2, 2, 2030, 2)
        repo, _ = setup(server, clock, 8)
        signed = sign_prospects(server, repo, clock, target_week=1, target_season=1)
        # Match the application's real allowed development origin. Arbitrary
        # ports are deliberately not allowed by its existing CORS policy.
        web_port = 5173
        web = f"http://127.0.0.1:{web_port}"
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
                    str(web_port),
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
                        viewport={"width": 1440, "height": 1050}
                    )
                    context.add_init_script(
                        "localStorage.setItem('squash-engine-language-v1','en')"
                    )
                    page = context.new_page()
                    page.set_default_timeout(60000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(web + "/admin/runs/run/tour/editions?branch=branch")
                    panel = page.get_by_role("region", name="Configured native Tour")
                    expect(panel.get_by_label("Tour operation reason")).to_be_visible()
                    capability = panel.get_by_label(
                        "Verified native transition capability"
                    )
                    capability.get_by_role(
                        "button", name="Check transition capability"
                    ).click()
                    expect(
                        capability.get_by_label("Verified transition readiness result")
                    ).to_contain_text("S2/W1")
                    expect(capability).to_contain_text("new Editions, Entry, draws and real matches")
                    viewer_url = server.base_url + "/viewer/runs/run/calendar-tour"
                    public_before = context.request.get(viewer_url).json()
                    assert public_before["saved_revision_id"] == signed["revision_id"]
                    panel.get_by_label("Tour operation reason").fill(
                        "Real browser confirmed birthday"
                    )
                    with page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith("/calendar-tour/preview")
                        ),
                        timeout=120000,
                    ) as response:
                        panel.get_by_role(
                            "button", name="Review Season Transition", exact=True
                        ).click()
                    assert response.value.status == 200, response.value.text()
                    assert response.value.json()["impact"]["admitted_player_ids"] == [
                        "born-native-15"
                    ]
                    expect(panel.get_by_label("Tour command review")).to_contain_text(
                        "Newly admitted players"
                    )
                    panel.get_by_label("Confirm Tour command").check()
                    with page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith("/calendar-tour/execute")
                        ),
                        timeout=120000,
                    ) as response:
                        panel.get_by_role(
                            "button", name="Execute confirmed operation"
                        ).click()
                    assert response.value.status == 201, response.value.text()
                    panel.get_by_text("New Tournament Edition", exact=True).click()
                    expect(
                        panel.get_by_role("button", name="Review new Edition")
                    ).to_be_disabled()
                    expect(panel.get_by_label("Confirm Tour Save")).to_be_visible()
                    assert context.request.get(viewer_url).json() == public_before
                    capability.get_by_role(
                        "button", name="Check transition capability"
                    ).click()
                    expect(capability).to_contain_text("Manual Save is required first.")
                    panel.get_by_label("Confirm Tour Save").check()
                    with page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith("/calendar-tour/save")
                        ),
                        timeout=120000,
                    ) as response:
                        panel.get_by_role("button", name="Manual Tour Save").click()
                    assert response.value.status == 201, response.value.text()
                    head = response.value.json()["saved_revision"]["revision_id"]
                    expect(panel).to_have_attribute("data-active-head", head)
                    expect(panel).to_have_attribute("data-saved-head", head)
                    capability.get_by_role(
                        "button", name="Check transition capability"
                    ).click()
                    expect(capability).to_contain_text(
                        "Transition review is available."
                    )
                    expect(capability).to_contain_text("Admitted players: 1")
                    panel.get_by_text("Current player state", exact=True).click()
                    panel.get_by_label("Tour player state").select_option(
                        "born-native-15"
                    )
                    expect(
                        panel.get_by_label("Current 57 attributes").locator("tr")
                    ).to_have_count(57)
                    assert (
                        context.request.get(viewer_url).json()["saved_revision_id"]
                        == head
                    )
                    assert repo.verify_branch_saved_revision_hash(revision_id=head)
                    assert not errors, errors
                    page.screenshot(
                        path=str(root / "native-birth-readiness.png"), full_page=True
                    )
                    browser.close()
                    print(
                        "Real Chromium native birth readiness, confirmation, 57 attributes, Save and Viewer passed.",
                        flush=True,
                    )
            finally:
                stop_process(frontend)


if __name__ == "__main__":
    main()
