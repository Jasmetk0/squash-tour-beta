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


def _validate_result_match_counters(result: TournamentResultAuthority) -> None:
    """Keep noncompetitive BYE/W/O progression separate from played match records."""

    players = {player.player_id: player for player in result.players}
    competitive_wins = {player_id: 0 for player_id in players}
    competitive_losses = {player_id: 0 for player_id in players}
    byes_received = {player_id: 0 for player_id in players}
    walkovers_received = {player_id: 0 for player_id in players}
    walkover_losses = {player_id: False for player_id in players}

    for match in result.matches:
        if match.winner_player_id not in players:
            raise ValueError("Tournament point source contains unknown match winner")
        if match.scoreline == "BYE":
            if match.loser_player_id is not None:
                raise ValueError("Canonical BYE point source cannot contain a loser")
            byes_received[match.winner_player_id] += 1
            continue
        if match.loser_player_id is None or match.loser_player_id not in players:
            raise ValueError("Tournament point source contains invalid match loser")
        if match.scoreline == "W/O":
            walkovers_received[match.winner_player_id] += 1
            walkover_losses[match.loser_player_id] = True
            continue
        competitive_wins[match.winner_player_id] += 1
        competitive_losses[match.loser_player_id] += 1

    for player_id, player in players.items():
        if (
            player.wins != competitive_wins[player_id]
            or player.losses != competitive_losses[player_id]
            or player.byes_received != byes_received[player_id]
            or player.walkovers_received != walkovers_received[player_id]
            or player.retired_or_walkover_loss != walkover_losses[player_id]
        ):
            raise ValueError(
                "Tournament point source match counters differ from canonical result"
            )


def _first_round_point_stage(
    result: TournamentResultAuthority,
    *,
    draw_type: str,
) -> str:
    rounds = [
        match.round_number
        for match in result.matches
        if match.draw_type == draw_type
    ]
    if not rounds:
        raise ValueError("Tournament point source has no matches for player draw")
    distance = max(rounds) - 1
    if draw_type == "qualification":
        if distance == 0:
            return "qualification_final"
        if distance == 1:
            return "qualification_semifinal"
        return "qualification_round"
    mapping = {
        0: "finalist",
        1: "semifinal",
        2: "quarterfinal",
        3: "round_of_16",
        4: "round_of_32",
        5: "round_of_64",
        6: "round_of_128",
    }
    return mapping.get(distance, "main_draw_participant")


def _player_draw_matches(
    result: TournamentResultAuthority,
    *,
    player_id: str,
    draw_type: str,
):
    return [
        match
        for match in result.matches
        if match.draw_type == draw_type
        and player_id in {match.winner_player_id, match.loser_player_id}
    ]


def _point_stage_for_draw(
    result: TournamentResultAuthority,
    *,
    player_id: str,
    draw_type: str,
    nominal_stage: str,
) -> str:
    """Apply Master §15.4 BYE/W/O unlock semantics inside exactly one draw."""

    matches = _player_draw_matches(
        result,
        player_id=player_id,
        draw_type=draw_type,
    )
    if not matches:
        # Historical/synthetic single-component authorities may carry an already
        # resolved reached_stage without match detail. Preserve that compatibility
        # boundary; additive Qualification + Main v3 still requires Q match history
        # in _qualification_nominal_stage so its extra component cannot be invented.
        return nominal_stage

    has_bye = any(
        match.scoreline == "BYE"
        and match.winner_player_id == player_id
        for match in matches
    )
    has_walkover_advance = any(
        match.scoreline == "W/O"
        and match.winner_player_id == player_id
        for match in matches
    )
    has_competitive_win = any(
        match.scoreline not in {"BYE", "W/O"}
        and match.winner_player_id == player_id
        for match in matches
    )

    # BYE alone never unlocks a later ranking value. This also covers a player
    # who wins an otherwise-empty Q section entirely through a BYE and therefore
    # has no competitive loss from which the old implementation could infer the
    # downgrade. A real win or the explicit Master §16.3 W/O exception unlocks it.
    if has_bye and not has_competitive_win and not has_walkover_advance:
        return _first_round_point_stage(result, draw_type=draw_type)
    return nominal_stage


def _qualification_nominal_stage(
    result: TournamentResultAuthority,
    *,
    player_id: str,
) -> str:
    """Resolve the Qualification component before BYE/W/O unlock adjustment."""

    matches = _player_draw_matches(
        result,
        player_id=player_id,
        draw_type="qualification",
    )
    if not matches:
        raise ValueError(
            "Additive Qualification points require Qualification match history"
        )
    if player_id in result.qualification_winner_ids:
        return "qualification_winner"

    losses = [
        match for match in matches if match.loser_player_id == player_id
    ]
    if not losses:
        raise ValueError(
            "Qualification/Main player is neither a Qualification winner nor loser"
        )
    elimination = max(
        losses,
        key=lambda match: (match.round_number, match.bracket_position, match.match_id),
    )
    final_round = max(
        match.round_number
        for match in result.matches
        if match.draw_type == "qualification"
    )
    distance = final_round - elimination.round_number
    if distance == 0:
        return "qualification_final"
    if distance == 1:
        return "qualification_semifinal"
    return "qualification_round"


def _point_stage(
    result: TournamentResultAuthority,
    player,
) -> str:
    """Compatibility helper for a player whose result has one draw component."""

    draw_type = (
        "qualification"
        if player.reached_stage.startswith("qualification_")
        else "main"
    )
    return _point_stage_for_draw(
        result,
        player_id=player.player_id,
        draw_type=draw_type,
        nominal_stage=player.reached_stage,
    )


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
    _validate_result_match_counters(result)
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
        qualification_point_stage = None
        qualification_points_awarded = None

        if player.draw_type == "both":
            main_point_stage = _point_stage_for_draw(
                result,
                player_id=player.player_id,
                draw_type="main",
                nominal_stage=player.reached_stage,
            )
            qualification_nominal_stage = _qualification_nominal_stage(
                result,
                player_id=player.player_id,
            )
            qualification_point_stage = _point_stage_for_draw(
                result,
                player_id=player.player_id,
                draw_type="qualification",
                nominal_stage=qualification_nominal_stage,
            )
            if (
                main_point_stage not in distribution
                or qualification_point_stage not in distribution
            ):
                raise ValueError(
                    "Canonical tournament point component has no frozen point mapping"
                )
            main_points = max(0, int(distribution[main_point_stage]))
            qualification_points_awarded = max(
                0,
                int(distribution[qualification_point_stage]),
            )
            points = main_points + qualification_points_awarded
            point_stage = main_point_stage
        else:
            point_stage = _point_stage(result, player)
            if point_stage not in distribution:
                raise ValueError(
                    "Canonical tournament point stage has no frozen point mapping"
                )
            points = max(0, int(distribution[point_stage]))

        player_fp = _hash(player.model_dump(mode="json"))
        stored_point_stage = (
            point_stage if point_stage != player.reached_stage else None
        )
        player_schema = (
            "tournament_player_point_award_authority.v3"
            if qualification_point_stage is not None
            else (
                "tournament_player_point_award_authority.v2"
                if stored_point_stage is not None
                else "tournament_player_point_award_authority.v1"
            )
        )
        award_fp_payload = {
            "schema_version": player_schema,
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
        if stored_point_stage is not None:
            award_fp_payload["point_stage"] = stored_point_stage
        if qualification_point_stage is not None:
            award_fp_payload["qualification_point_stage"] = (
                qualification_point_stage
            )
            award_fp_payload["qualification_points_awarded"] = (
                qualification_points_awarded
            )
        award_fp = _hash(award_fp_payload)
        awards.append(
            TournamentPlayerPointAwardAuthority(
                player_id=player.player_id,
                reached_stage=player.reached_stage,
                point_stage=stored_point_stage,
                qualification_point_stage=qualification_point_stage,
                qualification_points_awarded=qualification_points_awarded,
                qualifier=player.qualifier,
                seed_number=player.seed_number,
                ranking_points_awarded=points,
                race_points_awarded=points,
                source_player_result_fingerprint=player_fp,
                award_fingerprint=award_fp,
            )
        )

    schema_version = (
        "tournament_point_award_authority.v3"
        if any(
            award.qualification_point_stage is not None
            for award in awards
        )
        else (
            "tournament_point_award_authority.v2"
            if any(award.point_stage is not None for award in awards)
            else "tournament_point_award_authority.v1"
        )
    )
    return TournamentPointAwardAuthority(
        schema_version=schema_version,
        run_id=result.run_id,
        branch_id=result.branch_id,
        event_id=result.event_id,
        completed_week=result.completed_week,
        seed=seed,
        ranking_status="ranked",
        tournament_result_fingerprint=result.fingerprint,
        point_distribution=tuple(sorted(distribution.items())),
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
