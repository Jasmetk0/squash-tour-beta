"""Explicit initial health baseline; later health events need calendar-owned dates."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarInitialHealthState(FrozenInput):
    schema_version: Literal["calendar_initial_health_state.v1"] = (
        "calendar_initial_health_state.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[PlayerHealthProfile, ...] = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: None = None
    initialization_policy: Literal["fresh_without_history.v1"] = (
        "fresh_without_history.v1"
    )
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_baseline(self):
        if self.week.ordinal != 0:
            raise ValueError("Initial health requires opening Week 1")
        ids = tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("Initial health requires canonical distinct players")
        if any(p.records or p.permanent_consequences for p in self.players):
            raise ValueError(
                "Fresh initial health cannot contain invented history or legacy event dates"
            )
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))
