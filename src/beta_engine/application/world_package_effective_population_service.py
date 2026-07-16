"""Read-only effective population diagnostics for World Package countries."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.domain.countries.population_resolver import PopulationSourceType, resolve_effective_population


@dataclass(frozen=True)
class WorldPackageCountryEffectivePopulationResult:
    world_id: str
    world_name: str
    type: str
    source: str
    read_only: bool
    source_path: str
    country_code: str
    country_name: str
    requested_year: int
    effective_population: int
    source_year: int | None
    source_type: PopulationSourceType
    is_estimated: bool
    default_population_year: int | None
    default_population: int | None
    legacy_population: int
    population_by_year_count: int
    usable_population_by_year_count: int


@dataclass(slots=True)
class WorldPackageEffectivePopulationService:
    """Resolve package-scoped country population diagnostics without mutating config."""

    countries_service: WorldPackageCountriesService

    def get_effective_population(
        self,
        *,
        world_id: str,
        country_code: str,
        requested_year: int,
    ) -> WorldPackageCountryEffectivePopulationResult | None:
        countries_result = self.countries_service.get_countries(world_id)
        if countries_result is None:
            return None

        normalized_country_code = country_code.strip().upper()
        country = next((item for item in countries_result.countries if item.code == normalized_country_code), None)
        if country is None:
            return None

        resolved = resolve_effective_population(country, requested_year)
        population_by_year = country.population_by_year or {}
        return WorldPackageCountryEffectivePopulationResult(
            world_id=countries_result.world_id,
            world_name=countries_result.world_name,
            type=countries_result.type,
            source=countries_result.source,
            read_only=True,
            source_path=countries_result.source_path,
            country_code=country.code,
            country_name=country.name,
            requested_year=resolved.requested_year,
            effective_population=resolved.effective_population,
            source_year=resolved.source_year,
            source_type=resolved.source_type,
            is_estimated=resolved.is_estimated,
            default_population_year=country.default_population_year,
            default_population=country.default_population,
            legacy_population=country.population,
            population_by_year_count=len(population_by_year),
            usable_population_by_year_count=sum(1 for value in population_by_year.values() if value is not None),
        )
