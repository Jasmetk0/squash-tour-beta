"""Versioned initial-cohort sampling on an explicit Run year axis.

The historical generator remains the v1 replay path. This opt-in version shares
its individual attribute kernel, but owns its birth dates, cohort weights and
serialized time basis. It is not a lifecycle/adoption or simulation command.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.calendar.run_calendar import (
    RunCalendar,
    validate_calendar_scale,
)
from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    birth_year_for_age_at_calendar_position,
    completed_weeks_at_calendar_position,
)
from beta_engine.domain.countries import Country
from beta_engine.domain.countries.population_resolver import (
    resolve_population_for_calendar_year,
)
from beta_engine.domain.players.initial_pool import (
    STAGE_AGE_RANGES,
    STAGE_WEIGHTS,
    InitialPlayerPoolGenerator,
    InitialPoolGeneratedPlayer,
    InitialPoolMetadata,
    InitialPoolResult,
    initial_pool_effective_population_diagnostics,
)
from beta_engine.domain.run_packages import canonical_hash


class InitialPoolCalendarBasis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["initial_pool_calendar.v1"] = "initial_pool_calendar.v1"
    weeks_per_year: int = Field(gt=0)
    season_start_year_week: int = Field(gt=0)
    start_year: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_scale(self):
        validate_calendar_scale(weeks_per_year=self.weeks_per_year,
                                season_start_year_week=self.season_start_year_week)
        return self

    @classmethod
    def from_run_calendar(cls, calendar: RunCalendar):
        return cls(weeks_per_year=calendar.weeks_per_year,
                   season_start_year_week=calendar.season_start_year_week,
                   start_year=calendar.start_year)

    @property
    def season_label(self) -> str:
        return (str(self.start_year) if self.season_start_year_week == 1
                else f"{self.start_year}/{self.start_year + 1}")


class CalendarInitialPoolPlayer(InitialPoolGeneratedPlayer):
    schema_version: Literal["initial_pool_player.v2"] = "initial_pool_player.v2"
    time_basis: InitialPoolCalendarBasis
    # Signed birth years permit an adult cohort in a Run starting at year zero.
    birth_year: int
    birth_year_week: int = Field(ge=1)
    generation_source: Literal["initial_pool"] = "initial_pool"

    @model_validator(mode="after")
    def validate_calendar_identity(self):
        basis = self.time_basis
        age = age_at_calendar_position(
            birth_year=self.birth_year, birth_year_week=self.birth_year_week,
            calendar_year=basis.start_year, year_week=basis.season_start_year_week,
            weeks_per_calendar_year=basis.weeks_per_year,
        )
        elapsed = completed_weeks_at_calendar_position(
            birth_year=self.birth_year, birth_year_week=self.birth_year_week,
            calendar_year=basis.start_year, year_week=basis.season_start_year_week,
            weeks_per_calendar_year=basis.weeks_per_year,
        )
        if age != self.age_at_generation or age != self.current_age_years:
            raise ValueError("Generated age disagrees with the calendar birth identity")
        if elapsed <= 15 * basis.weeks_per_year:
            raise ValueError("Initial-pool players must be fifteen before opening Week 1")
        if self.created_for_season != basis.season_label:
            raise ValueError("Generated season disagrees with its explicit time basis")
        return self


class CalendarInitialPoolMetadata(InitialPoolMetadata):
    algorithm_version: Literal["calendar_initial_pool.v2"] = "calendar_initial_pool.v2"
    time_basis: InitialPoolCalendarBasis


class CalendarInitialPoolResult(InitialPoolResult):
    players: list[CalendarInitialPoolPlayer]
    metadata: CalendarInitialPoolMetadata


@dataclass(slots=True, kw_only=True)
class CalendarInitialPlayerPoolGenerator(InitialPlayerPoolGenerator):
    time_basis: InitialPoolCalendarBasis
    minimum_age: int = 15
    maximum_age: int = 45

    def __post_init__(self):
        if not 15 <= self.minimum_age <= self.maximum_age <= 45:
            raise ValueError("Calendar initial-pool age range must be within 15–45")
        if self.time_basis.weeks_per_year == 1 and self.maximum_age == 15:
            raise ValueError("A one-week year has no age-15 birthday strictly before opening Week 1")

    @property
    def effective_minimum_age(self) -> int:
        return max(self.minimum_age, 16 if self.time_basis.weeks_per_year == 1 else 15)

    def generate(self, **kwargs) -> CalendarInitialPoolResult:
        # v2 currently creates a fresh preview only. It cannot accept v1 Keep
        # profiles, hand-authored birthdays or silently convert an old identity.
        allowed = {"countries", "seed", "target_pool_size", "country_code", "region",
                   "country_quotas", "naming_policy", "dry_run"}
        if set(kwargs) - allowed:
            raise ValueError("Calendar preview accepts fresh generation conditions only")
        result = super(CalendarInitialPlayerPoolGenerator, self).generate(
            **kwargs, season=self.time_basis.season_label,
            min_age=self.effective_minimum_age, max_age=self.maximum_age,
        )
        return CalendarInitialPoolResult(
            players=result.players, summary=result.summary,
            metadata=CalendarInitialPoolMetadata(
                **result.metadata.model_dump(), time_basis=self.time_basis,
            ),
        )

    def _make_player(self, **values) -> CalendarInitialPoolPlayer:
        player = CalendarInitialPoolPlayer(**values, time_basis=self.time_basis)
        fingerprint = canonical_hash({
            "algorithm_version": "calendar_initial_pool.v2",
            "player": player.model_dump(mode="json", exclude={"generation_fingerprint"}),
        })
        return player.model_copy(update={"generation_fingerprint": fingerprint})

    def _birth_identity(
        self, *, rng: DeterministicRng, age: int, season_start_year: int,
    ) -> tuple[int, int]:
        basis = self.time_basis
        if season_start_year != basis.start_year:
            raise ValueError("Generation year disagrees with its calendar basis")
        birth_rng = rng.branch(SeedScope.SEASON, "calendar_birth_year_week.v1")
        width = basis.weeks_per_year
        if age == 15:
            # Constant memory even for a very long configured year. Sample all
            # weeks except the fifteenth birthday on the opening week itself.
            birth_week = birth_rng.randint(1, width - 1)
            birth_week += birth_week >= basis.season_start_year_week
        else:
            birth_week = birth_rng.randint(1, width)
        birth_year = birth_year_for_age_at_calendar_position(
            age=age, birth_year_week=birth_week, calendar_year=basis.start_year,
            year_week=basis.season_start_year_week, weeks_per_calendar_year=width,
        )
        return birth_year, birth_week

    def _age_weights(self) -> dict[int, Fraction]:
        weights: dict[int, Fraction] = {}
        for stage, weight in STAGE_WEIGHTS:
            low, high = STAGE_AGE_RANGES[stage]
            per_age = Fraction(str(weight)) / (high - low + 1)
            for age in range(max(low, self.effective_minimum_age), min(high, self.maximum_age) + 1):
                weights[age] = weights.get(age, Fraction()) + per_age
        total = sum(weights.values(), Fraction())
        return {age: weight / total for age, weight in sorted(weights.items())}

    def _birth_year_weights(self, season_start_year: int) -> dict[int, float]:
        basis = self.time_basis
        if season_start_year != basis.start_year:
            raise ValueError("Population year disagrees with its calendar basis")
        result: dict[int, Fraction] = {}
        for age, weight in self._age_weights().items():
            earlier = basis.weeks_per_year - basis.season_start_year_week
            same_year = basis.season_start_year_week - (age == 15)
            total = earlier + same_year
            for year, weeks in ((basis.start_year - age - 1, earlier),
                                (basis.start_year - age, same_year)):
                if weeks:
                    result[year] = result.get(year, Fraction()) + weight * Fraction(weeks, total)
        return {year: float(weight) for year, weight in sorted(result.items())}

    def _population_diagnostics(self, country: Country, season_start_year: int):
        result = initial_pool_effective_population_diagnostics(
            country, season_start_year, birth_year_weights=self._birth_year_weights(season_start_year),
            population_resolver=resolve_population_for_calendar_year,
        )
        return result.model_copy(update={"age_min": self.effective_minimum_age,
                                         "age_max": self.maximum_age})

    def _effective_population_quantity(self, country: Country, season_start_year: int) -> float:
        return self._population_diagnostics(country, season_start_year).effective_population_quantity

    def _population_at_year(self, country: Country, year: int):
        return resolve_population_for_calendar_year(country, year)

    def _country_at_year(self, country: Country, year: int) -> Country:
        if country.rating_history is not None and not 1954 <= year <= 2050:
            # Resolve the observation, never clamp the player's date. All
            # authored ratings currently lie in 1955–2026, so these are outside
            # the interpolation interval and use its nearest endpoint.
            source_year = min(country.rating_history.years, key=lambda y: (abs(y - year), y))
            return country.at_rating_year(source_year)
        return country.at_rating_year(year)

    def _population_weighting_metadata(self, season: str, *, diagnostics=None):
        result = super(CalendarInitialPlayerPoolGenerator, self)._population_weighting_metadata(
            season, diagnostics=diagnostics,
        )
        return {**result, "age_min": self.effective_minimum_age, "age_max": self.maximum_age}

    def _fingerprint(self, players, *, season: str, seed: int) -> str:
        return canonical_hash({
            "algorithm_version": "calendar_initial_pool.v2",
            "time_basis": self.time_basis.model_dump(mode="json"),
            "season": season, "seed": seed,
            "players": [player.model_dump(mode="json") for player in players],
        })
