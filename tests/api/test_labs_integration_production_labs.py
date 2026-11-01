from __future__ import annotations

import pytest
from test_simulation_api import ApiServer, _request

from beta_engine.domain.players import HiddenCareerTraits, Player

pytestmark = pytest.mark.pr_critical

def _player(player_id: str, base: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=base,
        movement=base,
        physical=base,
        mental=base,
        consistency=base,
        clutch=base,
        recovery=base,
        play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def test_match_lab_production_lifecycle(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'match-lab-prod.db'}"
    with ApiServer(database_url=db_url) as server:
        # 1. Fetch built-ins
        status, scenarios = _request("GET", f"{server.base_url}/admin/labs/match/scenarios")
        assert status == 200, scenarios
        assert len(scenarios) > 0

        # 2. Create Session
        status, session = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions",
            {
                "display_name": "Integration Test Match Lab",
                "built_in_scenario_id": scenarios[0]["scenario_id"]
            }
        )
        assert status == 201, session
        session_id = session["session_id"]
        fingerprint = session["session_fingerprint"]

        # Ensure isolated from Run Saved Revision
        assert "run_id" not in session
        assert "branch_id" not in session

        # 3. Reject stale/concurrent fingerprint
        update_payload = {
            "expected_session_fingerprint": "0" * 64,
            "display_name": "Integration Test Player Lab",
            "scenario": session["scenario"]
        }
        status, stale_update = _request(
            "PUT",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}",
            update_payload
        )
        assert status == 409, stale_update

        # 4. Explicit Save with correct fingerprint
        session["scenario"]["seed"] = 999
        update_payload["expected_session_fingerprint"] = fingerprint
        update_payload["display_name"] = "Integration Test Player Lab Updated"
        status, updated_session = _request(
            "PUT",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}",
            update_payload
        )
        assert status == 200, updated_session
        new_fingerprint = updated_session["session_fingerprint"]
        assert fingerprint != new_fingerprint

        # 5. Reject invalid repetitive command (running with stale fingerprint)
        status, run_stale = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": fingerprint, # Already stale
                "batch_seeds": [1, 2]
            }
        )
        assert status == 409, run_stale

    # 6. Restart & Reload (simulate independent load)
    with ApiServer(database_url=db_url) as server:
        status, reloaded = _request("GET", f"{server.base_url}/admin/labs/match/sessions/{session_id}")
        assert status == 200, reloaded
        assert reloaded["session_fingerprint"] == new_fingerprint
        assert reloaded["scenario"]["seed"] == 999


def test_tournament_lab_production_lifecycle(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'tournament-lab-prod.db'}"
    with ApiServer(database_url=db_url) as server:
        # 1. Fetch built-ins
        status, scenarios = _request("GET", f"{server.base_url}/admin/labs/tournament/scenarios")
        assert status == 200, scenarios
        assert len(scenarios) > 0

        # 2. Create Session
        status, session = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/sessions",
            {
                "display_name": "Integration Test Tournament Lab",
                "built_in_scenario_id": scenarios[0]["scenario_id"]
            }
        )
        assert status == 201, session
        session_id = session["session_id"]
        fingerprint = session["session_fingerprint"]
        assert "run_id" not in session

        # 3. Reject stale fingerprint
        update_payload = {
            "expected_session_fingerprint": "0" * 64,
            "display_name": "Integration Test Player Lab",
            "scenario": session["scenario"]
        }
        status, stale_update = _request(
            "PUT",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}",
            update_payload
        )
        assert status == 409, stale_update

        # 4. Explicit Save with correct fingerprint
        session["scenario"]["display_name"] = "Integration Test Edition"
        update_payload["expected_session_fingerprint"] = fingerprint
        update_payload["display_name"] = "Integration Test Player Lab Updated"
        status, updated_session = _request(
            "PUT",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}",
            update_payload
        )
        assert status == 200, updated_session
        new_fingerprint = updated_session["session_fingerprint"]
        assert fingerprint != new_fingerprint

        # 5. Missing boundary / Unsupported report (no false positive result)
        # Attempt to inspect an invalid format (to trigger a known domain failure explicitly described in missing boundary error, not a mock 200)
        invalid_scenario = dict(updated_session["scenario"])
        invalid_scenario["draw_format"] = "unsupported_draw_format_xyz"
        status, inspect_result = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/inspect",
            invalid_scenario
        )
        assert status == 422, inspect_result # Expect validation failure, no fake match engine result generated

    # 6. Restart & Reload
    with ApiServer(database_url=db_url) as server:
        status, reloaded = _request("GET", f"{server.base_url}/admin/labs/tournament/sessions/{session_id}")
        assert status == 200, reloaded
        assert reloaded["session_fingerprint"] == new_fingerprint
        assert reloaded["scenario"]["display_name"] == "Integration Test Edition"


def test_player_lab_production_lifecycle(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'player-lab-prod.db'}"
    with ApiServer(database_url=db_url) as server:
        # 1. Fetch built-ins
        status, scenarios = _request("GET", f"{server.base_url}/admin/labs/player/scenarios")
        assert status == 200, scenarios
        assert len(scenarios) > 0

        # 2. Create Session
        status, session = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/sessions",
            {
                "display_name": "Integration Test Player Lab",
                "scenario": scenarios[0]["scenario"]
            }
        )
        assert status == 201, session
        session_id = session["session_id"]
        fingerprint = session["session_fingerprint"]
        assert "run_id" not in session

        # 3. Reject stale fingerprint
        update_payload = {
            "expected_session_fingerprint": "0" * 64,
            "display_name": "Integration Test Player Lab",
            "scenario": session["scenario"]
        }
        status, stale_update = _request(
            "PUT",
            f"{server.base_url}/admin/labs/player/sessions/{session_id}",
            update_payload
        )
        assert status == 409, stale_update

        # 4. Explicit Save with correct fingerprint
        session["scenario"]["variants"][0]["competitive_match_counts"] = [5] * len(session["scenario"]["variants"][0]["competitive_match_counts"])
        update_payload["expected_session_fingerprint"] = fingerprint
        update_payload["display_name"] = "Integration Test Player Lab Updated"
        status, updated_session = _request(
            "PUT",
            f"{server.base_url}/admin/labs/player/sessions/{session_id}",
            update_payload
        )
        assert status == 200, updated_session
        new_fingerprint = updated_session["session_fingerprint"]
        assert fingerprint != new_fingerprint

        # 5. Execute run and verify Run/Branch separation
        status, run_result = _request(
            "POST",
            f"{server.base_url}/admin/labs/player/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": new_fingerprint
            }
        )
        assert status == 200, run_result
        assert run_result["compatibility"]["run_mutation_performed"] is False
        assert run_result["compatibility"]["run_live_link"] is False
        assert run_result["compatibility"]["training_load_supported"] is False

    # 6. Restart & Reload
    with ApiServer(database_url=db_url) as server:
        status, list_result = _request("GET", f"{server.base_url}/admin/labs/player/sessions")
        assert status == 200, list_result
        reloaded = next(s for s in list_result if s["session_id"] == session_id)
        assert reloaded["session_fingerprint"] == new_fingerprint
        assert reloaded["scenario"]["variants"][0]["competitive_match_counts"][0] == 5
