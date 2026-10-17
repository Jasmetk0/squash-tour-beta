"""Versioned *prepared*, never Official, knockout points from real Saved matches.

Operator-authored distribution is signed with the new Saved sporting component.
These awards cannot enter the Official ranking until a calendar-native
publication/Week Transition consumes and authenticates them.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_standalone_match_state import CalendarOpeningKnockout


class CalendarKnockoutPointPolicy(FrozenInput):
    schema_version: Literal["calendar_knockout_point_policy.v1"] = "calendar_knockout_point_policy.v1"
    source_kind: Literal["admin_explicit_reviewed"] = "admin_explicit_reviewed"
    category_label: str = Field(min_length=1, max_length=120)
    champion: int = Field(ge=0, le=1000000)
    finalist: int = Field(ge=0, le=1000000)
    semifinal: int = Field(ge=0, le=1000000)
    validity_weeks: int = Field(ge=1)

    @model_validator(mode="after")
    def points_order(self):
        if not self.champion >= self.finalist >= self.semifinal:
            raise ValueError("Knockout point table must be non-increasing by finishing stage")
        if self.champion == self.semifinal:
            raise ValueError("Knockout point table must distinguish champion and semifinalists")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class CalendarKnockoutPreparedAward(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: Literal["champion", "finalist", "semifinal"]
    main_points: int = Field(ge=0)
    source_knockout_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_policy_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


def derive_knockout_prepared_awards(
    knockout: CalendarOpeningKnockout,
    policy: CalendarKnockoutPointPolicy,
) -> tuple[CalendarKnockoutPreparedAward, ...]:
    semi_a, semi_b, final = knockout.matches
    stages = {
        semi_a.result.loser_player_id: "semifinal",
        semi_b.result.loser_player_id: "semifinal",
        final.result.loser_player_id: "finalist",
        final.result.winner_player_id: "champion",
    }
    if set(stages) != set(knockout.entrant_ids):
        raise ValueError("Point placements do not match four recorded knockout entrants")
    return tuple(
        CalendarKnockoutPreparedAward(
            player_id=player_id, reached_stage=stage,
            main_points=getattr(policy, stage),
            source_knockout_fingerprint=knockout.fingerprint,
            source_policy_fingerprint=policy.fingerprint,
        )
        for player_id, stage in sorted(stages.items())
    )


class CalendarScoredOpeningKnockout(FrozenInput):
    """Same table and Saved content key, different signed schema from legacy v1."""
    schema_version: Literal["calendar_scored_opening_knockout.v1"] = "calendar_scored_opening_knockout.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1, max_length=128)
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_saved_head: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    knockout: CalendarOpeningKnockout
    knockout_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: CalendarKnockoutPointPolicy
    first_publication_week: RunWeekPosition
    awards: tuple[
        CalendarKnockoutPreparedAward, CalendarKnockoutPreparedAward,
        CalendarKnockoutPreparedAward, CalendarKnockoutPreparedAward
    ]
    operator_label: str = Field(min_length=1)
    audit_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scoring(self):
        if (
            (self.run_id, self.branch_id, self.match_id, self.week)
            != (self.knockout.run_id, self.knockout.branch_id,
                self.knockout.match_id, self.knockout.week)
            or self.knockout_fingerprint != self.knockout.fingerprint
            or self.source_initial_world_fingerprint
            != self.knockout.source_initial_world_fingerprint
        ):
            raise ValueError("Prepared awards do not bind exactly to the original knockout")
        clock = self.week.calendar
        if (
            self.first_publication_week.calendar != clock
            or (self.first_publication_week.season_index, self.first_publication_week.week) != (0, 2)
            or self.policy.validity_weeks != clock.weeks_per_year
            or tuple(self.awards) != derive_knockout_prepared_awards(
                self.knockout, self.policy
            )
        ):
            raise ValueError("Prepared award timing or values disagree with Saved knockout policy")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))
