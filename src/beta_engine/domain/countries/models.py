"""Country domain models for config-driven world generation."""

from __future__ import annotations

import math
from typing import Annotated, Any, Self, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator, model_serializer


from beta_engine.domain.countries.rating_history import (
    CountryRatingHistory, GAME_ATTRIBUTE_NAMES, LEGACY_RATING_SCALE, RATING_SCALE_V2, validate_rating_v2,
)

def _validate_country_rating(value: Any) -> float:
    """Accept only finite JSON-style numbers on the inclusive V1 scale."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("country rating must be a numeric value")
    rating = float(value)
    if not math.isfinite(rating):
        raise ValueError("country rating must be finite")
    if not 1 <= rating <= 5:
        raise ValueError("country rating must be between 1 and 5 inclusive")
    return rating


CountrySimFactor = Annotated[float, BeforeValidator(_validate_country_rating)]


def _validate_versioned_rating(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("country rating must be numeric")
    if not math.isfinite(value) or not 1 <= value <= 10:
        raise ValueError("country rating must be finite and between 1 and 10")
    return float(value)


VersionedCountrySimFactor = Annotated[float, BeforeValidator(_validate_versioned_rating)]


class Country(BaseModel):
    """Canonical editable country profile used by deterministic simulation.

    V1 deliberately separates factual country data from six authored squash-system
    ratings. Legacy country payloads are accepted at the loading boundary so
    existing World Packages remain readable, but legacy factor names are not part
    of serialized/public country state. ``style_dna`` survives only as an always-
    empty read compatibility shim and has no authored/runtime influence.
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
    timezone_area: str | None = None
    notes: str | None = None

    rating_scale: Literal["country_ratings_1_5.v1", "country_ratings_1_10.v2"] = LEGACY_RATING_SCALE
    rating_history: CountryRatingHistory | None = None
    rating_effective_year: int | None = None

    # The scale is explicit; a missing version always means legacy 1..5.
    squash_popularity: VersionedCountrySimFactor
    squash_access: VersionedCountrySimFactor
    development_quality: VersionedCountrySimFactor
    competition_quality: VersionedCountrySimFactor
    elite_support: VersionedCountrySimFactor
    squash_tradition: VersionedCountrySimFactor

    @field_validator(*GAME_ATTRIBUTE_NAMES)
    @classmethod
    def validate_scaled_field(cls, value: float, info) -> float:
        validator = validate_rating_v2 if info.data.get("rating_scale") == RATING_SCALE_V2 else _validate_country_rating
        return validator(value)

    @model_validator(mode="after")
    def validate_rating_version(self) -> Self:
        validator = validate_rating_v2 if self.rating_scale == RATING_SCALE_V2 else _validate_country_rating
        for name in GAME_ATTRIBUTE_NAMES:
            validator(getattr(self, name))
        if self.rating_scale == RATING_SCALE_V2 and self.court_count is not None:
            raise ValueError("Court Count is deferred beyond pre-alpha in new-scale countries")
        if self.rating_history is not None:
            if self.rating_scale != RATING_SCALE_V2:
                raise ValueError("historical ratings require the explicit 1..10 scale")
            year = self.rating_effective_year if self.rating_effective_year is not None else self.rating_history.reference_year
            _, entry = self.rating_history.resolve(year)
            if any(getattr(self, name) != entry.ratings[name].value for name in GAME_ATTRIBUTE_NAMES):
                raise ValueError("scalar ratings must match the selected history year")
        elif self.rating_effective_year is not None:
            raise ValueError("effective rating year requires a history")
        return self

    @model_serializer(mode="wrap")
    def serialize_rating_version(self, handler):
        payload = handler(self)
        # Exact legacy payloads remain unchanged, including their snapshot hashes.
        if self.rating_scale == LEGACY_RATING_SCALE:
            for name in ("rating_scale", "rating_history", "rating_effective_year"):
                payload.pop(name, None)
        return payload

    def at_rating_year(self, year: int) -> Self:
        if self.rating_history is None:
            return self
        _, entry = self.rating_history.resolve(year)
        # Values come from the already validated history, not untrusted input.
        return self.model_copy(update={
            **{name: entry.ratings[name].value for name in GAME_ATTRIBUTE_NAMES},
            "rating_effective_year": year,
        })

    @property
    def rating_maximum(self) -> int:
        return 10 if self.rating_scale == RATING_SCALE_V2 else 5

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_factor_names(cls, value: Any) -> Any:
        """Read valid legacy country payloads without keeping the old model alive.

        The mapping is intentionally simple and deterministic. It is a storage
        migration bridge, not a claim that the old concepts are semantically
        identical to the new V1 attributes. It only supplies a V1 field when an
        actual legacy source exists; missing authored V1 fields are never silently
        invented, and malformed/out-of-range legacy ratings remain invalid.
        """

        if not isinstance(value, dict):
            return value
        data = dict(value)
        missing = object()

        def legacy_rating(*names: str) -> object:
            for name in names:
                if name not in data:
                    continue
                raw = data[name]
                try:
                    return _validate_country_rating(raw)
                except (TypeError, ValueError):
                    # Preserve malformed input so the canonical 1..5 field
                    # validation rejects it instead of manufacturing a default.
                    return raw
            return missing

        mappings: tuple[tuple[str, tuple[str, ...]], ...] = (
            ("squash_access", ("wealth_support",)),
            ("development_quality", ("system_quality",)),
            ("competition_quality", ("competition_density", "system_quality")),
            ("elite_support", ("federation_quality", "wealth_support")),
        )
        for target, sources in mappings:
            if target in data:
                continue
            migrated = legacy_rating(*sources)
            if migrated is not missing:
                data[target] = migrated

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

    @field_validator("travel_region", "timezone_area", mode="before")
    @classmethod
    def normalize_geography_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_factor(self, value: float) -> float:
        return (value - 1) / (self.rating_maximum - 1)

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

    @property
    def style_dna(self) -> dict[str, float]:
        """Neutral legacy read shim; Country V1 has no national style DNA."""

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
