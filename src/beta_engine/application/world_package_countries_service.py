"""Read-only access to countries contained inside registered World Packages."""

from __future__ import annotations

from dataclasses import dataclass

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
