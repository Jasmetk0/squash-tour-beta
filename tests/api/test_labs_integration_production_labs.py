from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest
from test_simulation_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical

def _run_lab_lifecycle(
    tmp_path,
    lab_type: str,
    modify_scenario_fn,
    run_or_inspect_fn,
    verify_reload_fn
) -> None:
    db_url = f"sqlite:///{tmp_path / f'{lab_type}-lab-prod.db'}"

    with ApiServer(database_url=db_url) as server:
        status, run = _request('POST', server.base_url + '/run-containers',
                               {'display_name': 'Unrelated Saved Run'})
        assert status == 201, run
        # 1. Fetch built-ins
        status, scenarios = _request("GET", f"{server.base_url}/admin/labs/{lab_type}/scenarios")
        assert status == 200, scenarios
        assert len(scenarios) > 0

        # 2. Create Session
        create_payload = {"display_name": f"Integration Test {lab_type.capitalize()} Lab"}
        if lab_type == "player":
            create_payload["scenario"] = scenarios[0]["scenario"]
        else:
            create_payload["built_in_scenario_id"] = scenarios[0]["scenario_id"]

        status, session = _request("POST", f"{server.base_url}/admin/labs/{lab_type}/sessions", create_payload)
        assert status == 201, session
        session_id = session["session_id"]
        fingerprint = session["session_fingerprint"]
        assert "run_id" not in session
        assert "branch_id" not in session

        # 3. Reject stale/concurrent fingerprint
        update_payload = {
            "expected_session_fingerprint": "0" * 64,
            "display_name": "Integration Test Update",
            "scenario": session["scenario"]
        }
        status, stale_update = _request("PUT", f"{server.base_url}/admin/labs/{lab_type}/sessions/{session_id}", update_payload)
        assert status == 409, stale_update

        # 4. Explicit Save with correct fingerprint
        modify_scenario_fn(session["scenario"])
        update_payload["expected_session_fingerprint"] = fingerprint
        update_payload["scenario"] = session["scenario"]
        status, updated_session = _request("PUT", f"{server.base_url}/admin/labs/{lab_type}/sessions/{session_id}", update_payload)
        assert status == 200, updated_session
        new_fingerprint = updated_session["session_fingerprint"]
        assert fingerprint != new_fingerprint

        # 5. Execute Lab Specific Run/Inspect
        with closing(sqlite3.connect(tmp_path / f'{lab_type}-lab-prod.db')) as db:
            before_run = tuple(db.iterdump())
        computed = run_or_inspect_fn(server, session_id, updated_session["scenario"], new_fingerprint)
        with closing(sqlite3.connect(tmp_path / f'{lab_type}-lab-prod.db')) as db:
            assert tuple(db.iterdump()) == before_run, 'Lab calculation mutated persisted state'

    # 6. Restart & Reload
    with ApiServer(database_url=db_url) as server:
        if lab_type == "player":
            status, list_result = _request("GET", f"{server.base_url}/admin/labs/player/sessions")
            assert status == 200, list_result
            reloaded = next(s for s in list_result if s["session_id"] == session_id)
        else:
            status, reloaded = _request("GET", f"{server.base_url}/admin/labs/{lab_type}/sessions/{session_id}")
            assert status == 200, reloaded

        assert reloaded["session_fingerprint"] == new_fingerprint
        verify_reload_fn(reloaded["scenario"])
        assert run_or_inspect_fn(server, session_id, reloaded['scenario'], new_fingerprint) == computed
        with closing(sqlite3.connect(tmp_path / f'{lab_type}-lab-prod.db')) as db:
            assert tuple(db.iterdump()) == before_run


def test_match_lab_production_lifecycle(tmp_path) -> None:
    def modify(s): s["seed"] = 999

    def run_fn(server, session_id, scenario, fingerprint):
        status, run_stale = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}/run",
            {"expected_session_fingerprint": "0" * 64, "batch_seeds": [1, 2]}
        )
        assert status == 409, run_stale
        status, result = _request(
            'POST', f'{server.base_url}/admin/labs/match/sessions/{session_id}/run',
            {'expected_session_fingerprint': fingerprint, 'batch_seeds': [1, 2]})
        assert status == 200, result
        assert [row['seed'] for row in result['results']] == [1, 2]
        assert all(row['rally_count'] > 0 and row['winner_player_id'] for row in result['results'])
        assert result['compatibility']['run_mutation_performed'] is False
        return result

    def verify(s): assert s["seed"] == 999

    _run_lab_lifecycle(tmp_path, "match", modify, run_fn, verify)


def test_tournament_lab_production_lifecycle(tmp_path) -> None:
    def modify(s): s["display_name"] = "Integration Test Edition"

    def run_fn(server, session_id, scenario, fingerprint):
        invalid_scenario = dict(scenario)
        invalid_scenario["draw_format"] = "unsupported_draw_format_xyz"
        status, inspect_result = _request(
            "POST", f"{server.base_url}/admin/labs/tournament/inspect", invalid_scenario
        )
        assert status == 422, inspect_result
        status, result = _request(
            'POST', f'{server.base_url}/admin/labs/tournament/sessions/{session_id}/run',
            {'expected_session_fingerprint': fingerprint, 'batch_match_seeds': [1]})
        assert status == 200, result
        assert result['compatibility']['runnable_in_lab'] is True
        assert result['compatibility']['run_mutation_performed'] is False
        assert result['runs'] and all(row['tournament_complete'] and row['champion_player_id']
                                      for row in result['runs'])
        assert result['diagnostics']['average_played_match_count'] > 0
        return result

    def verify(s): assert s["display_name"] == "Integration Test Edition"

    _run_lab_lifecycle(tmp_path, "tournament", modify, run_fn, verify)


def test_player_lab_production_lifecycle(tmp_path) -> None:
    def modify(s):
        s["variants"][0]["competitive_match_counts"] = [5] * len(s["variants"][0]["competitive_match_counts"])

    def run_fn(server, session_id, scenario, fingerprint):
        status, run_result = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/sessions/{session_id}/run",
            {"expected_session_fingerprint": fingerprint}
        )
        assert status == 200, run_result
        assert run_result["compatibility"]["run_mutation_performed"] is False
        assert run_result["compatibility"]["run_live_link"] is False
        return run_result

    def verify(s): assert s["variants"][0]["competitive_match_counts"][0] == 5

    _run_lab_lifecycle(tmp_path, "player", modify, run_fn, verify)
