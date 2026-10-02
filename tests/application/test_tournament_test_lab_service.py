from __future__ import annotations

import pytest

from beta_engine.application.tournament_test_lab_service import (
    TournamentLabAssertions,
    TournamentLabRequest,
    TournamentLabScenario,
    TournamentTestLabService,
)
from beta_engine.domain.matches import MatchParticipantContext
from beta_engine.domain.players import HiddenCareerTraits, Player


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


def _scenario(
    *,
    count: int = 8,
    capacity: int = 8,
    format_kind: str = "knockout",
    stop_after_round: int | None = None,
) -> TournamentLabScenario:
    participants = tuple(
        _participant(f"P{index}", 94 - index * 3)
        for index in range(1, count + 1)
    )
    return TournamentLabScenario(
        scenario_id=f"lab-{count}-{capacity}",
        display_name="Tournament Lab test",
        format_kind=format_kind,
        participants=participants,
        main_draw_size=capacity,
        seed_order_player_ids=tuple(item.player.player_id for item in participants),
        draw_seed=1701,
        match_seed=2701,
        stop_after_round=stop_after_round,
        assertions=TournamentLabAssertions(
            expected_played_match_count=(count - 1 if capacity == count else None)
        ),
    )


def test_tournament_lab_replays_shared_draw_and_match_kernels_deterministically() -> None:
    service = TournamentTestLabService()
    request = TournamentLabRequest(scenario=_scenario())

    first = service.run(request)
    second = service.run(request)

    assert first == second
    assert first.compatibility.runnable_in_lab is True
    assert first.compatibility.normal_run_compatible is True
    assert first.compatibility.run_mutation_performed is False
    assert first.compatibility.run_live_link is False
    assert any("TournamentDrawAuthorityBuilder" in value for value in first.compatibility.shared_authorities)
    assert any("MatchEngine.simulate" in value for value in first.compatibility.shared_authorities)
    assert first.draw is not None
    assert first.draw.main.bracket_size == 8
    assert first.draw.algorithm_version == "idealized_seed_tiers.v2"
    assert first.format_authority_fingerprint
    assert first.draw_input_fingerprint
    assert first.draw_authority_fingerprint
    assert len(first.runs) == 1
    run = first.runs[0]
    assert run.tournament_complete is True
    assert run.champion_player_id in {f"P{index}" for index in range(1, 9)}
    assert run.played_match_count == 7
    assert all(row.status == "played" for row in run.match_results)
    assert all(row.result_fingerprint for row in run.match_results)
    assert all(row.rally_count > 0 for row in run.match_results)
    assert run.assertions[0].status == "passed"


def test_tournament_lab_batch_changes_match_seed_without_redrawing() -> None:
    result = TournamentTestLabService().run(
        TournamentLabRequest(
            scenario=_scenario(),
            batch_match_seeds=(100, 101, 102, 103),
        )
    )

    assert [row.match_seed for row in result.runs] == [100, 101, 102, 103]
    assert result.diagnostics.run_count == 4
    assert result.diagnostics.completed_run_count == 4
    assert sum(result.diagnostics.champions.values()) == 4
    assert result.diagnostics.average_played_match_count == 7
    assert len({row.run_fingerprint for row in result.runs}) >= 1
    assert result.draw_authority_fingerprint == result.draw.fingerprint


def test_tournament_lab_can_stop_after_round_without_fabricating_champion() -> None:
    scenario = _scenario(stop_after_round=1).model_copy(
        update={
            "assertions": TournamentLabAssertions(
                expected_champion_player_id="P1",
                expected_played_match_count=4,
            )
        }
    )
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    run = result.runs[0]
    assert run.completed_rounds == 1
    assert run.tournament_complete is False
    assert run.champion_player_id is None
    assert run.played_match_count == 4
    assertions = {item.assertion: item for item in run.assertions}
    assert assertions["expected_champion_player_id"].status == "not_evaluated"
    assert assertions["expected_played_match_count"].status == "passed"


def test_tournament_lab_runs_unusual_bye_geometry_but_reports_normal_run_incompatibility() -> None:
    result = TournamentTestLabService().run(
        TournamentLabRequest(scenario=_scenario(count=8, capacity=16))
    )

    assert result.compatibility.runnable_in_lab is True
    assert result.compatibility.normal_run_compatible is False
    assert any(
        issue.code == "NONCANONICAL_CLASSIC_CAPACITY"
        for issue in result.compatibility.issues
    )
    assert result.draw is not None
    assert result.draw.main.bracket_size == 16
    assert result.runs[0].bye_advance_count > 0
    assert result.runs[0].champion_player_id is not None


def test_tournament_lab_invalid_or_unsupported_draft_is_inspectable_without_result() -> None:
    scenario = _scenario(format_kind="groups")
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert result.compatibility.normal_run_compatible is False
    assert any(
        issue.code == "FORMAT_NOT_EXECUTABLE_V1"
        for issue in result.compatibility.issues
    )
    assert result.draw is None
    assert result.runs == ()
    assert result.diagnostics.run_count == 0


def test_tournament_lab_seed_order_mismatch_blocks_execution_without_mutation() -> None:
    scenario = _scenario().model_copy(update={"seed_order_player_ids": ("P1", "P2")})
    result = TournamentTestLabService().run(TournamentLabRequest(scenario=scenario))

    assert result.compatibility.runnable_in_lab is False
    assert any(
        issue.code == "SEED_ORDER_NOT_FIELD_PERMUTATION"
        for issue in result.compatibility.issues
    )
    assert result.compatibility.run_mutation_performed is False
    assert result.runs == ()


def test_tournament_lab_rejects_duplicate_or_oversized_batch_seed_lists() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        TournamentLabRequest(scenario=_scenario(), batch_match_seeds=(1, 1))

    with pytest.raises(ValueError, match="at most"):
        TournamentLabRequest(
            scenario=_scenario(),
            batch_match_seeds=tuple(range(101)),
        )


def test_tournament_lab_built_ins_are_deterministic_and_read_only() -> None:
    service = TournamentTestLabService()
    rows = service.list_built_in_scenarios()

    assert [item.scenario_id for item in rows] == [
        "standard-eight-player-knockout",
        "oversized-eight-player-lab-bracket",
    ]
    assert all(item.read_only is True for item in rows)
    assert all(item.scenario_fingerprint == item.scenario.fingerprint for item in rows)
    assert rows == TournamentTestLabService().list_built_in_scenarios()
