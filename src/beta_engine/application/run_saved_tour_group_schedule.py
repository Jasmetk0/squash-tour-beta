"""Exact read-only group Match Day authority in a reachable Saved Edition.

Never derive a round-robin schedule from Calendar/Result alone. The saved Format,
Topology and Group Schedule must all be present, identically owned and replay
the original deterministic schedule without altering the Run or sporting RNG.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.domain.tournaments.format_authority import TournamentFormatAuthority
from beta_engine.domain.tournaments.topology_authority import TournamentTopologyAuthority
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority, TournamentGroupMatchScheduleBuilder,
)
from beta_engine.application.viewer_tournament_result_read_model import ViewerTournamentResult


class RunSavedTourGroupMatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    group_index: int = Field(ge=1)
    match_day_ordinal: int = Field(ge=1)
    match_order: int = Field(ge=1)
    top_player_id: str
    bottom_player_id: str
    best_of: Literal[3, 5]


class RunSavedTourGroupSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["run_saved_tour_group_schedule.v1"] = (
        "run_saved_tour_group_schedule.v1"
    )
    source: Literal["saved_tournament_group_match_schedule_authority.v1"] = (
        "saved_tournament_group_match_schedule_authority.v1"
    )
    run_id: str
    revision_branch_id: str
    event_id: str
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_count: int = Field(ge=1)
    group_size: int = Field(ge=2)
    match_day_count: int = Field(ge=1)
    matches: tuple[RunSavedTourGroupMatch, ...]


def resolve_saved_tour_group_schedule(
    component: dict | None, *, run_id: str, branch_id: str, event_id: str,
    published_result: ViewerTournamentResult | None,
) -> RunSavedTourGroupSchedule | None:
    if component is None:
        return None

    def one(kind: str):
        rows = [row for row in component.get(kind, ()) if row.get("event_id") == event_id]
        if len(rows) > 1:
            raise ValueError("Ambiguous saved group schedule source: " + kind)
        if rows and (
            rows[0].get("run_id"), rows[0].get("branch_id")
        ) != (run_id, branch_id):
            raise ValueError("Saved group schedule source belongs to another Run/Branch")
        return rows[0] if rows else None

    schedule_row = one("group_match_schedules")
    if schedule_row is None:
        return None
    format_row = one("format_authorities")
    topology_row = one("topology_authorities")
    if format_row is None or topology_row is None:
        raise ValueError("Saved group schedule requires its original Format and Topology")

    format_authority = TournamentFormatAuthority.model_validate_json(format_row["payload_json"])
    topology = TournamentTopologyAuthority.model_validate_json(topology_row["payload_json"])
    schedule = TournamentGroupMatchScheduleAuthority.model_validate_json(
        schedule_row["payload_json"]
    )
    for row, authority in (
        (format_row, format_authority),
        (topology_row, topology),
        (schedule_row, schedule),
    ):
        if (
            (authority.run_id, authority.branch_id, authority.event_id,
             authority.fingerprint, authority.generated_by_command_id if row is not format_row
             else authority.configured_by_command_id)
            != (run_id, branch_id, event_id, row.get("authority_fingerprint"),
                row.get("command_id"))
        ):
            raise ValueError("Saved group authority identity/fingerprint is corrupt")

    if (
        schedule.format_authority_fingerprint != format_authority.fingerprint
        or schedule.topology_authority_fingerprint != topology.fingerprint
        or topology.format_authority_fingerprint != format_authority.fingerprint
        or format_authority.format_kind not in {"groups", "groups_knockout"}
        or topology.format_kind != format_authority.format_kind
        or schedule_row.get("format_authority_fingerprint") != format_authority.fingerprint
        or schedule_row.get("topology_authority_fingerprint") != topology.fingerprint
        or topology_row.get("format_authority_fingerprint") != format_authority.fingerprint
    ):
        raise ValueError("Saved group schedule Format/Topology provenance mismatch")
    if TournamentGroupMatchScheduleBuilder.build(
        format_authority=format_authority, topology_authority=topology,
        command_id=schedule.generated_by_command_id,
    ) != schedule:
        raise ValueError("Saved group schedule does not replay from original Format/Topology")

    # Only published canonical results may be attached. A planned match is
    # never labelled played; no event/time/score is inferred by scheduling.
    if published_result is not None:
        published = [m for m in published_result.matches if m.draw_type == "group"]
        by_id = {m.match_id: m for m in schedule.matches}
        for match in published:
            planned = by_id.get(match.match_id)
            if planned is None or (
                match.loser_player_id is not None and
                {match.winner_player_id, match.loser_player_id} !=
                {planned.top_player_id, planned.bottom_player_id}
            ):
                raise ValueError("Published group match contradicts saved group schedule")

    return RunSavedTourGroupSchedule(
        run_id=run_id, revision_branch_id=branch_id, event_id=event_id,
        authority_fingerprint=schedule.fingerprint,
        group_count=schedule.group_count, group_size=schedule.group_size,
        match_day_count=schedule.match_day_count,
        matches=tuple(
            RunSavedTourGroupMatch(
                match_id=m.match_id, group_index=m.group_index,
                match_day_ordinal=m.match_day_ordinal, match_order=m.match_order,
                top_player_id=m.top_player_id, bottom_player_id=m.bottom_player_id,
                best_of=m.effective_match_format.format.best_of,
            )
            for m in sorted(
                schedule.matches,
                key=lambda m: (m.match_day_ordinal, m.match_order, m.group_index, m.match_id),
            )
        ),
    )
