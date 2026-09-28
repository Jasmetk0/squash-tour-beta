from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.finals import (
    WorldTourFinalsRaceInput,
    WorldTourFinalsRacePlayer,
    WorldTourFinalsRaceResult,
    calculate_world_tour_finals_race,
)
from beta_engine.domain.rankings.official import RankingWeek


FP = "a" * 64
ELIGIBILITY_FP = "b" * 64


def result(
    player_id: str,
    edition_id: str,
    points: int,
    *,
    week: int = 20,
    fingerprint_char: str = "c",
) -> WorldTourFinalsRaceResult:
    return WorldTourFinalsRaceResult(
        run_id="run",
        branch_id="branch",
        edition_id=edition_id,
        event_id=f"event-{edition_id}",
        player_id=player_id,
        completed_week=RankingWeek(season_index=3, week=week),
        race_points=points,
        source_award_fingerprint=fingerprint_char * 64,
    )


def source(*, players, results, best_n=3):
    return WorldTourFinalsRaceInput(
        run_id="run",
        branch_id="branch",
        target_season_index=3,
        cutoff_week=RankingWeek(season_index=3, week=50),
        cutoff_official_ranking_fingerprint=FP,
        eligibility_fingerprint=ELIGIBILITY_FP,
        policy_id="wtf-race-2003",
        best_n=best_n,
        players=tuple(players),
        eligible_results=tuple(results),
    )


@pytest.mark.pr_critical
def test_race_uses_best_n_and_master_result_profile_tie_break():
    snapshot = calculate_world_tour_finals_race(
        source(
            players=(
                WorldTourFinalsRacePlayer(player_id="A", tie_break_token="z-token"),
                WorldTourFinalsRacePlayer(player_id="B", tie_break_token="a-token"),
                WorldTourFinalsRacePlayer(player_id="ZERO", tie_break_token="m-token"),
            ),
            results=(
                result("A", "a1", 600, fingerprint_char="1"),
                result("A", "a2", 400, fingerprint_char="2"),
                result("A", "a3", 10, fingerprint_char="3"),
                result("B", "b1", 550, fingerprint_char="4"),
                result("B", "b2", 450, fingerprint_char="5"),
                result("B", "b3", 9, fingerprint_char="6"),
            ),
            best_n=2,
        )
    )

    assert [row.player_id for row in snapshot.rows] == ["A", "B", "ZERO"]
    assert snapshot.rows[0].race_points == snapshot.rows[1].race_points == 1000
    assert [item.race_points for item in snapshot.rows[0].counted_results] == [600, 400]
    assert [item.race_points for item in snapshot.rows[1].counted_results] == [550, 450]
    assert snapshot.rows[2].race_points == 0
    assert snapshot.eligible_result_count == 6


@pytest.mark.pr_critical
def test_race_uses_stored_token_only_after_full_points_profile_tie():
    snapshot = calculate_world_tour_finals_race(
        source(
            players=(
                WorldTourFinalsRacePlayer(player_id="PLAYER-Z", tie_break_token="a-token"),
                WorldTourFinalsRacePlayer(player_id="PLAYER-A", tie_break_token="z-token"),
            ),
            results=(
                result("PLAYER-Z", "z1", 700, fingerprint_char="1"),
                result("PLAYER-Z", "z2", 300, fingerprint_char="2"),
                result("PLAYER-A", "a1", 700, fingerprint_char="3"),
                result("PLAYER-A", "a2", 300, fingerprint_char="4"),
            ),
            best_n=2,
        )
    )

    assert [row.player_id for row in snapshot.rows] == ["PLAYER-Z", "PLAYER-A"]


@pytest.mark.pr_critical
def test_race_fingerprint_is_independent_of_input_tuple_order():
    players = (
        WorldTourFinalsRacePlayer(player_id="A", tie_break_token="a-token"),
        WorldTourFinalsRacePlayer(player_id="B", tie_break_token="b-token"),
    )
    results = (
        result("A", "a1", 500, fingerprint_char="1"),
        result("B", "b1", 400, fingerprint_char="2"),
    )
    first = source(players=players, results=results)
    second = source(players=tuple(reversed(players)), results=tuple(reversed(results)))

    assert first.fingerprint == second.fingerprint
    assert calculate_world_tour_finals_race(first) == calculate_world_tour_finals_race(second)


@pytest.mark.pr_critical
@pytest.mark.parametrize(
    "override, message",
    [
        (
            {
                "eligible_results": (
                    WorldTourFinalsRaceResult(
                        run_id="other",
                        branch_id="branch",
                        edition_id="e",
                        event_id="event",
                        player_id="A",
                        completed_week=RankingWeek(season_index=3, week=20),
                        race_points=10,
                        source_award_fingerprint="1" * 64,
                    ),
                )
            },
            "another Run/Branch",
        ),
        (
            {
                "eligible_results": (
                    WorldTourFinalsRaceResult(
                        run_id="run",
                        branch_id="branch",
                        edition_id="e",
                        event_id="event",
                        player_id="A",
                        completed_week=RankingWeek(season_index=3, week=51),
                        race_points=10,
                        source_award_fingerprint="1" * 64,
                    ),
                )
            },
            "later than the frozen cutoff",
        ),
    ],
)
def test_race_fails_closed_for_out_of_scope_or_future_evidence(override, message):
    kwargs = dict(
        run_id="run",
        branch_id="branch",
        target_season_index=3,
        cutoff_week=RankingWeek(season_index=3, week=50),
        cutoff_official_ranking_fingerprint=FP,
        eligibility_fingerprint=ELIGIBILITY_FP,
        policy_id="wtf-race-2003",
        best_n=2,
        players=(WorldTourFinalsRacePlayer(player_id="A", tie_break_token="token"),),
        eligible_results=(),
    )
    kwargs.update(override)
    with pytest.raises(ValidationError, match=message):
        WorldTourFinalsRaceInput(**kwargs)


@pytest.mark.pr_critical
def test_race_rejects_duplicate_tie_break_tokens_and_duplicate_player_edition():
    with pytest.raises(ValidationError, match="tie-break tokens"):
        source(
            players=(
                WorldTourFinalsRacePlayer(player_id="A", tie_break_token="same"),
                WorldTourFinalsRacePlayer(player_id="B", tie_break_token="same"),
            ),
            results=(),
        )

    with pytest.raises(ValidationError, match="one player/Edition"):
        source(
            players=(WorldTourFinalsRacePlayer(player_id="A", tie_break_token="token"),),
            results=(
                result("A", "edition", 100, fingerprint_char="1"),
                result("A", "edition", 90, fingerprint_char="2"),
            ),
        )
