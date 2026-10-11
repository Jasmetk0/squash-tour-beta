"""Canonical direct-entry evidence for World Tour Finals participant selection."""

from types import SimpleNamespace

import pytest

from beta_engine.application.finals_participant_selection import (
    resolve_world_tour_finals_direct_entry_winners,
)
from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek


def fp(char: str) -> str:
    return char * 64


def race():
    return calculate_world_tour_finals_race(
        WorldTourFinalsRaceInput(
            run_id="run",
            branch_id="branch",
            target_season_index=0,
            cutoff_week=RankingWeek(season_index=0, week=10),
            cutoff_official_ranking_fingerprint=fp("a"),
            eligibility_fingerprint=fp("b"),
            policy_id="world_tour_finals_race.v1",
            best_n=3,
            players=(
                WorldTourFinalsRacePlayer(
                    player_id="p1",
                    tie_break_token="token-1",
                ),
                WorldTourFinalsRacePlayer(
                    player_id="p2",
                    tie_break_token="token-2",
                ),
            ),
            eligible_results=(),
        )
    )


def configuration(race_snapshot):
    return WorldTourFinalsParticipantSelectionConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=2,
        direct_entry_event_ids=("DIRECT-A",),
        race_snapshot_fingerprint=race_snapshot.fingerprint,
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="select-field",
    )


def source(*, publication_week=8, canonical=True, champion="p2"):
    binding = SimpleNamespace(
        run_id="run",
        branch_id="branch",
        event_id="DIRECT-A",
        completed_week=RankingWeek(season_index=0, week=7),
        first_publication_week=RankingWeek(
            season_index=0,
            week=publication_week,
        ),
        expected_result_fingerprint=fp("d"),
    )
    result = (
        SimpleNamespace(
            run_id="run",
            branch_id="branch",
            event_id="DIRECT-A",
            completed_week=binding.completed_week,
            fingerprint=fp("d"),
            champion_player_id=champion,
        )
        if canonical
        else None
    )
    return SimpleNamespace(binding=binding, canonical_result=result)


@pytest.mark.pr_critical
def test_direct_entry_winner_comes_only_from_canonical_result_known_by_cutoff():
    race_snapshot = race()
    winners = resolve_world_tour_finals_direct_entry_winners(
        configuration=configuration(race_snapshot),
        race_snapshot=race_snapshot,
        tournament_sources=(source(),),
    )
    assert winners == (("DIRECT-A", "p2"),)

    with pytest.raises(ValueError, match="not public"):
        resolve_world_tour_finals_direct_entry_winners(
            configuration=configuration(race_snapshot),
            race_snapshot=race_snapshot,
            tournament_sources=(source(publication_week=11),),
        )

    with pytest.raises(ValueError, match="canonical Tournament Result"):
        resolve_world_tour_finals_direct_entry_winners(
            configuration=configuration(race_snapshot),
            race_snapshot=race_snapshot,
            tournament_sources=(source(canonical=False),),
        )


@pytest.mark.pr_critical
def test_direct_entry_evidence_requires_exactly_one_scoped_source():
    race_snapshot = race()
    config = configuration(race_snapshot)

    with pytest.raises(ValueError, match="exactly one"):
        resolve_world_tour_finals_direct_entry_winners(
            configuration=config,
            race_snapshot=race_snapshot,
            tournament_sources=(),
        )

    with pytest.raises(ValueError, match="exactly one"):
        resolve_world_tour_finals_direct_entry_winners(
            configuration=config,
            race_snapshot=race_snapshot,
            tournament_sources=(source(), source()),
        )

    wrong_scope = source()
    wrong_scope.binding.run_id = "other"
    with pytest.raises(ValueError, match="scope mismatch"):
        resolve_world_tour_finals_direct_entry_winners(
            configuration=config,
            race_snapshot=race_snapshot,
            tournament_sources=(wrong_scope,),
        )
