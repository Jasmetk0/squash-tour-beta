"""Read-only registry for world packages backed by current canonical world config."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService

OFFICIAL_FAX_WORLD_ID = "official_fax_world"
OFFICIAL_FAX_WORLD_NAME = "Official FAX World"
OFFICIAL_FAX_WORLD_DESCRIPTION = "Built-in official FAX squash world package."
OFFICIAL_FAX_WORLD_VERSION = "v1"


@dataclass(frozen=True)
class WorldPackageStorageSummary:
    countries_path: str
    manual_player_overrides_path: str


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
    """Read-only package registry exposing the canonical world as the official package."""

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
        countries_config = self.countries_service.get_config()
        overrides = self.manual_overrides_service.list_overrides()
        return WorldPackageRegistryRecord(
            world_id=OFFICIAL_FAX_WORLD_ID,
            name=OFFICIAL_FAX_WORLD_NAME,
            description=OFFICIAL_FAX_WORLD_DESCRIPTION,
            type="official",
            status="active",
            source="canonical_config",
            editable=False,
            deletable=False,
            archivable=False,
            version=OFFICIAL_FAX_WORLD_VERSION,
            fingerprint=self._fingerprint(),
            country_count=len(countries_config.countries),
            manual_override_count=len(overrides),
            continent_count=0,
            region_count=0,
            travel_region_count=0,
            used_by_run_count=None,
            validation_status="valid",
            storage=WorldPackageStorageSummary(
                countries_path=str(self.countries_service.config_path),
                manual_player_overrides_path=str(self.manual_overrides_service.config_path),
            ),
        )

    def _fingerprint(self) -> str:
        payload = self._fingerprint_payload()
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _fingerprint_payload(self) -> dict[str, object]:
        countries = sorted(
            (country.model_dump(mode="json") for country in self.countries_service.get_config().countries),
            key=lambda item: str(item["code"]),
        )
        overrides = sorted(
            (override.model_dump(mode="json") for override in self.manual_overrides_service.list_overrides()),
            key=lambda item: (int(item["season"]), str(item["country_code"]), str(item["override_id"])),
        )
        return {
            "countries": countries,
            "manual_player_overrides": overrides,
        }
