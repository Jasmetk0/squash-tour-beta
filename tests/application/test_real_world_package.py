from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import WorldPackageValidationService
from beta_engine.world_packages import REAL_WORLD_ID


def _validation_service(world_packages_root: Path) -> WorldPackageValidationService:
    registry = WorldPackageRegistryService(
        countries_service=CountriesConfigService(),
        manual_overrides_service=ManualPlayerOverridesService(),
        world_packages_root=world_packages_root,
    )
    return WorldPackageValidationService(registry_service=registry)


@pytest.mark.smoke
def test_real_world_is_read_only_and_has_complete_population_through_2050() -> None:
    registry = WorldPackageRegistryService(
        countries_service=CountriesConfigService(),
        manual_overrides_service=ManualPlayerOverridesService(),
    )
    package = registry.get_package(REAL_WORLD_ID)
    validation = WorldPackageValidationService(registry_service=registry).validate_package(REAL_WORLD_ID)

    assert package is not None
    assert package.type == "official"
    assert package.source == "built_in"
    assert package.editable is False
    assert package.deletable is False
    assert package.archivable is False
    assert package.country_count == 250
    assert validation is not None
    assert validation.status == "valid"
    assert any(check.code == "population_coverage_valid" and check.status == "passed" for check in validation.checks)


def test_real_world_validation_fails_loudly_when_2050_population_is_missing(tmp_path) -> None:
    world_packages_root = tmp_path / "world_packages"
    package_dir = world_packages_root / REAL_WORLD_ID
    shutil.copytree(Path("config/world_packages/real_world"), package_dir)
    countries_path = package_dir / "countries/ABW/attributes/population.json"
    payload = json.loads(countries_path.read_text(encoding="utf-8"))
    del payload["values_by_year"]["2050"]
    countries_path.write_text(json.dumps(payload), encoding="utf-8")

    validation = _validation_service(world_packages_root).validate_package(REAL_WORLD_ID)

    assert validation is not None
    assert validation.status == "errors"
    check = next(check for check in validation.checks if check.code == "population_coverage_valid")
    assert check.status == "failed"
    assert "2050" in check.message
