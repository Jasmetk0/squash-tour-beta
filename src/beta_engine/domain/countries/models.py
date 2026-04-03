"""Country domain models for config-driven world generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CountrySimFactor = Literal[1, 2, 3, 4, 5]


class Country(BaseModel):
    """Canonical editable country profile used by deterministic simulation."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=3)
    name: str
    flag_asset: str | None = None
    region: str
    population: int = Field(gt=0)

    wealth_support: CountrySimFactor
    squash_popularity: CountrySimFactor
    squash_tradition: CountrySimFactor
    system_quality: CountrySimFactor

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
    def travel_region(self) -> str:
        return self.region

    @property
    def travel_affinity(self) -> dict[str, float]:
        return {}


class CountriesConfig(BaseModel):
    """Top-level country config payload."""

    model_config = ConfigDict(extra="forbid")

    dataset_status: str | None = None
    countries: list[Country]
