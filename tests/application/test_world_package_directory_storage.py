import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from beta_engine.application.world_package_clone_service import WorldPackageCloneService
from beta_engine.application.world_package_countries_service import (
    WorldPackageCountriesService,
    WorldPackageCountryCreate,
    WorldPackageCountryPopulationUpdate,
    WorldPackageCountryUpdate,
    WorldPackageMutationError,
)
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.application.world_package_validation_service import (
    WorldPackageValidationResult,
    WorldPackageValidationService,
)
from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.infrastructure.world_package_storage import (
    ATTRIBUTE_NAMES,
    LEGACY_ATTRIBUTE_NAMES,
    WorldPackageCountryStore,
)


EDITABLE_FIELDS = {
    "name",
    "notes",
    "area_km2",
    "region",
    "travel_region",
    "court_count",
    "squash_popularity",
    "squash_access",
    "development_quality",
    "competition_quality",
    "elite_support",
    "squash_tradition",
}


def _scalar_country(*, name: str = "Alpha") -> Country:
    return Country(
        code="AAA",
        name=name,
        region="EUROPE",
        population=1_234_567,
        squash_popularity=4,
        squash_access=3,
        development_quality=5,
        competition_quality=4,
        elite_support=3,
        squash_tradition=2,
    )


def _country_update(country: Country, **changes: object) -> WorldPackageCountryUpdate:
    payload = country.model_dump(include=EDITABLE_FIELDS)
    payload.update(changes)
    return WorldPackageCountryUpdate.model_validate(payload)


def test_official_germanica_legacy_storage_is_losslessly_materialized() -> None:
    country = WorldPackageCountryStore(Path("config/world_packages/official_fax_world")).load_country("GER")
    assert (country.code, country.name, country.population, country.area_km2) == (
        "GER",
        "Germanica",
        169_702_055,
        870_516,
    )
    assert (country.squash_access, country.squash_popularity, country.squash_tradition, country.development_quality) == (
        5,
        3,
        3,
        5,
    )
    assert (country.competition_quality, country.elite_support, country.court_count, country.travel_region) == (
        4,
        5,
        1800,
        "EUROPE",
    )
    # Legacy style data is intentionally neutralized in V1. The read shim keeps
    # older callers safe but is never persisted/serialized as active country DNA.
    assert country.style_dna == {}
    assert "style_dna" not in country.model_dump()
    assert country.notes


def test_real_world_timelines_include_large_country_kosovo_and_fallback() -> None:
    store = WorldPackageCountryStore(Path("config/world_packages/real_world"))
    for code in ("USA", "XKX", "ALA"):
        country = store.load_country(code)
        assert country.population == country.population_by_year[2020]
        assert country.population_by_year[1955] > 0
        assert country.population_by_year[2050] > 0


def test_semantic_fingerprint_ignores_format_and_index_order_but_tracks_attribute(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    original = registry.get_official_package().fingerprint
    index = root / "official_fax_world/countries/index.json"
    data = json.loads(index.read_text())
    data["country_codes"].reverse()
    index.write_text(json.dumps(data, separators=(",", ":")))
    assert registry.get_official_package().fingerprint == original
    attribute = root / "official_fax_world/countries/GER/attributes/squash_popularity.json"
    data = json.loads(attribute.read_text())
    data["value"] = 4
    attribute.write_text(json.dumps(data, indent=8))
    assert registry.get_official_package().fingerprint != original


def test_clone_recursively_preserves_directory_country_storage(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    result = WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="example_world", name="Example", description=None, dry_run=False
    )
    assert result.ok and result.validation and result.validation.status == "valid"
    target = root / "custom/example_world"
    assert (target / "countries/GER/attributes/population.json").is_file()
    assert not (target / "countries.json").exists()
    assert WorldPackageCountryStore(target).load_country("GER") == WorldPackageCountryStore(
        root / "official_fax_world"
    ).load_country("GER")


def test_scalar_population_country_roundtrips_through_write_and_update(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "custom_world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    first = store.load_country("AAA")
    assert first.population == 1_234_567
    assert first.default_population_year == 2020
    assert first.default_population == 1_234_567
    assert first.population_by_year == {2020: 1_234_567}
    store.write_country(_scalar_country(name="Alpha Updated"))
    second = store.load_country("AAA")
    assert second.name == "Alpha Updated"
    assert second.population_by_year == {2020: 1_234_567}


def test_replace_dataset_restores_live_countries_when_stage_promotion_fails(tmp_path: Path, monkeypatch) -> None:
    store = WorldPackageCountryStore(tmp_path / "custom_world")
    store.replace_dataset(CountriesConfig(dataset_status="original", countries=[_scalar_country()]))
    original_rename = Path.rename

    def fail_stage_promotion(path: Path, target: Path):
        if path.name == "countries" and path.parent.name.startswith(".countries-stage-"):
            raise OSError("simulated promotion failure")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_stage_promotion)
    with pytest.raises(OSError, match="simulated promotion failure"):
        store.replace_dataset(CountriesConfig(dataset_status="replacement", countries=[_scalar_country(name="Replacement")]))
    restored = store.load_config()
    assert restored.dataset_status == "original"
    assert restored.countries[0].name == "Alpha"


def test_editable_custom_package_countries_are_not_reported_read_only(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    result = WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable_world", name="Editable", description=None, dry_run=False
    )
    assert result.ok
    countries = WorldPackageCountriesService(registry).get_countries("editable_world")
    assert countries is not None and countries.read_only is False


def test_clone_removes_target_and_fails_when_final_validation_has_errors(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    invalid = WorldPackageValidationResult("invalid_world", "errors", 1, 0, 0, [])
    monkeypatch.setattr(WorldPackageValidationService, "validate_package", lambda self, _world_id: invalid)
    result = WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="invalid_world", name="Invalid", description=None, dry_run=False
    )
    assert result.ok is False
    assert result.validation is invalid
    assert not (root / "custom/invalid_world").exists()
    assert (root / "official_fax_world").is_dir()


def test_legacy_builtin_is_readable_but_custom_write_is_canonical_v1(tmp_path: Path) -> None:
    official = Path("config/world_packages/official_fax_world/countries/GER/attributes")
    assert (official / "wealth_support.json").is_file()
    assert not (official / "squash_access.json").exists()

    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    store = WorldPackageCountryStore(root / "custom/editable")
    store.replace_country(store.load_country("GER"))
    attrs = store.countries_root / "GER/attributes"
    assert {path.stem for path in attrs.glob("*.json")} == {"population", *ATTRIBUTE_NAMES}
    for legacy in LEGACY_ATTRIBUTE_NAMES:
        assert not (attrs / f"{legacy}.json").exists()


def test_replace_country_preserves_index_population_and_cleans_artifacts(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    index = store.index_path.read_bytes()
    population = (store.countries_root / "AAA/attributes/population.json").read_bytes()
    store.replace_country(_scalar_country(name="Alpha Prime"))
    assert store.load_country("AAA").name == "Alpha Prime"
    assert store.index_path.read_bytes() == index
    assert (store.countries_root / "AAA/attributes/population.json").read_bytes() == population
    assert not list(store.countries_root.glob(".AAA-*"))


def test_replace_country_restores_live_country_when_promotion_fails(tmp_path: Path, monkeypatch) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    original_rename = Path.rename

    def fail(path: Path, target: Path):
        if path.name == "AAA" and path.parent.name == "countries" and path.parent.parent.name.startswith(".AAA-stage-"):
            raise OSError("promotion failed")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError, match="promotion failed"):
        store.replace_country(_scalar_country(name="Broken"))
    assert store.load_country("AAA").name == "Alpha"


def test_custom_country_edit_changes_fingerprint_preserves_population_and_writes_v1(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    service = WorldPackageCountriesService(registry, validation)
    before = registry.get_package("editable")
    assert before is not None
    detail = service.get_country("editable", "GER")
    assert detail is not None
    original = detail.country
    update = _country_update(
        original,
        name="Germanica Prime",
        squash_popularity=4,
        development_quality=4,
        expected_package_fingerprint=before.fingerprint,
    )
    result = service.update_country("editable", "GER", update)
    after = result.detail.country
    assert (after.code, after.name, after.squash_popularity, after.development_quality) == (
        "GER",
        "Germanica Prime",
        4,
        4,
    )
    assert after.population_by_year == original.population_by_year
    assert result.validation.status == "valid"
    assert result.detail.package.fingerprint != before.fingerprint
    attrs = root / "custom/editable/countries/GER/attributes"
    assert {path.stem for path in attrs.glob("*.json")} == {"population", *ATTRIBUTE_NAMES}
    assert not any((attrs / f"{legacy}.json").exists() for legacy in LEGACY_ATTRIBUTE_NAMES)


def test_official_country_edit_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    country = WorldPackageCountryStore(root / "official_fax_world").load_country("GER")
    with pytest.raises(WorldPackageMutationError) as exc:
        WorldPackageCountriesService(registry).update_country("official_fax_world", "GER", _country_update(country))
    assert exc.value.status_code == 403


@pytest.mark.parametrize("world_id", ["official_fax_world", "real_world"])
def test_builtin_country_edit_is_rejected_even_if_editable_metadata_is_true(tmp_path: Path, monkeypatch, world_id: str) -> None:
    root = tmp_path / "packages"
    shutil.copytree(f"config/world_packages/{world_id}", root / world_id)
    registry = WorldPackageRegistryService(world_packages_root=root)
    package = registry.get_package(world_id)
    assert package is not None
    monkeypatch.setattr(
        WorldPackageRegistryService,
        "get_package",
        lambda self, candidate: replace(package, editable=True) if candidate == world_id else None,
    )
    country = WorldPackageCountryStore(root / world_id).load_config().countries[0]
    with pytest.raises(WorldPackageMutationError) as exc:
        WorldPackageCountriesService(registry).update_country(world_id, country.code, _country_update(country))
    assert exc.value.status_code == 403


def test_country_edit_restores_original_after_final_validation_errors(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    store = WorldPackageCountryStore(root / "custom/editable")
    original = store.load_country("GER")
    index = store.index_path.read_bytes()
    payload = _country_update(original, name="Must Roll Back")
    invalid = WorldPackageValidationResult("editable", "errors", 1, 0, 0, [])
    monkeypatch.setattr(WorldPackageValidationService, "validate_package", lambda self, _world_id: invalid)
    with pytest.raises(WorldPackageMutationError, match="leave the World Package invalid"):
        WorldPackageCountriesService(registry, validation).update_country("editable", "GER", payload)
    assert store.load_country("GER") == original
    assert store.index_path.read_bytes() == index
    assert not list(store.countries_root.glob(".GER-*"))


def test_population_replacement_changes_only_population_and_materializes_default(tmp_path: Path) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    files = {path.relative_to(store.package_root): path.read_bytes() for path in store.package_root.rglob("*.json")}
    store.replace_population("AAA", {1995: 900_000, 2020: 2_000_000})
    country = store.load_country("AAA")
    assert country.population_by_year == {1995: 900_000, 2020: 2_000_000}
    assert country.population == country.default_population == 2_000_000
    changed = {path for path, data in files.items() if (store.package_root / path).read_bytes() != data}
    assert changed == {Path("countries/AAA/attributes/population.json")}


def test_population_service_fingerprint_non_default_and_rollback(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    store = WorldPackageCountryStore(root / "custom/editable")
    before = registry.get_package("editable")
    assert before is not None
    original = store.load_country("GER")
    update = WorldPackageCountryPopulationUpdate(
        population_by_year={1995: 30_000_000, 2020: 50_000_000},
        expected_package_fingerprint=before.fingerprint,
    )
    result = WorldPackageCountriesService(registry, validation).update_population("editable", "GER", update)
    after = result.detail.country
    assert after.population_by_year == {1995: 30_000_000, 2020: 50_000_000}
    assert after.population == after.default_population == 50_000_000
    assert result.detail.package.fingerprint != before.fingerprint

    current_package = registry.get_package("editable")
    assert current_package is not None
    invalid = WorldPackageValidationResult("editable", "errors", 1, 0, 0, [])
    monkeypatch.setattr(WorldPackageValidationService, "validate_package", lambda self, _world_id: invalid)
    with pytest.raises(WorldPackageMutationError, match="leave the World Package invalid"):
        WorldPackageCountriesService(registry, validation).update_population(
            "editable",
            "GER",
            WorldPackageCountryPopulationUpdate(
                population_by_year={2020: 99_000_000},
                expected_package_fingerprint=current_package.fingerprint,
            ),
        )
    assert store.load_country("GER") == after


def test_population_update_failure_after_replace_restores_original_and_cleans_artifacts(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    store = WorldPackageCountryStore(root / "custom/editable")
    before = store.load_country("GER")
    original_replace = store.replace_population
    calls = 0

    def fail_once_after_write(country_code: str, population_by_year: dict[int, int]) -> None:
        nonlocal calls
        calls += 1
        original_replace(country_code, population_by_year)
        if calls == 1:
            raise OSError("simulated post-write failure")

    monkeypatch.setattr(WorldPackageCountryStore, "replace_population", fail_once_after_write)
    with pytest.raises(OSError, match="simulated post-write failure"):
        WorldPackageCountriesService(registry, validation).update_population(
            "editable", "GER", WorldPackageCountryPopulationUpdate(population_by_year={2020: 123_000_000})
        )
    assert store.load_country("GER") == before
    assert not list(store.countries_root.glob(".GER-*"))


def test_delete_country_updates_index_and_removes_directory(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    service = WorldPackageCountriesService(registry, validation)
    store = WorldPackageCountryStore(root / "custom/editable")
    before = registry.get_package("editable")
    assert before is not None
    result = service.delete_country("editable", "GER", expected_package_fingerprint=before.fingerprint)
    assert store.load_country("GER") is None
    assert "GER" not in json.loads(store.index_path.read_text())["country_codes"]
    assert result.package.fingerprint != before.fingerprint
    assert result.validation.status == "valid"


def test_create_country_writes_identity_population_factors_and_index(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    service = WorldPackageCountriesService(registry, validation)
    before = registry.get_package("editable")
    assert before is not None
    create = WorldPackageCountryCreate(
        code="ABC",
        name="Alphabetia",
        notes="New country",
        area_km2=12345,
        region="EUROPE",
        travel_region="EUROPE",
        squash_popularity=2,
        squash_access=3,
        development_quality=4,
        competition_quality=3,
        elite_support=4,
        squash_tradition=1,
        court_count=12,
        population_by_year={1995: 900_000, 2020: 1_200_000},
        expected_package_fingerprint=before.fingerprint,
    )
    result = service.create_country("editable", create)
    detail = result.detail
    assert detail.country.code == "ABC"
    assert detail.country.population == detail.country.default_population == 1_200_000
    assert detail.country.default_population_year == 2020
    assert detail.country.population_by_year == {1995: 900_000, 2020: 1_200_000}
    assert detail.country.squash_access == 3
    assert detail.country.development_quality == 4
    assert detail.country.competition_quality == 3
    assert detail.country.elite_support == 4
    assert detail.package.fingerprint != before.fingerprint
    assert detail.validation if hasattr(detail, "validation") else True
    assert "ABC" in json.loads(WorldPackageCountryStore(root / "custom/editable").index_path.read_text())["country_codes"]
