from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

TOTAL_REGISTRY_SEASONS = 40
REGISTRY_START_YEAR = 2000
REGISTRY_END_YEAR = REGISTRY_START_YEAR + TOTAL_REGISTRY_SEASONS - 1
SIMPLIFIED_YEAR_WEEK_COUNT = 61
SEASON_WEEK_1_YEAR_WEEK = 37


class SeasonRegistryEntry(BaseModel):
    season_start_year: int
    label: str
    season_index: int = Field(description="0-based season index within the deterministic registry")
    week_count: int = SIMPLIFIED_YEAR_WEEK_COUNT
    season_week_start: int = 1
    season_week_end: int = SIMPLIFIED_YEAR_WEEK_COUNT
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
    """Read-only deterministic season registry using the simplified 61-week year model."""

    def list_seasons(self) -> list[SeasonRegistryEntry]:
        seasons: list[SeasonRegistryEntry] = []
        for season_index, start_year in enumerate(range(REGISTRY_START_YEAR, REGISTRY_END_YEAR + 1)):
            label = _season_label(start_year)
            seasons.append(
                SeasonRegistryEntry(
                    season_start_year=start_year,
                    label=label,
                    season_index=season_index,
                    year_week_end=self.season_week_to_year_week(SIMPLIFIED_YEAR_WEEK_COUNT),
                )
            )
        return seasons

    def get_season(self, *, label: str | None = None, start_year: int | None = None) -> SeasonRegistryEntry | None:
        if label is None and start_year is None:
            raise ValueError("label or start_year is required")
        for entry in self.list_seasons():
            if label is not None and entry.label == label:
                return entry
            if start_year is not None and entry.season_start_year == start_year:
                return entry
        return None

    def season_week_to_year_week(self, season_week: int) -> int:
        if not 1 <= season_week <= SIMPLIFIED_YEAR_WEEK_COUNT:
            raise ValueError("season_week must be between 1 and 61")
        return ((SEASON_WEEK_1_YEAR_WEEK + season_week - 2) % SIMPLIFIED_YEAR_WEEK_COUNT) + 1

    def year_week_to_season_week(self, year_week: int) -> int:
        if not 1 <= year_week <= SIMPLIFIED_YEAR_WEEK_COUNT:
            raise ValueError("year_week must be between 1 and 61")
        return ((year_week - SEASON_WEEK_1_YEAR_WEEK) % SIMPLIFIED_YEAR_WEEK_COUNT) + 1

    def build_registry(self) -> SeasonRegistryResponse:
        seasons = self.list_seasons()
        return SeasonRegistryResponse(
            start_season=seasons[0].label,
            end_season=seasons[-1].label,
            season_count=len(seasons),
            week_count=SIMPLIFIED_YEAR_WEEK_COUNT,
            season_week_1_year_week=SEASON_WEEK_1_YEAR_WEEK,
            seasons=seasons,
        )


def _season_label(start_year: int) -> str:
    return f"{start_year}/{(start_year + 1) % 100:02d}"
