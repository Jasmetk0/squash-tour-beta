"""Canonical World Tour Finals Race calculation rules."""

import pytest

from beta_engine.domain.finals import (
    FinalsRaceConfiguration,
    FinalsRaceTournamentAward,
    FinalsRaceTournamentSource,
    build_finals_race_snapshot,
)
from beta_engine.domain.rankings.official import OfficialRankingPlayer, RankingWeek


def fp(char: str) -> str:
    return char * 64


def player(player_id: str, token: str) -> OfficialRankingPlayer:
    return OfficialRankingPlayer(
        player_id=player_id,
        tie_break_token=token,
        tour_entry_week=RankingWeek(season_index=0, week=1),
        retired=False,
    )


def source(
    event_id: str,
    category: str,
    week: int,
    publication_week: int,
    awards: dict[str, int],
    marker: str,
) -> FinalsRaceTournamentSource:
    return FinalsRaceTournamentSource(
        run_id="run",
        branch_id="branch",
        event_id=event_id,
        category=category,
        completed_week=RankingWeek(season_index=0, week=week),
        first_publication_week=RankingWeek(
            season_index=0, week=publication_week
        ),
        owned_source_fingerprint=fp(marker),
        point_award_fingerprint=fp(marker),
        awards=tuple(
            FinalsRaceTournamentAward(
                player_id=player_id,
                race_points_awarded=points,
            )
            for player_id, points in sorted(awards.items())
        ),
    )


@pytest.mark.pr_critical
def test_race_uses_best_n_result_profile_then_frozen_player_token():
    configuration = FinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        season_index=0,
        best_n_results=2,
        eligible_categories=("DIAMOND", "WORLD_CHAMPIONSHIP"),
        cutoff_ranking_week=RankingWeek(season_index=0, week=10),
        cutoff_ranking_snapshot_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="race-config",
    )
    snapshot = build_finals_race_snapshot(
        configuration=configuration,
        players=(
            player("p1", "token-b"),
            player("p2", "token-a"),
            player("p3", "token-c"),
            player("p4", "token-d"),
        ),
        tournament_sources=(
            source("E1", "DIAMOND", 2, 3, {"p1": 500, "p2": 500, "p3": 700}, "d"),
            source("E2", "WORLD_CHAMPIONSHIP", 4, 5, {"p1": 300, "p2": 300, "p4": 750}, "e"),
            # Third eligible result is excluded from Best 2 for p1.
            source("E3", "DIAMOND", 6, 7, {"p1": 250, "p2": 200}, "f"),
            # Ineligible category must not affect Race.
            source("E4", "ELITE", 6, 7, {"p3": 5000}, "1"),
            # Publication after cutoff must not affect Race.
            source("E5", "DIAMOND", 9, 11, {"p4": 9000}, "2"),
        ),
        calendar_content_fingerprint=fp("c"),
        cutoff_transition_fingerprint=fp("b"),
    )

    assert [(row.rank, row.player_id, row.race_points) for row in snapshot.rows] == [
        (1, "p2", 800),
        (2, "p1", 800),
        (3, "p4", 750),
        (4, "p3", 700),
    ]
    by_player = {row.player_id: row for row in snapshot.rows}
    assert by_player["p1"].result_point_profile == (500, 300)
    assert [item.event_id for item in by_player["p1"].counted_contributions] == [
        "E1",
        "E2",
    ]
    assert by_player["p2"].result_point_profile == (500, 300)
    assert "E4" not in snapshot.source_event_ids
    assert "E5" not in snapshot.source_event_ids


@pytest.mark.pr_critical
def test_race_fails_if_frozen_calendar_or_transition_identity_changes():
    configuration = FinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        season_index=0,
        best_n_results=1,
        eligible_categories=("DIAMOND",),
        cutoff_ranking_week=RankingWeek(season_index=0, week=10),
        cutoff_ranking_snapshot_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=fp("c"),
        adopted_by_command_id="race-config",
    )
    with pytest.raises(ValueError, match="Calendar evidence changed"):
        build_finals_race_snapshot(
            configuration=configuration,
            players=(player("p1", "token-a"),),
            tournament_sources=(),
            calendar_content_fingerprint=fp("d"),
            cutoff_transition_fingerprint=fp("b"),
        )
    with pytest.raises(ValueError, match="transition evidence mismatch"):
        build_finals_race_snapshot(
            configuration=configuration,
            players=(player("p1", "token-a"),),
            tournament_sources=(),
            calendar_content_fingerprint=fp("c"),
            cutoff_transition_fingerprint=fp("d"),
        )
