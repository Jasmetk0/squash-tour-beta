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
    "timezone_area",
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
    assert country.style_dna == {}
    assert country.notes


def test_official_hungarica_fractional_legacy_rating_is_lossless() -> None:
    country = WorldPackageCountryStore(Path("config/world_packages/official_fax_world")).load_country("HUN")

    assert country.competition_quality == 2.5


def test_canonical_fractional_rating_round_trips_without_legacy_output(tmp_path: Path) -> None:
    root = tmp_path / "world"
    (root / "countries").mkdir(parents=True)
    (root / "countries/index.json").write_text(
        json.dumps({"schema_version": "world_package_countries_index.v1", "country_codes": ["AAA"]})
    )
    store = WorldPackageCountryStore(root)
    store.write_country(_scalar_country().model_copy(update={"competition_quality": 2.5}))

    assert store.load_country("AAA").competition_quality == 2.5
    value = json.loads((root / "countries/AAA/attributes/competition_quality.json").read_text())["value"]
    assert value == 2.5
    for legacy_name in LEGACY_ATTRIBUTE_NAMES:
        assert not (root / f"countries/AAA/attributes/{legacy_name}.json").exists()


def test_real_world_timelines_include_large_country_kosovo_and_fallback() -> None:
    store = WorldPackageCountryStore(Path("config/world_packages/real_world"))
    for code in ("USA", "XKX", "ALA"):
        country = store.load_country(code)
        assert country.population == country.population_by_year[2020]
        assert country.population_by_year[1955] > 0
        assert country.population_by_year[2050] > 0


@pytest.mark.smoke
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
    service = WorldPackageCountriesService(registry, validation)
    before = service.get_country("editable", "GER")
    assert before is not None
    fingerprint = before.package.fingerprint
    result = service.update_population(
        "editable",
        "GER",
        WorldPackageCountryPopulationUpdate(
            values_by_year={1995: 100, 2020: before.country.population},
            expected_package_fingerprint=fingerprint,
        ),
    )
    assert result.detail.country.population == before.country.population
    assert result.detail.country.population_by_year[1995] == 100
    assert result.detail.package.fingerprint != fingerprint
    original = (root / "custom/editable/countries/GER/attributes/population.json").read_bytes()
    invalid = WorldPackageValidationResult("editable", "errors", 1, 0, 0, [])
    monkeypatch.setattr(WorldPackageValidationService, "validate_package", lambda self, _world_id: invalid)
    with pytest.raises(WorldPackageMutationError, match="leave the World Package invalid"):
        service.update_population("editable", "GER", WorldPackageCountryPopulationUpdate(values_by_year={2020: 999}))
    assert (root / "custom/editable/countries/GER/attributes/population.json").read_bytes() == original


def _country_create(fingerprint: str) -> WorldPackageCountryCreate:
    return WorldPackageCountryCreate(
        code="ABC",
        name="Alphabetia",
        notes="Authored country",
        area_km2=1234,
        region="EUROPE",
        travel_region="EUROPE",
        court_count=12,
        squash_popularity=2,
        squash_access=3,
        development_quality=4,
        competition_quality=3,
        elite_support=4,
        squash_tradition=1,
        population_by_year={1995: 900_000, 2020: 1_200_000},
        expected_package_fingerprint=fingerprint,
    )


def test_country_create_delete_are_scoped_ordered_and_change_fingerprint(tmp_path: Path) -> None:
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
    store = WorldPackageCountryStore(root / "custom/editable")
    existing = {
        path.relative_to(store.countries_root): path.read_bytes()
        for path in store.countries_root.rglob("*.json")
        if "index.json" not in str(path)
    }
    created = service.create_country("editable", _country_create(before.fingerprint))
    assert created.detail.country.population == 1_200_000
    assert created.detail.country.population_by_year == {1995: 900_000, 2020: 1_200_000}
    assert store.load_index().country_codes == sorted(store.load_index().country_codes)
    assert store.load_index().country_codes.count("ABC") == 1
    assert created.detail.package.fingerprint != before.fingerprint
    assert created.validation.status == "valid"
    attrs = store.countries_root / "ABC/attributes"
    assert {path.stem for path in attrs.glob("*.json")} == {"population", *ATTRIBUTE_NAMES}
    assert all((store.countries_root / path).read_bytes() == value for path, value in existing.items())
    deleted = service.delete_country("editable", "ABC", created.detail.package.fingerprint)
    assert deleted.package.fingerprint != created.detail.package.fingerprint
    assert deleted.validation.status == "valid"
    assert "ABC" not in store.load_index().country_codes
    assert not (store.countries_root / "ABC").exists()
    assert all((store.countries_root / path).read_bytes() == value for path, value in existing.items())


@pytest.mark.parametrize("failure", ["errors", "exception"])
def test_country_lifecycle_validation_failure_restores_exact_state(tmp_path: Path, monkeypatch, failure: str) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    real_validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, real_validation).clone_official_world(
        new_world_id="editable", name="Editable", description=None, dry_run=False
    ).ok
    service = WorldPackageCountriesService(registry, real_validation)
    store = WorldPackageCountryStore(root / "custom/editable")
    before = registry.get_package("editable")
    assert before is not None
    index = store.index_path.read_bytes()

    def fail(*_):
        if failure == "exception":
            raise RuntimeError("validation exploded")
        return WorldPackageValidationResult("editable", "errors", 1, 0, 0, [])

    with monkeypatch.context() as scoped:
        scoped.setattr(WorldPackageValidationService, "validate_package", fail)
        with pytest.raises(WorldPackageMutationError):
            service.create_country("editable", _country_create(before.fingerprint))
    assert store.index_path.read_bytes() == index
    assert not (store.countries_root / "ABC").exists()

    created = service.create_country("editable", _country_create(before.fingerprint))
    index = store.index_path.read_bytes()
    country = store.load_country("ABC")
    with monkeypatch.context() as scoped:
        scoped.setattr(WorldPackageValidationService, "validate_package", fail)
        with pytest.raises(WorldPackageMutationError):
            service.delete_country("editable", "ABC", created.detail.package.fingerprint)
    assert store.index_path.read_bytes() == index
    assert store.load_country("ABC") == country


def _lifecycle_store(tmp_path: Path):
    store = WorldPackageCountryStore(tmp_path / "world")
    abc = _scalar_country(name="Alphabetia").model_copy(update={"code": "ABC"})
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country(), abc]))
    return store, store.load_country("ABC")


def _canonical_lifecycle_country(code: str = "ABC") -> Country:
    country = _scalar_country(name="Alphabetia").model_copy(update={"code": code})
    return country.model_copy(
        update={
            "default_population_year": 2020,
            "default_population": country.population,
            "population_by_year": {2020: country.population},
        }
    )


def test_create_country_directory_promotion_failure_restores_everything(tmp_path: Path, monkeypatch) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    index = store.index_path.read_bytes()
    existing = {path.relative_to(store.package_root): path.read_bytes() for path in store.package_root.rglob("*.json")}
    country = _canonical_lifecycle_country()
    original = Path.rename

    def fail(path: Path, target: Path):
        if path.name == "ABC" and "-create-" in str(path.parent):
            raise OSError("country promotion failed")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises(OSError, match="country promotion failed"):
        store.create_country(country)
    assert store.index_path.read_bytes() == index
    assert not (store.countries_root / "ABC").exists()
    assert {path.relative_to(store.package_root): path.read_bytes() for path in store.package_root.rglob("*.json")} == existing


def test_create_country_index_promotion_failure_rolls_back(tmp_path: Path, monkeypatch) -> None:
    store = WorldPackageCountryStore(tmp_path / "world")
    store.replace_dataset(CountriesConfig(dataset_status="test", countries=[_scalar_country()]))
    index = store.index_path.read_bytes()
    country = _canonical_lifecycle_country()
    original = Path.replace
    failed = False

    def fail_once(path: Path, target: Path):
        nonlocal failed
        if not failed and path.name.startswith(".index.json."):
            failed = True
            raise OSError("index promotion failed")
        return original(path, target)

    monkeypatch.setattr(Path, "replace", fail_once)
    with pytest.raises(OSError, match="index promotion failed"):
        store.create_country(country)
    assert store.index_path.read_bytes() == index
    assert not (store.countries_root / "ABC").exists()


def test_delete_country_index_promotion_failure_restores_country(tmp_path: Path, monkeypatch) -> None:
    store, abc = _lifecycle_store(tmp_path)
    index = store.index_path.read_bytes()
    original = Path.replace
    failed = False

    def fail_once(path: Path, target: Path):
        nonlocal failed
        if not failed and path.name.startswith(".index.json."):
            failed = True
            raise OSError("delete index promotion failed")
        return original(path, target)

    monkeypatch.setattr(Path, "replace", fail_once)
    with pytest.raises(OSError, match="delete index promotion failed"):
        store.delete_country("ABC")
    assert store.index_path.read_bytes() == index
    assert store.load_country("ABC") == abc


def test_delete_cleanup_failure_happens_after_semantic_commit(tmp_path: Path, monkeypatch) -> None:
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
    created = service.create_country("editable", _country_create(before.fingerprint))

    def partial_cleanup(backup: Path) -> None:
        (backup / "country.json").unlink()
        raise OSError("cleanup interrupted")

    monkeypatch.setattr(WorldPackageCountryStore, "finalize_delete", staticmethod(partial_cleanup))
    result = service.delete_country("editable", "ABC", created.detail.package.fingerprint)
    assert result.deleted_country_code == "ABC"
    assert "ABC" not in store.load_index().country_codes
    assert not (store.countries_root / "ABC").exists()
    assert store.load_config().countries


def test_timezone_registry_mutation_roundtrip_fingerprint_and_country_reference(tmp_path: Path) -> None:
    from beta_engine.domain.timezone_areas import TimezoneArea
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    validation = WorldPackageValidationService(registry)
    assert WorldPackageCloneService(registry, validation).clone_official_world(new_world_id="editable", name="Editable", description=None, dry_run=False).ok
    service = WorldPackageCountriesService(registry, validation)
    before = registry.get_package("editable")
    assert before is not None and before.timezone_area_count == 0
    geography = service.replace_timezone_areas("editable", [TimezoneArea(code="WEST",name="West",position=0), TimezoneArea(code="EAST",name="East",position=1)], before.fingerprint)
    assert [x.code for x in geography.timezone_areas] == ["WEST", "EAST"]
    after = registry.get_package("editable")
    assert after is not None and after.fingerprint != before.fingerprint and after.timezone_area_count == 2
    reordered = service.replace_timezone_areas("editable", [TimezoneArea(code="EAST",name="East",position=0), TimezoneArea(code="WEST",name="West",position=1)], after.fingerprint)
    reordered_package = registry.get_package("editable")
    assert reordered_package is not None and reordered_package.fingerprint != after.fingerprint
    country = service.get_country("editable", "GER").country
    update = _country_update(country, timezone_area="EAST", expected_package_fingerprint=reordered_package.fingerprint)
    result = service.update_country("editable", "GER", update)
    assert result.detail.country.timezone_area == "EAST"
    assert result.detail.timezone_area.code == "EAST"
    reloaded = WorldPackageCountryStore(root / "custom/editable").load_country("GER")
    assert reloaded.timezone_area == "EAST" and reloaded.travel_region == country.travel_region
    with pytest.raises(WorldPackageMutationError, match="unknown Timezone Area"):
        service.update_country("editable", "GER", _country_update(reloaded, timezone_area="MISSING", expected_package_fingerprint=result.detail.package.fingerprint))

@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "not valid JSON"),
        ('{"schema_version":"country_attribute.v999","value":"A"}', "unsupported schema_version"),
    ],
)
def test_existing_malformed_timezone_area_attribute_fails(tmp_path: Path, content: str, message: str) -> None:
    root = tmp_path / "package"
    shutil.copytree("config/world_packages/official_fax_world", root)
    path = root / "countries/GER/attributes/timezone_area.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        WorldPackageCountryStore(root).load_country("GER")


def test_missing_legacy_timezone_area_attribute_loads_none(tmp_path: Path) -> None:
    root = tmp_path / "package"
    shutil.copytree("config/world_packages/official_fax_world", root)
    assert not (root / "countries/GER/attributes/timezone_area.json").exists()
    assert WorldPackageCountryStore(root).load_country("GER").timezone_area is None


def test_legacy_fingerprint_stays_stable_until_timezone_data_is_authored(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    registry = WorldPackageRegistryService(world_packages_root=root)
    before = registry.get_official_package().fingerprint
    # Regression value from pre-Timezone-Area support: optional schema support is not semantic content.
    assert before == "4113f00b2f9c68e511b7ab8aa65c1139003f666bdb909a9e09c5c86888fc5ae9"
    # Loading support alone does not materialize either optional storage layer.
    assert not (root / "official_fax_world/geography/timezone_areas.json").exists()
    assert registry.get_official_package().fingerprint == before


def test_legacy_missing_timezone_layer_is_visible_consistent_info(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    shutil.copytree("config/world_packages/official_fax_world", root / "official_fax_world")
    result = WorldPackageValidationService(WorldPackageRegistryService(world_packages_root=root)).validate_package("official_fax_world")
    assert result is not None and result.status == "valid"
    check = next(item for item in result.checks if item.code == "timezone_areas_unavailable")
    assert (check.severity, check.status) == ("info", "passed")
