from __future__ import annotations

import json

import pytest

from beta_engine.application.canonical_tournament_points import (
    build_tournament_point_award_authority,
)
from beta_engine.application.season_point_awards_service import (
    FrozenPointAwardAuthority,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)


pytestmark = pytest.mark.pr_critical


def _points(**values: int) -> FrozenPointAwardAuthority:
    return FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution=values,
        point_distribution_source="calendar_event.ranking_points_table",
    )


def test_qualifier_and_lucky_loser_receive_additive_q_plus_main_components() -> None:
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="a" * 64,
        match_package_fingerprint="b" * 64,
        champion_player_id="A",
        finalist_player_id="QW",
        qualification_winner_ids=("QW",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="champion",
                wins=2,
            ),
            TournamentPlayerResultAuthority(
                player_id="QW",
                draw_type="both",
                qualifier=True,
                reached_stage="finalist",
                wins=2,
                losses=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="LL",
                draw_type="both",
                qualifier=True,
                reached_stage="semifinal",
                losses=2,
            ),
            TournamentPlayerResultAuthority(
                player_id="B",
                draw_type="main",
                reached_stage="semifinal",
                losses=1,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-final",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="QW",
                loser_player_id="LL",
                scoreline="3-0",
                result_fingerprint="1" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-semi-1",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="LL",
                scoreline="3-0",
                result_fingerprint="2" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-semi-2",
                draw_type="main",
                round_number=1,
                bracket_position=2,
                winner_player_id="QW",
                loser_player_id="B",
                scoreline="3-0",
                result_fingerprint="3" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-final",
                draw_type="main",
                round_number=2,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="QW",
                scoreline="3-0",
                result_fingerprint="4" * 64,
            ),
        ),
    )

    authority = build_tournament_point_award_authority(
        result=result,
        point_authority=_points(
            champion=1000,
            finalist=600,
            semifinal=300,
            qualification_winner=50,
            qualification_final=20,
        ),
        seed=7001,
    )

    assert authority.schema_version == "tournament_point_award_authority.v3"
    by_player = {award.player_id: award for award in authority.awards}

    qualifier = by_player["QW"]
    assert qualifier.point_stage is None
    assert qualifier.qualification_point_stage == "qualification_winner"
    assert qualifier.qualification_points_awarded == 50
    assert qualifier.ranking_points_awarded == 650
    assert qualifier.race_points_awarded == 650

    lucky_loser = by_player["LL"]
    assert lucky_loser.point_stage is None
    assert lucky_loser.qualification_point_stage == "qualification_final"
    assert lucky_loser.qualification_points_awarded == 20
    assert lucky_loser.ranking_points_awarded == 320
    assert lucky_loser.race_points_awarded == 320

    # Direct-Main players stay single-component even inside an event-level v3.
    assert by_player["A"].qualification_point_stage is None
    assert by_player["A"].ranking_points_awarded == 1000

    reopened = TournamentPointAwardAuthority.model_validate_json(
        authority.model_dump_json()
    )
    assert reopened == authority

    payload = authority.model_dump(mode="json")
    ll_payload = next(
        award for award in payload["awards"] if award["player_id"] == "LL"
    )
    ll_payload["qualification_points_awarded"] += 1
    with pytest.raises(
        ValueError,
        match="Qualification point component amount differs",
    ):
        TournamentPointAwardAuthority.model_validate_json(
            json.dumps(payload, sort_keys=True, separators=(",", ":"))
        )


def test_qualification_bye_alone_does_not_unlock_qualification_winner_points() -> None:
    result = TournamentResultAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        completed_week=RankingWeek(season_index=0, week=1),
        draw_authority_fingerprint="c" * 64,
        match_package_fingerprint="d" * 64,
        champion_player_id="A",
        finalist_player_id="QB",
        qualification_winner_ids=("QB",),
        players=(
            TournamentPlayerResultAuthority(
                player_id="A",
                draw_type="main",
                reached_stage="champion",
                wins=1,
            ),
            TournamentPlayerResultAuthority(
                player_id="QB",
                draw_type="both",
                qualifier=True,
                reached_stage="finalist",
                losses=1,
                byes_received=1,
            ),
        ),
        matches=(
            TournamentMatchResultAuthority(
                match_id="q-bye",
                draw_type="qualification",
                round_number=1,
                bracket_position=1,
                winner_player_id="QB",
                scoreline="BYE",
                result_fingerprint="5" * 64,
            ),
            TournamentMatchResultAuthority(
                match_id="main-final",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="A",
                loser_player_id="QB",
                scoreline="3-0",
                result_fingerprint="6" * 64,
            ),
        ),
    )

    authority = build_tournament_point_award_authority(
        result=result,
        point_authority=_points(
            champion=1000,
            finalist=600,
            qualification_winner=50,
            qualification_final=20,
        ),
        seed=7002,
    )
    qualifier = next(
        award for award in authority.awards if award.player_id == "QB"
    )

    assert qualifier.qualification_point_stage == "qualification_final"
    assert qualifier.qualification_points_awarded == 20
    assert qualifier.ranking_points_awarded == 620
