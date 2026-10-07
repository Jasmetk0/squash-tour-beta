from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import (
    build_earth_package,
    load_earth_research_bundle,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.application.world_package_clone_service import WorldPackageCloneService
from beta_engine.application.world_package_countries_service import WorldPackageCountriesService
from beta_engine.application.world_package_validation_service import WorldPackageValidationService
from beta_engine.domain.countries import Country, CountriesConfig
from beta_engine.domain.players.weekly_intake import WeeklyIntakePlanner
from beta_engine.domain.players.talent_planner import AnnualTalentClassPlanner
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from tests.domain.test_country_rating_history import (
    DATASET_ID,
    OBSERVATION_ID,
    country,
    history,
    research_bundle,
)


def _stored_history_path(root: Path, world_id: str, code: str) -> Path:
    context_path = root / world_id / f"countries/{code}/attributes/rating_context.json"
    context = json.loads(context_path.read_text())
    assert context["schema_version"] == "country_rating_context.v2"
    return root / world_id / context["rating_history_file"]


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
    profile = research_bundle(
        history({year: (2.0 if year < 2000 else 8.0) for year in range(1955, 2027)}),
        world_id,
    )
    root = tmp_path / "packages"
    build_earth_package(base_package=base, bundle=profile, output=root / world_id)
    registry = WorldPackageRegistryService(world_packages_root=root)
    service = WorldPackageCountriesService(registry)
    original = registry.get_package(world_id)
    assert original and not original.editable
    assert WorldPackageValidationService(registry).validate_package(world_id).status == "valid"
    assert service.get_country(world_id, "AAA", rating_year=1955).country.elite_support == 2
    assert service.get_country(world_id, "AAA", rating_year=2026).country.elite_support == 8
    assert registry.get_package(world_id).fingerprint == original.fingerprint

    # Observation dataset content identity participates in package identity even
    # when the already-authored numerical country ratings do not change.
    manifests = root / world_id / "generation/observation_manifests/synthetic-observations.json"
    manifest_payload = json.loads(manifests.read_text())
    original_manifest_payload = json.loads(manifests.read_text())
    manifest_payload["sha256"] = "1" * 64
    manifests.write_text(json.dumps(manifest_payload))
    assert registry.get_package(world_id).fingerprint != original.fingerprint
    manifests.write_text(json.dumps(original_manifest_payload))
    assert registry.get_package(world_id).fingerprint == original.fingerprint

    # Source catalogue evidence also remains semantic package identity.
    sources = root / world_id / "generation/sources/test.json"
    payload = json.loads(sources.read_text())
    original_sources = json.loads(sources.read_text())
    payload["limitations"] += " Reviewed again."
    sources.write_text(json.dumps(payload))
    assert registry.get_package(world_id).fingerprint != original.fingerprint
    sources.write_text(json.dumps(original_sources))

    history_path = _stored_history_path(root, world_id, "AAA")
    stored_history = json.loads(history_path.read_text())
    del stored_history["years"]["1960"]
    history_path.write_text(json.dumps(stored_history))
    invalid = WorldPackageValidationService(registry).validate_package(world_id)
    assert invalid.status == "errors"
    assert any("1960" in check.message for check in invalid.checks if check.status == "failed")

    # Observation evidence is checked from persisted content, not a stale
    # coverage report.
    manifest_payload = json.loads(manifests.read_text())
    manifest_payload.clear()
    manifests.write_text(json.dumps(manifest_payload))
    invalid = WorldPackageValidationService(registry).validate_package(world_id)
    assert any(
        "observation dataset catalogue" in check.message
        for check in invalid.checks
        if check.status == "failed"
    )

    # Source references are likewise validated from persisted content.
    payload = json.loads(sources.read_text())
    sources.unlink()
    invalid = WorldPackageValidationService(registry).validate_package(world_id)
    assert any(
        "unknown source" in check.message or "source catalogue" in check.message
        for check in invalid.checks
        if check.status == "failed"
    )


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



def _build_portable_test_package(tmp_path: Path, *, derived: bool = False) -> tuple[Path, str]:
    world_id = "fifa_earth"
    real = Path("config/world_packages/real_world")
    base = tmp_path / "base"
    base.mkdir()
    shutil.copy(real / "world.json", base / "world.json")
    shutil.copytree(real / "geography", base / "geography")
    template = WorldPackageCountryStore(real).load_country("CZE").model_copy(update={"code": "AAA"})
    WorldPackageCountryStore(base).replace_dataset(CountriesConfig(countries=[template]))

    authored = history({year: 4.0 for year in range(1955, 2027)})
    calibration_models = {}
    if derived:
        raw = authored.model_dump()
        for entry in raw["years"].values():
            for rating in entry["ratings"].values():
                rating["method"] = "derived_estimate"
                rating["calibration_model_id"] = "synthetic-calibration.v1"
        authored = type(authored).model_validate(raw)
        calibration_models = {
            "synthetic-calibration.v1": {
                "schema_version": "earth_country_calibration_model.v1",
                "calibration_model_id": "synthetic-calibration.v1",
                "world_id": world_id,
                "countries": ["AAA"],
                "description": "Synthetic calibration definition for provenance tests.",
            }
        }

    root = tmp_path / "packages"
    build_earth_package(
        base_package=base,
        bundle=research_bundle(authored, world_id, calibration_models),
        output=root / world_id,
    )
    return root, world_id


def _failed_messages(result) -> list[str]:
    return [check.message for check in result.checks if check.status == "failed"]


def test_missing_observation_file_fails_closed(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path)
    observation = root / world_id / "observations/synthetic.json"
    observation.unlink()

    result = WorldPackageValidationService(
        WorldPackageRegistryService(world_packages_root=root)
    ).validate_package(world_id)
    assert result.status == "errors"
    assert any("unavailable" in message for message in _failed_messages(result))


def test_changed_observation_content_and_hash_fail_closed(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path)
    observation = root / world_id / "observations/synthetic.json"
    payload = json.loads(observation.read_text())
    payload["observations"][0]["text_value"] = "Tampered evidence"
    observation.write_text(json.dumps(payload))

    registry = WorldPackageRegistryService(world_packages_root=root)
    result = WorldPackageValidationService(registry).validate_package(world_id)
    assert result.status == "errors"
    assert any("SHA-256 mismatch" in message for message in _failed_messages(result))


def test_known_dataset_with_missing_local_observation_id_fails_closed(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path)
    history_path = _stored_history_path(root, world_id, "AAA")
    stored_history = json.loads(history_path.read_text())
    rating = stored_history["years"]["1955"]["ratings"]["elite_support"]
    rating["observation_ids"] = [f"{DATASET_ID}#missing"]
    history_path.write_text(json.dumps(stored_history))

    result = WorldPackageValidationService(
        WorldPackageRegistryService(world_packages_root=root)
    ).validate_package(world_id)
    assert result.status == "errors"
    assert any("missing normalized observation" in message for message in _failed_messages(result))


def test_missing_calibration_definition_fails_closed(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path, derived=True)
    model = root / world_id / "generation/calibration/synthetic-calibration.v1.json"
    model.unlink()

    result = WorldPackageValidationService(
        WorldPackageRegistryService(world_packages_root=root)
    ).validate_package(world_id)
    assert result.status == "errors"
    messages = _failed_messages(result)
    assert any("calibration" in message for message in messages)
    assert any("missing calibration model" in message for message in messages)


def test_unsafe_observation_path_and_symlink_are_rejected(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path)
    manifests_path = root / world_id / "generation/observation_manifests/synthetic-observations.json"
    original = json.loads(manifests_path.read_text())

    unsafe = json.loads(manifests_path.read_text())
    unsafe["relative_path"] = "../outside.json"
    manifests_path.write_text(json.dumps(unsafe))
    registry = WorldPackageRegistryService(world_packages_root=root)
    result = WorldPackageValidationService(registry).validate_package(world_id)
    assert result.status == "errors"
    assert any(
        "unsafe package evidence path" in message
        or "escapes package root" in message
        or "observation dataset" in message
        for message in _failed_messages(result)
    )

    manifests_path.write_text(json.dumps(original))
    observation = root / world_id / "observations/synthetic.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(observation.read_bytes())
    observation.unlink()
    observation.symlink_to(outside)
    result = WorldPackageValidationService(registry).validate_package(world_id)
    assert result.status == "errors"
    assert any("symlink" in message for message in _failed_messages(result))


def test_relocated_package_remains_self_contained(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path, derived=True)
    moved_root = tmp_path / "relocated"
    shutil.copytree(root / world_id, moved_root / world_id)
    shutil.rmtree(root)

    registry = WorldPackageRegistryService(world_packages_root=moved_root)
    package = registry.get_package(world_id)
    assert package is not None
    assert package.type == "official"
    assert package.editable is False
    assert WorldPackageValidationService(registry).validate_package(world_id).status == "valid"
    assert (moved_root / world_id / "observations/synthetic.json").is_file()
    assert (
        moved_root
        / world_id
        / "generation/calibration/synthetic-calibration.v1.json"
    ).is_file()



@pytest.mark.parametrize(
    ("world_id", "expected_name"),
    [
        ("fifa_earth", "FIFA Earth Package"),
        ("atp_earth", "ATP Earth Package"),
    ],
)
def test_distributed_earth_packages_are_registered_and_valid(world_id, expected_name):
    registry = WorldPackageRegistryService()
    package = registry.get_package(world_id)
    assert package is not None
    assert package.name == expected_name
    assert package.type == "official"
    assert package.source == "built_in"
    assert package.editable is False
    assert package.deletable is False
    assert package.archivable is False
    assert package.country_count == 250

    validation = WorldPackageValidationService(registry).validate_package(world_id)
    assert validation is not None
    assert validation.status == "valid", [
        check.message for check in validation.checks if check.status == "failed"
    ]

    countries = WorldPackageCountriesService(registry)
    old = countries.get_country(world_id, "CZE", rating_year=1955)
    current = countries.get_country(world_id, "CZE", rating_year=2026)
    assert old is not None and current is not None
    assert old.country.rating_effective_year == 1955
    assert current.country.rating_effective_year == 2026
    assert old.country.court_count is None
    assert current.country.court_count is None


def test_portable_earth_clone_keeps_provenance_and_is_independent(tmp_path):
    root, world_id = _build_portable_test_package(tmp_path, derived=True)
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    clone_service = WorldPackageCloneService(registry, validation)

    result = clone_service.clone_world(
        source_world_id=world_id,
        new_world_id="portable_copy",
        name="Portable copy",
        description="Independent editable clone.",
        dry_run=False,
    )
    assert result.ok
    assert result.package is not None
    assert result.package.type == "custom"
    assert result.package.editable is True
    assert result.validation is not None
    assert result.validation.status == "valid"

    source_history = _stored_history_path(root, world_id, "AAA")
    clone_context = json.loads(
        (root / "custom/portable_copy/countries/AAA/attributes/rating_context.json").read_text()
    )
    clone_history = root / "custom/portable_copy" / clone_context["rating_history_file"]
    assert clone_history.read_bytes() == source_history.read_bytes()

    changed = json.loads(clone_history.read_text())
    changed["years"]["1955"]["ratings"]["elite_support"]["value"] = 4.1
    clone_history.write_text(json.dumps(changed))
    assert json.loads(source_history.read_text())["years"]["1955"]["ratings"]["elite_support"]["value"] == 4.0



@pytest.mark.parametrize("world_id", ["fifa_earth", "atp_earth"])
def test_earth_history_survives_run_package_adapter(world_id):
    registry = WorldPackageRegistryService()
    document = WorldPackageRunAdapter(registry).build_document(world_id)
    country_entity = next(
        entity
        for entity in document.entities
        if entity.scope == "countries" and entity.source_entity_id == "CZE"
    )
    run_country = Country.model_validate(country_entity.payload)
    assert run_country.rating_history is not None
    assert len(run_country.rating_history.years) == 72
    assert run_country.at_rating_year(1955).rating_effective_year == 1955
    assert run_country.at_rating_year(2026).rating_effective_year == 2026


@pytest.mark.parametrize("world_id", ["fifa_earth", "atp_earth"])
def test_full_earth_research_builds_to_valid_distributed_semantics(tmp_path, world_id):
    research_path = Path(f"config/earth_research/{world_id}.json")
    bundle = load_earth_research_bundle(research_path)
    output = tmp_path / world_id

    report = build_earth_package(
        base_package=Path("config/world_packages/real_world"),
        bundle=bundle,
        output=output,
    )
    assert report["coverage_complete"] is True
    assert report["required_country_count"] == 250
    assert report["authored_rating_count"] == 108_000
    assert report["observation_dataset_count"] == (318 if world_id == "fifa_earth" else 486)
    assert report["observation_record_count"] == (2081 if world_id == "fifa_earth" else 1033)
    assert report["realism_validated"] is False

    built_registry = WorldPackageRegistryService(world_packages_root=tmp_path)
    built_record = built_registry.get_package(world_id)
    assert built_record is not None
    assert built_record.country_count == 250
    validation = WorldPackageValidationService(built_registry).validate_package(world_id)
    assert validation is not None
    assert validation.status == "valid", [
        check.message for check in validation.checks if check.status == "failed"
    ]

    distributed_root = Path("config/world_packages") / world_id
    assert WorldPackageCountryStore(output).semantic_payload() == (
        WorldPackageCountryStore(distributed_root).semantic_payload()
    )
