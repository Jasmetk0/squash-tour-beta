"""Test-only builders and loaders for canonical directory-backed World Packages."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from beta_engine.domain.countries import CountriesConfig
from beta_engine.infrastructure.world_package_storage import PACKAGE_FORMAT_VERSION, WorldPackageCountryStore

REPOSITORY_WORLD_PACKAGES_ROOT = Path("config/world_packages")


def load_fax_reference_countries() -> CountriesConfig:
    return WorldPackageCountryStore(REPOSITORY_WORLD_PACKAGES_ROOT / "official_fax_world").load_config()


def load_simulation_test_countries() -> CountriesConfig:
    """Expanded disposable population for draw/waitlist simulation contracts."""
    source = load_fax_reference_countries()
    countries = list(source.countries)
    for index in range(20):
        base = source.countries[index % len(source.countries)]
        code = f"X{chr(65 + index // 26)}{chr(65 + index % 26)}"
        update: dict[str, object] = {"code": code, "name": f"Simulation Test {index + 1}"}
        if index >= 10:
            update.update({"wealth_support": 1, "squash_popularity": 1, "squash_tradition": 1, "system_quality": 1})
        countries.append(base.model_copy(update=update))
    return CountriesConfig(dataset_status="disposable_simulation_test", countries=countries)


def copy_builtin_world_packages(destination: Path) -> Path:
    for world_id in ("official_fax_world", "real_world"):
        shutil.copytree(REPOSITORY_WORLD_PACKAGES_ROOT / world_id, destination / world_id)
    return destination


def materialize_test_world_package(
    world_packages_root: Path,
    countries: CountriesConfig,
    *,
    world_id: str = "official_fax_world",
    editable: bool = False,
) -> Path:
    """Write a complete canonical package for synthetic-country mutation tests."""
    package_root = world_packages_root / world_id
    package_root.mkdir(parents=True, exist_ok=True)
    metadata = {
        "world_id": world_id,
        "name": "Test World",
        "description": "Disposable canonical test World Package.",
        "type": "official" if world_id in {"official_fax_world", "real_world"} else "custom",
        "status": "active",
        "source": "built_in" if world_id in {"official_fax_world", "real_world"} else "custom_config",
        "editable": editable,
        "deletable": world_id not in {"official_fax_world", "real_world"},
        "archivable": world_id not in {"official_fax_world", "real_world"},
        "version": "test-v1",
        "content_schema_version": "1",
        "package_format_version": PACKAGE_FORMAT_VERSION,
    }
    (package_root / "world.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    WorldPackageCountryStore(package_root).replace_dataset(countries)

    regions = sorted({country.region for country in countries.countries})
    travel_regions = sorted({country.travel_region for country in countries.countries if country.travel_region})
    geography = package_root / "geography"
    geography.mkdir(exist_ok=True)
    (geography / "continents.json").write_text(json.dumps({"continents": [{"code": "TEST", "name": "Test"}]}, indent=2) + "\n")
    (geography / "regions.json").write_text(json.dumps({"regions": [{"code": code, "name": code, "continent_code": "TEST"} for code in regions]}, indent=2) + "\n")
    (geography / "travel_regions.json").write_text(json.dumps({"travel_regions": [{"code": code, "name": code} for code in travel_regions]}, indent=2) + "\n")
    return package_root
