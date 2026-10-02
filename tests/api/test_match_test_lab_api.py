from __future__ import annotations

import pytest

from beta_engine.domain.matches import MatchContext, MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player

from test_simulation_api import ApiServer, _request


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


def _payload() -> dict:
    context = MatchContext(
        match_id="api-lab-match",
        player_a=MatchParticipantContext(player=_player("API-A", 87)),
        player_b=MatchParticipantContext(player=_player("API-B", 80)),
    )
    return {
        "scenario": {
            "schema_version": "match_test_lab_scenario.v1",
            "scenario_id": "api-portable-scenario",
            "context": context.model_dump(mode="json"),
            "seed": 42,
            "source_kind": "portable",
        },
        "batch_seeds": [42, 43, 44],
    }


def test_match_lab_api_runs_portable_batch_without_run_scope(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'match-lab.db'}") as server:
        status, body = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/run",
            _payload(),
        )

        assert status == 200, body
        assert body["schema_version"] == "match_test_lab_result.v1"
        assert body["scenario_id"] == "api-portable-scenario"
        assert len(body["scenario_fingerprint"]) == 64
        assert len(body["request_fingerprint"]) == 64
        assert body["compatibility"]["production_kernel"].endswith("MatchEngine.simulate")
        assert body["compatibility"]["match_engine_version"] == "match_engine_v10"
        assert body["compatibility"]["run_mutation_performed"] is False
        assert body["compatibility"]["run_live_link"] is False
        assert body["diagnostics"]["seed_count"] == 3
        assert [row["seed"] for row in body["results"]] == [42, 43, 44]


def test_match_lab_api_exact_replay_returns_identical_content(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'match-lab-replay.db'}") as server:
        payload = _payload()
        first_status, first = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/run",
            payload,
        )
        second_status, second = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/run",
            payload,
        )

        assert first_status == second_status == 200
        assert first == second


def test_match_lab_api_rejects_invalid_batch_contract(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'match-lab-invalid.db'}") as server:
        payload = _payload()
        payload["batch_seeds"] = [1, 1]
        status, _ = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/run",
            payload,
        )
        assert status == 422



def test_match_lab_api_built_ins_and_new_test_session_are_isolated(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'match-lab-sessions.db'}") as server:
        status, scenarios = _request("GET", f"{server.base_url}/admin/labs/match/scenarios")
        assert status == 200
        assert [row["scenario_id"] for row in scenarios] == [
            "standard-even-match",
            "standard-strength-gap",
        ]
        assert all(row["read_only"] is True for row in scenarios)

        status, created = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions",
            {
                "display_name": "API isolated session",
                "built_in_scenario_id": "standard-even-match",
            },
        )
        assert status == 201, created
        assert created["schema_version"] == "match_test_lab_session.v1"
        assert created["version"] == 1
        assert created["scenario"]["source_kind"] == "built_in_copy"
        assert created["scenario"]["source_reference"] == "standard-even-match"
        assert created["scenario"]["source_fingerprint"] == scenarios[0]["scenario_fingerprint"]
        session_id = created["session_id"]

        status, listed = _request("GET", f"{server.base_url}/admin/labs/match/sessions")
        assert status == 200
        assert [item["session_id"] for item in listed] == [session_id]

        edited = created["scenario"]
        edited["seed"] += 5
        edited["context"]["best_of"] = 3
        status, updated = _request(
            "PUT",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}",
            {
                "expected_session_fingerprint": _session_fingerprint(created),
                "display_name": "API edited session",
                "scenario": edited,
            },
        )
        assert status == 200, updated
        assert updated["version"] == 2
        assert updated["display_name"] == "API edited session"

        status, result = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": _session_fingerprint(updated),
                "batch_seeds": [91, 92],
            },
        )
        assert status == 200, result
        assert result["diagnostics"]["seed_count"] == 2
        assert result["compatibility"]["run_mutation_performed"] is False
        assert result["compatibility"]["run_live_link"] is False
        assert result["compatibility"]["normal_format"] is False

        status, scenarios_after = _request("GET", f"{server.base_url}/admin/labs/match/scenarios")
        assert status == 200
        assert scenarios_after == scenarios


def _session_fingerprint(session_payload: dict) -> str:
    import hashlib
    import json

    return hashlib.sha256(
        json.dumps(session_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def test_match_lab_api_rejects_stale_session_mutation_and_run(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'match-lab-stale.db'}") as server:
        status, created = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions",
            {
                "display_name": "Stale test",
                "scenario": _payload()["scenario"],
            },
        )
        assert status == 201
        session_id = created["session_id"]

        stale = "0" * 64
        status, _ = _request(
            "PUT",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}",
            {
                "expected_session_fingerprint": stale,
                "scenario": created["scenario"],
            },
        )
        assert status == 409

        status, _ = _request(
            "POST",
            f"{server.base_url}/admin/labs/match/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": stale,
                "batch_seeds": [],
            },
        )
        assert status == 409
