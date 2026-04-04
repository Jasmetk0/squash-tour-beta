"""Typed models for deterministic annual talent-class planning."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class ManualPlayerProfileTier(str, Enum):
    STRONG = "strong"
    ELITE = "elite"
    SPECIAL = "special"
    GENERATIONAL = "generational"


class ManualPlayerAttributeOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technique: int | None = Field(default=None, ge=20, le=99)
    movement: int | None = Field(default=None, ge=20, le=99)
    physical: int | None = Field(default=None, ge=20, le=99)
    mental: int | None = Field(default=None, ge=20, le=99)
    consistency: int | None = Field(default=None, ge=20, le=99)
    clutch: int | None = Field(default=None, ge=20, le=99)
    recovery: int | None = Field(default=None, ge=20, le=99)


class ManualPlayerHiddenTraitOverrides(BaseModel):
    model_config = ConfigDict(extra="forbid")

    potential_ceiling: int | None = Field(default=None, ge=55, le=99)
    growth_curve: str | None = None
    professionalism: float | None = Field(default=None, ge=0.0, le=1.0)
    ambition: float | None = Field(default=None, ge=0.0, le=1.0)
    travel_tolerance: float | None = Field(default=None, ge=0.0, le=1.0)
    schedule_aggression: float | None = Field(default=None, ge=0.0, le=1.0)
    injury_proneness: float | None = Field(default=None, ge=0.0, le=1.0)
    resilience: float | None = Field(default=None, ge=0.0, le=1.0)


class ManualPlayerOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    override_id: str = Field(min_length=1, max_length=128)
    season: int = Field(ge=1900)
    country_code: str = Field(min_length=3, max_length=3)
    player_name: str = Field(min_length=1, max_length=128)
    player_slug: str | None = Field(default=None, min_length=1, max_length=64)
    player_id: str | None = Field(default=None, min_length=1, max_length=128)
    age: int = Field(ge=15, le=45)
    profile_tier: ManualPlayerProfileTier
    quality_band_override: TalentQualityBand | None = None
    attribute_overrides: ManualPlayerAttributeOverrides | None = None
    hidden_trait_overrides: ManualPlayerHiddenTraitOverrides | None = None
    is_exceptional: bool = False
    enabled: bool = True
    notes: str | None = Field(default=None, max_length=512)

    @field_validator("country_code")
    @classmethod
    def _normalize_country_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != 3:
            raise ValueError("country_code must be 3 letters")
        return cleaned

    @field_validator("override_id", "player_slug", mode="before")
    @classmethod
    def _strip_optional_slug_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("player_name", mode="before")
    @classmethod
    def _strip_player_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("player_name cannot be blank")
        return cleaned


class ManualPlayerOverridesRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overrides: list[ManualPlayerOverride] = Field(default_factory=list)
