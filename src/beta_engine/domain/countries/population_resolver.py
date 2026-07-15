"""Pure effective population resolution for country population timelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from beta_engine.domain.countries.models import Country

MIN_POPULATION_YEAR = 1955
MAX_POPULATION_YEAR = 2035
DEFAULT_POPULATION_YEAR = 2020

PopulationSourceType = Literal[
    "exact_population_year",
    "nearest_population_year",
    "default_population",
    "legacy_population",
]


@dataclass(frozen=True)
class EffectivePopulationResult:
    """Resolved population for a requested year without mutating country storage."""

    requested_year: int
    effective_population: int
    source_year: int | None
    source_type: PopulationSourceType
    is_estimated: bool


def resolve_effective_population(country: Country, requested_year: int) -> EffectivePopulationResult:
    """Resolve country population for ``requested_year`` using authored timeline fallbacks.

    Legacy ``country.population`` has no explicit source year in the country model, so
    legacy fallback reports ``source_year=None`` and marks the value as estimated.
    """

    if not MIN_POPULATION_YEAR <= requested_year <= MAX_POPULATION_YEAR:
        raise ValueError("requested population year must be between 1955 and 2035")

    usable_population_by_year = _usable_population_by_year(country.population_by_year)
    exact_population = usable_population_by_year.get(requested_year)
    if exact_population is not None:
        return EffectivePopulationResult(
            requested_year=requested_year,
            effective_population=exact_population,
            source_year=requested_year,
            source_type="exact_population_year",
            is_estimated=False,
        )

    if usable_population_by_year:
        source_year, effective_population = min(
            usable_population_by_year.items(),
            key=lambda item: (abs(item[0] - requested_year), item[0]),
        )
        return EffectivePopulationResult(
            requested_year=requested_year,
            effective_population=effective_population,
            source_year=source_year,
            source_type="nearest_population_year",
            is_estimated=True,
        )

    if country.default_population is not None:
        return EffectivePopulationResult(
            requested_year=requested_year,
            effective_population=country.default_population,
            source_year=DEFAULT_POPULATION_YEAR,
            source_type="default_population",
            is_estimated=requested_year != DEFAULT_POPULATION_YEAR,
        )

    return EffectivePopulationResult(
        requested_year=requested_year,
        effective_population=country.population,
        source_year=None,
        source_type="legacy_population",
        is_estimated=True,
    )


def _usable_population_by_year(population_by_year: dict[int, int | None] | None) -> dict[int, int]:
    if not population_by_year:
        return {}
    return {year: population for year, population in population_by_year.items() if population is not None}
