"""Country domain models for config-driven world generation."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CountrySimFactor = Literal[1, 2, 3, 4, 5]


class Country(BaseModel):
    """Canonical editable country profile used by deterministic simulation.

    V1 deliberately separates factual country data from six authored squash-system
    ratings. Legacy country payloads are accepted at the loading boundary so
    existing World Packages remain readable, but legacy factor names are not part
    of the serialized/public country model.
    """

    model_config = ConfigDict(extra="forbid")

    # Identity / factual world data.
    code: str = Field(min_length=3, max_length=3)
    name: str
    flag_asset: str | None = None
    region: str
    population: int = Field(gt=0)
    area_km2: int | None = Field(default=None, gt=0)
    default_population_year: int | None = Field(default=None)
    default_population: int | None = Field(default=None, gt=0)
    population_by_year: dict[int, int | None] | None = None
    court_count: int | None = Field(default=None, ge=0)
    travel_region: str | None = None
    notes: str | None = None

    # Country Game Attributes V1. All six are authored integer ratings 1..5.
    squash_popularity: CountrySimFactor
    squash_access: CountrySimFactor
    development_quality: CountrySimFactor
    competition_quality: CountrySimFactor
    elite_support: CountrySimFactor
    squash_tradition: CountrySimFactor

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_factor_names(cls, value: Any) -> Any:
        """Read valid legacy country payloads without keeping the old model alive.

        The mapping is intentionally simple and deterministic. It is a storage
        migration bridge, not a claim that the old concepts are semantically
        identical to the new V1 attributes. Invalid legacy ratings stay invalid
        instead of being silently clamped into the authored 1..5 contract.
        """

        if not isinstance(value, dict):
            return value
        data = dict(value)

        def legacy_rating(name: str, fallback: int = 3) -> int:
            raw = data.get(name, fallback)
            try:
                return int(round(float(raw)))
            except (TypeError, ValueError):
                return fallback

        data.setdefault("squash_access", legacy_rating("wealth_support"))
        data.setdefault("development_quality", legacy_rating("system_quality"))
        data.setdefault(
            "competition_quality",
            legacy_rating("competition_density", legacy_rating("system_quality")),
        )
        data.setdefault(
            "elite_support",
            legacy_rating("federation_quality", legacy_rating("wealth_support")),
        )

        # These fields belonged to the superseded country model. style_dna is
        # explicitly deferred beyond V1 rather than being silently retained.
        for legacy_name in (
            "wealth_support",
            "system_quality",
            "competition_density",
            "federation_quality",
            "style_dna",
        ):
            data.pop(legacy_name, None)
        return data

    @field_validator("default_population_year")
    @classmethod
    def validate_default_population_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value != 2020:
            raise ValueError("default_population_year must be 2020 when provided")
        return value

    @field_validator("population_by_year")
    @classmethod
    def validate_population_by_year(cls, value: dict[int, int | None] | None) -> dict[int, int | None] | None:
        if value is None:
            return None
        normalized: dict[int, int | None] = {}
        for year, population in value.items():
            year_int = int(year)
            if not 1955 <= year_int <= 2050:
                raise ValueError("population_by_year years must be between 1955 and 2050")
            if population is not None and population <= 0:
                raise ValueError("population_by_year values must be positive integers or null")
            normalized[year_int] = population
        return normalized

    @model_validator(mode="after")
    def apply_population_defaults(self) -> Self:
        """Keep scalar/legacy population callers usable during package migration."""

        if self.default_population_year is None and self.default_population is not None:
            self.default_population_year = 2020
        return self

    @field_validator("travel_region", mode="before")
    @classmethod
    def normalize_travel_region(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_factor(value: int) -> float:
        return (value - 1) / 4.0

    @property
    def squash_popularity_norm(self) -> float:
        return self._normalize_factor(self.squash_popularity)

    @property
    def squash_access_norm(self) -> float:
        return self._normalize_factor(self.squash_access)

    @property
    def development_quality_norm(self) -> float:
        return self._normalize_factor(self.development_quality)

    @property
    def competition_quality_norm(self) -> float:
        return self._normalize_factor(self.competition_quality)

    @property
    def elite_support_norm(self) -> float:
        return self._normalize_factor(self.elite_support)

    @property
    def squash_tradition_norm(self) -> float:
        return self._normalize_factor(self.squash_tradition)

    @property
    def effective_travel_region(self) -> str:
        """Region used by travel/entry calculations when no explicit override is authored."""

        return self.travel_region or self.region

    # Compatibility properties for code paths that have not yet been deleted.
    # They are derived from V1 state and are intentionally absent from model_dump.
    @property
    def wealth_support(self) -> int:
        return self.elite_support

    @property
    def system_quality(self) -> int:
        return self.development_quality

    @property
    def competition_density(self) -> float:
        return float(self.competition_quality)

    @property
    def federation_quality(self) -> float:
        return float(self.elite_support)

    @property
    def style_dna(self) -> dict[str, float]:
        return {}

    @property
    def infrastructure_level(self) -> float:
        return self.squash_access_norm

    @property
    def development_pipeline_quality(self) -> float:
        return self.development_quality_norm

    @property
    def elite_system_strength(self) -> float:
        return min(
            1.0,
            self.development_quality_norm * 0.45
            + self.competition_quality_norm * 0.25
            + self.elite_support_norm * 0.20
            + self.squash_tradition_norm * 0.10,
        )

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
