"""Canonical hybrid ranking composition without double-counted tournament sources."""

import pytest

from beta_engine.application.hybrid_tournament_closure import (
    build_hybrid_tournament_point_award_authority,
    hybrid_ranking_policy_blockers,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupResultReceipt,
    TournamentGroupStanding,
    TournamentGroupStandingRow,
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
    TournamentHybridKnockoutBracketMatch,
)
from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)


def fp(char: str) -> str:
    return char * 64


def policy(*, group_win: int = 10, stages=None):
    return TournamentHybridRankingPolicyAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        configured_by_command_id="configure-ranking",
        played_group_win_points=group_win,
        knockout_stage_points=tuple(
            sorted(
                stages
                or {
                    "champion": 100,
                    "finalist": 60,
                }.items()
            )
        ),
    )


def hybrid_result() -> TournamentResultAuthority:
    players = (
        TournamentPlayerResultAuthority(
            player_id="A",
            draw_type="hybrid",
            reached_stage="champion",
            final_round_number=1,
            last_match_id="final",
            wins=3,
            losses=0,
            group_index=1,
            group_position=1,
            played_group_wins=2,
            group_walkovers_received=0,
            knockout_reached_stage="champion",
        ),
        TournamentPlayerResultAuthority(
            player_id="B",
            draw_type="hybrid",
            reached_stage="finalist",
            final_round_number=1,
            eliminated_by_player_id="A",
            last_match_id="final",
            wins=1,
            losses=2,
            group_index=2,
            group_position=1,
            played_group_wins=1,
            group_walkovers_received=0,
            knockout_reached_stage="finalist",
        ),
        TournamentPlayerResultAuthority(
            player_id="C",
            draw_type="hybrid",
            reached_stage="group_stage",
            last_match_id="g-c",
            wins=0,
            losses=2,
            group_index=1,
            group_position=2,
            played_group_wins=0,
            group_walkovers_received=0,
        ),
    )
    return TournamentResultAuthority(
        schema_version="tournament_result_authority.v2",
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=10),
        group_standings_authority_fingerprint=fp("a"),
        hybrid_knockout_bracket_authority_fingerprint=fp("b"),
        champion_player_id="A",
        finalist_player_id="B",
        players=players,
        matches=(
            TournamentMatchResultAuthority(
                match_id="g-a",
                draw_type="group",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="C",
                scoreline="11-5 11-7",
                result_fingerprint=fp("1"),
            ),
            TournamentMatchResultAuthority(
                match_id="g-b",
                draw_type="group",
                round_number=1,
                bracket_position=2,
                winner_player_id="B",
                loser_player_id="C",
                scoreline="11-8 11-9",
                result_fingerprint=fp("2"),
            ),
            TournamentMatchResultAuthority(
                match_id="final",
                draw_type="knockout",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="B",
                scoreline="11-8 11-9 11-7",
                result_fingerprint=fp("3"),
            ),
        ),
    )


@pytest.mark.pr_critical
def test_hybrid_phase_points_become_one_award_and_one_ranking_result_per_player():
    result = hybrid_result()
    awards = build_hybrid_tournament_point_award_authority(
        result=result,
        policy=policy(),
    )
    by_id = {award.player_id: award for award in awards.awards}

    assert awards.schema_version == "tournament_point_award_authority.v4"
    assert by_id["A"].ranking_points_awarded == 120
    assert tuple(
        (component.component_id, component.points_awarded)
        for component in by_id["A"].phase_components
    ) == (
        ("group_played_wins", 20),
        ("knockout_finish", 100),
    )
    assert by_id["B"].ranking_points_awarded == 70
    assert by_id["C"].ranking_points_awarded == 0
    assert len(awards.awards) == len(result.players)

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
    assert len(versions) == 3
    assert len({version.result.player_id for version in versions}) == 3
    assert {v.result.player_id: v.result.main_points for v in versions} == {
        "A": 120,
        "B": 70,
        "C": 0,
    }


@pytest.mark.pr_critical
def test_hybrid_phase_policy_does_not_infer_missing_knockout_values():
    result = hybrid_result()
    with pytest.raises(ValueError, match="lacks knockout stage values"):
        build_hybrid_tournament_point_award_authority(
            result=result,
            policy=policy(stages={"champion": 100, "finalist": 60}),
        ).model_copy(
            update={}
        )

    # The builder only sees stages actually reached, so demonstrate the strict
    # boundary with a result carrying a stage absent from the authored table.
    altered_players = tuple(
        (
            player.model_copy(update={"knockout_reached_stage": "semifinal", "reached_stage": "semifinal"})
            if player.player_id == "C"
            else player
        )
        for player in result.players
    )
    altered = result.model_copy(update={"players": altered_players})
    with pytest.raises(ValueError, match="lacks knockout stage values"):
        build_hybrid_tournament_point_award_authority(
            result=altered,
            policy=policy(),
        )


def standings_with_walkover() -> TournamentGroupStandingsAuthority:
    return TournamentGroupStandingsAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="standings",
        group_match_schedule_fingerprint=fp("c"),
        group_rules_policy_fingerprint=fp("d"),
        source_results=(
            TournamentGroupResultReceipt(
                match_id="g1",
                group_index=1,
                result_fingerprint=fp("4"),
                result_kind="walkover",
                winner_player_id="A",
                loser_player_id="B",
                best_of=3,
                termination_reason="W/O",
            ),
        ),
        groups=(
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
                        played_matches=0,
                        walkovers_received=1,
                        walkovers_conceded=0,
                        games_won=0,
                        games_lost=0,
                        points_won=0,
                        points_lost=0,
                    ),
                    TournamentGroupStandingRow(
                        group_index=1,
                        position=2,
                        player_id="B",
                        wins=0,
                        losses=1,
                        group_points=0,
                        played_matches=0,
                        walkovers_received=0,
                        walkovers_conceded=1,
                        games_won=0,
                        games_lost=0,
                        points_won=0,
                        points_lost=0,
                    ),
                ),
            ),
        ),
    )


def two_player_bracket() -> TournamentHybridKnockoutBracketAuthority:
    match = TournamentHybridKnockoutBracketMatch(
        match_id="final",
        round_number=1,
        match_index=1,
        participant_sources=("player:A", "player:B"),
    )
    return TournamentHybridKnockoutBracketAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        generated_by_command_id="bracket",
        entrants_authority_fingerprint=fp("e"),
        entrant_count=2,
        round_count=1,
        matches=(match,),
        terminal_match_id="final",
    )


@pytest.mark.pr_critical
def test_group_walkover_ranking_reward_remains_explicitly_unresolved():
    blockers = hybrid_ranking_policy_blockers(
        standings=standings_with_walkover(),
        bracket=two_player_bracket(),
        policy=policy(group_win=10),
    )
    assert "hybrid_group_walkover_ranking_unresolved" in blockers

    assert hybrid_ranking_policy_blockers(
        standings=standings_with_walkover(),
        bracket=two_player_bracket(),
        policy=policy(group_win=0),
    ) == ()
