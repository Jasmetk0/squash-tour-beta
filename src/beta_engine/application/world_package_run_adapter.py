"""Adapt directory-backed source World Packages to canonical Run Package documents."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.world_package_registry_service import (
    WorldPackageRegistryRecord,
    WorldPackageRegistryService,
)
from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.domain.run_packages import (
    CanonicalPackageDocument,
    PackageEntity,
    PackageType,
    RunPackageState,
    canonical_hash,
)
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore

WORLD_METADATA_ENTITY_ID = "world.metadata"
WORLD_METADATA_ENTITY_KIND = "world.metadata.v1"
WORLD_COUNTRY_ENTITY_KIND = "world.country.v1"
WORLD_COUNTRY_SCOPE = "countries"
WORLD_GEOGRAPHY_SCOPE = "geography"

_GEOGRAPHY_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("geography.continents", "continents", "world.geography.continents.v1"),
    ("geography.regions", "regions", "world.geography.regions.v1"),
    ("geography.travel_regions", "travel_regions", "world.geography.travel_regions.v1"),
    ("geography.timezone_areas", "timezone_areas", "world.geography.timezone_areas.v1"),
)


class RunWorldCountryProvenance(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    country_code: str = Field(min_length=3, max_length=3)
    run_local_id: int = Field(ge=1)
    source_package_version: int = Field(ge=1)
    source_package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entity_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunWorldCountryProjection(BaseModel):
    """Typed Run-owned World country view derived only from Run Package state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    package_id: str
    run_id: str
    branch_id: str
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    countries: tuple[Country, ...]
    provenance: tuple[RunWorldCountryProvenance, ...]

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


@dataclass(slots=True)
class WorldPackageRunAdapter:
    registry_service: WorldPackageRegistryService

    def build_document(self, world_id: str) -> CanonicalPackageDocument:
        record = self.registry_service.get_package(world_id)
        if record is None:
            raise KeyError(f"World Package '{world_id}' was not found")
        package_root = self.registry_service.package_dir(record.world_id)
        if package_root is None:
            raise KeyError(f"World Package '{world_id}' storage was not found")

        version = self._source_version(record)
        country_store = WorldPackageCountryStore(package_root)
        countries = tuple(
            sorted(country_store.load_config().countries, key=lambda item: item.code)
        )

        entities: list[PackageEntity] = [
            PackageEntity(
                source_entity_id=WORLD_METADATA_ENTITY_ID,
                entity_kind=WORLD_METADATA_ENTITY_KIND,
                entity_schema_version=1,
                scope="world_metadata",
                payload=self._metadata_payload(record),
            )
        ]
        entities.extend(
            PackageEntity(
                source_entity_id=country.code,
                entity_kind=WORLD_COUNTRY_ENTITY_KIND,
                entity_schema_version=1,
                scope=WORLD_COUNTRY_SCOPE,
                payload=country.model_dump(mode="json"),
            )
            for country in countries
        )
        entities.extend(self._geography_entities(package_root))

        scopes = {"world_metadata", WORLD_COUNTRY_SCOPE}
        if any(entity.scope == WORLD_GEOGRAPHY_SCOPE for entity in entities):
            scopes.add(WORLD_GEOGRAPHY_SCOPE)

        return CanonicalPackageDocument(
            package_type=PackageType.WORLD,
            package_id=record.world_id,
            source_version=version,
            provenance={
                "adapter": "directory_world_package.v1",
                "source_world_id": record.world_id,
                "source_world_version": record.version,
                "source_world_fingerprint": record.fingerprint,
                "source_type": record.type,
                "source_mode": record.source,
                "source_read_only": not record.editable,
            },
            explicit_scope=tuple(sorted(scopes)),
            entities=tuple(sorted(entities, key=lambda item: item.source_entity_id)),
        )

    def project_countries(
        self, state: RunPackageState, *, package_id: str
    ) -> RunWorldCountryProjection:
        versions = [
            version
            for version in state.package_versions
            if version.package_id == package_id
            and version.package_type == PackageType.WORLD
        ]
        if not versions:
            raise ValueError(
                f"Run Package state has no applied World Package '{package_id}'"
            )

        countries: list[Country] = []
        provenance: list[RunWorldCountryProvenance] = []
        seen_codes: set[str] = set()
        for entity in sorted(state.entities, key=lambda item: item.run_local_id):
            if entity.source_package_id != package_id:
                continue
            if entity.entity_kind != WORLD_COUNTRY_ENTITY_KIND:
                continue
            country = Country.model_validate(entity.payload)
            if country.code != entity.source_entity_id:
                raise ValueError(
                    "Run World country source identity does not match country code"
                )
            if country.code in seen_codes:
                raise ValueError(
                    f"Run World country projection contains duplicate code '{country.code}'"
                )
            seen_codes.add(country.code)
            countries.append(country)
            provenance.append(
                RunWorldCountryProvenance(
                    country_code=country.code,
                    run_local_id=entity.run_local_id,
                    source_package_version=entity.source_package_version,
                    source_package_fingerprint=entity.source_package_fingerprint,
                    entity_content_fingerprint=entity.content_fingerprint,
                )
            )
        if not countries:
            raise ValueError(
                f"Run World Package '{package_id}' has no materialized country entities"
            )
        return RunWorldCountryProjection(
            package_id=package_id,
            run_id=state.run_id,
            branch_id=state.branch_id,
            run_package_state_fingerprint=state.fingerprint,
            countries=tuple(sorted(countries, key=lambda item: item.code)),
            provenance=tuple(sorted(provenance, key=lambda item: item.country_code)),
        )

    @staticmethod
    def countries_config(projection: RunWorldCountryProjection) -> CountriesConfig:
        return CountriesConfig(
            dataset_status=f"run_package:{projection.package_id}",
            countries=list(projection.countries),
        )

    @staticmethod
    def _source_version(record: WorldPackageRegistryRecord) -> int:
        match = re.search(r"(?:^|[-_])v([1-9][0-9]*)$", record.version, re.IGNORECASE)
        if match is None:
            raise ValueError(
                f"World Package '{record.world_id}' version '{record.version}' "
                "cannot be mapped to canonical positive integer source_version"
            )
        return int(match.group(1))

    @staticmethod
    def _metadata_payload(record: WorldPackageRegistryRecord) -> dict[str, object]:
        return {
            "world_id": record.world_id,
            "name": record.name,
            "description": record.description,
            "type": record.type,
            "status": record.status,
            "source": record.source,
            "editable": record.editable,
            "version": record.version,
            "source_fingerprint": record.fingerprint,
            "country_count": record.country_count,
            "continent_count": record.continent_count,
            "region_count": record.region_count,
            "travel_region_count": record.travel_region_count,
            "timezone_area_count": record.timezone_area_count,
        }

    @staticmethod
    def _read_object(path: Path) -> dict[str, object]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return value

    def _geography_entities(self, package_root: Path) -> list[PackageEntity]:
        entities: list[PackageEntity] = []
        geography_root = package_root / "geography"
        for entity_id, filename, entity_kind in _GEOGRAPHY_SOURCES:
            path = geography_root / f"{filename}.json"
            if not path.is_file():
                if filename == "timezone_areas":
                    continue
                raise ValueError(f"World Package geography source '{path}' is missing")
            entities.append(
                PackageEntity(
                    source_entity_id=entity_id,
                    entity_kind=entity_kind,
                    entity_schema_version=1,
                    scope=WORLD_GEOGRAPHY_SCOPE,
                    payload=self._read_object(path),
                )
            )
        return entities
