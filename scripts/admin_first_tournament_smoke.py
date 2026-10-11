"""Disposable real Admin/browser acceptance; source preparation contains no players or results."""

import json
import shutil
from pathlib import Path

import uvicorn

from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import (
    SeasonCategoryPointsService,
)
from beta_engine.application.tournament_templates_service import (
    TournamentTemplatesConfigService,
)
from beta_engine.domain.tournaments import SeasonCalendarBuildRequest
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.main import create_app


def create_smoke_app(root: Path):
    """Prepare only the source package and isolated production persistence paths."""
    root.mkdir(parents=True, exist_ok=True)
    worlds = root / "worlds"
    if not worlds.exists():
        for name in ("official_fax_world", "real_world"):
            shutil.copytree(Path("config/world_packages") / name, worlds / name)
    countries = WorldPackageCountryStore(worlds / "official_fax_world").load_config()
    (root / "countries.json").write_text(countries.model_dump_json())
    template = {
        "template_id": "browser_cup",
        "tour_level": "WORLD_TOUR",
        "category": "PLATINUM",
        "event_name": "Browser Acceptance Cup",
        "region": "EUROPE",
        "host_country": "CZE",
        "main_draw_size": 4,
        "qualification_draw_size": 0,
        "seeds_count": 2,
        "qualifier_spots": 0,
        "wild_cards": 0,
        "byes": 0,
        "lucky_loser_rules": {
            "enabled": False,
            "max_spots": 0,
            "replacement_window": "pre_main_draw_round_1",
        },
        "point_distribution": {
            "winner": 100,
            "finalist": 60,
            "semifinalist": 30,
            "quarterfinalist": 10,
        },
        "prize_money": 10000,
        "prestige": 9,
        "event_duration_days": 2,
        "qualification_duration_days": 0,
        "duration_in_season_weeks": 1,
        "active": True,
    }
    (root / "templates.json").write_text(json.dumps({"templates": [template]}))
    templates = TournamentTemplatesConfigService(
        config_path=root / "templates.json", calendar_dir=root / "legacy"
    )
    points = SeasonCategoryPointsService(templates, root / "category_points.json")
    calendar = SeasonCalendarService(templates, root / "calendars.json", points)
    if not (root / "calendars.json").exists():
        points.initialize("2000/2001")
        points.update(
            "2000/2001", "PLATINUM", {"champion": 100, "finalist": 60, "semifinal": 30}
        )
        built = calendar.build_calendar(
            season="2000/2001",
            request=SeasonCalendarBuildRequest(seed=1, dry_run=False, max_events=1),
        )
        assert built.calendar and not built.validation_errors, built
        registry = calendar._load_registry()
        event = registry.calendars_by_season["2000/2001"].events[0]
        updated = type(event).model_validate(
            {
                **event.model_dump(mode="json"),
                "event_id": "EVT-2000-W01-browser_cup",
                "season_week": 1,
                "start_season_week": 1,
                "end_season_week": 1,
            }
        )
        _warnings, errors = calendar.validate_calendar_events([updated])
        assert not errors, errors
        registry.calendars_by_season["2000/2001"].events = [updated]
        calendar._save_registry(registry)

    paths = {
        "countries_config_path": "countries.json",
        "tournament_templates_config_path": "templates.json",
        "initial_player_pool_config_path": "initial_pool.json",
        "manual_player_overrides_config_path": "overrides.json",
        "season_active_players_config_path": "active.json",
        "season_calendar_registry_path": "calendars.json",
        "season_category_points_registry_path": "category_points.json",
        "planning_season_calendar_registry_path": "planning.json",
        "calendar_templates_registry_path": "calendar_templates.json",
        "season_builder_apply_audit_log_path": "builder_audit.json",
        "planning_calendar_apply_audit_log_path": "planning_audit.json",
        "season_entry_lists_registry_path": "entries.json",
        "season_draws_registry_path": "draws.json",
        "season_matches_registry_path": "matches.json",
        "season_event_results_registry_path": "results.json",
        "season_point_awards_registry_path": "awards.json",
        "season_ranking_snapshots_registry_path": "rankings.json",
    }
    tuning = root / "entry_tuning.json"
    if not tuning.exists():
        shutil.copyfile("config/balance/entry_tuning.json", tuning)
    app = create_app(
        entry_tuning_config_path=str(tuning),
        database_url=f"sqlite:///{root}/browser.sqlite",
        world_packages_root=str(worlds),
        calendar_config_dir=str(root / "legacy"),
        planning_calendar_apply_backup_dir=str(root / "backups"),
        **{key: str(root / value) for key, value in paths.items()},
    )
    return app


def setup_run(page, base_url: str, artifacts: Path) -> str:
    """All Run writes below are normal browser form submissions."""
    from playwright.sync_api import expect

    artifacts.mkdir(parents=True, exist_ok=True)
    click = lambda name: browser_click(page, name)
    check = lambda name: page.get_by_label(name, exact=True).check()
    page.goto(base_url + "/admin/runs/new")
    page.get_by_label("Unique Run name").fill("Browser Tournament Acceptance")
    click("Create isolated Run")
    page.get_by_role("heading", name="World and Calendar copies", exact=True).wait_for()
    run_url = page.url
    (artifacts / "run-url.txt").write_text(run_url)
    for kind in ("world", "calendar"):
        page.get_by_label("Source kind").select_option(kind)
        if kind == "world":
            page.get_by_label("World source").select_option("official_fax_world")
        click("Preview copy")
        check("Confirm source copy")
        click("Confirm copy to Working Draft")
        check("Confirm save revision")
        click("Save copied packages")
        expect(
            page.get_by_text("Current Run copy: Present. Draft: clean.", exact=False)
        ).to_be_visible()
        print("BROWSER: copied and saved", kind, flush=True)
    page.get_by_label("Number of generated players").fill("64")
    page.get_by_label("Player generation seed").fill("4201")
    page.get_by_label("InitialWorld audit reason").fill(
        "Disposable real browser acceptance"
    )
    click("Preview generated players")
    check("Approve InitialWorld adoption")
    click("Adopt generated players")
    check("Approve InitialWorld revision save")
    click("Save InitialWorld revision")
    expect(
        page.get_by_text("InitialWorld exists: 64 players", exact=False)
    ).to_be_visible()
    browser_settle(page)
    print("BROWSER: generated, adopted and saved 64 players", flush=True)
    page.get_by_label("Initial ranking audit reason").fill(
        "Initial Week 1 browser acceptance"
    )
    browser_settle(page)
    click("Preview initial ranking")
    check("Approve initial ranking preparation")
    click("Confirm initial ranking")
    check("Approve initial ranking save")
    click("Save initial ranking revision")
    click("Review initial publication")
    check("Approve initial publication")
    click("Publish initial ranking")
    click("Review unsaved published ranking state")
    check("Approve published ranking revision save")
    click("Save published ranking revision")
    expect(page.get_by_text("Viewer readback verified:", exact=False)).to_be_visible()
    page.screenshot(path=str(artifacts / "01-initial-ranking.png"), full_page=True)
    print(
        "BROWSER: prepared, saved, published initial ranking; saved Viewer readback",
        flush=True,
    )
    page.get_by_role(
        "link", name="Open first Run-owned tournament preparation", exact=True
    ).click()
    assert "/calendar/" in page.url, ("Tournament preparation navigation was blocked", page.url, page.smoke_dialogs)
    page.get_by_label("Published Official Ranking", exact=True).select_option(index=1)
    click("Adopt selected Official Ranking")
    click("Preview real Entry decisions")
    check("Approve frozen Entry generation")
    click("Confirm and freeze Entry decisions")
    page.locator('select[aria-label^="Entry outcome "]').first.wait_for()
    selects = page.locator('select[aria-label^="Entry outcome "]').all()
    assert len(selects) >= 4, (
        "Real Entry AI did not propose enough applications; do not fabricate a field"
    )
    for select in selects:
        select.select_option("valid")
    page.get_by_label("Entry review operator").fill("Browser acceptance admin")
    page.get_by_label("Entry review audit reason").fill(
        "Explicit review of generated applications in disposable Run"
    )
    click("Review entire application batch")
    check("Confirm reviewed application batch")
    click("Commit reviewed applications")
    page.get_by_role("button", name="Preview actual Entry Field", exact=True).wait_for()
    page.smoke_entry_decision_count = len(selects)
    print(
        "BROWSER: generated and explicitly validated",
        len(selects),
        "real Entry decisions",
        flush=True,
    )
    (artifacts / "run-url.txt").write_text(run_url)
    return run_url


def browser_settle(page):
    """Wait for actual AJAX completion, including queries invalidated after Save."""
    import time

    deadline = time.monotonic() + 60
    quiet_since = None
    while time.monotonic() < deadline:
        page.wait_for_timeout(50)
        if page.smoke_pending_requests:
            quiet_since = None
        elif quiet_since is None:
            quiet_since = time.monotonic()
        elif time.monotonic() - quiet_since >= 0.35:
            return
    raise RuntimeError("Browser requests did not settle; inspect the trace")


def browser_click(page, name):
    page.get_by_role("button", name=name, exact=True).click()
    browser_settle(page)


def finish_tournament(page, artifacts: Path):
    from playwright.sync_api import expect

    click = lambda name: browser_click(page, name)
    check = lambda name: page.get_by_label(name, exact=True).check()
    click("Preview actual Entry Field")
    check("Approve reviewed Entry Field")
    click("Commit reviewed Entry Field")
    click("Review first Draw Input")
    check("Approve Draw Input")
    click("Commit reviewed Draw Input")
    click("Review initial bracket generation")
    check("Approve initial bracket generation")
    click("Generate reviewed initial Draw")
    expect(
        page.locator('section[aria-label="Verified real tournament bracket"]')
    ).to_contain_text("Actual Main slots: 4")
    click("Preview complete Week Schedule")
    check("Approve full Week Schedule")
    click("Commit reviewed Week Schedule")
    expect(
        page.get_by_role("heading", name="Adopted Week Schedule", exact=True)
    ).to_be_visible()
    page.screenshot(path=str(artifacts / "02-draw-schedule.png"), full_page=True)
    click("Review first real match")
    check("Approve first real match")
    click("Simulate reviewed first match")
    expect(
        page.get_by_text(
            "The authoritative match, winner and stored replay were verified.",
            exact=False,
        )
    ).to_be_visible()
    page.get_by_role(
        "link",
        name="Open authoritative Position, subsequent rounds and recovery controls",
        exact=True,
    ).click()
    browser_settle(page)
    for _ in range(2):
        check("Confirm authoritative simulation")
        click("Review authoritative Next Round")
        click("Simulate reviewed authoritative Next Round")
        expect(
            page.get_by_role(
                "button", name="Simulate reviewed authoritative Next Round", exact=True
            )
        ).to_have_count(0)
    replay = page.get_by_label("Completed authoritative replay match", exact=True)
    expect(replay.locator("option")).to_have_count(3)
    options = replay.locator("option").all_text_contents()
    assert ":main:R2-N1" in options[0], options
    replay.select_option(index=0)
    browser_settle(page)
    page.screenshot(path=str(artifacts / "03-completed-final.png"), full_page=True)
    click("Save authoritative simulation")
    page.get_by_label("Operator label", exact=True).fill("Browser acceptance admin")
    page.get_by_label("Authority reason", exact=True).fill(
        "Derive Week 2 ranking after all three real matches"
    )
    click("Review derived Ranking Transition Authority")
    click("Confirm reviewed Ranking Transition Authority")
    with page.expect_response(
        lambda r: r.url.endswith("/authoritative-simulation/position")
    ) as position_response:
        click("Save Ranking Transition Authority")
    # These are read-only HTTP concurrency checks, separate from UI writes.
    positions = page.evaluate(
        """async (url) => Promise.all(Array.from({length: 8}, async () => {
        const response = await fetch(url);
        return {status: response.status, body: await response.json()};
    }))""",
        position_response.value.url,
    )
    assert all(
        p["status"] == 200 and p["body"]["week_ready_for_transition"] for p in positions
    ), positions
    assert len({p["body"]["position_fingerprint"] for p in positions}) == 1
    click("Review derived Week Transition")
    click("Confirm reviewed Week Transition")
    click("Save transitioned week")
    print(
        "BROWSER: three real matches, winner feeders, sporting Save, derived ranking and saved Week 2",
        flush=True,
    )
    return options


def verify_viewer(page, run_url, artifacts: Path, prefix=""):
    from playwright.sync_api import expect

    base, run_id = run_url.split("/admin/runs/")
    page.goto(f"{base}/viewer/runs/{run_id}/rankings")
    page.get_by_role("link", name="Open Week 2 ranking", exact=True).click()
    browser_settle(page)
    table = page.get_by_role(
        "table", name="Historical Official Ranking table", exact=True
    )
    expect(table.locator("tbody tr")).to_have_count(64)
    rows = table.locator("tbody tr").all_text_contents()
    points = [
        row.locator("td").nth(3).inner_text() for row in table.locator("tbody tr").all()
    ]
    assert points[:4] == ["100", "60", "30", "30"], points[:4]
    assert all(value == "0" for value in points[4:])
    page.screenshot(
        path=str(artifacts / f"{prefix}04-week2-ranking.png"), full_page=True
    )
    page.goto(f"{base}/viewer/runs/{run_id}/tournaments/EVT-2000-W01-browser_cup")
    browser_settle(page)
    # Persisted published result and its ranking awards, rather than a legacy event.
    expect(page.get_by_text("Published", exact=True).first).to_be_visible()
    page.screenshot(
        path=str(artifacts / f"{prefix}05-tournament-results.png"), full_page=True
    )
    return rows


def run_acceptance(root: Path, *, port: int, base_url: str, chromium: str, saved_replay_only: bool = False, saved_replay_fork: bool = False):
    from saved_player_replay_browser_checks import verify_saved_player_replay, verify_materialized_branch_fork_replay
    """Own the disposable backend process, restart it, and reopen a fresh browser."""
    import socket
    import subprocess
    import sys
    import time
    from urllib.request import urlopen

    from playwright.sync_api import expect, sync_playwright

    if (root / "browser.sqlite").exists():
        raise ValueError(
            "Acceptance requires a fresh disposable directory; never replace a database"
        )
    # Never accept a different backend already listening on the selected port.
    # Health alone cannot prove that our isolated database owns the server.
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))
    root.mkdir(parents=True, exist_ok=True)
    artifacts = root / "artifacts"
    artifacts.mkdir()
    log = (root / "server.log").open("w")
    errors = []

    def start():
        process = subprocess.Popen(
            [sys.executable, __file__, "--serve", str(root), "--port", str(port)],
            stdout=log,
            stderr=log,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Disposable backend exited; inspect server.log")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                    if response.status == 200:
                        return process
            except OSError:
                time.sleep(0.1)
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError("Disposable backend did not become ready")

    def open_page(browser):
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        page.set_default_timeout(30000)
        page.smoke_pending_requests = set()
        page.on("request", lambda r: page.smoke_pending_requests.add(r))
        page.on("requestfinished", lambda r: page.smoke_pending_requests.discard(r))
        page.on("requestfailed", lambda r: page.smoke_pending_requests.discard(r))
        # The current Admin shell guards navigation with a native confirmation.
        # Chromium dismisses dialogs without a handler and silently cancels
        # the user click, so explicitly accept the real navigation prompt.
        page.smoke_dialogs = []
        def accept_dialog(dialog):
            page.smoke_dialogs.append(dialog.message)
            dialog.accept()
        page.on("dialog", accept_dialog)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "response",
            lambda r: (
                errors.append(f"HTTP {r.status}: {r.url}") if r.status >= 500 else None
            ),
        )
        return context, page

    process = start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=chromium,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context, page = open_page(browser)
            try:
                run_url = setup_run(page, base_url, artifacts)
                entry_count = page.smoke_entry_decision_count
                match_options = finish_tournament(page, artifacts)
                ranking_rows = verify_viewer(page, run_url, artifacts)
                saved_match = verify_saved_player_replay(page, run_url, artifacts, port)
                fork_match = verify_materialized_branch_fork_replay(page, run_url, artifacts, port, saved_match) if saved_replay_fork else None
                context.tracing.stop(path=str(artifacts / "before-restart.zip"))
                context.close()
                process.terminate()
                process.wait(timeout=20)
                process = start()
                context, page = open_page(browser)
                assert (
                    verify_viewer(page, run_url, artifacts, "reopened-") == ranking_rows
                )
                reopened_match = verify_saved_player_replay(page, run_url, artifacts, port, prefix="reopened-", expected_branch_id=saved_match["branch_id"] if saved_replay_fork else None)
                reopened_fork = verify_materialized_branch_fork_replay(page, run_url, artifacts, port, saved_match, fork_id=fork_match["target_branch_id"], prefix="reopened-") if saved_replay_fork else None
                if saved_replay_fork: assert reopened_fork == fork_match, "Forked replay changed after restart"
                assert reopened_match == saved_match, "Saved replay changed across restart"
                if saved_replay_only:
                    # This dedicated acceptance ends after actual replay and
                    # backend restart. The pre-existing Next Week continuation
                    # belongs to the separate full tournament smoke workflow.
                    assert not errors, errors
                    (artifacts / "evidence.json").write_text(
                        json.dumps({
                            "run_url": run_url,
                            "entry_decisions": entry_count,
                            "authoritative_matches": match_options,
                            "saved_player_replay": saved_match,
                            "saved_branch_fork": fork_match,
                            "fork_equal_after_restart": fork_match == reopened_fork if saved_replay_fork else None,
                            "reopened_replay_equal": True,
                            "browser_errors": errors,
                        }, indent=2)
                    )
                    print("SAVED PLAYER REPLAY BROWSER ACCEPTANCE PASSED", flush=True)
                    return
                page.goto(run_url + "/simulate")
                browser_settle(page)
                replay = page.get_by_label(
                    "Completed authoritative replay match", exact=True
                )
                expect(replay.locator("option")).to_have_count(3)
                assert replay.locator("option").all_text_contents() == match_options
                # Continue a real operation in the next empty Calendar week.
                page.get_by_label("Next Week operator", exact=True).fill(
                    "Browser recovery admin"
                )
                page.get_by_label("Next Week audit reason", exact=True).fill(
                    "Verify continuation after backend restart"
                )
                page.get_by_label(
                    "Confirm authoritative simulation", exact=True
                ).check()
                browser_click(page, "Confirm calendar-proven empty week")
                browser_click(page, "Save authoritative simulation")
                page.get_by_label("Next Week operator", exact=True).fill(
                    "Browser recovery admin"
                )
                page.get_by_label("Next Week audit reason", exact=True).fill(
                    "Verify continuation from saved empty-week evidence"
                )
                page.get_by_label(
                    "Confirm authoritative simulation", exact=True
                ).check()
                browser_click(page, "Review authoritative Next Week")
                expect(
                    page.get_by_role(
                        "heading",
                        name="Reviewed canonical Week · S0 W2 → W3",
                        exact=True,
                    )
                ).to_be_visible()
                page.screenshot(
                    path=str(artifacts / "06-reopened-continuation.png"), full_page=True
                )
                assert not errors, errors
                (artifacts / "evidence.json").write_text(
                    json.dumps(
                        {
                            "run_url": run_url,
                            "real_entry_decisions": entry_count,
                            "matches": match_options,
                            "saved_player_replay": saved_match,
                            "reopened_saved_replay_equal": reopened_match == saved_match,
                            "week2_ranking_rows": ranking_rows,
                            "browser_errors": errors,
                            "restart": "fresh browser context after terminated/restarted production backend",
                        },
                        indent=2,
                    )
                )
                print("BROWSER ACCEPTANCE PASSED:", run_url, flush=True)
            except Exception:
                page.screenshot(path=str(artifacts / "failure.png"), full_page=True)
                (artifacts / "failure.txt").write_text(
                    page.locator("body").inner_text()
                )
                raise
            finally:
                if context.tracing:
                    context.tracing.stop(path=str(artifacts / "after-restart.zip"))
                browser.close()
    finally:
        process.terminate()
        process.wait(timeout=20)
        log.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", type=Path)
    mode.add_argument("--acceptance", type=Path)
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--saved-replay-only", action="store_true")
    parser.add_argument("--saved-replay-fork", action="store_true")
    args = parser.parse_args()
    if args.serve:
        uvicorn.run(
            create_smoke_app(args.serve.resolve()),
            host="127.0.0.1",
            port=args.port,
            log_level="warning",
        )
    else:
        run_acceptance(
            args.acceptance.resolve(),
            port=args.port,
            base_url=args.base_url,
            chromium=args.chromium,
            saved_replay_only=args.saved_replay_only,
            saved_replay_fork=args.saved_replay_fork,
        )
