"""Canonical in-memory MatchPackage projection from Run-owned Draw authority.

This is a compatibility payload for existing result/point builders. Sporting topology
comes exclusively from TournamentDrawAuthority; no legacy EntryList, DrawPackage or
season_matches file is read while building it.
"""

from __future__ import annotations

from beta_engine.application.season_match_service import (
    MatchPackageMetadata,
    MatchPackageSummary,
    SeasonEventMatchPackage,
    SeasonMatchRecord,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import fingerprint
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawBracket,
    TournamentDrawNode,
)
from beta_engine.domain.tournaments.models import CalendarEvent


def build_run_owned_match_package(
    *,
    draw: TournamentDrawAuthority,
    event: CalendarEvent,
    week: RankingWeek,
) -> SeasonEventMatchPackage:
    """Project a canonical Draw into the legacy-shaped in-memory execution payload."""
    expected_season = f"{2000 + week.season_index}/{2001 + week.season_index}"
    if draw.event_id != event.event_id:
        raise ValueError("canonical Draw and Calendar Event identities differ")
    if event.season_week != week.week:
        raise ValueError("canonical Draw Calendar Event belongs to a different week")

    qualification = (
        _build_bracket_records(draw, draw.qualification)
        if draw.qualification is not None
        else []
    )
    main = _build_bracket_records(draw, draw.main)
    records = qualification + main
    build_fp = fingerprint(
        {
            "schema_version": "run_owned_match_package_projection.v1",
            "draw_authority_fingerprint": draw.fingerprint,
            "event": {
                "event_id": event.event_id,
                "template_id": event.template_id,
                "season": expected_season,
                "season_week": event.season_week,
                "calendar_year": event.calendar_year,
                "year_week": event.year_week,
            },
            "matches": [record.model_dump(mode="json") for record in records],
        }
    )
    pending = sum(record.status == "pending" for record in records)
    blocked = sum(record.status == "blocked_waiting_for_sources" for record in records)
    bye_pending = sum(record.status == "bye_auto_advance_pending" for record in records)
    summary = MatchPackageSummary(
        event_id=event.event_id,
        total_matches=len(records),
        qualification_matches=len(qualification),
        main_draw_matches=len(main),
        pending_matches=pending,
        blocked_matches=blocked,
        bye_auto_advances=bye_pending,
    )
    seed = int(draw.fingerprint[:15], 16)
    metadata = MatchPackageMetadata(
        event_id=event.event_id,
        season=expected_season,
        seed=seed,
        dry_run=False,
        persisted=True,
        build_fingerprint=build_fp,
        # Compatibility field: the canonical Draw fingerprint now anchors this
        # payload. It is intentionally not a legacy DrawPackage fingerprint.
        draw_package_fingerprint=draw.fingerprint,
        active_players_fingerprint=draw.draw_input_fingerprint,
        persistence_path=None,
        qualification_winners_promoted=draw.qualification is not None,
    )
    return SeasonEventMatchPackage(
        event_id=event.event_id,
        season=expected_season,
        template_id=event.template_id,
        season_week=event.season_week,
        calendar_year=event.calendar_year,
        year_week=event.year_week,
        seed=seed,
        dry_run=False,
        persisted=True,
        qualification_matches=qualification,
        main_draw_matches=main,
        summary=summary,
        metadata=metadata,
        validation_warnings=[],
        validation_errors=[],
    )


def _build_bracket_records(
    draw: TournamentDrawAuthority,
    bracket: TournamentDrawBracket,
) -> list[SeasonMatchRecord]:
    by_id = {node.node_id: node for node in bracket.nodes}
    targets: dict[str, str | None] = {}
    for node in bracket.nodes:
        target = next(
            (
                candidate.node_id
                for candidate in bracket.nodes
                if f"winner:{node.node_id}"
                in (candidate.source_top, candidate.source_bottom)
            ),
            None,
        )
        targets[node.node_id] = target

    records: list[SeasonMatchRecord] = []
    for node in sorted(
        bracket.nodes,
        key=lambda item: (item.round_number, item.round_sequence),
    ):
        top_player, top_kind = _source_identity(bracket, node.source_top)
        bottom_player, bottom_kind = _source_identity(bracket, node.source_bottom)
        status = _initial_status(
            top_player=top_player,
            bottom_player=bottom_player,
            top_kind=top_kind,
            bottom_kind=bottom_kind,
        )
        target_node_id = targets[node.node_id]
        target_match_id = target_node_id
        generated_fp = fingerprint(
            {
                "schema_version": "run_owned_match_record_projection.v1",
                "draw_authority_fingerprint": draw.fingerprint,
                "draw_type": bracket.draw_type,
                "node": node.model_dump(mode="json"),
                "top_player_id": top_player,
                "bottom_player_id": bottom_player,
                "status": status,
                "winner_to_match_id": target_match_id,
            }
        )
        records.append(
            SeasonMatchRecord(
                match_id=node.node_id,
                event_id=draw.event_id,
                draw_type=bracket.draw_type,
                round_number=node.round_number,
                round_name=(
                    f"Qualification R{node.round_number}"
                    if bracket.draw_type == "qualification"
                    else f"Main R{node.round_number}"
                ),
                bracket_position=node.round_sequence,
                top_slot_id=node.source_top,
                bottom_slot_id=node.source_bottom,
                top_source=node.source_top,
                bottom_source=node.source_bottom,
                top_player_id=top_player,
                bottom_player_id=bottom_player,
                status=status,
                winner_to_match_id=target_match_id,
                source_draw_fingerprint=bracket.fingerprint,
                generated_fingerprint=generated_fp,
            )
        )
    if set(by_id) != {record.match_id for record in records}:
        raise ValueError("canonical MatchPackage projection lost Draw nodes")
    return records


def _source_identity(
    bracket: TournamentDrawBracket,
    source: str,
) -> tuple[str | None, str]:
    if source.startswith("winner:"):
        return None, "winner"
    if not source.startswith("slot:"):
        raise ValueError("canonical Draw contains unsupported participant source")
    slot_index = int(source.removeprefix("slot:"))
    slots = {slot.slot_index: slot for slot in bracket.slots}
    slot = slots.get(slot_index)
    if slot is None:
        raise ValueError("canonical Draw source references a missing slot")
    if slot.entrant_kind == "player":
        return slot.player_id, "player"
    if slot.entrant_kind == "bye":
        return None, "bye"
    if slot.entrant_kind == "qualifier_placeholder":
        return None, "qualifier_placeholder"
    raise ValueError("canonical Draw slot entrant is unsupported")


def _initial_status(
    *,
    top_player: str | None,
    bottom_player: str | None,
    top_kind: str,
    bottom_kind: str,
) -> str:
    kinds = (top_kind, bottom_kind)
    if "bye" in kinds:
        if kinds.count("bye") != 1:
            raise ValueError("canonical Draw contains a double BYE")
        live_player = bottom_player if top_kind == "bye" else top_player
        if live_player is None:
            raise ValueError(
                "canonical BYE currently requires a directly known player opponent"
            )
        return "bye_auto_advance_pending"
    if top_player is not None and bottom_player is not None:
        return "pending"
    return "blocked_waiting_for_sources"
