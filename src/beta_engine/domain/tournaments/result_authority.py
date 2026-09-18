"""Immutable Run-owned tournament result authority.

This module derives tournament outcomes only from canonical Draw authority plus the
completed Run-owned match compatibility payload. Legacy SeasonEventResultsService is
not consulted.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.application.season_event_results_service import (
    EventResultMetadata,
    EventResultSummary,
    MatchResultRef,
    PlayerEventResult,
    PlayerResultSummary,
    SeasonEventResultPackage,
)
from beta_engine.application.season_match_service import SeasonEventMatchPackage
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.models import CalendarEvent


class TournamentMatchResultAuthority(FrozenInput):
    match_id: str = Field(min_length=1)
    draw_type: Literal["qualification", "main"]
    round_number: int = Field(ge=1)
    bracket_position: int = Field(ge=1)
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str | None = None
    scoreline: str = Field(min_length=1)
    result_fingerprint: str | None = None


class TournamentPlayerResultAuthority(FrozenInput):
    player_id: str = Field(min_length=1)
    draw_type: Literal["qualification", "main", "both"]
    seed_number: int | None = Field(default=None, ge=1)
    qualifier: bool = False
    reached_stage: str = Field(min_length=1)
    final_round_number: int | None = Field(default=None, ge=1)
    eliminated_by_player_id: str | None = None
    last_match_id: str | None = None
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    byes_received: int = Field(default=0, ge=0)


class TournamentResultAuthority(FrozenInput):
    schema_version: Literal["tournament_result_authority.v1"] = (
        "tournament_result_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    completed_week: RankingWeek
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    match_package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    champion_player_id: str = Field(min_length=1)
    finalist_player_id: str = Field(min_length=1)
    qualification_winner_ids: tuple[str, ...] = ()
    players: tuple[TournamentPlayerResultAuthority, ...]
    matches: tuple[TournamentMatchResultAuthority, ...]

    @model_validator(mode="after")
    def validate_result(self) -> "TournamentResultAuthority":
        player_ids = tuple(player.player_id for player in self.players)
        if len(player_ids) != len(set(player_ids)):
            raise ValueError("Tournament Result contains duplicate player identity")
        if self.champion_player_id not in player_ids:
            raise ValueError("Tournament Result champion is absent from player results")
        if self.finalist_player_id not in player_ids:
            raise ValueError("Tournament Result finalist is absent from player results")
        match_ids = tuple(match.match_id for match in self.matches)
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("Tournament Result contains duplicate match identity")
        if any(
            winner not in player_ids for winner in self.qualification_winner_ids
        ):
            raise ValueError("Qualification winner is absent from player results")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def build_tournament_result_authority(
    *,
    run_id: str,
    branch_id: str,
    week: RankingWeek,
    draw: TournamentDrawAuthority,
    package: SeasonEventMatchPackage,
) -> TournamentResultAuthority:
    """Build the completed tournament truth without legacy result extraction."""
    if package.event_id != draw.event_id:
        raise ValueError("canonical Draw and completed MatchPackage event differ")
    if package.season_week != week.week:
        raise ValueError("completed MatchPackage belongs to a different week")
    if package.validation_errors:
        raise ValueError("completed MatchPackage has validation errors")

    all_matches = tuple(package.qualification_matches + package.main_draw_matches)
    if not all_matches or any(
        match.status != "completed"
        or not match.winner_player_id
        or not match.scoreline
        for match in all_matches
    ):
        raise ValueError("Tournament Result requires every canonical match completed")

    draw_node_ids = {
        node.node_id
        for node in (
            *(
                node
                for bracket in draw.qualification_brackets
                for node in bracket.nodes
            ),
            *draw.main.nodes,
        )
    }
    if {match.match_id for match in all_matches} != draw_node_ids:
        raise ValueError("completed MatchPackage universe differs from canonical Draw")

    main_terminal = max(
        draw.main.nodes,
        key=lambda node: (node.round_number, node.round_sequence),
    )
    main_final = next(
        match for match in package.main_draw_matches if match.match_id == main_terminal.node_id
    )
    if main_final.loser_player_id is None:
        raise ValueError("canonical Main terminal lacks a finalist")
    champion_id = main_final.winner_player_id
    finalist_id = main_final.loser_player_id

    qualification_winners: tuple[str, ...] = ()
    if draw.qualification_brackets:
        winners = []
        for bracket in draw.qualification_brackets:
            q_terminal = max(
                bracket.nodes,
                key=lambda node: (node.round_number, node.round_sequence),
            )
            q_final = next(
                match
                for match in package.qualification_matches
                if match.match_id == q_terminal.node_id
            )
            winners.append(q_final.winner_player_id)
        qualification_winners = tuple(winners)

    seed_by_player: dict[str, int] = {}
    direct_main_ids: set[str] = set()
    q_ids: set[str] = set()
    for slot in draw.main.slots:
        if slot.player_id:
            direct_main_ids.add(slot.player_id)
            if slot.seed_number is not None:
                seed_by_player[slot.player_id] = slot.seed_number
    for bracket in draw.qualification_brackets:
        for slot in bracket.slots:
            if slot.player_id:
                q_ids.add(slot.player_id)
                if slot.seed_number is not None and slot.player_id not in seed_by_player:
                    seed_by_player[slot.player_id] = slot.seed_number

    stats: dict[str, dict[str, object]] = {}
    q_final_round = max(
        (match.round_number for match in package.qualification_matches),
        default=0,
    )
    main_final_round = max(match.round_number for match in package.main_draw_matches)

    for match in sorted(
        all_matches,
        key=lambda item: (
            item.draw_type != "qualification",
            item.round_number,
            item.bracket_position,
            item.match_id,
        ),
    ):
        involved = [match.winner_player_id]
        if match.loser_player_id is not None:
            involved.append(match.loser_player_id)
        for player_id in involved:
            record = stats.setdefault(
                player_id,
                {
                    "draws": set(),
                    "wins": 0,
                    "losses": 0,
                    "byes": 0,
                    "last_match_id": None,
                    "last_round": None,
                    "last_draw": match.draw_type,
                    "eliminated_by": None,
                    "stage": "unknown",
                },
            )
            record["draws"].add(match.draw_type)

        winner = stats[match.winner_player_id]
        winner["last_match_id"] = match.match_id
        winner["last_round"] = match.round_number
        winner["last_draw"] = match.draw_type
        if match.scoreline == "BYE":
            if match.loser_player_id is not None:
                raise ValueError("canonical BYE result cannot contain a loser")
            winner["byes"] += 1
        else:
            if match.loser_player_id is None:
                raise ValueError("competitive canonical match lacks a loser")
            winner["wins"] += 1

        if match.loser_player_id is not None:
            loser = stats[match.loser_player_id]
            loser["losses"] += 1
            loser["last_match_id"] = match.match_id
            loser["last_round"] = match.round_number
            loser["last_draw"] = match.draw_type
            loser["eliminated_by"] = match.winner_player_id
            loser["stage"] = _loss_stage(
                draw_type=match.draw_type,
                round_number=match.round_number,
                final_round=(
                    q_final_round
                    if match.draw_type == "qualification"
                    else main_final_round
                ),
            )

    for player_id in qualification_winners:
        if player_id not in stats:
            raise ValueError("Qualification winner has no completed result history")
    if champion_id not in stats or finalist_id not in stats:
        raise ValueError("Main terminal players are absent from result history")
    stats[champion_id]["stage"] = "champion"
    stats[finalist_id]["stage"] = "finalist"

    players = []
    for player_id, item in stats.items():
        draws = item["draws"]
        draw_type = (
            "both"
            if draws == {"qualification", "main"}
            else ("main" if "main" in draws else "qualification")
        )
        qualifier = player_id in q_ids
        stage = str(item["stage"])
        if draw_type in {"main", "both"} and stage.startswith("qualification_"):
            stage = "main_draw_participant"
        players.append(
            TournamentPlayerResultAuthority(
                player_id=player_id,
                draw_type=draw_type,
                seed_number=seed_by_player.get(player_id),
                qualifier=qualifier,
                reached_stage=stage,
                final_round_number=item["last_round"],
                eliminated_by_player_id=item["eliminated_by"],
                last_match_id=item["last_match_id"],
                wins=int(item["wins"]),
                losses=int(item["losses"]),
                byes_received=int(item["byes"]),
            )
        )

    match_results = tuple(
        TournamentMatchResultAuthority(
            match_id=match.match_id,
            draw_type=match.draw_type,
            round_number=match.round_number,
            bracket_position=match.bracket_position,
            winner_player_id=match.winner_player_id,
            loser_player_id=match.loser_player_id,
            scoreline=match.scoreline,
            result_fingerprint=match.result_fingerprint,
        )
        for match in sorted(
            all_matches,
            key=lambda item: (
                item.draw_type != "qualification",
                item.round_number,
                item.bracket_position,
                item.match_id,
            ),
        )
    )
    return TournamentResultAuthority(
        run_id=run_id,
        branch_id=branch_id,
        event_id=draw.event_id,
        completed_week=week,
        draw_authority_fingerprint=draw.fingerprint,
        match_package_fingerprint=package.metadata.build_fingerprint,
        champion_player_id=champion_id,
        finalist_player_id=finalist_id,
        qualification_winner_ids=qualification_winners,
        players=tuple(sorted(players, key=lambda player: player.player_id)),
        matches=match_results,
    )


def project_tournament_result_legacy_dto(
    *,
    authority: TournamentResultAuthority,
    event: CalendarEvent,
    package: SeasonEventMatchPackage,
    seed: int,
) -> SeasonEventResultPackage:
    """Compatibility DTO for the existing point/ranking adapters.

    The content is derived from TournamentResultAuthority, not from
    SeasonEventResultsService.
    """
    if authority.event_id != event.event_id or authority.event_id != package.event_id:
        raise ValueError("Tournament Result compatibility projection scope mismatch")
    season = package.season
    player_results = [
        PlayerEventResult(
            player_id=player.player_id,
            draw_type=player.draw_type,
            entry_decision=(
                "accepted_qualification"
                if player.qualifier
                else "accepted_main_draw"
            ),
            seed_number=player.seed_number,
            qualifier=player.qualifier,
            reached_stage=player.reached_stage,
            final_round_number=player.final_round_number,
            eliminated_by_player_id=player.eliminated_by_player_id,
            last_match_id=player.last_match_id,
            wins=player.wins,
            losses=player.losses,
            byes_received=player.byes_received,
            walkovers_received=0,
            retired_or_walkover_loss=False,
        )
        for player in authority.players
    ]
    by_id = {player.player_id: player for player in authority.players}

    def summary(player_id: str) -> PlayerResultSummary:
        player = by_id[player_id]
        return PlayerResultSummary(
            player_id=player_id,
            seed_number=player.seed_number,
            entry_decision=(
                "accepted_qualification"
                if player.qualifier
                else "accepted_main_draw"
            ),
            qualifier=player.qualifier,
        )

    refs = [
        MatchResultRef(
            match_id=match.match_id,
            draw_type=match.draw_type,
            round_number=match.round_number,
            round_name=(
                f"Qualification R{match.round_number}"
                if match.draw_type == "qualification"
                else f"Main R{match.round_number}"
            ),
            bracket_position=match.bracket_position,
            winner_player_id=match.winner_player_id,
            loser_player_id=match.loser_player_id,
            scoreline=match.scoreline,
            result_fingerprint=match.result_fingerprint,
        )
        for match in authority.matches
    ]
    q_ids = {
        player.player_id
        for player in authority.players
        if player.draw_type in {"qualification", "both"}
    }
    main_ids = {
        player.player_id
        for player in authority.players
        if player.draw_type in {"main", "both"}
    }
    q_winners = [summary(player_id) for player_id in authority.qualification_winner_ids]
    result_fp = _hash(
        {
            "event_id": authority.event_id,
            "seed": seed,
            "match_package_fingerprint": authority.match_package_fingerprint,
            "champion": summary(authority.champion_player_id).model_dump(mode="json"),
            "finalist": summary(authority.finalist_player_id).model_dump(mode="json"),
            "player_results": [
                player.model_dump(mode="json") for player in player_results
            ],
            "match_refs": [ref.model_dump(mode="json") for ref in refs],
        }
    )
    event_result_summary = EventResultSummary(
        event_id=authority.event_id,
        completion_status="complete",
        player_count=len(player_results),
        main_draw_player_count=len(main_ids),
        qualification_player_count=len(q_ids),
        completed_matches=len(refs),
        incomplete_matches=0,
        champion_player_id=authority.champion_player_id,
        finalist_player_id=authority.finalist_player_id,
        qualification_winner_count=len(q_winners),
        validation_warning_count=0,
        validation_error_count=0,
    )
    return SeasonEventResultPackage(
        event_id=authority.event_id,
        season=season,
        template_id=package.template_id,
        season_week=package.season_week,
        calendar_year=package.calendar_year,
        year_week=package.year_week,
        event_name=event.event_name,
        category=event.category,
        tour_level=event.tour_level,
        host_country=event.host_country,
        seed=seed,
        dry_run=False,
        persisted=True,
        completion_status="complete",
        champion=summary(authority.champion_player_id),
        finalist=summary(authority.finalist_player_id),
        semifinalists=[
            summary(player.player_id)
            for player in authority.players
            if player.reached_stage == "semifinal"
        ],
        quarterfinalists=[
            summary(player.player_id)
            for player in authority.players
            if player.reached_stage == "quarterfinal"
        ],
        qualification_winners=q_winners,
        player_results=player_results,
        match_result_refs=refs,
        summary=event_result_summary,
        metadata=EventResultMetadata(
            event_id=authority.event_id,
            season=season,
            seed=seed,
            dry_run=False,
            persisted=True,
            build_fingerprint=result_fp,
            match_package_fingerprint=authority.match_package_fingerprint,
            draw_package_fingerprint=authority.draw_authority_fingerprint,
            calendar_event_fingerprint=event.calendar_fingerprint,
            persistence_path=None,
        ),
        validation_warnings=[],
        validation_errors=[],
    )


def _loss_stage(*, draw_type: str, round_number: int, final_round: int) -> str:
    distance = final_round - round_number
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


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()