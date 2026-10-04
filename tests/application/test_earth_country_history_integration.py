from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import build_earth_package
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.application.world_package_validation_service import WorldPackageValidationService
from beta_engine.domain.countries import CountriesConfig
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlanner
from beta_engine.domain.players.talent_planner import AnnualTalentClassPlanner
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from tests.domain.test_country_rating_history import country, history, research


@pytest.mark.parametrize("world_id", ["fifa_earth", "atp_earth"])
def test_real_registry_and_year_detail_preserve_history_and_fingerprint(tmp_path, world_id):
    base = tmp_path / "base"
    base.mkdir()
    real = Path("config/world_packages/real_world")
    shutil.copy(real / "world.json", base / "world.json")
    shutil.copytree(real / "geography", base / "geography")
    template = WorldPackageCountryStore(real).load_country("CZE")
    template = template.model_copy(update={"code": "AAA"})
    WorldPackageCountryStore(base).replace_dataset(CountriesConfig(countries=[template]))
    profile = research(history({year: (2.0 if year < 2000 else 8.0) for year in range(1955, 2027)}), world_id)
    root = tmp_path / "packages"
    build_earth_package(base_package=base, research=profile, output=root / world_id)
    registry = WorldPackageRegistryService(world_packages_root=root)
    service = WorldPackageCountriesService(registry)
    original = registry.get_package(world_id)
    assert original and not original.editable
    assert WorldPackageValidationService(registry).validate_package(world_id).status == "valid"
    assert service.get_country(world_id, "AAA", rating_year=1955).country.elite_support == 2
    assert service.get_country(world_id, "AAA", rating_year=2026).country.elite_support == 8
    assert registry.get_package(world_id).fingerprint == original.fingerprint
    # Evidence is part of package identity even when the numerical ratings do not change.
    sources = root / world_id / "generation/country_rating_sources.json"
    payload = json.loads(sources.read_text())
    payload["test"]["limitations"] += " Reviewed again."
    sources.write_text(json.dumps(payload))
    assert registry.get_package(world_id).fingerprint != original.fingerprint
    context_path = root / world_id / "countries/AAA/attributes/rating_context.json"
    context = json.loads(context_path.read_text())
    del context["rating_history"]["years"]["1960"]
    context_path.write_text(json.dumps(context))
    invalid = WorldPackageValidationService(registry).validate_package(world_id)
    assert invalid.status == "errors"
    assert any("1960" in check.message for check in invalid.checks if check.status == "failed")
    # Evidence references are checked from persisted content, not a stale coverage report.
    payload.clear()
    sources.write_text(json.dumps(payload))
    invalid = WorldPackageValidationService(registry).validate_package(world_id)
    assert any("source catalogue" in check.message for check in invalid.checks if check.status == "failed")


def test_weekly_intake_selects_birth_year_without_future_rating_leak():
    changing = country(history({1955: 1, 1985: 1, 1986: 10, 2026: 10}))
    fixed = country(history({1955: 5, 2026: 5}), code="BBB")
    planner = WeeklyIntakePlanner()
    old = planner.plan_weekly_intake(countries=[changing, fixed], season="2000/01", season_week=1, target_intake_count=100)
    later = planner.plan_weekly_intake(countries=[changing, fixed], season="2001/02", season_week=1, target_intake_count=100)
    assert old.birth_year == 1985 and later.birth_year == 1986
    assert old.allocations[0].allocated_count < later.allocations[0].allocated_count
    assert changing.rating_effective_year is None
    assert planner.plan_weekly_intake(countries=[fixed, changing], season="2000/01", season_week=1, target_intake_count=100) == old


def test_annual_intake_reads_requested_year():
    changing = country(history({1955: 1, 2026: 10}))
    fixed = country(history({1955: 5, 2026: 5}), code="BBB")
    planner = AnnualTalentClassPlanner()
    old = planner.plan(year=1955, seed=42, countries=[changing, fixed])
    new = planner.plan(year=2026, seed=42, countries=[changing, fixed])
    assert old.allocations[0].planned_count / old.total_talents < new.allocations[0].planned_count / new.total_talents
