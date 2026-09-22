from __future__ import annotations

import hashlib
import json

import pytest

from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
    prepare_canonical_tournament_ranking_sources,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPlayerPointAwardAuthority,
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.prize_money_award_authority import (
    TournamentPlayerPrizeMoneyAwardAuthority,
    TournamentPrizeMoneyAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import (
    TournamentMatchResultAuthority,
    TournamentPlayerResultAuthority,
    TournamentResultAuthority,
)
pytestmark = pytest.mark.pr_critical

from beta_engine.infrastructure.db.ranking_fork_remap import (
    RankingForkRemapUnsupportedError,
    _remap_result_sources,
    _remap_tournament_sources,
)


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _canonical_source(*, with_prize_money: bool) -> OwnedTournamentRankingSource:
    completed = RankingWeek(season_index=0, week=1)
    published = RankingWeek(season_index=0, week=2)
    champion = TournamentPlayerResultAuthority(
        player_id="player-a",
        draw_type="main",
        main_entry_status="wild_card",
        reached_stage="champion",
        final_round_number=1,
        last_match_id="match-final",
        wins=1,
    )
    finalist = TournamentPlayerResultAuthority(
        player_id="player-b",
        draw_type="main",
        main_entry_status="direct",
        reached_stage="finalist",
        final_round_number=1,
        eliminated_by_player_id="player-a",
        last_match_id="match-final",
        losses=1,
    )
    result = TournamentResultAuthority(
        run_id="run-one",
        branch_id="branch-source",
        event_id="edition-a",
        completed_week=completed,
        draw_authority_fingerprint="1" * 64,
        match_package_fingerprint="2" * 64,
        champion_player_id="player-a",
        finalist_player_id="player-b",
        players=(champion, finalist),
        matches=(
            TournamentMatchResultAuthority(
                match_id="match-final",
                draw_type="main",
                round_number=1,
                bracket_position=1,
                winner_player_id="player-a",
                loser_player_id="player-b",
                scoreline="11-5 11-7 11-8",
                result_fingerprint="3" * 64,
            ),
        ),
    )

    distribution = (("champion", 100), ("finalist", 60))
    distribution_fingerprint = _hash(dict(distribution))
    point_awards = []
    for player, points in ((champion, 100), (finalist, 60)):
        player_fingerprint = _hash(player.model_dump(mode="json"))
        award_payload = {
            "schema_version": "tournament_player_point_award_authority.v1",
            "event_id": "edition-a",
            "seed": 77,
            "player_id": player.player_id,
            "reached_stage": player.reached_stage,
            "qualifier": False,
            "seed_number": None,
            "ranking_points_awarded": points,
            "race_points_awarded": points,
            "source_tournament_result_fingerprint": result.fingerprint,
            "source_player_result_fingerprint": player_fingerprint,
        }
        point_awards.append(
            TournamentPlayerPointAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                ranking_points_awarded=points,
                race_points_awarded=points,
                source_player_result_fingerprint=player_fingerprint,
                award_fingerprint=_hash(award_payload),
            )
        )
    awards = TournamentPointAwardAuthority(
        run_id="run-one",
        branch_id="branch-source",
        event_id="edition-a",
        completed_week=completed,
        seed=77,
        ranking_status="ranked",
        tournament_result_fingerprint=result.fingerprint,
        point_distribution=distribution,
        point_distribution_fingerprint=distribution_fingerprint,
        point_distribution_source="calendar_event.point_distribution",
        awards=tuple(point_awards),
        total_ranking_points=160,
        total_race_points=160,
    )
    binding = TournamentRankingBinding(
        run_id="run-one",
        branch_id="branch-source",
        edition_id="edition-a",
        event_id="edition-a",
        completed_week=completed,
        first_publication_week=published,
        validity_weeks=61,
        ranking_status="ranked",
        expected_result_fingerprint=result.fingerprint,
        expected_award_fingerprint=awards.fingerprint,
    )

    prize_authority = None
    schema_version = "owned_tournament_ranking_source.v4"
    provenance_kind = "canonical_run_owned_tournament_authorities"
    if with_prize_money:
        config_payload = {
            "event_id": "edition-a",
            "original_currency": None,
            "configured_stage_payouts": [],
            "required_stage_ids": [],
        }
        config_fingerprint = _hash(config_payload)
        prize_awards = []
        for player in (champion, finalist):
            player_fingerprint = _hash(player.model_dump(mode="json"))
            award_payload = {
                "schema_version": "tournament_player_prize_money_award_authority.v1",
                "event_id": "edition-a",
                "player_id": player.player_id,
                "reached_stage": player.reached_stage,
                "payout_status": "not_configured",
                "amount": None,
                "currency": None,
                "source_tournament_result_fingerprint": result.fingerprint,
                "source_player_result_fingerprint": player_fingerprint,
                "edition_prize_money_config_fingerprint": config_fingerprint,
            }
            prize_awards.append(
                TournamentPlayerPrizeMoneyAwardAuthority(
                    player_id=player.player_id,
                    reached_stage=player.reached_stage,
                    payout_status="not_configured",
                    source_player_result_fingerprint=player_fingerprint,
                    award_fingerprint=_hash(award_payload),
                )
            )
        prize_authority = TournamentPrizeMoneyAwardAuthority(
            run_id="run-one",
            branch_id="branch-source",
            event_id="edition-a",
            completed_week=completed,
            tournament_result_fingerprint=result.fingerprint,
            edition_prize_money_config_fingerprint=config_fingerprint,
            configured_stage_payouts=(),
            required_stage_ids=(),
            configuration_status="not_configured",
            awards=tuple(prize_awards),
            known_awarded_amount=0,
            unknown_award_count=2,
            total_prize_pool_status="not_configured",
        )
        schema_version = "owned_tournament_ranking_source.v5"
        provenance_kind = (
            "canonical_run_owned_tournament_authorities_and_prize_money"
        )

    return OwnedTournamentRankingSource(
        schema_version=schema_version,
        binding=binding,
        canonical_result=result,
        canonical_awards=awards,
        canonical_prize_awards=prize_authority,
        adopted_by_command_id="rank-week-two",
        provenance_kind=provenance_kind,
    )


@pytest.mark.parametrize("with_prize_money", [False, True])
def test_canonical_tournament_source_remaps_branch_scoped_authorities(
    with_prize_money: bool,
):
    source = _canonical_source(with_prize_money=with_prize_money)
    (
        remapped,
        by_edition,
        version_map,
        editions,
    ) = _remap_tournament_sources(
        (source,),
        run_id="run-one",
        source_branch_id="branch-source",
        target_branch_id="branch-target",
    )

    assert editions == {"edition-a"}
    assert len(remapped) == 1
    target = remapped[0]
    assert by_edition["edition-a"] == target
    assert target.binding.branch_id == "branch-target"
    assert target.canonical_result is not None
    assert target.canonical_awards is not None
    assert target.canonical_result.branch_id == "branch-target"
    assert target.canonical_awards.branch_id == "branch-target"
    assert target.binding.expected_result_fingerprint == target.canonical_result.fingerprint
    assert target.binding.expected_award_fingerprint == target.canonical_awards.fingerprint
    assert target.canonical_result.fingerprint != source.canonical_result.fingerprint
    assert target.canonical_awards.fingerprint != source.canonical_awards.fingerprint
    source_statuses = {
        player.player_id: player.main_entry_status
        for player in source.canonical_result.players
    }
    target_statuses = {
        player.player_id: player.main_entry_status
        for player in target.canonical_result.players
    }
    assert source_statuses == {
        "player-a": "wild_card",
        "player-b": "direct",
    }
    assert target_statuses == source_statuses

    source_versions = prepare_canonical_tournament_ranking_sources(
        source.binding,
        source.canonical_result,
        source.canonical_awards,
    )
    assert set(version_map) == {item.fingerprint for item in source_versions}
    assert all(
        version.branch_id == "branch-target" for version in version_map.values()
    )
    assert [version.result.main_points for version in version_map.values()] == [100, 60]

    if with_prize_money:
        assert target.canonical_prize_awards is not None
        assert source.canonical_prize_awards is not None
        assert target.canonical_prize_awards.branch_id == "branch-target"
        assert (
            target.canonical_prize_awards.tournament_result_fingerprint
            == target.canonical_result.fingerprint
        )
        assert (
            target.canonical_prize_awards.fingerprint
            != source.canonical_prize_awards.fingerprint
        )
    else:
        assert target.canonical_prize_awards is None


@pytest.mark.parametrize(
    "schema_version",
    ["owned_tournament_ranking_source.v3", "owned_tournament_ranking_source.v6"],
)
def test_noncanonical_or_final_closing_tournament_sources_stay_fail_closed(
    schema_version: str,
):
    source = _canonical_source(with_prize_money=False).model_copy(
        update={"schema_version": schema_version}
    )
    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="canonical v4/v5",
    ):
        _remap_tournament_sources(
            (source,),
            run_id="run-one",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
        )


def test_correction_over_canonical_tournament_source_remaps_predecessor_chain():
    source = _canonical_source(with_prize_money=False)
    (
        _,
        _,
        version_map,
        tournament_editions,
    ) = _remap_tournament_sources(
        (source,),
        run_id="run-one",
        source_branch_id="branch-source",
        target_branch_id="branch-target",
    )
    initial = prepare_canonical_tournament_ranking_sources(
        source.binding,
        source.canonical_result,
        source.canonical_awards,
    )[0]
    correction = RankingResultVersion(
        run_id="run-one",
        branch_id="branch-source",
        effective_week=RankingWeek(season_index=0, week=3),
        previous_fingerprint=initial.fingerprint,
        result=initial.result.model_copy(update={"main_points": 125}),
    )

    remapped, by_source_fingerprint = _remap_result_sources(
        (initial, correction),
        run_id="run-one",
        source_branch_id="branch-source",
        target_branch_id="branch-target",
        tournament_version_map=version_map,
        tournament_editions=tournament_editions,
    )

    target_initial, target_correction = remapped
    assert target_initial.branch_id == "branch-target"
    assert target_correction.branch_id == "branch-target"
    assert target_initial.fingerprint != initial.fingerprint
    assert target_correction.fingerprint != correction.fingerprint
    assert target_correction.previous_fingerprint == target_initial.fingerprint
    assert target_correction.result.main_points == 125
    assert by_source_fingerprint[correction.fingerprint] == target_correction


def test_canonical_tournament_correction_with_broken_source_predecessor_fails_closed():
    source = _canonical_source(with_prize_money=False)
    (
        _,
        _,
        version_map,
        tournament_editions,
    ) = _remap_tournament_sources(
        (source,),
        run_id="run-one",
        source_branch_id="branch-source",
        target_branch_id="branch-target",
    )
    initial = prepare_canonical_tournament_ranking_sources(
        source.binding,
        source.canonical_result,
        source.canonical_awards,
    )[0]
    broken = RankingResultVersion(
        run_id="run-one",
        branch_id="branch-source",
        effective_week=RankingWeek(season_index=0, week=3),
        previous_fingerprint="f" * 64,
        result=initial.result.model_copy(update={"main_points": 125}),
    )

    with pytest.raises(
        RankingForkRemapUnsupportedError,
        match="predecessor differs from source history",
    ):
        _remap_result_sources(
            (initial, broken),
            run_id="run-one",
            source_branch_id="branch-source",
            target_branch_id="branch-target",
            tournament_version_map=version_map,
            tournament_editions=tournament_editions,
        )
