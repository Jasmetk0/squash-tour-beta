"""Canonical research-observation contracts for Earth sport calibration.

These models describe extracted/source facts only. They do not author country
ratings and they are deliberately separate from runtime simulation state.
"""
from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


OBSERVATION_SCHEMA_V2 = "earth_source_observations.v2"
OBSERVATION_MANIFEST_SCHEMA_V1 = "earth_source_observations_manifest.v1"


class EarthObservation(BaseModel):
    """One normalized source fact with explicit measurement semantics."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=3)
    source_id: str = Field(min_length=1)
    source_entity: str = Field(min_length=1)
    earth_country_code: str | None = Field(default=None, min_length=3, max_length=3)
    historical_entity: str | None = None

    observation_year: int | None = Field(default=None, ge=1800, le=2026)
    period_start_year: int | None = Field(default=None, ge=1800, le=2026)
    period_end_year: int | None = Field(default=None, ge=1800, le=2026)

    measurement_type: str = Field(min_length=1)
    sex_scope: Literal["male", "female", "mixed", "unknown", "not_applicable"] = "unknown"
    age_scope: str | None = None
    competition_scope: str | None = None

    numeric_value: float | None = None
    text_value: str | None = None
    unit: str = Field(min_length=1)

    collection_method: Literal[
        "administrative_registry",
        "survey",
        "published_table",
        "statistically_processed",
        "modelled_source_estimate",
        "mixed",
        "unknown",
    ] = "unknown"
    coverage_scope: Literal[
        "national",
        "association",
        "territory",
        "regional",
        "partial",
        "unknown",
    ] = "unknown"
    comparability_group: str | None = None
    cross_country_comparable: bool = False

    is_direct_observation: bool
    is_statistically_modelled: bool = False

    territory_mapping_method: str | None = None
    territory_weight: float | None = Field(default=None, gt=0, le=1)

    source_page: int | None = Field(default=None, ge=1)
    source_locator: str | None = None
    definition_notes: str = Field(min_length=1)
    quality_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_semantics(self) -> "EarthObservation":
        if self.earth_country_code is not None:
            code = self.earth_country_code
            if not code.isascii() or not code.isalpha() or not code.isupper():
                raise ValueError("earth_country_code must be a three-letter uppercase ASCII code")
        numeric = self.numeric_value is not None
        textual = self.text_value is not None
        if numeric == textual:
            raise ValueError("exactly one of numeric_value or text_value must be provided")
        if numeric and not math.isfinite(self.numeric_value):
            raise ValueError("numeric_value must be finite")
        if textual and not self.text_value.strip():
            raise ValueError("text_value must not be blank")
        if self.period_start_year is not None or self.period_end_year is not None:
            if self.period_start_year is None or self.period_end_year is None:
                raise ValueError("period_start_year and period_end_year must be provided together")
            if self.period_start_year > self.period_end_year:
                raise ValueError("observation period must be ordered")
        if self.observation_year is not None and self.period_start_year is not None:
            raise ValueError("use either observation_year or a period, not both")
        if self.territory_weight is not None and not self.territory_mapping_method:
            raise ValueError("territory_weight requires territory_mapping_method")
        if len(set(self.quality_flags)) != len(self.quality_flags):
            raise ValueError("quality_flags must be unique")
        return self


class EarthObservationDataset(BaseModel):
    """A reproducible normalized dataset derived from one catalogued source."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["earth_source_observations.v2"] = OBSERVATION_SCHEMA_V2
    dataset_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    source_id: str = Field(min_length=1)
    source_url: str = Field(pattern=r"^https://")
    source_document_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    generated_by: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    limitations: str = Field(min_length=1)
    observations: list[EarthObservation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset(self) -> "EarthObservationDataset":
        seen: set[str] = set()
        prefix = f"{self.dataset_id}#"
        for observation in self.observations:
            if observation.source_id != self.source_id:
                raise ValueError("every observation source_id must match the dataset source_id")
            if not observation.observation_id.startswith(prefix):
                raise ValueError("observation_id must be namespaced by dataset_id using '<dataset_id>#'")
            if observation.observation_id in seen:
                raise ValueError(f"duplicate observation_id {observation.observation_id!r}")
            seen.add(observation.observation_id)
        return self


class EarthObservationDatasetManifest(BaseModel):
    """Content-addressed reference to a normalized observation dataset."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["earth_source_observations_manifest.v1"] = OBSERVATION_MANIFEST_SCHEMA_V1
    dataset_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    source_id: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=1)
    source_document_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    generated_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def safe_relative_path(self) -> "EarthObservationDatasetManifest":
        path = self.relative_path.replace("\\", "/")
        if path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError("relative_path must be a safe non-empty relative path")
        return self


def observation_dataset_id(observation_id: str) -> str:
    """Return the manifest dataset namespace from '<dataset_id>#<local-id>'."""

    dataset_id, separator, local_id = observation_id.partition("#")
    if not separator or not dataset_id or not local_id:
        raise ValueError("observation_id must use '<dataset_id>#<local-id>'")
    return dataset_id
