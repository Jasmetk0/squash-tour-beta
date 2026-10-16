"""Calendar-owned population bootstrap, before Tour/sporting initialization."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarPlayerLifecycleIdentity(FrozenInput):
    player_id: str = Field(min_length=1)
    birth_year: int
    birth_year_week: int = Field(ge=1)
    age: int = Field(ge=15, le=120)
    status: Literal["active"] = "active"
    source_generation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CalendarPlayerLifecycleState(FrozenInput):
    schema_version: Literal["player_lifecycle_calendar_state.v2"] = (
        "player_lifecycle_calendar_state.v2"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[CalendarPlayerLifecycleIdentity, ...]
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: None = None
    policy: PlayerLifecyclePolicy
    # Population adoption creates no historical Tour entry or retirement event.
    # The future ranking/entry migration must initialize those separately.
    initialization_stage: Literal["population_only"] = "population_only"

    @model_validator(mode="after")
    def validate_initial_population(self):
        if self.week.ordinal != 0:
            raise ValueError("Calendar population bootstrap must be at opening Week 1")
        ids = [p.player_id for p in self.players]
        if not ids or ids != sorted(set(ids)):
            raise ValueError("Calendar lifecycle requires canonical distinct players")
        position = self.week.calendar_position
        for player in self.players:
            age = age_at_calendar_position(
                birth_year=player.birth_year,
                birth_year_week=player.birth_year_week,
                calendar_year=position.calendar_year,
                year_week=position.year_week,
                weeks_per_calendar_year=self.week.calendar.weeks_per_year,
            )
            if player.age != age:
                raise ValueError(
                    "Calendar lifecycle age differs from its birth identity"
                )
            if age >= self.policy.automatic_retirement_age:
                raise ValueError(
                    "Initial player already reached the stored retirement age"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))
