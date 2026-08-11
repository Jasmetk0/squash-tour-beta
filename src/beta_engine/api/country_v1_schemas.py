"""Country V1 request/response contracts.

Kept separate from the legacy all-domain schema module so the country migration is
small, reviewable and does not require rewriting unrelated API contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from beta_engine.api.schemas import (
    WorldPackageContinentResponse,
    WorldPackageRegionResponse,
    WorldPackageSummaryResponse,
    WorldPackageTravelRegionResponse,
    WorldPackageValidationResponse,
)
from beta_engine.domain.countries.models import CountrySimFactor


class CountryV1Response(BaseModel):
    code: str
    name: str
    flag_asset: str | None = None
    region: str
    population: int
    area_km2: int | None = None
    default_population_year: int | None = None
    default_population: int | None = None
    population_by_year: dict[int, int | None] | None = None
    court_count: int | None = None
    travel_region: str | None = None
    notes: str | None = None

    squash_popularity: CountrySimFactor
    squash_access: CountrySimFactor
    development_quality: CountrySimFactor
    competition_quality: CountrySimFactor
    elite_support: CountrySimFactor
    squash_tradition: CountrySimFactor


class CountryV1UpsertRequest(CountryV1Response):
    model_config = ConfigDict(extra="forbid")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("code must be exactly 3 characters")
        return normalized

    @field_validator("default_population_year")
    @classmethod
    def validate_default_population_year(cls, value: int | None) -> int | None:
        if value is not None and value != 2020:
            raise ValueError("default_population_year must be 2020 when provided")
        return value

    @field_validator("population_by_year")
    @classmethod
    def validate_population_by_year(
        cls,
        value: dict[int, int | None] | None,
    ) -> dict[int, int | None] | None:
        if value is None:
            return None
        if any(year < 1955 or year > 2050 for year in value):
            raise ValueError("population_by_year years must be between 1955 and 2050")
        if any(population is not None and (isinstance(population, bool) or population <= 0) for population in value.values()):
            raise ValueError("population_by_year values must be positive integers or null")
        return value


class CountriesV1ListResponse(BaseModel):
    countries: list[CountryV1Response] = Field(default_factory=list)


class CountriesV1DatasetResponse(BaseModel):
    dataset_status: str | None = None
    countries: list[CountryV1Response] = Field(default_factory=list)


class WorldPackageCountriesV1Response(BaseModel):
    world_id: str
    world_name: str
    type: str
    source: str
    read_only: bool
    country_count: int
    source_path: str
    countries: list[CountryV1Response] = Field(default_factory=list)


class WorldPackageCountryV1DetailResponse(BaseModel):
    package: WorldPackageSummaryResponse
    country: CountryV1Response
    region: WorldPackageRegionResponse | None = None
    continent: WorldPackageContinentResponse | None = None
    travel_region: WorldPackageTravelRegionResponse | None = None
    source_path: str


class WorldPackageCountryV1UpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    notes: str | None = None
    area_km2: int | None = Field(gt=0)
    region: str = Field(min_length=1)
    travel_region: str | None = None
    court_count: int | None = Field(ge=0)

    squash_popularity: CountrySimFactor
    squash_access: CountrySimFactor
    development_quality: CountrySimFactor
    competition_quality: CountrySimFactor
    elite_support: CountrySimFactor
    squash_tradition: CountrySimFactor

    expected_package_fingerprint: str | None = None


class WorldPackageCountryV1CreateRequest(WorldPackageCountryV1UpdateRequest):
    code: str = Field(pattern=r"^[A-Z]{3}$")
    population_by_year: dict[int, StrictInt]
    expected_package_fingerprint: str

    @field_validator("population_by_year")
    @classmethod
    def validate_population(cls, value: dict[int, int]) -> dict[int, int]:
        if 2020 not in value:
            raise ValueError("population_by_year must contain default year 2020")
        if any(year < 1955 or year > 2050 for year in value):
            raise ValueError("population years must be between 1955 and 2050")
        if any(isinstance(population, bool) or population <= 0 for population in value.values()):
            raise ValueError("population values must be positive integers")
        return value


class WorldPackageCountryV1UpdateResponse(BaseModel):
    country_detail: WorldPackageCountryV1DetailResponse
    package: WorldPackageSummaryResponse
    validation: WorldPackageValidationResponse
