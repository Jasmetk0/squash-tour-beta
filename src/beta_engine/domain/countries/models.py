"""Country domain models for config-driven world generation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Country(BaseModel):
    """Country configuration used by talent generation."""

    code: str = Field(min_length=3, max_length=3)
    name: str
    region: str
    population: int = Field(gt=0)
    squash_popularity: float = Field(ge=0.0, le=1.0)
    infrastructure_level: float = Field(ge=0.0, le=1.0)
    development_pipeline_quality: float = Field(ge=0.0, le=1.0)
    elite_system_strength: float = Field(ge=0.0, le=1.0)
    historical_tradition: float = Field(ge=0.0, le=1.0)
    travel_region: str
    travel_affinity: dict[str, float] = Field(default_factory=dict)


class CountriesConfig(BaseModel):
    """Top-level country config payload."""

    countries: list[Country]
