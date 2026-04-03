"""Typed models for deterministic annual talent-class planning."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TalentQualityBand(str, Enum):
    SOLID = "solid_prospect"
    STRONG = "strong_prospect"
    ELITE = "elite_prospect"
    SPECIAL = "special_prospect"
    GENERATIONAL = "generational_talent"


class TalentSeed(BaseModel):
    """Single deterministic future-player seed prepared for later generation slices."""

    model_config = ConfigDict(extra="forbid")

    sequence: int = Field(ge=1)
    seed_value: int
    quality_band: TalentQualityBand


class CountryGenerationBiasProfile(BaseModel):
    """Low-intensity country bias scaffold for style/personality generation."""

    model_config = ConfigDict(extra="forbid")

    professionalism_tendency: float = Field(ge=-0.3, le=0.3)
    technical_vs_physical_lean: float = Field(ge=-0.3, le=0.3)
    mental_sharpness_tendency: float = Field(ge=-0.3, le=0.3)


class CountryTalentAllocation(BaseModel):
    """Deterministic annual talent allocation output for one country."""

    model_config = ConfigDict(extra="forbid")

    country_code: str
    planned_count: int = Field(ge=0)
    quality_weights: dict[TalentQualityBand, float]
    bias_profile: CountryGenerationBiasProfile
    talents: list[TalentSeed]


class AnnualTalentClassPlan(BaseModel):
    """Deterministic annual talent class plan across the configured world."""

    model_config = ConfigDict(extra="forbid")

    year: int
    seed: int
    total_talents: int = Field(ge=0)
    allocations: list[CountryTalentAllocation]
