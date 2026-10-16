"""Explicit Run-owned position; never reinterpret legacy RankingWeek ordinals."""

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.official import FrozenInput


class RunWeekPosition(FrozenInput):
    calendar: RunCalendar
    season_index: int = Field(ge=0)
    week: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_position(self):
        self.calendar.season_to_calendar(self.season_index, self.week)
        return self

    @property
    def ordinal(self) -> int:
        return self.calendar.ordinal(self.season_index, self.week)

    @property
    def calendar_position(self):
        return self.calendar.season_to_calendar(self.season_index, self.week)
