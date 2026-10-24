"""A real terminal Edition result, with no out-of-horizon publication position.

The eligibility boundary is a scalar, not a Run week. The production Tour
rebuilds these records from the frozen Edition, draw and played MatchEngine
event; a matching self-declared fingerprint alone is never source authority.
"""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingResult,
    CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import FrozenInput


class CalendarTerminalRankingResult(FrozenInput):
    schema_version: Literal["calendar_terminal_edition_result.v1"] = "calendar_terminal_edition_result.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    completed_week: RunWeekPosition
    closing_eligibility_ordinal: int = Field(ge=1)
    created_saved_head: str = Field(min_length=1)
    played_saved_head: str = Field(min_length=1)
    edition_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    played_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_points: Literal[0] = 0
    main_points: int = Field(ge=0)
    validity_weeks: int = Field(ge=1)
    ranked: bool
    terminal_status: Literal["completed"] = "completed"

    @model_validator(mode="after")
    def validate_boundary(self):
        clock = self.completed_week.calendar
        end = clock.weeks_per_year * clock.season_count
        if self.completed_week.ordinal != end - 1 or self.closing_eligibility_ordinal != end:
            raise ValueError("Terminal result must own its original actual Run-end boundary")
        return self

    @property
    def points(self):
        return self.main_points

    def for_publication(self, calendar):
        """Explicit extended-clock projection; never modifies the original record."""
        original = self.completed_week.calendar
        if (
            (calendar.weeks_per_year, calendar.season_start_year_week, calendar.start_year)
            != (original.weeks_per_year, original.season_start_year_week, original.start_year)
            or calendar.season_count <= original.season_count
        ):
            raise ValueError("Terminal result publication requires an explicit strict horizon extension")
        position = calendar.position_at_ordinal(self.closing_eligibility_ordinal)
        return CalendarRankingResult(
            edition_id=self.edition_id, player_id=self.player_id,
            source_fingerprint=self.source_fingerprint,
            completed_week=CalendarRankingWeek(season_index=self.completed_week.season_index, week=self.completed_week.week),
            first_publication_week=CalendarRankingWeek(season_index=position.season_index, week=position.season_week),
            main_points=self.main_points, validity_weeks=self.validity_weeks,
            ranked=self.ranked,
        )


def result_activation_ordinal(result, calendar):
    if isinstance(result, CalendarTerminalRankingResult):
        original = result.completed_week.calendar
        if (
            (calendar.weeks_per_year, calendar.season_start_year_week, calendar.start_year)
            != (original.weeks_per_year, original.season_start_year_week, original.start_year)
            or calendar.season_count < original.season_count
        ):
            raise ValueError("Terminal result has a foreign execution calendar")
        return result.closing_eligibility_ordinal
    return calendar.ordinal(result.first_publication_week.season_index, result.first_publication_week.week)
