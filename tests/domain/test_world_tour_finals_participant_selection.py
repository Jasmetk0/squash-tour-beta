"""Canonical World Tour Finals participant selection from frozen Race."""

import pytest

from beta_engine.domain.finals import (
    WorldTourFinalsParticipantSelectionConfiguration,
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    WorldTourFinalsRaceResult,
    calculate_world_tour_finals_race,
    select_world_tour_finals_participants,
)
from beta_engine.domain.rankings.official import RankingWeek


def fp(char: str) -> str:
    return char * 64


def race():
    players = tuple(
        WorldTourFinalsRacePlayer(
            player_id=f"p{index}",
            tie_break_token=f"token-{index:02d}",
        )
        for index in range(1, 7)
    )
    results = tuple(
        WorldTourFinalsRaceResult(
            run_id="run",
            branch_id="branch",
            edition_id="edition-1",
            event_id="EVT-POINTS",
            player_id=f"p{index}",
            completed_week=RankingWeek(season_index=0, week=5),
            race_points=700 - index * 100,
            source_award_fingerprint=fp(str(index)),
        )
        for index in range(1, 7)
    )
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
            players=players,
            eligible_results=results,
        )
    )


def configuration(race_snapshot, **updates):
    values = dict(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        participant_capacity=4,
        direct_entry_event_ids=("DIRECT-A", "DIRECT-B"),
        race_snapshot_fingerprint=race_snapshot.fingerprint,
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="select-finals-field",
    )
    values.update(updates)
    return WorldTourFinalsParticipantSelectionConfiguration(**values)


@pytest.mark.pr_critical
def test_direct_entry_deduplicates_winner_and_seeding_remains_pure_race_order():
    race_snapshot = race()
    config = configuration(race_snapshot)

    selection = select_world_tour_finals_participants(
        configuration=config,
        race_snapshot=race_snapshot,
        direct_entry_winners=(
            ("DIRECT-A", "p6"),
            ("DIRECT-B", "p6"),
        ),
    )

    # p6 consumes one direct spot despite two selected wins; remaining places are
    # the first three non-selected players in Race order.
    assert [player.player_id for player in selection.participants] == [
        "p1",
        "p2",
        "p3",
        "p6",
    ]
    assert [player.seed for player in selection.participants] == [1, 2, 3, 4]
    assert [player.race_rank for player in selection.participants] == [1, 2, 3, 6]

    direct = selection.participants[-1]
    assert direct.qualification_source == "direct_entry"
    assert direct.direct_entry_event_ids == ("DIRECT-A", "DIRECT-B")
    assert all(
        player.qualification_source == "race"
        for player in selection.participants[:-1]
    )


@pytest.mark.pr_critical
def test_direct_entry_does_not_transfer_and_remaining_capacity_follows_race():
    race_snapshot = race()
    config = configuration(
        race_snapshot,
        direct_entry_event_ids=("DIRECT-A",),
    )

    selection = select_world_tour_finals_participants(
        configuration=config,
        race_snapshot=race_snapshot,
        direct_entry_winners=(("DIRECT-A", "p2"),),
    )

    # p2 already sits inside the Race-qualified top four. Its direct berth does
    # not transfer to another player; the selected field remains p1-p4.
    assert [player.player_id for player in selection.participants] == [
        "p1",
        "p2",
        "p3",
        "p4",
    ]
    assert selection.participants[1].qualification_source == "direct_entry"
    assert selection.participants[3].qualification_source == "race"


@pytest.mark.pr_critical
def test_configuration_preserves_at_least_one_race_place():
    race_snapshot = race()
    with pytest.raises(ValueError, match="strictly below capacity"):
        configuration(
            race_snapshot,
            participant_capacity=2,
            direct_entry_event_ids=("DIRECT-A", "DIRECT-B"),
        )


@pytest.mark.pr_critical
def test_selection_fails_closed_for_missing_direct_winner_or_short_race():
    race_snapshot = race()
    config = configuration(
        race_snapshot,
        direct_entry_event_ids=("DIRECT-A",),
    )
    with pytest.raises(ValueError, match="absent from frozen Race"):
        select_world_tour_finals_participants(
            configuration=config,
            race_snapshot=race_snapshot,
            direct_entry_winners=(("DIRECT-A", "missing"),),
        )

    short_config = configuration(
        race_snapshot,
        participant_capacity=7,
        direct_entry_event_ids=(),
    )
    with pytest.raises(ValueError, match="enough players"):
        select_world_tour_finals_participants(
            configuration=short_config,
            race_snapshot=race_snapshot,
            direct_entry_winners=(),
        )
