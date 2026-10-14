"""Isolated Chromium acceptance of an authentic cyclic Group tie.

Only the *schedule/result input adapters* are replaced with a deterministic
bounded collection of six real MatchEngine rally logs (as in the existing
production HTTP/SQLite test). All read/resolve/generate HTTP endpoints,
immutability, CAS, SQLite rows and real Run-owned Admin controls are production.
This is NOT normal Run Match-Day seeding, a Run Save or an archived Edition test.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote


def install_real_match_engine_cyclic_fixture(root: Path) -> None:
    """Install test-only result inputs on a disposable backend process.

    The explicit scope file is created only after real Run/Branch/Event setup.
    Foreign Run, Branch and Event requests cannot borrow the test evidence.
    """
    # A CLI script starts with scripts/ on sys.path; fixture tests live in the
    # repository root and must take precedence over unrelated site packages.
    import sys
    repository_root = str(Path(__file__).resolve().parents[1])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    from beta_engine.infrastructure.db import (
        tournament_group_standings_authority as standings_module,
        tournament_group_tie_resolution_authority as tie_module,
    )
    from tests.infrastructure.real_four_player_cyclic_tie_evidence import (
        _generate_four_player_cyclic_receipts,
    )

    original, receipts, expected_case = _generate_four_player_cyclic_receipts()
    assert len(receipts) == 6
    assert expected_case.player_ids == ("A", "B", "C")
    scope_file = root / "real-cyclic-tie-scope.json"

    class ExactFixtureSchedule:
        def __init__(self, session):
            self.session = session

        def get(self, *, run_id: str, branch_id: str, event_id: str):
            if not scope_file.is_file():
                return None
            scope = json.loads(scope_file.read_text())
            if (run_id, branch_id, event_id) != (
                scope["run_id"], scope["branch_id"], scope["event_id"],
            ):
                return None
            return original.model_copy(update={
                "run_id": run_id, "branch_id": branch_id, "event_id": event_id,
            })

    tie_module.TournamentGroupMatchScheduleAuthorityStore = ExactFixtureSchedule
    standings_module.TournamentGroupMatchScheduleAuthorityStore = ExactFixtureSchedule
    standings_module.TournamentGroupStandingsAuthorityStore._result_receipts = (
        lambda self, **kwargs: receipts
    )


def exercise_real_cyclic_browser(
    *, request, page, event_url: str, event_scope: str, artifacts: Path,
    root: Path, run_id: str, branch_id: str, event_id: str,
    restart_backend,
) -> dict:
    """Browser UI commits the *real* three-way case, then HTTP/SQLite restarts."""
    from playwright.sync_api import expect
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from beta_engine.infrastructure.db.models import (
        TournamentGroupStandingsAuthorityModel,
        TournamentGroupTieResolutionAuthorityModel,
    )
    from admin_first_tournament_smoke import browser_click, browser_settle

    scope = {"run_id": run_id, "branch_id": branch_id, "event_id": event_id}
    (root / "real-cyclic-tie-scope.json").write_text(json.dumps(scope))
    tied_path = event_scope + "/group-standings/tie-resolution"
    final_path = event_scope + "/group-standings"

    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    pending = request("GET", tied_path)
    case = pending["unresolved_case"]
    assert case is not None and case["player_ids"] == ["A", "B", "C"], pending
    assert case["reason"] == "automatic_tie_breaks_exhausted"
    assert len(case["source_match_results"]) == 6
    assert pending["resolutions"] == []
    assert len(pending["unresolved_case_fingerprint"]) == 64
    request("GET", final_path, status=404)
    request("POST", final_path + "/generate",
            {"command_id": "premature-real-cyclic-browser"}, status=409)

    # The identity-derived live schedule has *not* produced this deliberately
    # selected cyclic score pattern. Assert the adapter boundary explicitly.
    actual_schedule = request(
        "GET", event_scope + "/format/group-match-schedule",
    )
    assert len(actual_schedule["matches"]) == 6
    assert {m["match_id"] for m in actual_schedule["matches"]} != {
        m["match_id"] for m in case["source_match_results"]
    }, "Fixture must never masquerade as normal Run Match-Day evidence"

    editor = page.get_by_role("group", name="Explicit group tie decision")
    expect(editor).to_be_visible(timeout=30000)
    expect(editor.get_by_role("list", name="Proposed tie order")).to_contain_text("A")
    commit = editor.get_by_role("button", name="Commit audited group tie decision")
    expect(commit).to_be_disabled()
    # C,A,B is an explicit *human-selected* permutation, never an algorithmic
    # tie-break or an automatically inferred national/potential ranking.
    editor.get_by_role("button", name="Move C up").click()
    editor.get_by_role("button", name="Move C up").click()
    ordered = editor.get_by_role("list", name="Proposed tie order")
    assert ordered.locator("li code").all_inner_texts() == ["C", "A", "B"]
    editor.get_by_label("Admin tie decision reason").fill(
        "Reviewed six natural BO3 MatchEngine rally logs and exact exhausted tie criteria."
    )
    expect(commit).to_be_disabled()
    editor.get_by_label(
        "Confirm this exact player order and recorded audit reason"
    ).check()
    expect(commit).to_be_enabled()
    # Production HTTP rejects a stale fingerprint without recording anything.
    request("POST", tied_path, {
        "command_id": "browser-stale-attempt",
        "case_fingerprint": "0" * 64,
        "ordered_player_ids": ["C", "A", "B"],
        "admin_reason": "Must never be committed",
    }, status=409)
    assert request("GET", tied_path)["resolutions"] == []
    page.screenshot(path=str(artifacts / "cyclic-01-reviewed-order.png"),
                    full_page=True)
    browser_click(page, "Commit audited group tie decision")
    browser_settle(page)

    decided = request("GET", tied_path)
    assert decided["unresolved_case"] is None
    assert decided["unresolved_case_fingerprint"] is None
    assert len(decided["resolutions"]) == 1
    saved = decided["resolutions"][0]
    assert saved["decision"]["case"]["player_ids"] == ["A", "B", "C"]
    assert saved["decision"]["ordered_player_ids"] == ["C", "A", "B"]
    assert saved["decision"]["admin_reason"].startswith("Reviewed six natural")
    # Explicit re-use of a stale resolved case must fail closed.
    request("POST", tied_path, {
        "command_id": "browser-stale-after-commit",
        "case_fingerprint": pending["unresolved_case_fingerprint"],
        "ordered_player_ids": ["A", "B", "C"],
        "admin_reason": "Attempt to overwrite exact committed group ordering",
    }, status=409)

    engine = create_engine(f"sqlite:///{root / 'browser.sqlite'}")
    with Session(engine) as session:
        row = session.get(TournamentGroupTieResolutionAuthorityModel,
                          (run_id, branch_id, event_id,
                           pending["unresolved_case_fingerprint"]))
        assert row is not None
        assert row.authority_fingerprint == saved["authority_fingerprint"]
    engine.dispose()
    page.screenshot(path=str(artifacts / "cyclic-02-audited-decision.png"),
                    full_page=True)

    # Real service process restart, same SQLite DB and same explicit test-only
    # evidence adapters. No React intercepts or replacement HTTP responses.
    restart_backend()
    persisted = request("GET", tied_path)
    assert persisted["resolutions"] == [saved]
    assert persisted["unresolved_case"] is None

    page.goto(event_url)
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    expect(page.get_by_label("Canonical completed group standings")).to_be_visible()
    assert page.get_by_role(
        "group", name="Explicit group tie decision"
    ).count() == 0
    button = page.get_by_role("button", name="Generate canonical group standings")
    expect(button).to_be_disabled()
    page.get_by_label(
        "Confirm generation from all completed canonical group matches"
    ).check()
    expect(button).to_be_enabled()
    button.click()
    table = page.get_by_role("table", name="Canonical group 1 standings")
    expect(table).to_be_visible(timeout=30000)
    assert table.locator("tbody tr td:nth-child(2) code").all_inner_texts() == [
        "C", "A", "B", "D"
    ]
    final = request("GET", final_path)
    assert len(final["groups"]) == 1
    assert [r["player_id"] for r in final["groups"][0]["rows"]] == [
        "C", "A", "B", "D"
    ]
    assert final["admin_tie_resolutions"][0]["authority_fingerprint"] == (
        saved["authority_fingerprint"]
    )
    page.screenshot(path=str(artifacts / "cyclic-03-frozen-standings.png"),
                    full_page=True)

    engine = create_engine(f"sqlite:///{root / 'browser.sqlite'}")
    with Session(engine) as session:
        row = session.get(TournamentGroupStandingsAuthorityModel,
                          (run_id, branch_id, event_id))
        assert row is not None
        assert row.authority_fingerprint == final["authority_fingerprint"]
    engine.dispose()

    restart_backend()
    assert request("GET", final_path) == final
    assert request("GET", tied_path)["resolutions"] == [saved]
    page.goto(event_url)
    table = page.get_by_role("table", name="Canonical group 1 standings")
    expect(table).to_be_visible(timeout=30000)
    assert table.locator("tbody tr td:nth-child(2) code").all_inner_texts() == [
        "C", "A", "B", "D"
    ]
    page.screenshot(path=str(artifacts / "cyclic-04-after-sqlite-restart.png"),
                    full_page=True)
    return {
        "scope": scope,
        "original_case_fingerprint": pending["unresolved_case_fingerprint"],
        "committed_authority_fingerprint": saved["authority_fingerprint"],
        "final_table_fingerprint": final["authority_fingerprint"],
        "reviewed_order": ["C", "A", "B"],
        "MatchEngine_games": 6,
        "test_input_adapter": "original_schedule_and_real_matchengine_receipts",
        "production_API_and_SQLite": True,
        "browser_admin_decision": True,
        "SQLite_restarts": 2,
        "Run_match_day_execution": False,
        "Run_Saved_Revision": False,
    }
