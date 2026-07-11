"""Read-only registry for world packages backed by built-in world package config."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.infrastructure.world_config import load_countries_config

OFFICIAL_FAX_WORLD_ID = "official_fax_world"
OFFICIAL_FAX_WORLD_NAME = "Official FAX World"
OFFICIAL_FAX_WORLD_DESCRIPTION = "Built-in official FAX squash world package."
OFFICIAL_FAX_WORLD_VERSION = "v1"
OFFICIAL_FAX_WORLD_DIR = Path("config/worlds/official_fax_world")


@dataclass(frozen=True)
class WorldPackageStorageSummary:
    countries_path: str
    manual_player_overrides_path: str
    world_metadata_path: str | None = None
    continents_path: str | None = None
    regions_path: str | None = None
    travel_regions_path: str | None = None


@dataclass(frozen=True)
class WorldPackageRegistryRecord:
    world_id: str
    name: str
    description: str
    type: str
    status: str
    source: str
    editable: bool
    deletable: bool
    archivable: bool
    version: str
    fingerprint: str
    country_count: int
    manual_override_count: int
    continent_count: int
    region_count: int
    travel_region_count: int
    used_by_run_count: int | None
    validation_status: str
    storage: WorldPackageStorageSummary


@dataclass(slots=True)
class WorldPackageRegistryService:
    """Read-only package registry exposing the built-in official package.

    Phase 4 intentionally leaves the legacy Countries Editor and /world/countries
    endpoints on config/world/countries.json while this registry reads the new
    built-in package storage under config/worlds/official_fax_world.
    """

    countries_service: CountriesConfigService
    manual_overrides_service: ManualPlayerOverridesService

    def list_packages(self) -> list[WorldPackageRegistryRecord]:
        return [self.get_official_package()]

    def get_package(self, world_id: str) -> WorldPackageRegistryRecord | None:
        normalized = world_id.strip().lower()
        if normalized != OFFICIAL_FAX_WORLD_ID:
            return None
        return self.get_official_package()

    def get_official_package(self) -> WorldPackageRegistryRecord:
        metadata = self._read_json(self._world_metadata_path())
        countries_config = load_countries_config(self._countries_path())
        continents = self._read_registry_items(self._continents_path(), "continents")
        regions = self._read_registry_items(self._regions_path(), "regions")
        travel_regions = self._read_registry_items(self._travel_regions_path(), "travel_regions")
        overrides = self.manual_overrides_service.list_overrides()
        return WorldPackageRegistryRecord(
            world_id=str(metadata["world_id"]),
            name=str(metadata["name"]),
            description=str(metadata["description"]),
            type=str(metadata["type"]),
            status=str(metadata["status"]),
            source=str(metadata["source"]),
            editable=bool(metadata["editable"]),
            deletable=bool(metadata["deletable"]),
            archivable=bool(metadata["archivable"]),
            version=str(metadata["version"]),
            fingerprint=self._fingerprint(),
            country_count=len(countries_config.countries),
            manual_override_count=len(overrides),
            continent_count=len(continents),
            region_count=len(regions),
            travel_region_count=len(travel_regions),
            used_by_run_count=None,
            validation_status="valid",
            storage=WorldPackageStorageSummary(
                countries_path=str(self._countries_path()),
                manual_player_overrides_path=str(self.manual_overrides_service.config_path),
                world_metadata_path=str(self._world_metadata_path()),
                continents_path=str(self._continents_path()),
                regions_path=str(self._regions_path()),
                travel_regions_path=str(self._travel_regions_path()),
            ),
        )

    def official_paths(self) -> dict[str, Path]:
        """Return built-in official package storage paths for read-only consumers."""
        return {
            "world": self._world_metadata_path(),
            "countries": self._countries_path(),
            "continents": self._continents_path(),
            "regions": self._regions_path(),
            "travel_regions": self._travel_regions_path(),
        }

    def _fingerprint(self) -> str:
        payload = self._fingerprint_payload()
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _fingerprint_payload(self) -> dict[str, object]:
        metadata = self._read_json(self._world_metadata_path())
        meaning_metadata = {
            key: metadata[key]
            for key in (
                "world_id",
                "name",
                "type",
                "status",
                "source",
                "editable",
                "deletable",
                "archivable",
                "version",
                "content_schema_version",
            )
        }
        countries = sorted(
            (country.model_dump(mode="json") for country in load_countries_config(self._countries_path()).countries),
            key=lambda item: str(item["code"]),
        )
        return {
            "world_metadata": meaning_metadata,
            "countries": countries,
            "continents": self._read_json(self._continents_path()),
            "regions": self._read_json(self._regions_path()),
            "travel_regions": self._read_json(self._travel_regions_path()),
        }

    def _world_metadata_path(self) -> Path:
        return OFFICIAL_FAX_WORLD_DIR / "world.json"

    def _countries_path(self) -> Path:
        return OFFICIAL_FAX_WORLD_DIR / "countries.json"

    def _continents_path(self) -> Path:
        return OFFICIAL_FAX_WORLD_DIR / "continents.json"

    def _regions_path(self) -> Path:
        return OFFICIAL_FAX_WORLD_DIR / "regions.json"

    def _travel_regions_path(self) -> Path:
        return OFFICIAL_FAX_WORLD_DIR / "travel_regions.json"

    def _read_json(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_registry_items(self, path: Path, key: str) -> list[object]:
        payload = self._read_json(path)
        items = payload.get(key, [])
        return items if isinstance(items, list) else []
