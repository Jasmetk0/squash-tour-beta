"""Pure deterministic weekly 15-year-old intake planning."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, computed_field

from beta_engine.domain.calendar import parse_season_start_year, season_week_to_calendar_position
from beta_engine.domain.calendar.season_weeks import PLAYER_15TH_BIRTHDAY_AGE
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.countries.population_resolver import resolve_effective_population


class WeeklyIntakeCountryAllocation(BaseModel):
    """Read-only country allocation row for a weekly intake preview."""

    model_config = ConfigDict(extra="forbid")

    country_code: str = Field(min_length=3, max_length=3)
    allocated_count: int = Field(ge=0)
    allocation_weight: float = Field(ge=0.0)
    allocation_share: float = Field(ge=0.0, le=1.0)
    effective_population: int | float = Field(ge=0)
    population_source_type: str
    population_source_year: int | None
    is_population_estimated: bool


class WeeklyIntakePlan(BaseModel):
    """Pure weekly intake timing and country allocation preview."""

    model_config = ConfigDict(extra="forbid")

    season: str
    season_start_year: int
    season_week: int = Field(ge=1, le=61)
    calendar_year: int
    year_week: int = Field(ge=1, le=61)
    birth_year: int
    birth_year_week: int = Field(ge=1, le=61)
    intake_age: int = PLAYER_15TH_BIRTHDAY_AGE
    target_intake_count: int = Field(ge=0)
    allocations: list[WeeklyIntakeCountryAllocation]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_allocated(self) -> int:
        return sum(allocation.allocated_count for allocation in self.allocations)


class WeeklyIntakePlanner:
    """Plans weekly 15-year-old intake without generating or persisting players."""

    def plan_weekly_intake(
        self,
        *,
        countries: list[Country],
        season: str | int,
        season_week: int,
        target_intake_count: int,
    ) -> WeeklyIntakePlan:
        if target_intake_count < 0:
            raise ValueError("target_intake_count must be greater than or equal to 0")

        position = season_week_to_calendar_position(season, season_week)
        season_start_year = position.season_start_year
        if season_start_year is None:
            season_start_year = parse_season_start_year(position.season)

        birth_year = position.calendar_year - PLAYER_15TH_BIRTHDAY_AGE
        birth_year_week = position.year_week
        allocations = self._allocate_countries(
            countries=countries,
            population_year=birth_year,
            target_intake_count=target_intake_count,
        )

        return WeeklyIntakePlan(
            season=position.season_label or position.season,
            season_start_year=season_start_year,
            season_week=season_week,
            calendar_year=position.calendar_year,
            year_week=position.year_week,
            birth_year=birth_year,
            birth_year_week=birth_year_week,
            target_intake_count=target_intake_count,
            allocations=allocations,
        )

    def _allocate_countries(
        self,
        *,
        countries: list[Country],
        population_year: int,
        target_intake_count: int,
    ) -> list[WeeklyIntakeCountryAllocation]:
        if not countries or target_intake_count == 0:
            return []

        talent_model = CountryTalentModel()
        rows = []
        for country in sorted(countries, key=lambda item: item.code):
            resolved = resolve_effective_population(country, population_year)
            # V1 country allocation samples from the effective squash-playing
            # pool, not raw national population alone. Popularity and access are
            # the authored inputs to that pool; development quality does not
            # change a person's innate potential.
            weight = max(
                1.0,
                talent_model.effective_squash_pool_weight(country, resolved.effective_population),
            )
            rows.append((country.code, resolved, weight))

        total_weight = sum(weight for _, _, weight in rows)
        if total_weight <= 0.0:
            total_weight = float(len(rows))
            rows = [(code, resolved, 1.0) for code, resolved, _ in rows]

        raw_counts = {
            code: (target_intake_count * weight / total_weight)
            for code, _, weight in rows
        }
        allocated_counts = {code: math.floor(raw_counts[code]) for code, _, _ in rows}
        remaining = target_intake_count - sum(allocated_counts.values())
        remainders = sorted(
            raw_counts.items(),
            key=lambda item: (-(item[1] - math.floor(item[1])), item[0]),
        )
        for index in range(remaining):
            allocated_counts[remainders[index % len(remainders)][0]] += 1

        return [
            WeeklyIntakeCountryAllocation(
                country_code=code,
                allocated_count=allocated_counts[code],
                allocation_weight=weight,
                allocation_share=weight / total_weight,
                effective_population=resolved.effective_population,
                population_source_type=resolved.source_type,
                population_source_year=resolved.source_year,
                is_population_estimated=resolved.is_estimated,
            )
            for code, resolved, weight in rows
        ]
