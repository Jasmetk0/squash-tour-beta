"""Immutable World Tour Finals replacement lineage sourced only from frozen Race."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.finals.participant_selection import (
    WorldTourFinalsParticipantSelectionSnapshot,
    WorldTourFinalsSelectedPlayer,
)
from beta_engine.domain.finals.race import WorldTourFinalsRaceSnapshot
from beta_engine.domain.rankings.official import FrozenInput


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class FinalsReplacementCandidateDecision(FrozenInput):
    player_id: str = Field(min_length=1)
    race_rank: int = Field(ge=1)
    decision: Literal["declined", "accepted"]


class WorldTourFinalsEffectiveParticipantState(FrozenInput):
    """One append-only effective field version; the initial selection is never edited."""

    schema_version: Literal["world_tour_finals_effective_participant_state.v1"] = "world_tour_finals_effective_participant_state.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    initial_selection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    race_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    participants: tuple[WorldTourFinalsSelectedPlayer, ...]
    created_by_command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_field(self) -> "WorldTourFinalsEffectiveParticipantState":
        ids = tuple(row.player_id for row in self.participants)
        if len(ids) != len(set(ids)):
            raise ValueError("Effective Finals field has duplicate players")
        if tuple(row.race_rank for row in self.participants) != tuple(sorted(row.race_rank for row in self.participants)):
            raise ValueError("Effective Finals field must remain in frozen Race order")
        if tuple(row.seed for row in self.participants) != tuple(range(1, len(self.participants) + 1)):
            raise ValueError("Effective Finals field seeds must be contiguous")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class WorldTourFinalsReplacementAuthority(FrozenInput):
    """Audit record for one vacancy and its explicit candidate decisions."""

    schema_version: Literal["world_tour_finals_race_replacement_authority.v1"] = "world_tour_finals_race_replacement_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_season_index: int = Field(ge=0, le=49)
    finals_event_id: str = Field(min_length=1)
    vacancy_id: str = Field(min_length=1, max_length=128)
    race_snapshot_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_selection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_effective_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    withdrawn_player_id: str = Field(min_length=1)
    withdrawal_reason: str = Field(min_length=1, max_length=2000)
    decisions: tuple[FinalsReplacementCandidateDecision, ...] = ()
    status: Literal["awaiting_decision", "accepted", "exhausted"]
    offered_candidate_player_id: str | None = None
    offered_candidate_race_rank: int | None = Field(default=None, ge=1)
    resulting_effective_state_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_status(self) -> "WorldTourFinalsReplacementAuthority":
        if bool(self.offered_candidate_player_id) != bool(self.offered_candidate_race_rank):
            raise ValueError("Replacement offer identity is incomplete")
        if self.status == "awaiting_decision" and not self.offered_candidate_player_id:
            raise ValueError("Awaiting replacement decision requires a candidate")
        if self.status != "awaiting_decision" and self.offered_candidate_player_id:
            raise ValueError("Terminal replacement state cannot carry an offer")
        accepted = tuple(d for d in self.decisions if d.decision == "accepted")
        if self.status == "accepted" and (len(accepted) != 1 or self.resulting_effective_state_fingerprint is None):
            raise ValueError("Accepted replacement requires one accepted decision and resulting field")
        if self.status != "accepted" and self.resulting_effective_state_fingerprint is not None:
            raise ValueError("Non-accepted replacement cannot carry a resulting field")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def initial_effective_participant_state(selection: WorldTourFinalsParticipantSelectionSnapshot, *, command_id: str) -> WorldTourFinalsEffectiveParticipantState:
    return WorldTourFinalsEffectiveParticipantState(
        run_id=selection.run_id, branch_id=selection.branch_id,
        target_season_index=selection.target_season_index, finals_event_id=selection.finals_event_id,
        initial_selection_fingerprint=selection.fingerprint,
        race_snapshot_fingerprint=selection.race_snapshot_fingerprint,
        participants=selection.participants, created_by_command_id=command_id,
    )


def preview_race_replacement(*, race: WorldTourFinalsRaceSnapshot, selection: WorldTourFinalsParticipantSelectionSnapshot, effective: WorldTourFinalsEffectiveParticipantState, withdrawn_player_id: str, withdrawal_reason: str, vacancy_id: str, prior_decisions: tuple[FinalsReplacementCandidateDecision, ...] = ()) -> WorldTourFinalsReplacementAuthority:
    """Return the next Race candidate; declines are vacancy-local and never global."""
    if not withdrawal_reason.strip():
        raise ValueError("Finals withdrawal reason is required")
    scope = (race.run_id, race.branch_id, race.target_season_index, race.fingerprint)
    if scope != (effective.run_id, effective.branch_id, effective.target_season_index, effective.race_snapshot_fingerprint):
        raise ValueError("Effective Finals field does not bind the supplied frozen Race")
    if selection.fingerprint != effective.initial_selection_fingerprint:
        raise ValueError("Effective Finals field does not bind the initial selection")
    if withdrawn_player_id not in {p.player_id for p in effective.participants}:
        raise ValueError("Withdrawn player is not currently confirmed in Finals")
    if any(d.decision == "accepted" for d in prior_decisions):
        raise ValueError("Accepted vacancy is already terminal")
    excluded = {p.player_id for p in effective.participants} | {d.player_id for d in prior_decisions}
    candidate = next((row for row in race.rows if row.player_id not in excluded), None)
    return WorldTourFinalsReplacementAuthority(
        run_id=effective.run_id, branch_id=effective.branch_id,
        target_season_index=effective.target_season_index, finals_event_id=effective.finals_event_id,
        vacancy_id=vacancy_id, race_snapshot_fingerprint=race.fingerprint,
        initial_selection_fingerprint=selection.fingerprint,
        source_effective_state_fingerprint=effective.fingerprint,
        withdrawn_player_id=withdrawn_player_id, withdrawal_reason=withdrawal_reason.strip(),
        decisions=prior_decisions, status="awaiting_decision" if candidate else "exhausted",
        offered_candidate_player_id=candidate.player_id if candidate else None,
        offered_candidate_race_rank=candidate.rank if candidate else None,
    )


def decide_race_replacement(*, preview: WorldTourFinalsReplacementAuthority, race: WorldTourFinalsRaceSnapshot, selection: WorldTourFinalsParticipantSelectionSnapshot, effective: WorldTourFinalsEffectiveParticipantState, decision: Literal["decline", "accept"], command_id: str) -> tuple[WorldTourFinalsReplacementAuthority, WorldTourFinalsEffectiveParticipantState | None]:
    if preview.status != "awaiting_decision" or preview.source_effective_state_fingerprint != effective.fingerprint:
        raise ValueError("Replacement preview is stale or has no candidate")
    candidate = next((row for row in race.rows if row.player_id == preview.offered_candidate_player_id), None)
    if candidate is None or candidate.rank != preview.offered_candidate_race_rank:
        raise ValueError("Replacement candidate is not backed by frozen Race")
    recorded = FinalsReplacementCandidateDecision(player_id=candidate.player_id, race_rank=candidate.rank, decision="accepted" if decision == "accept" else "declined")
    decisions = (*preview.decisions, recorded)
    if decision == "decline":
        return preview_race_replacement(race=race, selection=selection, effective=effective, withdrawn_player_id=preview.withdrawn_player_id, withdrawal_reason=preview.withdrawal_reason, vacancy_id=preview.vacancy_id, prior_decisions=decisions), None
    rows = {row.player_id: row for row in race.rows}
    ids = ({p.player_id for p in effective.participants} - {preview.withdrawn_player_id}) | {candidate.player_id}
    ordered = [row for row in race.rows if row.player_id in ids]
    prior = {p.player_id: p for p in effective.participants}
    participants = tuple(WorldTourFinalsSelectedPlayer(player_id=row.player_id, race_rank=row.rank, race_points=row.race_points, seed=i, qualification_source=prior[row.player_id].qualification_source if row.player_id in prior else "race", direct_entry_event_ids=prior[row.player_id].direct_entry_event_ids if row.player_id in prior else ()) for i, row in enumerate(ordered, 1))
    state = WorldTourFinalsEffectiveParticipantState(run_id=effective.run_id, branch_id=effective.branch_id, target_season_index=effective.target_season_index, finals_event_id=effective.finals_event_id, initial_selection_fingerprint=selection.fingerprint, race_snapshot_fingerprint=race.fingerprint, predecessor_fingerprint=effective.fingerprint, participants=participants, created_by_command_id=command_id)
    authority = preview.model_copy(update={"decisions": decisions, "status": "accepted", "offered_candidate_player_id": None, "offered_candidate_race_rank": None, "resulting_effective_state_fingerprint": state.fingerprint})
    return authority, state
