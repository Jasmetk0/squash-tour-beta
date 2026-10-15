"""Pure, versioned Run calendar contract (Master v82).

This contract does not persist calendar metadata or change existing Run payloads.
Missing historical metadata is *explicitly* legacy FAX; malformed metadata is not.
Consumers must not infer a new Run's calendar from a historical missing field.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from beta_engine.domain.calendar.season_labels import long_season_label_from_start_year

CALENDAR_SCHEMA_VERSION = "run_calendar.v1"
LEGACY_FAX_CALENDAR_SCHEMA_VERSION = "legacy_fax_calendar.v0"
_MISSING = object()


def validate_calendar_scale(*, weeks_per_year: int, season_start_year_week: int) -> None:
    """Validate the common W/O constraints without imposing a FAX-only bound."""

    if type(weeks_per_year) is not int or weeks_per_year <= 0:
        raise ValueError("weeks_per_year must be a positive integer")
    if (
        type(season_start_year_week) is not int
        or not 1 <= season_start_year_week <= weeks_per_year
    ):
        raise ValueError(
            f"season_start_year_week must be between 1 and {weeks_per_year}"
        )


@dataclass(frozen=True, slots=True)
class RunCalendarPosition:
    season_index: int
    season_week: int
    calendar_year: int
    year_week: int


@dataclass(frozen=True, slots=True)
class RunCalendar:
    """Equal-length season/year clock, anchored at the Run's first season.

    Legacy instances are read-time interpretations of absent older metadata;
    they must never be serialized back into an old historical Saved Revision.
    """

    weeks_per_year: int
    season_start_year_week: int
    start_year: int
    season_count: int
    schema_version: str = CALENDAR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validate_calendar_scale(
            weeks_per_year=self.weeks_per_year,
            season_start_year_week=self.season_start_year_week,
        )
        if type(self.start_year) is not int or self.start_year < 0:
            raise ValueError("start_year must be a non-negative integer")
        if type(self.season_count) is not int or self.season_count <= 0:
            raise ValueError("season_count must be a positive integer")
        if self.schema_version not in (
            CALENDAR_SCHEMA_VERSION, LEGACY_FAX_CALENDAR_SCHEMA_VERSION
        ):
            raise ValueError("unsupported Run calendar schema_version")
        if self.schema_version == LEGACY_FAX_CALENDAR_SCHEMA_VERSION and (
            self.weeks_per_year,
            self.season_start_year_week,
            self.start_year,
            self.season_count,
        ) != (61, 37, 2000, 50):
            raise ValueError("legacy FAX calendar values cannot be reinterpreted")

    @classmethod
    def earth_default(cls, *, start_year: int = 2000, season_count: int = 50) -> RunCalendar:
        return cls(52, 1, start_year, season_count)

    @classmethod
    def fax_default(cls, *, start_year: int = 2000, season_count: int = 50) -> RunCalendar:
        return cls(61, 37, start_year, season_count)

    @classmethod
    def legacy_fax(cls) -> RunCalendar:
        return cls(61, 37, 2000, 50, LEGACY_FAX_CALENDAR_SCHEMA_VERSION)

    @classmethod
    def from_metadata(cls, metadata: object = _MISSING) -> RunCalendar:
        """Parse explicit v1 metadata or an *absent* historical calendar field.

        An explicit null, incomplete dict or unknown schema is corruption,
        never an invitation to silently use a default.
        """

        if metadata is _MISSING:
            return cls.legacy_fax()
        required = {
            "schema_version", "weeks_per_year", "season_start_year_week",
            "start_year", "season_count",
        }
        if not isinstance(metadata, Mapping) or set(metadata) != required:
            raise ValueError("Run calendar metadata must contain exactly the v1 fields")
        if metadata["schema_version"] != CALENDAR_SCHEMA_VERSION:
            raise ValueError("unsupported Run calendar schema_version")
        return cls(
            weeks_per_year=metadata["weeks_per_year"],
            season_start_year_week=metadata["season_start_year_week"],
            start_year=metadata["start_year"],
            season_count=metadata["season_count"],
            schema_version=metadata["schema_version"],
        )

    def to_metadata(self) -> dict[str, int | str]:
        if self.schema_version != CALENDAR_SCHEMA_VERSION:
            raise ValueError("legacy calendar has no writable v1 metadata")
        return {
            "schema_version": self.schema_version,
            "weeks_per_year": self.weeks_per_year,
            "season_start_year_week": self.season_start_year_week,
            "start_year": self.start_year,
            "season_count": self.season_count,
        }

    def label(self, season_index: int) -> str:
        """Single-year display for O=1, crossing-year display otherwise."""

        self._validate_season_index(season_index)
        start = self.start_year + season_index
        return str(start) if self.season_start_year_week == 1 else long_season_label_from_start_year(start)

    def _validate_season_index(self, season_index: int) -> None:
        if type(season_index) is not int or not 0 <= season_index < self.season_count:
            raise ValueError("season_index is outside the Run horizon")

    def season_to_calendar(self, season_index: int, season_week: int) -> RunCalendarPosition:
        self._validate_season_index(season_index)
        if type(season_week) is not int or not 1 <= season_week <= self.weeks_per_year:
            raise ValueError(f"season_week must be between 1 and {self.weeks_per_year}")
        absolute = self.season_start_year_week - 1 + season_week - 1
        return RunCalendarPosition(
            season_index=season_index,
            season_week=season_week,
            calendar_year=self.start_year + season_index + absolute // self.weeks_per_year,
            year_week=absolute % self.weeks_per_year + 1,
        )

    def calendar_to_season(
        self, calendar_year: int, year_week: int
    ) -> RunCalendarPosition | None:
        if type(calendar_year) is not int or calendar_year < 0:
            raise ValueError("calendar_year must be a non-negative integer")
        if type(year_week) is not int or not 1 <= year_week <= self.weeks_per_year:
            raise ValueError(f"year_week must be between 1 and {self.weeks_per_year}")
        elapsed = (
            (calendar_year - self.start_year) * self.weeks_per_year
            + year_week - self.season_start_year_week
        )
        index, week_zero = divmod(elapsed, self.weeks_per_year)
        if not 0 <= index < self.season_count:
            return None
        return RunCalendarPosition(index, week_zero + 1, calendar_year, year_week)

    def ordinal(self, season_index: int, season_week: int) -> int:
        """Zero-based elapsed Run weeks; does not use legacy RankingWeek.ordinal.

        The current 61-week ranking ordinal is a historical implementation
        detail. All new target arithmetic is explicitly scoped to this W.
        """

        self.season_to_calendar(season_index, season_week)
        return season_index * self.weeks_per_year + season_week - 1

    def position_at_ordinal(self, ordinal: int) -> RunCalendarPosition:
        """Invert a Run week ordinal without wrapping or clamping its horizon."""

        if (
            type(ordinal) is not int
            or not 0 <= ordinal < self.season_count * self.weeks_per_year
        ):
            raise ValueError("week ordinal is outside the Run horizon")
        index, week_zero = divmod(ordinal, self.weeks_per_year)
        return self.season_to_calendar(index, week_zero + 1)

    def advance_weeks(
        self, season_index: int, season_week: int, count: int
    ) -> RunCalendarPosition:
        """Return an in-horizon target; negative/overflow movement is invalid."""

        if type(count) is not int or count < 0:
            raise ValueError("advance_weeks count must be a non-negative integer")
        return self.position_at_ordinal(self.ordinal(season_index, season_week) + count)

    def remaining_weeks_including_current(
        self, season_index: int, season_week: int
    ) -> int:
        """Number of distinct inclusive Run weeks left from this week."""

        return (
            self.season_count * self.weeks_per_year
            - self.ordinal(season_index, season_week)
        )

    def extend_to(self, season_count: int) -> RunCalendar:
        """Pure planning only; persistence/Completed continuation belongs elsewhere."""

        if self.schema_version != CALENDAR_SCHEMA_VERSION:
            raise ValueError("legacy calendar extension requires explicit migration")
        if type(season_count) is not int or season_count <= self.season_count:
            raise ValueError("extended season_count must exceed current horizon")
        return replace(self, season_count=season_count)
