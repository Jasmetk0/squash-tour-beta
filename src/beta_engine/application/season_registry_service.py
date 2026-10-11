from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from beta_engine.domain.calendar import (
    DEFAULT_WEEKS_PER_CALENDAR_YEAR,
    DEFAULT_WEEKS_PER_SEASON,
    SEASON_WEEK_1_YEAR_WEEK,
    season_week_to_calendar_position,
    season_week_to_year_week,
    year_week_to_season_week,
)
from beta_engine.domain.calendar.season_labels import normalize_season_label, season_label_from_start_year

TOTAL_REGISTRY_SEASONS = 50
REGISTRY_START_YEAR = 2000
REGISTRY_END_YEAR = REGISTRY_START_YEAR + TOTAL_REGISTRY_SEASONS - 1
SIMPLIFIED_YEAR_WEEK_COUNT = DEFAULT_WEEKS_PER_CALENDAR_YEAR


class SeasonRegistryEntry(BaseModel):
    season_start_year: int
    label: str
    season_index: int = Field(description="0-based season index within the deterministic registry")
    week_count: int = DEFAULT_WEEKS_PER_SEASON
    season_week_start: int = 1
    season_week_end: int = DEFAULT_WEEKS_PER_SEASON
    year_week_start: int = SEASON_WEEK_1_YEAR_WEEK
    year_week_end: int
    status: str = "registry_only"


class SeasonRegistryResponse(BaseModel):
    start_season: str
    end_season: str
    season_count: int
    week_count: int
    season_week_1_year_week: int
    seasons: list[SeasonRegistryEntry]


@dataclass(slots=True)
class SeasonRegistryService:
    """Read-only deterministic season registry using the shared FAX 61-week calendar model."""

    def list_seasons(self) -> list[SeasonRegistryEntry]:
        seasons: list[SeasonRegistryEntry] = []
        for season_index, start_year in enumerate(range(REGISTRY_START_YEAR, REGISTRY_END_YEAR + 1)):
            label = _season_label(start_year)
            end_position = season_week_to_calendar_position(start_year, DEFAULT_WEEKS_PER_SEASON)
            seasons.append(
                SeasonRegistryEntry(
                    season_start_year=start_year,
                    label=label,
                    season_index=season_index,
                    year_week_end=end_position.year_week,
                )
            )
        return seasons

    def get_season(self, *, label: str | None = None, start_year: int | None = None) -> SeasonRegistryEntry | None:
        if label is None and start_year is None:
            raise ValueError("label or start_year is required")
        normalized_label = normalize_season_label(label) if label is not None else None
        for entry in self.list_seasons():
            if normalized_label is not None and entry.label == normalized_label:
                return entry
            if start_year is not None and entry.season_start_year == start_year:
                return entry
        return None

    def get_next_season(
        self, *, label: str | None = None, start_year: int | None = None
    ) -> SeasonRegistryEntry | None:
        current = self.get_season(label=label, start_year=start_year)
        if current is None:
            return None
        return self.get_season(start_year=current.season_start_year + 1)

    def season_week_to_year_week(self, season_week: int) -> int:
        return season_week_to_year_week(season_week)

    def year_week_to_season_week(self, year_week: int) -> int:
        return year_week_to_season_week(year_week)

    def build_registry(self) -> SeasonRegistryResponse:
        seasons = self.list_seasons()
        return SeasonRegistryResponse(
            start_season=seasons[0].label,
            end_season=seasons[-1].label,
            season_count=len(seasons),
            week_count=DEFAULT_WEEKS_PER_SEASON,
            season_week_1_year_week=SEASON_WEEK_1_YEAR_WEEK,
            seasons=seasons,
        )


def _season_label(start_year: int) -> str:
    return season_label_from_start_year(start_year)
