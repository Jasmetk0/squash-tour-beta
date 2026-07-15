"""Country domain models for config-driven world generation."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CountrySimFactor = Literal[1, 2, 3, 4, 5]


class Country(BaseModel):
    """Canonical editable country profile used by deterministic simulation."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=3)
    name: str
    flag_asset: str | None = None
    region: str
    population: int = Field(gt=0)
    area_km2: int | None = Field(default=None, gt=0)
    default_population_year: int | None = Field(default=None)
    default_population: int | None = Field(default=None, gt=0)
    population_by_year: dict[int, int | None] | None = None

    wealth_support: CountrySimFactor
    squash_popularity: CountrySimFactor
    squash_tradition: CountrySimFactor
    system_quality: CountrySimFactor
    competition_density: float | None = Field(default=None, ge=1.0, le=5.0)
    federation_quality: float | None = Field(default=None, ge=1.0, le=5.0)
    court_count: int | None = Field(default=None, ge=0)
    travel_region: str | None = None
    notes: str | None = None
    style_dna: dict[str, float] = Field(default_factory=dict)

    @field_validator("default_population_year")
    @classmethod
    def validate_default_population_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not 1955 <= value <= 2035:
            raise ValueError("default_population_year must be between 1955 and 2035")
        return value

    @field_validator("population_by_year")
    @classmethod
    def validate_population_by_year(cls, value: dict[int, int | None] | None) -> dict[int, int | None] | None:
        if value is None:
            return None
        normalized: dict[int, int | None] = {}
        for year, population in value.items():
            year_int = int(year)
            if not 1955 <= year_int <= 2035:
                raise ValueError("population_by_year years must be between 1955 and 2035")
            if population is not None and population <= 0:
                raise ValueError("population_by_year values must be positive integers or null")
            normalized[year_int] = population
        return normalized

    @model_validator(mode="after")
    def apply_phase_two_defaults(self) -> Self:
        """Keep old country configs valid while exposing Phase 2 world-editor fields."""

        if self.competition_density is None:
            self.competition_density = 3.0
        if self.federation_quality is None:
            self.federation_quality = float(self.system_quality)
        return self

    @field_validator("travel_region", mode="before")
    @classmethod
    def normalize_travel_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @property
    def effective_travel_region(self) -> str:
        """Region used by travel/entry calculations when no explicit override is authored."""

        return self.travel_region or self.region

    @staticmethod
    def _normalize_factor(value: int) -> float:
        return (value - 1) / 4.0

    @property
    def wealth_support_norm(self) -> float:
        return self._normalize_factor(self.wealth_support)

    @property
    def squash_popularity_norm(self) -> float:
        return self._normalize_factor(self.squash_popularity)

    @property
    def squash_tradition_norm(self) -> float:
        return self._normalize_factor(self.squash_tradition)

    @property
    def system_quality_norm(self) -> float:
        return self._normalize_factor(self.system_quality)

    # Backward-compatible aliases for flows not yet migrated in this slice.
    @property
    def infrastructure_level(self) -> float:
        return self.system_quality_norm

    @property
    def development_pipeline_quality(self) -> float:
        return self.system_quality_norm

    @property
    def elite_system_strength(self) -> float:
        return min(1.0, self.system_quality_norm * 0.7 + self.squash_tradition_norm * 0.3)

    @property
    def historical_tradition(self) -> float:
        return self.squash_tradition_norm

    @property
    def travel_affinity(self) -> dict[str, float]:
        return {}


class CountriesConfig(BaseModel):
    """Top-level country config payload."""

    model_config = ConfigDict(extra="forbid")

    dataset_status: str | None = None
    countries: list[Country]
