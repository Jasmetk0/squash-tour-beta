"""Canonical point awards derived from Run-owned tournament result authority."""

from __future__ import annotations

import hashlib
import json

from beta_engine.application.season_point_awards_service import (
    EventPointAwardPackage,
    FrozenPointAwardAuthority,
    PlayerPointAward,
    PointAwardMetadata,
    PointAwardSummary,
)
from beta_engine.domain.tournaments.point_award_authority import (
    TournamentPlayerPointAwardAuthority,
    TournamentPointAwardAuthority,
)
from beta_engine.domain.tournaments.result_authority import TournamentResultAuthority
from beta_engine.application.season_event_results_service import SeasonEventResultPackage


def build_tournament_point_award_authority(
    *,
    result: TournamentResultAuthority,
    point_authority: FrozenPointAwardAuthority,
    seed: int,
) -> TournamentPointAwardAuthority:
    """Resolve ranking/race points from already frozen sporting + point inputs."""

    if point_authority.ranking_status != "ranked":
        raise ValueError(
            "Canonical ranked tournament close requires ranked point authority"
        )
    if (
        point_authority.point_distribution_source.startswith("fallback")
        or point_authority.point_distribution_source == "calendar_event.unranked"
    ):
        raise ValueError(
            "Canonical ranked tournament close requires authored point distribution"
        )

    distribution = dict(point_authority.point_distribution)
    distribution_fp = _hash(distribution)
    awards: list[TournamentPlayerPointAwardAuthority] = []
    for player in sorted(result.players, key=lambda item: item.player_id):
        if player.reached_stage not in distribution:
            raise ValueError(
                "Canonical tournament reached stage has no frozen point mapping"
            )
        points = max(0, int(distribution[player.reached_stage]))
        player_fp = _hash(player.model_dump(mode="json"))
        award_fp = _hash(
            {
                "schema_version": "tournament_player_point_award_authority.v1",
                "event_id": result.event_id,
                "seed": seed,
                "player_id": player.player_id,
                "reached_stage": player.reached_stage,
                "qualifier": player.qualifier,
                "seed_number": player.seed_number,
                "ranking_points_awarded": points,
                "race_points_awarded": points,
                "source_tournament_result_fingerprint": result.fingerprint,
                "source_player_result_fingerprint": player_fp,
            }
        )
        awards.append(
            TournamentPlayerPointAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                qualifier=player.qualifier,
                seed_number=player.seed_number,
                ranking_points_awarded=points,
                race_points_awarded=points,
                source_player_result_fingerprint=player_fp,
                award_fingerprint=award_fp,
            )
        )

    return TournamentPointAwardAuthority(
        run_id=result.run_id,
        branch_id=result.branch_id,
        event_id=result.event_id,
        completed_week=result.completed_week,
        seed=seed,
        ranking_status="ranked",
        tournament_result_fingerprint=result.fingerprint,
        point_distribution_fingerprint=distribution_fp,
        point_distribution_source=point_authority.point_distribution_source,
        awards=tuple(awards),
        total_ranking_points=sum(
            award.ranking_points_awarded for award in awards
        ),
        total_race_points=sum(award.race_points_awarded for award in awards),
    )


def project_tournament_point_award_legacy_dto(
    *,
    authority: TournamentPointAwardAuthority,
    result_authority: TournamentResultAuthority,
    result: SeasonEventResultPackage,
) -> EventPointAwardPackage:
    """Produce a self-consistent legacy-shaped DTO without legacy award generation."""

    if (
        authority.run_id,
        authority.branch_id,
        authority.event_id,
        authority.completed_week,
        authority.tournament_result_fingerprint,
    ) != (
        result_authority.run_id,
        result_authority.branch_id,
        result_authority.event_id,
        result_authority.completed_week,
        result_authority.fingerprint,
    ):
        raise ValueError("Canonical Point Award / Tournament Result scope mismatch")
    if result.event_id != authority.event_id:
        raise ValueError("Point Award compatibility result event mismatch")

    compatibility_players = {
        player.player_id: player for player in result.player_results
    }
    if set(compatibility_players) != {
        award.player_id for award in authority.awards
    }:
        raise ValueError(
            "Point Award compatibility result player universe mismatch"
        )

    result_fp = result.metadata.build_fingerprint
    awards: list[PlayerPointAward] = []
    for canonical_award in authority.awards:
        player = compatibility_players[canonical_award.player_id]
        if (
            player.reached_stage,
            player.qualifier,
            player.seed_number,
        ) != (
            canonical_award.reached_stage,
            canonical_award.qualifier,
            canonical_award.seed_number,
        ):
            raise ValueError(
                "Point Award compatibility player semantics differ from canonical result"
            )
        player_result_fp = _hash(player.model_dump(mode="json"))
        award_fp = _hash(
            {
                "event_id": authority.event_id,
                "seed": authority.seed,
                "player_id": player.player_id,
                "reached_stage": player.reached_stage,
                "ranking_points_awarded": canonical_award.ranking_points_awarded,
                "race_points_awarded": canonical_award.race_points_awarded,
                "source_result_fingerprint": result_fp,
                "source_player_result_fingerprint": player_result_fp,
            }
        )
        awards.append(
            PlayerPointAward(
                player_id=player.player_id,
                player_name=player.player_name,
                country_code=player.country_code,
                reached_stage=player.reached_stage,
                qualifier=player.qualifier,
                seed_number=player.seed_number,
                ranking_points_awarded=canonical_award.ranking_points_awarded,
                race_points_awarded=canonical_award.race_points_awarded,
                previous_ranking_points=None,
                previous_race_points=None,
                projected_ranking_points=None,
                projected_race_points=None,
                source_result_fingerprint=result_fp,
                source_player_result_fingerprint=player_result_fp,
                award_fingerprint=award_fp,
            )
        )

    sorted_awards = sorted(awards, key=lambda item: item.player_id)
    build_fp = _hash(
        {
            "event_id": authority.event_id,
            "seed": authority.seed,
            "result_package_fingerprint": result_fp,
            "point_distribution_fingerprint": authority.point_distribution_fingerprint,
            "awards": [
                award.model_dump(mode="json") for award in sorted_awards
            ],
        }
    )
    champion = next(
        (
            award
            for award in sorted_awards
            if award.player_id == result.summary.champion_player_id
        ),
        None,
    )
    finalist = next(
        (
            award
            for award in sorted_awards
            if award.player_id == result.summary.finalist_player_id
        ),
        None,
    )
    summary = PointAwardSummary(
        event_id=authority.event_id,
        player_count=len(sorted_awards),
        awarded_player_count=sum(
            1
            for award in sorted_awards
            if award.ranking_points_awarded > 0
            or award.race_points_awarded > 0
        ),
        total_ranking_points=sum(
            award.ranking_points_awarded for award in sorted_awards
        ),
        total_race_points=sum(
            award.race_points_awarded for award in sorted_awards
        ),
        champion_player_id=(
            champion.player_id if champion else result.summary.champion_player_id
        ),
        champion_points=champion.ranking_points_awarded if champion else 0,
        finalist_player_id=(
            finalist.player_id if finalist else result.summary.finalist_player_id
        ),
        finalist_points=finalist.ranking_points_awarded if finalist else 0,
        applied=False,
        validation_warning_count=0,
        validation_error_count=0,
    )
    return EventPointAwardPackage(
        event_id=authority.event_id,
        season=result.season,
        template_id=result.template_id,
        event_name=result.event_name,
        category=result.category,
        tour_level=result.tour_level,
        seed=authority.seed,
        dry_run=False,
        persisted=True,
        applied=False,
        awards=sorted_awards,
        summary=summary,
        metadata=PointAwardMetadata(
            event_id=authority.event_id,
            season=result.season,
            seed=authority.seed,
            dry_run=False,
            persisted=True,
            applied=False,
            build_fingerprint=build_fp,
            result_package_fingerprint=result_fp,
            point_distribution_fingerprint=authority.point_distribution_fingerprint,
            point_distribution_source=authority.point_distribution_source,
            persistence_path=None,
        ),
        validation_warnings=[],
        validation_errors=[],
    )


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
