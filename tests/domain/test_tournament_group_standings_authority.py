"""Domain coverage for canonical tournament group standings."""

import pytest

from beta_engine.domain.matches.formats import EffectiveMatchFormatSnapshot, MatchFormat
from beta_engine.domain.matches.models import (
    MatchResult,
    MatchTerminationReason,
    SetResult,
)
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
    TournamentGroupScheduledMatch,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder,
    TournamentGroupStandingsUnresolvedTie,
    TournamentGroupStandingsUnsupportedResult,
)
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult


def fp(char: str) -> str:
    return char * 64


def format_snapshot(best_of: int = 3) -> EffectiveMatchFormatSnapshot:
    return EffectiveMatchFormatSnapshot.create(
        format=MatchFormat(best_of=best_of, games_to=11, win_by=2),
        source_scope="tournament_group_rules_policy",
        source_key=f"group-rules-policy:{fp('a')}",
    )


def schedule_three() -> TournamentGroupMatchScheduleAuthority:
    fmt = format_snapshot()
    return TournamentGroupMatchScheduleAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="schedule",
        format_authority_fingerprint=fp("b"),
        topology_authority_fingerprint=fp("c"),
        group_rules_policy_fingerprint=fp("a"),
        group_count=1,
        group_size=3,
        match_day_count=3,
        matches=(
            TournamentGroupScheduledMatch(
                match_id="A-B",
                group_index=1,
                topology_match_index=1,
                match_day_ordinal=1,
                match_order=1,
                top_slot_index=1,
                bottom_slot_index=2,
                top_player_id="A",
                bottom_player_id="B",
                effective_match_format=fmt,
            ),
            TournamentGroupScheduledMatch(
                match_id="A-C",
                group_index=1,
                topology_match_index=2,
                match_day_ordinal=2,
                match_order=1,
                top_slot_index=1,
                bottom_slot_index=3,
                top_player_id="A",
                bottom_player_id="C",
                effective_match_format=fmt,
            ),
            TournamentGroupScheduledMatch(
                match_id="B-C",
                group_index=1,
                topology_match_index=3,
                match_day_ordinal=3,
                match_order=1,
                top_slot_index=2,
                bottom_slot_index=3,
                top_player_id="B",
                bottom_player_id="C",
                effective_match_format=fmt,
            ),
        ),
    )


def schedule_four() -> TournamentGroupMatchScheduleAuthority:
    fmt = format_snapshot()
    raw = (
        ("A-D", 1, 1, 1, 4, "A", "D"),
        ("B-C", 2, 1, 2, 3, "B", "C"),
        ("A-C", 3, 2, 1, 3, "A", "C"),
        ("B-D", 4, 2, 2, 4, "B", "D"),
        ("A-B", 5, 3, 1, 2, "A", "B"),
        ("C-D", 6, 3, 3, 4, "C", "D"),
    )
    order_by_day = {1: 0, 2: 0, 3: 0}
    matches = []
    for match_id, topology_index, day, top_slot, bottom_slot, top, bottom in raw:
        order_by_day[day] += 1
        matches.append(
            TournamentGroupScheduledMatch(
                match_id=match_id,
                group_index=1,
                topology_match_index=topology_index,
                match_day_ordinal=day,
                match_order=order_by_day[day],
                top_slot_index=top_slot,
                bottom_slot_index=bottom_slot,
                top_player_id=top,
                bottom_player_id=bottom,
                effective_match_format=fmt,
            )
        )
    return TournamentGroupMatchScheduleAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="schedule",
        format_authority_fingerprint=fp("b"),
        topology_authority_fingerprint=fp("c"),
        group_rules_policy_fingerprint=fp("a"),
        group_count=1,
        group_size=4,
        match_day_count=3,
        matches=tuple(matches),
    )


def played(
    match_id: str,
    player_a: str,
    player_b: str,
    winner: str,
    score: tuple[int, int],
    *,
    set_points: tuple[tuple[int, int], ...] | None = None,
    termination: MatchTerminationReason = MatchTerminationReason.COMPLETED,
) -> MatchResult:
    loser = player_b if winner == player_a else player_a
    player_a_sets, player_b_sets = score
    winner_sets = player_a_sets if winner == player_a else player_b_sets
    loser_sets = player_b_sets if winner == player_a else player_a_sets
    if winner_sets <= loser_sets:
        raise ValueError("winner must own the decisive set count")
    if set_points is None:
        set_points = tuple((11, 5) for _ in range(winner_sets + loser_sets))
    set_winners = []
    for _ in range(loser_sets):
        set_winners.extend((winner, loser))
    set_winners.extend([winner] * (winner_sets - loser_sets))
    sets = []
    for index, (set_winner, points) in enumerate(
        zip(set_winners, set_points, strict=True), start=1
    ):
        set_loser = player_b if set_winner == player_a else player_a
        sets.append(
            SetResult(
                set_number=index,
                winner_player_id=set_winner,
                loser_player_id=set_loser,
                winner_games=points[0],
                loser_games=points[1],
            )
        )
    return MatchResult(
        match_id=match_id,
        winner_player_id=winner,
        loser_player_id=loser,
        player_a_id=player_a,
        player_b_id=player_b,
        best_of=3,
        games_to=11,
        win_by=2,
        sets=sets,
        sets_won={winner: winner_sets, loser: loser_sets},
        termination_reason=termination,
        retired_player_id=(loser if termination == MatchTerminationReason.RETIREMENT else None),
        retired_at_set_start=(3 if termination == MatchTerminationReason.RETIREMENT else None),
    )


def receipt(schedule, result, char):
    frozen = next(match for match in schedule.matches if match.match_id == result.match_id)
    return TournamentGroupStandingsBuilder.receipt_from_result(
        scheduled_match=frozen,
        result=result,
        result_fingerprint=fp(char),
    )


@pytest.mark.pr_critical
def test_group_table_scores_played_matches_and_walkover_without_fake_ratios():
    schedule = schedule_three()
    receipts = (
        TournamentGroupStandingsBuilder.receipt_from_result(
            scheduled_match=schedule.matches[0],
            result=TournamentWalkoverResult(
                match_id="A-B", winner_player_id="A", loser_player_id="B"
            ),
            result_fingerprint=fp("1"),
        ),
        receipt(schedule, played("A-C", "A", "C", "A", (2, 0)), "2"),
        receipt(schedule, played("B-C", "B", "C", "C", (0, 2)), "3"),
    )

    authority = TournamentGroupStandingsBuilder.build(
        schedule=schedule, receipts=receipts, command_id="standings"
    )
    rows = {row.player_id: row for row in authority.groups[0].rows}

    assert tuple(row.player_id for row in authority.groups[0].rows) == ("A", "C", "B")
    assert (rows["A"].wins, rows["A"].group_points) == (2, 8)
    assert rows["A"].walkovers_received == 1
    assert rows["A"].played_matches == 1
    assert (rows["A"].games_won, rows["A"].games_lost) == (2, 0)
    assert rows["A"].points_won == 22
    assert rows["A"].points_lost == 10
    assert rows["B"].walkovers_conceded == 1
    assert rows["B"].played_matches == 1


@pytest.mark.pr_critical
def test_two_player_primary_tie_is_resolved_by_head_to_head():
    schedule = schedule_four()
    results = {
        "A-D": played("A-D", "A", "D", "D", (0, 2)),
        "B-C": played("B-C", "B", "C", "B", (2, 0)),
        "A-C": played("A-C", "A", "C", "C", (0, 2)),
        "B-D": played("B-D", "B", "D", "D", (0, 2)),
        "A-B": played("A-B", "A", "B", "A", (2, 0)),
        "C-D": played("C-D", "C", "D", "D", (0, 2)),
    }
    receipts = tuple(
        receipt(schedule, results[match.match_id], str(index))
        for index, match in enumerate(schedule.matches, start=1)
    )

    authority = TournamentGroupStandingsBuilder.build(
        schedule=schedule, receipts=receipts, command_id="standings"
    )
    rows = authority.groups[0].rows
    by_id = {row.player_id: row for row in rows}

    assert by_id["A"].wins == by_id["B"].wins == 1
    assert by_id["A"].group_points == by_id["B"].group_points == 4
    assert next(row.position for row in rows if row.player_id == "A") < next(
        row.position for row in rows if row.player_id == "B"
    )


@pytest.mark.pr_critical
def test_three_player_tie_uses_all_group_game_then_point_ratios_exactly():
    schedule = schedule_three()
    results = (
        played(
            "A-B",
            "A",
            "B",
            "A",
            (2, 1),
            set_points=((11, 1), (11, 9), (11, 1)),
        ),
        played(
            "A-C",
            "A",
            "C",
            "C",
            (1, 2),
            set_points=((11, 9), (11, 9), (11, 9)),
        ),
        played(
            "B-C",
            "B",
            "C",
            "B",
            (2, 1),
            set_points=((11, 9), (11, 9), (11, 9)),
        ),
    )
    receipts = tuple(
        receipt(schedule, result, str(index))
        for index, result in enumerate(results, start=1)
    )

    authority = TournamentGroupStandingsBuilder.build(
        schedule=schedule, receipts=receipts, command_id="standings"
    )

    # All three have one win, four group points and a 3:3 game ratio.
    # Exact all-group point ratios then order A (60:44), C (60:60), B (44:60).
    assert tuple(row.player_id for row in authority.groups[0].rows) == ("A", "C", "B")


@pytest.mark.pr_critical
def test_exact_unresolved_tie_has_no_hidden_player_id_or_random_fallback():
    schedule = schedule_three()
    results = (
        played(
            "A-B",
            "A",
            "B",
            "A",
            (2, 1),
            set_points=((11, 9), (11, 9), (11, 9)),
        ),
        played(
            "A-C",
            "A",
            "C",
            "C",
            (1, 2),
            set_points=((11, 9), (11, 9), (11, 9)),
        ),
        played(
            "B-C",
            "B",
            "C",
            "B",
            (2, 1),
            set_points=((11, 9), (11, 9), (11, 9)),
        ),
    )
    receipts = tuple(
        receipt(schedule, result, str(index))
        for index, result in enumerate(results, start=1)
    )

    with pytest.raises(
        TournamentGroupStandingsUnresolvedTie,
        match="explicit Admin resolution",
    ):
        TournamentGroupStandingsBuilder.build(
            schedule=schedule, receipts=receipts, command_id="standings"
        )


@pytest.mark.pr_critical
def test_group_retirement_table_effect_fails_closed_until_master_decides_it():
    schedule = schedule_three()
    retired = played(
        "A-B",
        "A",
        "B",
        "A",
        (1, 0),
        termination=MatchTerminationReason.RETIREMENT,
    )

    with pytest.raises(
        TournamentGroupStandingsUnsupportedResult,
        match="RET table points",
    ):
        receipt(schedule, retired, "1")
