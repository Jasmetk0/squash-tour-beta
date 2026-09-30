from __future__ import annotations

import hashlib

import pytest

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.application.viewer_tournament_result_read_model import (
    resolve_viewer_completed_tournaments,
    resolve_viewer_tournament_result,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)


pytestmark = pytest.mark.pr_critical


def _source(
    *,
    run_id: str = "run",
    branch_id: str = "branch",
    event_id: str = "event",
    season_index: int = 2,
    week_number: int = 17,
) -> OwnedTournamentRankingSource:
    week = RankingWeek(season_index=season_index, week=week_number)
    result = TournamentResultAuthority(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
        completed_week=week,
        draw_authority_fingerprint=hashlib.sha256(b"draw").hexdigest(),
        match_package_fingerprint=hashlib.sha256(b"matches").hexdigest(),
        champion_player_id="A",
        finalist_player_id="B",
        qualification_winner_ids=("Q",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                seed_number=1,
                main_entry_status="direct",
                reached_stage="champion",
                final_round_number=2,
                last_match_id="final",
                wins=2,
                losses=0,
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                seed_number=2,
                reached_stage="finalist",
                final_round_number=2,
                eliminated_by_player_id="A",
                last_match_id="final",
                wins=1,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="Q",
                draw_type="both",
                qualifier=True,
                reached_stage="semifinal",
                final_round_number=1,
                eliminated_by_player_id="A",
                last_match_id="semi-a",
                wins=1,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="C",
                draw_type="main",
                reached_stage="semifinal",
                final_round_number=1,
                eliminated_by_player_id="B",
                last_match_id="semi-b",
                wins=0,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="D",
                draw_type="qualification",
                reached_stage="qualification_final",
                final_round_number=1,
                eliminated_by_player_id="Q",
                last_match_id="q-final",
                wins=0,
                losses=1,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-final",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="Q",
                loser_player_id="D",
                scoreline="3-1",
                result_fingerprint="1" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="semi-a",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="Q",
                scoreline="3-0",
                result_fingerprint="2" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="semi-b",
                draw_type="main",
                round_number=1,
                bracket_position=2,
                winner_player_id="B",
                loser_player_id="C",
                scoreline="3-1",
                result_fingerprint="3" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="final",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="B",
                scoreline="3-2",
                result_fingerprint="4" * 64,
            ),
        ),
    )
    awards = build_tournament_point_award_authority(
        result=result,
        point_authority=FrozenPointAwardAuthority(
            ranking_status="ranked",
            point_distribution={
                "champion": 1000,
                "finalist": 650,
                "semifinal": 400,
                "qualification_winner": 150,
                "qualification_final": 100,
            },
            point_distribution_source="test",
        ),
        seed=77,
    )
    binding = TournamentRankingBinding(
        run_id=run_id,
        branch_id=branch_id,
        edition_id=event_id,
        event_id=event_id,
        completed_week=week,
        first_publication_week=RankingWeek(
            season_index=season_index,
            week=min(61, week_number + 1),
        ),
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )
    return OwnedTournamentRankingSource(
        schema_version="owned_tournament_ranking_source.v4",
        binding=binding,
        canonical_result=result,
        canonical_awards=awards,
        adopted_by_command_id="close-event",
        provenance_kind="canonical_run_owned_tournament_authorities",
    )


def test_viewer_result_projects_only_public_sporting_facts() -> None:
    source = _source()
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(source,),
    )

    result = resolve_viewer_tournament_result(
        ranking,
        run_id="run",
        branch_id="branch",
        event_id="event",
    )

    assert result.schema_version == "viewer_tournament_result.v1"
    assert result.completed_season_index == 2
    assert result.completed_week == 17
    assert result.champion_player_id == "A"
    assert result.finalist_player_id == "B"
    assert result.qualification_winner_ids == ("Q",)
    assert [player.player_id for player in result.players] == ["A", "B", "Q", "C", "D"]
    assert result.players[0].main_entry_status == "direct"
    assert result.players[2].qualifier
    assert result.players[2].walkovers_received == 0
    assert [match.match_id for match in result.matches] == [
        "q-final",
        "semi-a",
        "semi-b",
        "final",
    ]
    assert result.matches[-1].scoreline == "3-2"

    serialized = result.model_dump(mode="json")
    rendered = str(serialized)
    for forbidden in (
        "fingerprint",
        "command_id",
        "provenance",
        "canonical_awards",
        "canonical_prize_awards",
        "point_distribution",
        "draw_authority_fingerprint",
        "match_package_fingerprint",
        "result_fingerprint",
    ):
        assert forbidden not in rendered


def test_viewer_result_fails_closed_without_canonical_source() -> None:
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(),
    )
    with pytest.raises(KeyError, match="not present"):
        resolve_viewer_tournament_result(
            ranking,
            run_id="run",
            branch_id="branch",
            event_id="missing",
        )


def test_viewer_result_rejects_wrong_requested_scope() -> None:
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(_source(),),
    )
    with pytest.raises(ValueError, match="scope"):
        resolve_viewer_tournament_result(
            ranking,
            run_id="run",
            branch_id="other",
            event_id="event",
        )



def test_viewer_completed_tournaments_orders_saved_canonical_results() -> None:
    later = _source(event_id="later", season_index=3, week_number=4)
    earlier = _source(event_id="earlier", season_index=2, week_number=55)
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(earlier, later),
    )

    result = resolve_viewer_completed_tournaments(
        ranking,
        run_id="run",
        branch_id="branch",
    )

    assert result.schema_version == "viewer_completed_tournaments.v1"
    assert result.tournament_count == 2
    assert [item.event_id for item in result.tournaments] == ["earlier", "later"]
    assert [(item.completed_season_index, item.completed_week) for item in result.tournaments] == [
        (2, 55),
        (3, 4),
    ]
    assert result.tournaments[0].champion_player_id == "A"
    assert result.tournaments[0].finalist_player_id == "B"
    assert result.tournaments[0].player_count == 5
    assert result.tournaments[0].match_count == 4

    rendered = str(result.model_dump(mode="json"))
    for forbidden in (
        "fingerprint",
        "command_id",
        "provenance",
        "canonical_awards",
        "point_distribution",
    ):
        assert forbidden not in rendered


def test_viewer_completed_tournaments_rejects_duplicate_event_sources() -> None:
    first = _source(event_id="duplicate")
    second = _source(event_id="duplicate")
    ranking = RankingRevisionState(
        run_id="run",
        branch_id="branch",
        entries=(),
        sources=(),
        tournament_sources=(first, second),
    )
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_viewer_completed_tournaments(
            ranking,
            run_id="run",
            branch_id="branch",
        )
