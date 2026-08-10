"""Read-only access to countries contained inside registered World Packages."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.world_package_registry_service import WorldPackageRegistryRecord, WorldPackageRegistryService
from beta_engine.domain.countries import Country
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.application.world_package_validation_service import WorldPackageValidationResult, WorldPackageValidationService


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


class WorldPackageCountryUpdate(BaseModel):
    """Complete editable country state; stable identity and population are absent."""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    notes: str | None = None
    area_km2: int | None = Field(gt=0)
    region: str = Field(min_length=1)
    travel_region: str | None = None
    wealth_support: int = Field(ge=1, le=5)
    squash_popularity: int = Field(ge=1, le=5)
    squash_tradition: int = Field(ge=1, le=5)
    system_quality: int = Field(ge=1, le=5)
    competition_density: float = Field(ge=1.0, le=5.0)
    federation_quality: float = Field(ge=1.0, le=5.0)
    court_count: int | None = Field(ge=0)
    style_dna: dict[str, float]
    expected_package_fingerprint: str | None = None


class WorldPackageMutationError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class WorldPackageCountryUpdateResult:
    detail: WorldPackageCountryDetailResult
    validation: WorldPackageValidationResult


@dataclass(slots=True)
class WorldPackageCountriesService:
    """Load package-scoped countries without touching canonical countries config."""

    registry_service: WorldPackageRegistryService
    validation_service: WorldPackageValidationService | None = None

    def __post_init__(self) -> None:
        if self.validation_service is None:
            self.validation_service = WorldPackageValidationService(self.registry_service)

    def update_country(self, world_id: str, country_code: str, update: WorldPackageCountryUpdate) -> WorldPackageCountryUpdateResult:
        package = self.registry_service.get_package(world_id)
        if package is None:
            raise WorldPackageMutationError(f"world package '{world_id}' not found", 404)
        if package.type != "custom" or package.source != "custom_config" or not package.editable:
            raise WorldPackageMutationError(f"world package '{world_id}' is read-only", 403)
        if update.expected_package_fingerprint and update.expected_package_fingerprint != package.fingerprint:
            raise WorldPackageMutationError("world package changed since this country was loaded", 409)
        paths = self.registry_service.package_paths(world_id)
        assert paths is not None
        store = WorldPackageCountryStore(paths["package_root"])
        code = country_code.upper()
        if code not in store.load_index().country_codes:
            raise WorldPackageMutationError(f"country '{code}' not found in world package '{world_id}'", 404)
        geography = self.get_geography(world_id)
        assert geography is not None
        if update.region not in {item.code for item in geography.regions}:
            raise WorldPackageMutationError(f"unknown Region '{update.region}'")
        if update.travel_region is not None and update.travel_region not in {item.code for item in geography.travel_regions}:
            raise WorldPackageMutationError(f"unknown Travel Region '{update.travel_region}'")
        original = store.load_country(code)
        try:
            updated = Country.model_validate({
                **original.model_dump(),
                **update.model_dump(exclude={"expected_package_fingerprint"}),
            })
            store.replace_country(updated)
            assert self.validation_service is not None
            validation = self.validation_service.validate_package(world_id)
            if validation is None or validation.status == "errors":
                store.replace_country(original)
                raise WorldPackageMutationError("country edit would leave the World Package invalid")
        except WorldPackageMutationError:
            raise
        except Exception as exc:
            # replace_country restores promotion failures. If failure happened later,
            # make the best bounded effort to restore the typed original.
            try:
                if store.load_country(code) != original:
                    store.replace_country(original)
            except Exception:
                pass
            raise WorldPackageMutationError(f"country edit failed: {exc}") from exc
        detail = self.get_country(world_id, code)
        assert detail is not None
        return WorldPackageCountryUpdateResult(detail=detail, validation=validation)

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
