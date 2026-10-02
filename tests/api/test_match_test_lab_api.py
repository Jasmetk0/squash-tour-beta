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
