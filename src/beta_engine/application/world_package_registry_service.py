"""Read-only registry for world packages backed by repository world package config."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.infrastructure.world_config import load_countries_config
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID

OFFICIAL_FAX_WORLD_NAME = "Official FAX World"
OFFICIAL_FAX_WORLD_DESCRIPTION = "Built-in official FAX squash world package."
OFFICIAL_FAX_WORLD_VERSION = "v1"
DEFAULT_WORLDS_ROOT = Path("config/worlds")

REQUIRED_WORLD_PACKAGE_FILES = (
    "world.json",
    "countries.json",
    "continents.json",
    "regions.json",
    "travel_regions.json",
)


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
    """Read-only package registry exposing built-in and repository custom packages."""

    countries_service: CountriesConfigService
    manual_overrides_service: ManualPlayerOverridesService
    worlds_root: Path = DEFAULT_WORLDS_ROOT

    def list_packages(self) -> list[WorldPackageRegistryRecord]:
        packages = [self.get_official_package()]
        seen = {OFFICIAL_FAX_WORLD_ID}
        for package_dir in self._custom_package_dirs():
            record = self._build_custom_package(package_dir)
            if record is None or record.world_id in seen:
                continue
            seen.add(record.world_id)
            packages.append(record)
        return packages

    def get_package(self, world_id: str) -> WorldPackageRegistryRecord | None:
        normalized = world_id.strip().lower()
        if normalized == OFFICIAL_FAX_WORLD_ID:
            return self.get_official_package()
        for record in self.list_packages()[1:]:
            if record.world_id == normalized:
                return record
        return None

    def get_official_package(self) -> WorldPackageRegistryRecord:
        package_dir = self._official_dir()
        metadata = self._read_json(package_dir / "world.json")
        countries_config = load_countries_config(package_dir / "countries.json")
        continents = self._read_registry_items(package_dir / "continents.json", "continents")
        regions = self._read_registry_items(package_dir / "regions.json", "regions")
        travel_regions = self._read_registry_items(package_dir / "travel_regions.json", "travel_regions")
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
            fingerprint=self._fingerprint(package_dir),
            country_count=len(countries_config.countries),
            manual_override_count=len(overrides),
            continent_count=len(continents),
            region_count=len(regions),
            travel_region_count=len(travel_regions),
            used_by_run_count=None,
            validation_status="valid",
            storage=self._storage_summary(package_dir, include_manual_overrides=True),
        )

    def official_paths(self) -> dict[str, Path]:
        return self.package_paths(OFFICIAL_FAX_WORLD_ID) or {}

    def package_paths(self, world_id: str) -> dict[str, Path] | None:
        normalized = world_id.strip().lower()
        if normalized == OFFICIAL_FAX_WORLD_ID:
            return self._paths_for_dir(self._official_dir())
        for package_dir in self._custom_package_dirs():
            metadata = self._safe_read_json(package_dir / "world.json")
            if isinstance(metadata, dict) and str(metadata.get("world_id", "")).strip().lower() == normalized:
                return self._paths_for_dir(package_dir)
        return None

    def _build_custom_package(self, package_dir: Path) -> WorldPackageRegistryRecord | None:
        if not all((package_dir / name).is_file() for name in REQUIRED_WORLD_PACKAGE_FILES):
            return None
        try:
            metadata = self._read_json(package_dir / "world.json")
            world_id = str(metadata.get("world_id", "")).strip().lower()
            if world_id != package_dir.name.strip().lower() or world_id == OFFICIAL_FAX_WORLD_ID:
                return None
            if metadata.get("type") != "custom" or metadata.get("source") != "custom_config" or metadata.get("status") not in {"active", "archived"}:
                return None
            countries_config = load_countries_config(package_dir / "countries.json")
            continents = self._read_registry_items(package_dir / "continents.json", "continents")
            regions = self._read_registry_items(package_dir / "regions.json", "regions")
            travel_regions = self._read_registry_items(package_dir / "travel_regions.json", "travel_regions")
            return WorldPackageRegistryRecord(
                world_id=world_id,
                name=str(metadata["name"]),
                description=str(metadata.get("description", "")),
                type="custom",
                status=str(metadata["status"]),
                source="custom_config",
                editable=bool(metadata.get("editable", True)),
                deletable=bool(metadata.get("deletable", True)),
                archivable=bool(metadata.get("archivable", True)),
                version=str(metadata["version"]),
                fingerprint=self._fingerprint(package_dir),
                country_count=len(countries_config.countries),
                manual_override_count=0,
                continent_count=len(continents),
                region_count=len(regions),
                travel_region_count=len(travel_regions),
                used_by_run_count=None,
                validation_status="valid",
                storage=self._storage_summary(package_dir, include_manual_overrides=False),
            )
        except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
            return None

    def _fingerprint(self, package_dir: Path) -> str:
        payload = self._fingerprint_payload(package_dir)
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _fingerprint_payload(self, package_dir: Path) -> dict[str, object]:
        metadata = self._read_json(package_dir / "world.json")
        meaning_metadata = {
            key: metadata[key]
            for key in (
                "world_id", "name", "type", "status", "source", "editable", "deletable", "archivable", "version", "content_schema_version"
            )
            if key in metadata
        }
        countries = sorted((country.model_dump(mode="json") for country in load_countries_config(package_dir / "countries.json").countries), key=lambda item: str(item["code"]))
        return {
            "world_metadata": meaning_metadata,
            "countries": countries,
            "continents": self._read_json(package_dir / "continents.json"),
            "regions": self._read_json(package_dir / "regions.json"),
            "travel_regions": self._read_json(package_dir / "travel_regions.json"),
        }

    def _official_dir(self) -> Path:
        return self.worlds_root / OFFICIAL_FAX_WORLD_ID

    def _custom_root(self) -> Path:
        return self.worlds_root / "custom"

    def _custom_package_dirs(self) -> list[Path]:
        root = self._custom_root()
        if not root.is_dir():
            return []
        return sorted((path for path in root.iterdir() if path.is_dir()), key=lambda path: path.name.lower())

    def _paths_for_dir(self, package_dir: Path) -> dict[str, Path]:
        return {
            "world": package_dir / "world.json",
            "countries": package_dir / "countries.json",
            "continents": package_dir / "continents.json",
            "regions": package_dir / "regions.json",
            "travel_regions": package_dir / "travel_regions.json",
        }

    def _storage_summary(self, package_dir: Path, *, include_manual_overrides: bool) -> WorldPackageStorageSummary:
        return WorldPackageStorageSummary(
            countries_path=str(package_dir / "countries.json"),
            manual_player_overrides_path=str(self.manual_overrides_service.config_path) if include_manual_overrides else "",
            world_metadata_path=str(package_dir / "world.json"),
            continents_path=str(package_dir / "continents.json"),
            regions_path=str(package_dir / "regions.json"),
            travel_regions_path=str(package_dir / "travel_regions.json"),
        )

    def _read_json(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return payload

    def _safe_read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            return self._read_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def _read_registry_items(self, path: Path, key: str) -> list[object]:
        payload = self._read_json(path)
        items = payload.get(key, [])
        return items if isinstance(items, list) else []
