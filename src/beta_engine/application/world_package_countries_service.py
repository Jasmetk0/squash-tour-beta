"""Read-only access to countries contained inside registered World Packages."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from beta_engine.application.world_package_registry_service import WorldPackageRegistryRecord, WorldPackageRegistryService
from beta_engine.domain.countries import Country
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


@dataclass(frozen=True)
class WorldPackageCountriesResult:
    world_id: str
    world_name: str
    type: str
    source: str
    read_only: bool
    country_count: int
    source_path: str
    countries: list[Country]


class ContinentRecord(BaseModel):
    code: str
    name: str


class RegionRecord(BaseModel):
    code: str
    name: str
    continent_code: str | None = None


class TravelRegionRecord(BaseModel):
    code: str
    name: str
    description: str | None = None


@dataclass(frozen=True)
class WorldPackageGeographyResult:
    world_id: str
    continents: list[ContinentRecord]
    regions: list[RegionRecord]
    travel_regions: list[TravelRegionRecord]


@dataclass(frozen=True)
class WorldPackageCountryDetailResult:
    package: WorldPackageRegistryRecord
    country: Country
    region: RegionRecord | None
    continent: ContinentRecord | None
    travel_region: TravelRegionRecord | None
    source_path: str


@dataclass(slots=True)
class WorldPackageCountriesService:
    """Load package-scoped countries without touching canonical countries config."""

    registry_service: WorldPackageRegistryService

    def get_countries(self, world_id: str) -> WorldPackageCountriesResult | None:
        record = self.registry_service.get_package(world_id)
        paths = self.registry_service.package_paths(world_id)
        if record is None or paths is None:
            return None
        countries_config = WorldPackageCountryStore(paths["package_root"]).load_config()
        return self._to_result(record=record, source_path=str(paths["countries_index"]), countries=countries_config.countries)

    def get_geography(self, world_id: str) -> WorldPackageGeographyResult | None:
        if self.registry_service.get_package(world_id) is None:
            return None
        paths = self.registry_service.package_paths(world_id)
        if paths is None:
            return None
        return WorldPackageGeographyResult(
            world_id=world_id,
            continents=self._load_items(paths["continents"], "continents", ContinentRecord),
            regions=self._load_items(paths["regions"], "regions", RegionRecord),
            travel_regions=self._load_items(paths["travel_regions"], "travel_regions", TravelRegionRecord),
        )

    def get_country(self, world_id: str, country_code: str) -> WorldPackageCountryDetailResult | None:
        package = self.registry_service.get_package(world_id)
        paths = self.registry_service.package_paths(world_id)
        if package is None or paths is None:
            return None
        code = country_code.upper()
        store = WorldPackageCountryStore(paths["package_root"])
        if code not in store.load_index().country_codes:
            return None
        country = store.load_country(code)
        geography = self.get_geography(world_id)
        assert geography is not None
        region = next((item for item in geography.regions if item.code == country.region), None)
        continent = next((item for item in geography.continents if region and item.code == region.continent_code), None)
        travel_region = next((item for item in geography.travel_regions if item.code == country.travel_region), None)
        return WorldPackageCountryDetailResult(
            package=package, country=country, region=region, continent=continent,
            travel_region=travel_region,
            source_path=str(Path(paths["countries_root"]) / code),
        )

    @staticmethod
    def _load_items(path: Path, key: str, model: type[BaseModel]) -> list[Any]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
            raise ValueError(f"{path} must contain a {key} list")
        return [model.model_validate(item) for item in payload[key]]

    def _to_result(self, *, record: WorldPackageRegistryRecord, source_path: str, countries: list[Country]) -> WorldPackageCountriesResult:
        return WorldPackageCountriesResult(
            world_id=record.world_id,
            world_name=record.name,
            type=record.type,
            source=record.source,
            read_only=not record.editable,
            country_count=len(countries),
            source_path=source_path,
            countries=countries,
        )
