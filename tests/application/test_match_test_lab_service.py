from __future__ import annotations

import pytest

from beta_engine.application.match_test_lab_service import (
    MatchLabRequest,
    MatchLabScenario,
    MatchTestLabService,
)
from beta_engine.domain.matches import MatchContext, MatchParticipantContext
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


def _request(*, seeds: tuple[int, ...] = ()) -> MatchLabRequest:
    context = MatchContext(
        match_id="lab-match-1",
        player_a=MatchParticipantContext(player=_player("LAB-A", 86)),
        player_b=MatchParticipantContext(player=_player("LAB-B", 81)),
    )
    return MatchLabRequest(
        scenario=MatchLabScenario(
            scenario_id="portable-v1",
            context=context,
            seed=777,
        ),
        batch_seeds=seeds,
    )


def test_match_lab_exact_replay_is_deterministic_and_isolated() -> None:
    service = MatchTestLabService()
    request = _request()

    first = service.run(request)
    second = service.run(request)

    assert first == second
    assert first.compatibility.production_kernel.endswith("MatchEngine.simulate")
    assert first.compatibility.match_engine_version == "match_engine_v10"
    assert first.compatibility.portable is True
    assert first.compatibility.isolated is True
    assert first.compatibility.run_mutation_performed is False
    assert first.compatibility.run_live_link is False
    assert first.compatibility.normal_format is True
    assert first.compatibility.warnings == ()
    assert first.diagnostics.seed_count == 1
    assert len(first.results) == 1
    assert first.results[0].seed == 777
    assert first.results[0].rally_count > 0
    assert first.results[0].elapsed_seconds > 0


def test_match_lab_multi_seed_batch_uses_same_scenario_without_persistence() -> None:
    result = MatchTestLabService().run(_request(seeds=(100, 101, 102, 103, 104)))

    assert [row.seed for row in result.results] == [100, 101, 102, 103, 104]
    assert result.diagnostics.seed_count == 5
    assert sum(result.diagnostics.wins_by_player.values()) == 5
    assert result.diagnostics.distinct_result_count >= 1
    assert result.diagnostics.average_rally_count > 0
    assert result.diagnostics.average_elapsed_seconds > 0
    assert set(result.diagnostics.wins_by_player) <= {"LAB-A", "LAB-B"}


def test_match_lab_reports_nonstandard_format_compatibility_without_rejecting_kernel() -> None:
    request = _request()
    changed = request.model_copy(
        update={
            "scenario": request.scenario.model_copy(
                update={
                    "context": request.scenario.context.model_copy(
                        update={"best_of": 3}
                    )
                }
            )
        }
    )

    result = MatchTestLabService().run(changed)

    assert result.compatibility.normal_format is False
    assert any("non-standard match format" in warning for warning in result.compatibility.warnings)


def test_match_lab_run_snapshot_copy_requires_fingerprint_for_equivalence_claim() -> None:
    request = _request()
    changed = request.model_copy(
        update={
            "scenario": request.scenario.model_copy(
                update={
                    "source_kind": "run_snapshot_copy",
                    "source_reference": "run-a/branch-b/revision-c",
                }
            )
        }
    )

    result = MatchTestLabService().run(changed)

    assert result.compatibility.isolated is True
    assert result.compatibility.run_live_link is False
    assert any("source_fingerprint" in warning for warning in result.compatibility.warnings)


def test_match_lab_rejects_duplicate_or_oversized_batch_seed_lists() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        _request(seeds=(1, 1))

    with pytest.raises(ValueError, match="at most"):
        _request(seeds=tuple(range(101)))
