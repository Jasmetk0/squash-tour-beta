"""Canonical, sporting-model-neutral Package documents and Run-owned snapshots."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


TECHNICAL_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
SHA256_HEX_PATTERN = r"^[0-9a-f]{64}$"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def entity_content_fingerprint(
    *,
    entity_kind: str,
    entity_schema_version: int,
    scope: str,
    payload: dict[str, Any],
    references: tuple["SourceReference", ...],
) -> str:
    """Hash all technical content fields, excluding source identity/provenance."""
    return canonical_hash(
        {
            "entity_kind": entity_kind,
            "entity_schema_version": entity_schema_version,
            "scope": scope,
            "payload": payload,
            "references": [item.model_dump(mode="json") for item in references],
        }
    )


class PackageType(str, Enum):
    WORLD = "World"
    CATEGORY = "Category"
    SERIES = "Series"
    CALENDAR = "Calendar"
    SETUP = "Setup"


class SourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_package_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    source_entity_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    expected_entity_kind: str = Field(min_length=1)
    minimum_schema_version: int = Field(default=1, ge=1)


class PackageEntity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_entity_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    entity_kind: str = Field(min_length=1)
    entity_schema_version: int = Field(default=1, ge=1)
    scope: str = Field(min_length=1)
    payload: dict[str, Any]
    references: tuple[SourceReference, ...] = ()
    valid: bool = True

    @property
    def fingerprint(self) -> str:
        return entity_content_fingerprint(
            entity_kind=self.entity_kind,
            entity_schema_version=self.entity_schema_version,
            scope=self.scope,
            payload=self.payload,
            references=self.references,
        )


class CanonicalPackageDocument(BaseModel):
    """Immutable reviewed input. Setup children are frozen full documents."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    package_type: PackageType
    package_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    source_version: int = Field(ge=1)
    provenance: dict[str, Any] = Field(default_factory=dict)
    explicit_scope: tuple[str, ...]
    entities: tuple[PackageEntity, ...] = ()
    children: tuple["CanonicalPackageDocument", ...] = ()
    parent_source_fingerprint: str | None = Field(
        default=None, pattern=SHA256_HEX_PATTERN
    )

    @model_validator(mode="after")
    def validate_shape(self):
        if self.package_type == PackageType.SETUP:
            if self.entities or any(
                c.package_type == PackageType.SETUP for c in self.children
            ):
                raise ValueError(
                    "Setup contains only non-Setup child Package documents"
                )
            child_ids = [child.package_id for child in self.children]
            if self.package_id in child_ids or len(child_ids) != len(set(child_ids)):
                raise ValueError("Setup and child package_id values must be unique")
        elif self.children:
            raise ValueError("Only Setup Packages may contain child documents")
        ids = [e.source_entity_id for e in self.entities]
        if len(ids) != len(set(ids)):
            raise ValueError("Package source entity identities must be unique")
        return self

    @property
    def source_fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))

    def leaf_documents(self) -> tuple["CanonicalPackageDocument", ...]:
        return self.children if self.package_type == PackageType.SETUP else (self,)


class RunPackageEntity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_local_id: int = Field(ge=1)
    source_package_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    source_package_version: int = Field(ge=1)
    source_package_fingerprint: str = Field(pattern=SHA256_HEX_PATTERN)
    source_entity_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    entity_kind: str = Field(min_length=1)
    entity_schema_version: int = Field(default=1, ge=1)
    scope: str = Field(min_length=1)
    payload: dict[str, Any]
    source_baseline_fingerprint: str = Field(pattern=SHA256_HEX_PATTERN)
    references: tuple[SourceReference, ...] = ()
    provenance: Literal["package", "manual"] = "package"

    @property
    def content_fingerprint(self) -> str:
        return entity_content_fingerprint(
            entity_kind=self.entity_kind,
            entity_schema_version=self.entity_schema_version,
            scope=self.scope,
            payload=self.payload,
            references=self.references,
        )


class AppliedPackageVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    package_type: PackageType
    package_id: str = Field(pattern=TECHNICAL_ID_PATTERN)
    source_version: int = Field(ge=1)
    source_fingerprint: str = Field(pattern=SHA256_HEX_PATTERN)
    parent_source_fingerprint: str | None = Field(
        default=None, pattern=SHA256_HEX_PATTERN
    )
    document_explicit_scope: tuple[str, ...] = Field(
        default=(),
        validation_alias=AliasChoices("document_explicit_scope", "applied_scope"),
    )
    applied_entity_ids: tuple[str, ...] = ()
    conflict_resolutions: dict[str, Literal["keep_run", "use_source"]] = Field(
        default_factory=dict
    )
    frozen_child_versions: tuple[str, ...] = ()
    provenance: dict[str, Any]


class RunPackageState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    run_id: str
    branch_id: str
    entities: tuple[RunPackageEntity, ...] = ()
    package_versions: tuple[AppliedPackageVersion, ...] = ()

    @model_validator(mode="after")
    def validate_identity(self):
        local = [e.run_local_id for e in self.entities]
        source = [(e.source_package_id, e.source_entity_id) for e in self.entities]
        if len(local) != len(set(local)) or len(source) != len(set(source)):
            raise ValueError("Run Package identity mapping is duplicated")
        package_types: dict[str, PackageType] = {}
        version_by_identity: dict[tuple[str, int], AppliedPackageVersion] = {}
        for version in self.package_versions:
            version_identity = (version.package_id, version.source_version)
            if version_identity in version_by_identity:
                raise ValueError("Run Package version identity is duplicated")
            version_by_identity[version_identity] = version
            previous = package_types.setdefault(
                version.package_id, version.package_type
            )
            if previous != version.package_type:
                raise ValueError("A package_id cannot change package_type")
        by_source = {
            key: entity for key, entity in zip(source, self.entities, strict=True)
        }
        for entity in self.entities:
            source_version = version_by_identity.get(
                (entity.source_package_id, entity.source_package_version)
            )
            if (
                source_version is None
                or source_version.source_fingerprint
                != entity.source_package_fingerprint
            ):
                raise ValueError(
                    "Run Package entity source baseline has no matching Package version"
                )
            for ref in entity.references:
                target = by_source.get((ref.source_package_id, ref.source_entity_id))
                if target is not None and (
                    target.entity_kind != ref.expected_entity_kind
                    or target.entity_schema_version < ref.minimum_schema_version
                ):
                    raise ValueError(
                        "Resolved source reference has an incompatible kind or schema"
                    )
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class PackagePreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    document: CanonicalPackageDocument
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    draft_version: int
    current_state_fingerprint: str | None
    additions: tuple[str, ...]
    unchanged: tuple[str, ...]
    updates: tuple[str, ...]
    not_included: tuple[str, ...]
    unresolved: tuple[str, ...]
    automatically_resolvable: tuple[str, ...]
    invalid: tuple[str, ...]
    conflicts: tuple[str, ...]

    @property
    def preview_fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))
