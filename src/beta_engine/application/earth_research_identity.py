"""Typed, content-addressed mapping from source observations to Earth identities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


IDENTITY_RESOLUTION_SCHEMA_V1 = "earth_observation_identity_resolutions.v1"
IDENTITY_RESOLUTION_MANIFEST_V1 = "earth_observation_identity_manifest.v1"


def _valid_code(code: str) -> bool:
    return len(code) == 3 and code.isascii() and code.isalpha() and code.isupper()


class EarthObservationIdentityResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=3)
    source_id: str = Field(min_length=1)
    source_entity: str = Field(min_length=1)
    source_page: int | None = Field(default=None, ge=1)

    status: Literal["direct", "aggregate_member", "manual_review", "unresolved"]
    method: Literal[
        "explicit_override",
        "exact_normalized_name",
        "aggregate_group",
        "manual_review",
        "unresolved",
    ]
    confidence: Literal["low", "medium", "high"]
    earth_country_code: str | None = Field(default=None, min_length=3, max_length=3)
    candidate_earth_codes: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_resolution(self) -> "EarthObservationIdentityResolution":
        if self.earth_country_code is not None and not _valid_code(self.earth_country_code):
            raise ValueError("earth_country_code must be a three-letter uppercase ASCII code")
        if any(not _valid_code(code) for code in self.candidate_earth_codes):
            raise ValueError("candidate_earth_codes must contain three-letter uppercase ASCII codes")
        if len(set(self.candidate_earth_codes)) != len(self.candidate_earth_codes):
            raise ValueError("candidate_earth_codes must be unique")

        if self.status == "direct":
            if self.earth_country_code is None:
                raise ValueError("direct resolution requires earth_country_code")
            if self.method not in {"explicit_override", "exact_normalized_name"}:
                raise ValueError("direct resolution requires explicit/name-match method")
        elif self.status == "aggregate_member":
            if self.earth_country_code is None or self.method != "aggregate_group":
                raise ValueError("aggregate member requires Earth target and aggregate_group method")
        elif self.status == "manual_review":
            if self.earth_country_code is not None or self.method != "manual_review":
                raise ValueError("manual review must not claim a resolved Earth target")
        elif self.status == "unresolved":
            if self.earth_country_code is not None or self.method != "unresolved":
                raise ValueError("unresolved mapping must not claim an Earth target")
        return self


class EarthObservationIdentityResolutionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["earth_observation_identity_resolutions.v1"] = (
        IDENTITY_RESOLUTION_SCHEMA_V1
    )
    resolution_set_id: str = Field(
        min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    source_id: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)
    mapping_algorithm_id: str = Field(min_length=1)
    input_dataset_sha256s: dict[str, str] = Field(min_length=1)
    override_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    earth_identity_catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolutions: list[EarthObservationIdentityResolution] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_set(self) -> "EarthObservationIdentityResolutionSet":
        for dataset_id, digest in self.input_dataset_sha256s.items():
            if not dataset_id.strip():
                raise ValueError("input dataset IDs must not be blank")
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("input dataset SHA-256 must be lowercase hex")
        seen: set[str] = set()
        for resolution in self.resolutions:
            if resolution.source_id != self.source_id:
                raise ValueError("resolution source_id must match its resolution set")
            if resolution.observation_id in seen:
                raise ValueError(f"duplicate identity resolution {resolution.observation_id!r}")
            seen.add(resolution.observation_id)
        return self


class EarthObservationIdentityManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["earth_observation_identity_manifest.v1"] = (
        IDENTITY_RESOLUTION_MANIFEST_V1
    )
    resolution_set_id: str = Field(
        min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    source_id: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    record_count: int = Field(ge=1)
    generated_by: str = Field(min_length=1)

    @model_validator(mode="after")
    def safe_relative_path(self) -> "EarthObservationIdentityManifest":
        path = self.relative_path.replace("\\", "/")
        if path.startswith("/") or any(part in ("", ".", "..") for part in path.split("/")):
            raise ValueError("relative_path must be a safe non-empty relative path")
        return self


def identity_resolution_semantic_bytes(
    resolution_set: EarthObservationIdentityResolutionSet,
) -> bytes:
    return json.dumps(
        resolution_set.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def identity_resolution_sha256(
    resolution_set: EarthObservationIdentityResolutionSet,
) -> str:
    return hashlib.sha256(identity_resolution_semantic_bytes(resolution_set)).hexdigest()


def load_identity_resolution_set(path: Path) -> EarthObservationIdentityResolutionSet:
    return EarthObservationIdentityResolutionSet.model_validate_json(
        path.read_text(encoding="utf-8")
    )
