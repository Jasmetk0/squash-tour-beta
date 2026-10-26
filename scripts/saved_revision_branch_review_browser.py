"""Actual Chromium/HTTP/SQLite reviewed native fork creation and continuation."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api.test_calendar_tour_flow import setup
    from tests.api.test_player_generation_calendar_gate import _dump
    from tests.api.test_saved_revision_history_api import (
        ApiServer,
        _create_run,
        _request,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "branches.sqlite"
    if path.exists():
        raise ValueError("Use a fresh disposable fixture")
    expect.set_options(timeout=30000)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run, branch, revision = _create_run(
            server, display_name="Browser reviewed Branches"
        )
        repo, native_head = setup(server, RunCalendar(7, 1, 2030, 3), 4)
        native_original = repo.get_branch_saved_revision(
            revision_id=native_head["revision_id"]
        )
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
                web = "http://127.0.0.1:5173"
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        executable_path=args.chromium, args=["--no-sandbox"]
                    )
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1100}
                    )
                    context.add_init_script(
                        "if (!localStorage.getItem('squash-engine-language-v1')) localStorage.setItem('squash-engine-language-v1','en')"
                    )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(f"{web}/admin/runs/{run}/branches?branch={branch}")
                    page.get_by_role("button", name="Revision 1:", exact=False).click()
                    page.get_by_label("New Branch name from Saved Revision").fill(
                        "Browser alternative"
                    )
                    before = _dump(path)
                    page.get_by_role(
                        "button", name="Review new Branch creation", exact=True
                    ).click()
                    dialog = page.get_by_role(
                        "alertdialog", name="Review new Branch creation"
                    )
                    checkbox = dialog.get_by_role(
                        "checkbox", name="Confirm new Branch creation"
                    )
                    expect(checkbox).to_be_enabled()
                    confirm = dialog.get_by_role(
                        "button", name="Confirm new Branch creation", exact=True
                    )
                    expect(confirm).to_be_disabled()
                    assert _dump(path) == before
                    dialog.get_by_role("button", name="Cancel Branch creation").click()
                    assert _dump(path) == before
                    page.get_by_role(
                        "button", name="Review new Branch creation", exact=True
                    ).click()
                    expect(checkbox).to_be_enabled()
                    checkbox.check()
                    expect(confirm).to_be_enabled()
                    with page.expect_response(
                        lambda r: (
                            r.request.method == "POST"
                            and r.url.endswith(f"/run-containers/{run}/branches")
                        )
                    ) as response:
                        confirm.click()
                    created = response.value.json()
                    assert response.value.status == 201, created
                    expect(
                        page.get_by_label("Saved Revision Branch result")
                    ).to_be_visible()
                    page.screenshot(
                        path=str(root / "created-branch-en.png"), full_page=True
                    )
                    page.get_by_role(
                        "link", name="Open created Branch in Admin"
                    ).click()
                    expect(page).to_have_url(
                        f"{web}/admin/runs/{run}?branch={created['branch_id']}"
                    )
                    expect(
                        page.get_by_text("Browser alternative", exact=True).first
                    ).to_be_visible()
                    assert (
                        _request("GET", f"{server.base_url}/run-containers/{run}")[1][
                            "viewer_branch_id"
                        ]
                        == branch
                    )
                    native_created = []
                    # Real native Saved sources now create independent active
                    # timelines. Exercise reviewed creation, Week Transition and
                    # explicit Save/reload through the actual Admin in CS/EN.
                    for language, title, button, check_label in (
                        (
                            "en",
                            "Review new Branch creation",
                            "Review new Branch creation",
                            "Confirm new Branch creation",
                        ),
                        (
                            "cs",
                            "Zkontrolovat vytvoření nové větve",
                            "Zkontrolovat vytvoření nové větve",
                            "Potvrdit vytvoření nové větve",
                        ),
                    ):
                        page.evaluate(
                            '(language) => localStorage.setItem("squash-engine-language-v1", language)',
                            language,
                        )
                        page.goto(f"{web}/admin/runs/run/branches?branch=branch")
                        page.get_by_role(
                            "button", name=native_head["revision_id"], exact=False
                        ).click()
                        before = _dump(path)
                        page.get_by_role("button", name=button, exact=True).click()
                        native_dialog = page.get_by_role("alertdialog", name=title)
                        native_check = native_dialog.get_by_role(
                            "checkbox", name=check_label
                        )
                        expect(native_check).to_be_enabled()
                        native_confirm = native_dialog.get_by_role(
                            "button", name=check_label, exact=True
                        )
                        expect(native_confirm).to_be_disabled()
                        assert _dump(path) == before
                        native_check.check()
                        with page.expect_response(
                            lambda r: (
                                r.request.method == "POST"
                                and r.url.endswith("/run-containers/run/branches")
                            )
                        ) as response:
                            native_confirm.click()
                        native_branch = response.value.json()
                        assert response.value.status == 201, native_branch
                        native_created.append(native_branch["branch_id"])
                        expect(
                            page.get_by_label(
                                "Saved Revision Branch result"
                                if language == "en"
                                else "Výsledek vytvoření větve z uložené revize"
                            )
                        ).to_be_visible()
                        page.get_by_role(
                            "link",
                            name="Open created Branch in Admin"
                            if language == "en"
                            else "Otevřít vytvořenou větev v Adminu",
                        ).click()
                        page.goto(
                            f"{web}/admin/runs/run/tour/editions?branch={native_branch['branch_id']}"
                        )
                        tour = page.get_by_role("region", name="Configured native Tour")
                        expect(tour).to_be_visible()
                        tour.get_by_label("Tour operation reason").fill(
                            "Reviewed independent native fork browser continuation"
                        )
                        tour.get_by_role(
                            "button",
                            name="Review Week Transition"
                            if language == "en"
                            else "Zkontrolovat Week Transition",
                            exact=True,
                        ).click()
                        tour.get_by_label("Confirm Tour command").check()
                        with page.expect_response(
                            lambda r: (
                                r.request.method == "POST"
                                and r.url.endswith("/calendar-tour/execute?include_inspection=true")
                            )
                        ) as execution:
                            tour.get_by_role(
                                "button",
                                name="Execute confirmed operation"
                                if language == "en"
                                else "Provést potvrzenou operaci",
                                exact=True,
                            ).click()
                        assert execution.value.status == 201, execution.value.text()
                        tour.get_by_label("Confirm Tour Save").check()
                        with page.expect_response(
                            lambda r: (
                                r.request.method == "POST"
                                and r.url.endswith("/calendar-tour/save")
                            )
                        ) as saved_response:
                            tour.get_by_role(
                                "button",
                                name="Manual Tour Save"
                                if language == "en"
                                else "Ruční Save Tour",
                                exact=True,
                            ).click()
                        assert saved_response.value.status == 201, (
                            saved_response.value.text()
                        )
                        page.reload()
                        tour.get_by_label("Tour operation reason").fill(
                            "Continue after reloaded explicit Save"
                        )
                        expect(
                            tour.get_by_role(
                                "button",
                                name="Review Week Transition"
                                if language == "en"
                                else "Zkontrolovat Week Transition",
                                exact=True,
                            )
                        ).to_be_enabled()
                        code, view = _request(
                            "GET",
                            server.base_url
                            + f"/admin/runs/run/branches/{native_branch['branch_id']}/calendar-tour",
                        )
                        assert (
                            code == 200
                            and view["saved"]
                            and view["state"]["week"]["week"] == 3
                        ), view
                        assert (
                            _request("GET", server.base_url + "/run-containers/run")[1][
                                "viewer_branch_id"
                            ]
                            == "branch"
                        )
                        page.screenshot(
                            path=str(root / f"native-created-saved-{language}.png"),
                            full_page=True,
                        )
                    assert (
                        repo.get_branch_saved_revision(
                            revision_id=native_head["revision_id"]
                        )
                        == native_original
                    )
                    assert not errors, errors
                    (root / "evidence.json").write_text(
                        json.dumps(
                            {
                                "created_branch": created["branch_id"],
                                "source_revision": revision,
                                "native_source_revision": native_head["revision_id"],
                                "native_fork_supported": True,
                                "native_created_branches": native_created,
                                "checks": [
                                    "explicit review/cancel/confirm",
                                    "read-only preview",
                                    "open created Branch",
                                    "Viewer isolation",
                                    "native create, transition, Manual Save and reload EN/CS",
                                ],
                            },
                            indent=2,
                        )
                    )
                    browser.close()
            finally:
                stop_process(frontend)
                # Closing Chromium cancels its HTTP clients, not synchronous
                # backend work already running. Drain the real API before Python
                # tears down native libraries on the daemon server thread.
                server.server.should_exit = True
                server.thread.join(timeout=30)
                if server.thread.is_alive():
                    import faulthandler
                    faulthandler.dump_traceback()
                    raise RuntimeError(
                        "Browser API did not drain during bounded shutdown"
                    )


if __name__ == "__main__":
    main()
