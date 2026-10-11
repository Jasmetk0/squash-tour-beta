"""Explicit first-version Week Tournament Lock authority.

The lock resolves only already-materialized tournament field conflicts. It does not
invent Final Commitment timing, AI preference, sanctions, eligibility or deadline
policy. An Admin explicitly selects exactly one accepted event for every player who
is currently present in more than one canonical tournament field in the same week.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class WeekTournamentLockEventEvidence(FrozenInput):
    event_id: str = Field(min_length=1)
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_player_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_players(self):
        if self.accepted_player_ids != tuple(sorted(set(self.accepted_player_ids))):
            raise ValueError(
                "Week Tournament Lock accepted players must be unique and canonical"
            )
        return self


class WeekTournamentPlayerLock(FrozenInput):
    player_id: str = Field(min_length=1)
    eligible_event_ids: tuple[str, ...] = Field(min_length=2)
    selected_event_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_selection(self):
        if self.eligible_event_ids != tuple(sorted(set(self.eligible_event_ids))):
            raise ValueError(
                "Week Tournament Lock eligible events must be unique and canonical"
            )
        if self.selected_event_id not in self.eligible_event_ids:
            raise ValueError(
                "Week Tournament Lock selected event is not an eligible conflict event"
            )
        return self


class WeekTournamentLockAuthority(FrozenInput):
    schema_version: Literal["week_tournament_lock_authority.v1"] = (
        "week_tournament_lock_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    resolved_by_command_id: str = Field(min_length=1, max_length=128)
    selection_policy_id: Literal["explicit_admin_week_tournament_lock.v1"] = (
        "explicit_admin_week_tournament_lock.v1"
    )
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)
    event_evidence: tuple[WeekTournamentLockEventEvidence, ...] = Field(min_length=1)
    player_locks: tuple[WeekTournamentPlayerLock, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_complete_conflict_resolution(self):
        if self.operator_label != self.operator_label.strip():
            raise ValueError("Week Tournament Lock operator label must be trimmed")
        if self.audit_reason != self.audit_reason.strip():
            raise ValueError("Week Tournament Lock audit reason must be trimmed")

        event_ids = tuple(item.event_id for item in self.event_evidence)
        if event_ids != tuple(sorted(set(event_ids))):
            raise ValueError(
                "Week Tournament Lock event evidence must be unique and canonical"
            )

        accepted_by_player: dict[str, list[str]] = {}
        for evidence in self.event_evidence:
            for player_id in evidence.accepted_player_ids:
                accepted_by_player.setdefault(player_id, []).append(evidence.event_id)
        conflicts = {
            player_id: tuple(sorted(event_ids))
            for player_id, event_ids in accepted_by_player.items()
            if len(set(event_ids)) > 1
        }
        if not conflicts:
            raise ValueError(
                "Week Tournament Lock requires at least one overlapping accepted player"
            )

        lock_players = tuple(item.player_id for item in self.player_locks)
        if lock_players != tuple(sorted(set(lock_players))):
            raise ValueError(
                "Week Tournament Lock player locks must be unique and canonical"
            )
        if set(lock_players) != set(conflicts):
            raise ValueError(
                "Week Tournament Lock must resolve every and only current field conflict"
            )
        for lock in self.player_locks:
            if lock.eligible_event_ids != conflicts[lock.player_id]:
                raise ValueError(
                    "Week Tournament Lock eligible events differ from field evidence"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))
