"""Immutable completed-group table and audited tie evidence for one Saved Edition.

Restore-grade Saved Slot validation runs upstream. Here we additionally bind
one Edition's standings, schedule and explicit tie decisions to the same
original Run/Branch, command/fingerprint and published phase identities.
Never build a hypothetical table from planned group fixtures.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthority,
)
from beta_engine.application.run_saved_tour_group_schedule import RunSavedTourGroupSchedule


class SavedGroupTableRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position: int = Field(ge=1)
    player_id: str
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    group_points: int = Field(ge=0)
    played_matches: int = Field(ge=0)
    walkovers_received: int = Field(ge=0)
    walkovers_conceded: int = Field(ge=0)
    games_won: int = Field(ge=0)
    games_lost: int = Field(ge=0)
    points_won: int = Field(ge=0)
    points_lost: int = Field(ge=0)


class SavedGroupTable(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    group_index: int = Field(ge=1)
    rows: tuple[SavedGroupTableRow, ...]


class SavedGroupTieDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    group_index: int = Field(ge=1)
    case_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ordered_player_ids: tuple[str, ...]
    admin_reason: str


class RunSavedTourGroupStandings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_saved_tour_group_standings.v1"] = (
        "run_saved_tour_group_standings.v1"
    )
    source: Literal["saved_tournament_group_standings_authority"] = (
        "saved_tournament_group_standings_authority"
    )
    run_id: str
    revision_branch_id: str
    event_id: str
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_schedule_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    groups: tuple[SavedGroupTable, ...]
    tie_decisions: tuple[SavedGroupTieDecision, ...]


def resolve_saved_tour_group_standings(
    component: dict | None, *, run_id: str, branch_id: str,
    event_id: str, group_schedule: RunSavedTourGroupSchedule | None,
) -> RunSavedTourGroupStandings | None:
    if component is None:
        return None
    rows = [
        row for row in component.get("group_standings", ())
        if row.get("event_id") == event_id
    ]
    tie_rows = [
        row for row in component.get("group_tie_resolutions", ())
        if row.get("event_id") == event_id
    ]
    if not rows:
        if tie_rows:
            raise ValueError("Saved group tie decisions lack group standings")
        return None
    if len(rows) != 1:
        raise ValueError("Ambiguous saved group standings authority")
    if group_schedule is None:
        raise ValueError("Saved group standings lack their saved group Match Schedule")
    row = rows[0]
    if (row.get("run_id"), row.get("branch_id")) != (run_id, branch_id):
        raise ValueError("Saved group standings belong to another Run/Branch")
    standings = TournamentGroupStandingsAuthority.model_validate_json(row["payload_json"])
    if (
        (standings.run_id, standings.branch_id, standings.event_id,
         standings.generated_by_command_id, standings.fingerprint,
         standings.group_match_schedule_fingerprint,
         standings.group_rules_policy_fingerprint)
        != (run_id, branch_id, event_id, row.get("command_id"),
            row.get("authority_fingerprint"),
            row.get("group_match_schedule_fingerprint"),
            row.get("group_rules_policy_fingerprint"))
        or standings.group_match_schedule_fingerprint
        != group_schedule.authority_fingerprint
        or len(standings.groups) != group_schedule.group_count
        or any(len(group.rows) != group_schedule.group_size for group in standings.groups)
    ):
        raise ValueError("Saved group standings authority provenance is corrupt")

    # Decisions are never inferred from final position. Show audited source
    # decisions only when they are exactly included in the saved standings.
    decisions = []
    for tie_row in tie_rows:
        if (tie_row.get("run_id"), tie_row.get("branch_id")) != (run_id, branch_id):
            raise ValueError("Saved group tie decision belongs to another Run/Branch")
        authority = TournamentGroupTieResolutionAuthority.model_validate_json(
            tie_row["payload_json"]
        )
        if (
            (authority.run_id, authority.branch_id, authority.event_id,
             authority.resolved_by_command_id, authority.fingerprint,
             authority.case.fingerprint, authority.group_match_schedule_fingerprint)
            != (run_id, branch_id, event_id, tie_row.get("command_id"),
                tie_row.get("authority_fingerprint"), tie_row.get("case_fingerprint"),
                group_schedule.authority_fingerprint)
            or tie_row.get("group_match_schedule_fingerprint")
            != group_schedule.authority_fingerprint
        ):
            raise ValueError("Saved group tie decision audit identity is corrupt")
        decisions.append(authority)
    if len({item.case.fingerprint for item in decisions}) != len(decisions):
        raise ValueError("Saved group tie case is duplicated")
    if standings.schema_version == "tournament_group_standings_authority.v1":
        if decisions:
            raise ValueError("Legacy standings cannot carry Admin tie decisions")
    elif {decision.fingerprint for decision in standings.admin_tie_resolutions} != {
        decision.decision.fingerprint for decision in decisions
    } or len(standings.admin_tie_resolutions) != len(decisions):
        raise ValueError("Saved group tie decisions do not match frozen standings")

    return RunSavedTourGroupStandings(
        run_id=run_id, revision_branch_id=branch_id, event_id=event_id,
        authority_fingerprint=standings.fingerprint,
        group_schedule_fingerprint=group_schedule.authority_fingerprint,
        groups=tuple(SavedGroupTable(
            group_index=group.group_index,
            rows=tuple(SavedGroupTableRow(**{
                field: getattr(r, field)
                for field in SavedGroupTableRow.model_fields
            }) for r in group.rows),
        ) for group in standings.groups),
        tie_decisions=tuple(SavedGroupTieDecision(
            group_index=decision.case.group_index,
            case_fingerprint=decision.case.fingerprint,
            ordered_player_ids=decision.decision.ordered_player_ids,
            admin_reason=decision.decision.admin_reason,
        ) for decision in sorted(decisions, key=lambda d: (
            d.case.group_index, d.case.fingerprint,
        ))),
    )
