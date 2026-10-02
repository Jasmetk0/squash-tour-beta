from __future__ import annotations

import pytest

from beta_engine.application.tournament_test_lab_service import (
    TournamentLabAssertions,
    TournamentLabScenario,
)
from beta_engine.domain.matches import MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player

from test_simulation_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def _participant(player_id: str, base: int) -> MatchParticipantContext:
    return MatchParticipantContext(
        player=Player(
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
    )


def _scenario() -> TournamentLabScenario:
    participants = tuple(
        _participant(f"API-P{index}", 92 - index * 4)
        for index in range(1, 5)
    )
    return TournamentLabScenario(
        scenario_id="api-four-player-knockout",
        display_name="API four-player knockout",
        format_kind="knockout",
        participants=participants,
        main_draw_size=4,
        seed_order_player_ids=tuple(item.player.player_id for item in participants),
        draw_seed=411,
        match_seed=511,
        assertions=TournamentLabAssertions(expected_played_match_count=3),
    )


def test_tournament_lab_api_lists_built_ins_and_inspects_without_run_scope(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tournament-lab-inspect.db'}") as server:
        status, built_ins = _request(
            "GET",
            f"{server.base_url}/admin/labs/tournament/scenarios",
        )
        assert status == 200, built_ins
        assert [row["scenario_id"] for row in built_ins] == [
            "standard-eight-player-knockout",
            "oversized-eight-player-lab-bracket",
        ]

        scenario = _scenario().model_dump(mode="json")
        status, compatibility = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/inspect",
            scenario,
        )
        assert status == 200, compatibility
        assert compatibility["runnable_in_lab"] is True
        assert compatibility["normal_run_compatible"] is True
        assert compatibility["run_mutation_performed"] is False
        assert compatibility["run_live_link"] is False


def test_tournament_lab_api_runs_replayable_batch_and_returns_machine_report(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tournament-lab-run.db'}") as server:
        payload = {
            "scenario": _scenario().model_dump(mode="json"),
            "batch_match_seeds": [71, 72, 73],
        }
        status, first = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/run",
            payload,
        )
        second_status, second = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/run",
            payload,
        )

        assert status == second_status == 200, first
        assert first == second
        assert first["schema_version"] == "tournament_test_lab_result.v1"
        assert first["compatibility"]["runnable_in_lab"] is True
        assert first["compatibility"]["run_mutation_performed"] is False
        assert len(first["scenario_fingerprint"]) == 64
        assert len(first["request_fingerprint"]) == 64
        assert len(first["draw_authority_fingerprint"]) == 64
        assert first["draw"]["main"]["bracket_size"] == 4
        assert [row["match_seed"] for row in first["runs"]] == [71, 72, 73]
        assert first["diagnostics"]["run_count"] == 3
        assert first["diagnostics"]["completed_run_count"] == 3
        assert first["diagnostics"]["average_played_match_count"] == 3
        assert all(row["tournament_complete"] is True for row in first["runs"])
        assert all(row["champion_player_id"] for row in first["runs"])


def test_tournament_lab_api_reports_unsupported_draft_without_fake_result(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tournament-lab-invalid.db'}") as server:
        scenario = _scenario().model_copy(update={"format_kind": "groups"})
        status, body = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/run",
            {
                "scenario": scenario.model_dump(mode="json"),
                "batch_match_seeds": [],
            },
        )

        assert status == 200, body
        assert body["compatibility"]["runnable_in_lab"] is False
        assert body["draw"] is None
        assert body["runs"] == []
        assert body["diagnostics"]["run_count"] == 0
        assert any(
            issue["code"] == "FORMAT_NOT_EXECUTABLE_V1"
            for issue in body["compatibility"]["issues"]
        )



def test_tournament_lab_api_persistent_test_session_roundtrip_and_stale_guard(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tournament-lab-sessions.db'}") as server:
        status, built_ins = _request(
            "GET",
            f"{server.base_url}/admin/labs/tournament/scenarios",
        )
        assert status == 200

        status, created = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/sessions",
            {
                "display_name": "API Tournament Session",
                "built_in_scenario_id": built_ins[0]["scenario_id"],
            },
        )
        assert status == 201, created
        assert created["schema_version"] == "tournament_test_lab_session.v1"
        assert created["version"] == 1
        assert created["scenario"]["source_kind"] == "built_in_copy"
        assert created["scenario"]["source_reference"] == built_ins[0]["scenario_id"]
        assert created["scenario"]["source_fingerprint"] == built_ins[0]["scenario_fingerprint"]
        session_id = created["session_id"]

        status, listed = _request(
            "GET",
            f"{server.base_url}/admin/labs/tournament/sessions",
        )
        assert status == 200
        assert [row["session_id"] for row in listed] == [session_id]

        status, loaded = _request(
            "GET",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}",
        )
        assert status == 200
        assert loaded == created

        edited = created["scenario"]
        edited["draw_seed"] += 1
        status, stale = _request(
            "PUT",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}",
            {
                "expected_session_fingerprint": "0" * 64,
                "display_name": "stale",
                "scenario": edited,
            },
        )
        assert status == 409, stale

        status, updated = _request(
            "PUT",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}",
            {
                "expected_session_fingerprint": created["session_fingerprint"],
                "display_name": "API Tournament Session v2",
                "scenario": edited,
            },
        )
        assert status == 200, updated
        assert updated["version"] == 2
        assert updated["display_name"] == "API Tournament Session v2"

        status, stale_run = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": created["session_fingerprint"],
                "batch_match_seeds": [91],
            },
        )
        assert status == 409, stale_run

        status, result = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/sessions/{session_id}/run",
            {
                "expected_session_fingerprint": updated["session_fingerprint"],
                "batch_match_seeds": [91, 92],
            },
        )
        assert status == 200, result
        assert result["diagnostics"]["run_count"] == 2
        assert result["compatibility"]["run_mutation_performed"] is False
        assert result["compatibility"]["run_live_link"] is False


def test_tournament_lab_api_rejects_unknown_built_in_session_source(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'tournament-lab-missing-built-in.db'}") as server:
        status, body = _request(
            "POST",
            f"{server.base_url}/admin/labs/tournament/sessions",
            {
                "display_name": "Missing source",
                "built_in_scenario_id": "does-not-exist",
            },
        )
        assert status == 404, body
