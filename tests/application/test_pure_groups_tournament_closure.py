"""Pure single-group Tournament Edition closure and group-position prize payouts."""

from types import SimpleNamespace

import pytest

import beta_engine.application.pure_groups_tournament_closure as closure_module

from beta_engine.application.pure_groups_tournament_closure import (
    build_pure_groups_point_award_authority,
    build_pure_groups_tournament_result_authority,
    pure_groups_closure_blockers,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupPlayedGame,
    TournamentGroupResultReceipt,
    TournamentGroupStanding,
    TournamentGroupStandingRow,
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.domain.tournaments.prize_money_award_authority import (
    build_tournament_prize_money_award_authority,
)
from beta_engine.domain.tournaments.pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)


def fp(char: str) -> str:
    return char * 64


def pure_result() -> TournamentResultAuthority:
    players = (
        TournamentPlayerResultAuthority(
            player_id="A",
            draw_type="group",
            reached_stage="group_position_1",
            last_match_id="A-B",
            wins=2,
            losses=0,
            group_index=1,
            group_position=1,
            played_group_wins=2,
            group_walkovers_received=0,
        ),
        TournamentPlayerResultAuthority(
            player_id="B",
            draw_type="group",
            reached_stage="group_position_2",
            last_match_id="A-B",
            wins=1,
            losses=1,
            group_index=1,
            group_position=2,
            played_group_wins=1,
            group_walkovers_received=0,
        ),
        TournamentPlayerResultAuthority(
            player_id="C",
            draw_type="group",
            reached_stage="group_position_3",
            last_match_id="B-C",
            wins=0,
            losses=2,
            group_index=1,
            group_position=3,
            played_group_wins=0,
            group_walkovers_received=0,
        ),
    )
    return TournamentResultAuthority(
        schema_version="tournament_result_authority.v3",
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=10),
        group_standings_authority_fingerprint=fp("a"),
        champion_player_id="A",
        finalist_player_id="B",
        players=players,
        matches=(
            TournamentMatchResultAuthority(
                match_id="A-C",
                draw_type="group",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="C",
                scoreline="11-7 11-8",
                result_fingerprint=fp("1"),
            ),
            TournamentMatchResultAuthority(
                match_id="B-C",
                draw_type="group",
                round_number=1,
                bracket_position=2,
                winner_player_id="B",
                loser_player_id="C",
                scoreline="11-9 11-6",
                result_fingerprint=fp("2"),
            ),
            TournamentMatchResultAuthority(
                match_id="A-B",
                draw_type="group",
                round_number=2,
                bracket_position=3,
                winner_player_id="A",
                loser_player_id="B",
                scoreline="11-8 11-9",
                result_fingerprint=fp("3"),
            ),
        ),
    )


def policy(points: int = 10) -> TournamentPureGroupsRankingPolicyAuthority:
    return TournamentPureGroupsRankingPolicyAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        configured_by_command_id="policy",
        played_group_win_points=points,
    )


def event() -> CalendarEvent:
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=10,
        calendar_year=2000,
        year_week=10,
        template_id="template",
        event_name="Round Robin Cup",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=3,
        qualification_draw_size=0,
        seeds_count=0,
        qualifier_spots=0,
        ranking_points_table={"champion": 1, "finalist": 1},
        ranking_configuration_legacy=False,
        prize_money_currency="EUR",
        prize_money_table={
            "group_position_3": 100,
            "group_position_2": 200,
            "group_position_1": 300,
        },
        calendar_fingerprint=fp("f"),
    )


@pytest.mark.pr_critical
def test_pure_groups_points_are_one_tournament_result_from_played_wins_only():
    result = pure_result()
    awards = build_pure_groups_point_award_authority(
        result=result,
        policy=policy(10),
    )
    by_id = {award.player_id: award for award in awards.awards}

    assert awards.schema_version == "tournament_point_award_authority.v5"
    assert {player_id: award.ranking_points_awarded for player_id, award in by_id.items()} == {
        "A": 20,
        "B": 10,
        "C": 0,
    }
    assert all(
        len(award.phase_components) == 1
        and award.phase_components[0].component_id == "group_played_wins"
        for award in awards.awards
    )

    binding = TournamentRankingBinding(
        run_id="run",
        branch_id="branch",
        edition_id="event",
        event_id="event",
        completed_week=result.completed_week,
        first_publication_week=RankingWeek(season_index=0, week=11),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )
    versions = prepare_canonical_tournament_ranking_sources(binding, result, awards)
    assert {item.result.player_id: item.result.main_points for item in versions} == {
        "A": 20,
        "B": 10,
        "C": 0,
    }


@pytest.mark.pr_critical
def test_group_position_prize_money_uses_actual_single_group_finish():
    authority = build_tournament_prize_money_award_authority(
        result=pure_result(),
        event=event(),
    )
    by_id = {award.player_id: award for award in authority.awards}

    assert authority.configuration_status == "complete"
    assert authority.required_stage_ids == (
        "group_position_3",
        "group_position_2",
        "group_position_1",
    )
    assert by_id["A"].amount == 300
    assert by_id["B"].amount == 200
    assert by_id["C"].amount == 100
    assert authority.total_prize_pool_amount == 600


def standings(*, group_count: int = 1, walkover: bool = False):
    groups = [
        TournamentGroupStanding(
            group_index=1,
            rows=(
                TournamentGroupStandingRow(
                    group_index=1,
                    position=1,
                    player_id="A",
                    wins=1,
                    losses=0,
                    group_points=4,
                    played_matches=0 if walkover else 1,
                    walkovers_received=1 if walkover else 0,
                    walkovers_conceded=0,
                    games_won=0 if walkover else 2,
                    games_lost=0,
                    points_won=0 if walkover else 22,
                    points_lost=0 if walkover else 14,
                ),
                TournamentGroupStandingRow(
                    group_index=1,
                    position=2,
                    player_id="B",
                    wins=0,
                    losses=1,
                    group_points=0,
                    played_matches=0 if walkover else 1,
                    walkovers_received=0,
                    walkovers_conceded=1 if walkover else 0,
                    games_won=0,
                    games_lost=0 if walkover else 2,
                    points_won=0 if walkover else 14,
                    points_lost=0 if walkover else 22,
                ),
            ),
        )
    ]
    if group_count == 2:
        groups.append(
            TournamentGroupStanding(
                group_index=2,
                rows=(
                    TournamentGroupStandingRow(
                        group_index=2,
                        position=1,
                        player_id="C",
                        wins=1,
                        losses=0,
                        group_points=4,
                        played_matches=1,
                        walkovers_received=0,
                        walkovers_conceded=0,
                        games_won=2,
                        games_lost=0,
                        points_won=22,
                        points_lost=14,
                    ),
                    TournamentGroupStandingRow(
                        group_index=2,
                        position=2,
                        player_id="D",
                        wins=0,
                        losses=1,
                        group_points=0,
                        played_matches=1,
                        walkovers_received=0,
                        walkovers_conceded=0,
                        games_won=0,
                        games_lost=2,
                        points_won=14,
                        points_lost=22,
                    ),
                ),
            )
        )
    return TournamentGroupStandingsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="standings",
        group_match_schedule_fingerprint=fp("b"),
        group_rules_policy_fingerprint=fp("c"),
        source_results=(
            TournamentGroupResultReceipt(
                match_id="A-B",
                group_index=1,
                result_fingerprint=fp("d"),
                result_kind="walkover" if walkover else "played",
                winner_player_id="A",
                loser_player_id="B",
                best_of=3,
                termination_reason="W/O" if walkover else "COMPLETED",
                games=(
                    ()
                    if walkover
                    else (
                        TournamentGroupPlayedGame(
                            winner_player_id="A",
                            loser_player_id="B",
                            winner_points=11,
                            loser_points=6,
                        ),
                        TournamentGroupPlayedGame(
                            winner_player_id="A",
                            loser_player_id="B",
                            winner_points=11,
                            loser_points=8,
                        ),
                    )
                ),
            ),
        ),
        groups=tuple(groups),
    )


@pytest.mark.pr_critical
def test_pure_groups_closure_refuses_multi_group_outcome_without_cross_group_rule():
    assert pure_groups_closure_blockers(
        standings=standings(group_count=2),
        policy=policy(),
        ranking_status="ranked",
    ) == ("groups_only_unique_outcome_required",)


@pytest.mark.pr_critical
def test_pure_groups_walkover_ranking_reward_remains_explicitly_unresolved():
    assert "pure_groups_group_walkover_ranking_unresolved" in pure_groups_closure_blockers(
        standings=standings(walkover=True),
        policy=policy(10),
        ranking_status="ranked",
    )
    assert pure_groups_closure_blockers(
        standings=standings(walkover=True),
        policy=policy(0),
        ranking_status="ranked",
    ) == ()



@pytest.mark.pr_critical
def test_pure_groups_result_builder_uses_exact_final_standings_and_group_receipts(
    monkeypatch,
):
    schedule = SimpleNamespace(
        fingerprint=fp("b"),
        matches=(
            SimpleNamespace(
                match_id="A-B",
                match_day_ordinal=1,
                topology_match_index=1,
            ),
        ),
    )

    class FakeScheduleStore:
        def __init__(self, session):
            pass

        def get(self, **kwargs):
            return schedule

    monkeypatch.setattr(
        closure_module,
        "TournamentGroupMatchScheduleAuthorityStore",
        FakeScheduleStore,
    )
    source = standings()

    result = build_pure_groups_tournament_result_authority(
        session=object(),
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=10),
        standings=source,
    )

    assert result.schema_version == "tournament_result_authority.v3"
    assert result.champion_player_id == "A"
    assert result.finalist_player_id == "B"
    by_id = {player.player_id: player for player in result.players}
    assert by_id["A"].reached_stage == "group_position_1"
    assert by_id["B"].reached_stage == "group_position_2"
    assert by_id["A"].played_group_wins == 1
    assert by_id["B"].played_group_wins == 0
    assert tuple(match.draw_type for match in result.matches) == ("group",)
