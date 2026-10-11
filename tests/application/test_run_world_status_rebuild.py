from __future__ import annotations
from tests.support.world_packages import load_fax_reference_countries

import json
from pathlib import Path

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.domain.countries import CountriesConfig
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
from beta_engine.infrastructure.world_config import load_manual_player_overrides_config
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from tests.support.world_packages import materialize_test_world_package


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _service(tmp_path: Path, *, countries_payload: dict[str, object] | None = None, overrides_payload: dict[str, object] | None = None) -> SimulationApiService:
    db_file = tmp_path / "run_world_status.db"
    overrides_path = tmp_path / "manual_player_overrides.json"
    packages_root = tmp_path / "world_packages"
    materialize_test_world_package(packages_root, CountriesConfig.model_validate(countries_payload or load_fax_reference_countries().model_dump(mode="json")))
    _write_json(overrides_path, overrides_payload or load_manual_player_overrides_config().model_dump(mode="json"))

    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(
        repository=repository,
        manual_overrides_service=ManualPlayerOverridesService(config_path=overrides_path),
        world_package_registry_service=WorldPackageRegistryService(world_packages_root=packages_root),
    )


def test_unchanged_world_data_reports_fresh_status(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-fresh", season=2027, seed=100, config_version=None, config_fingerprint=None)

    status = service.get_run_world_status(run_id="run-fresh")
    assert status.is_stale is False
    assert status.rebuild_supported is True
    assert status.stored_world_generation_fingerprint == status.current_world_generation_fingerprint


def test_changed_countries_dataset_marks_run_as_stale(tmp_path: Path) -> None:
    countries_payload = load_fax_reference_countries().model_dump(mode="json")
    service = _service(tmp_path, countries_payload=countries_payload)
    service.initialize_run(run_id="run-stale-countries", season=2027, seed=100, config_version=None, config_fingerprint=None)

    store = WorldPackageCountryStore(tmp_path / "world_packages/official_fax_world")
    country = store.load_config().countries[0]
    store.write_country(country.model_copy(update={"population": country.population + 1, "default_population": country.population + 1, "population_by_year": {2020: country.population + 1}}))

    status = service.get_run_world_status(run_id="run-stale-countries")
    assert status.is_stale is True


def test_changed_manual_overrides_marks_run_as_stale(tmp_path: Path) -> None:
    overrides_payload = load_manual_player_overrides_config().model_dump(mode="json")
    service = _service(tmp_path, overrides_payload=overrides_payload)
    service.initialize_run(run_id="run-stale-overrides", season=2027, seed=100, config_version=None, config_fingerprint=None)

    overrides_payload["overrides"].append(
        {
            "override_id": "stale-check",
            "season": 2027,
            "country_code": "GER",
            "player_name": "Stale Check",
            "age": 19,
            "profile_tier": "elite",
            "enabled": True,
        }
    )
    _write_json(tmp_path / "manual_player_overrides.json", overrides_payload)

    status = service.get_run_world_status(run_id="run-stale-overrides")
    assert status.is_stale is True


def test_progressed_and_child_runs_report_rebuild_not_supported(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=200, config_version=None, config_fingerprint=None)
    service.simulate_next_week(run_id="run-parent")
    progressed = service.get_run_world_status(run_id="run-parent")
    assert progressed.rebuild_supported is False

    service.initialize_run(run_id="run-base", season=2027, seed=300, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-base")
    service.rollover_to_next_season(run_id="run-base")
    service.bootstrap_next_season_run(run_id="run-base", child_run_id="run-child")
    child = service.get_run_world_status(run_id="run-child")
    assert child.source_type == "rollover_bootstrap"
    assert child.rebuild_supported is False


def test_rebuild_regenerates_world_artifacts_and_updates_fingerprint(tmp_path: Path) -> None:
    overrides_payload = load_manual_player_overrides_config().model_dump(mode="json")
    service = _service(tmp_path, overrides_payload=overrides_payload)
    service.initialize_run(run_id="run-rebuild", season=2027, seed=500, config_version=None, config_fingerprint=None)
    before_status = service.get_run_world_status(run_id="run-rebuild")
    before_provenance = service.list_generated_player_provenance(run_id="run-rebuild")

    overrides_payload["overrides"].append(
        {
            "override_id": "rebuild-star",
            "season": 2027,
            "country_code": "GER",
            "player_name": "Rebuild Star",
            "age": 18,
            "profile_tier": "special",
            "enabled": True,
        }
    )
    _write_json(tmp_path / "manual_player_overrides.json", overrides_payload)

    status = service.rebuild_run_world(run_id="run-rebuild")
    after_provenance = service.list_generated_player_provenance(run_id="run-rebuild")
    assert status.rebuild_supported is True
    assert status.is_stale is False
    assert status.stored_world_generation_fingerprint == status.current_world_generation_fingerprint
    assert status.stored_world_generation_fingerprint != before_status.stored_world_generation_fingerprint
    assert any(row.override_id == "rebuild-star" for row in after_provenance if row.source_type == "manual_override")
    assert len(after_provenance) > len(before_provenance)


def test_rebuild_is_deterministic_for_same_current_world_data(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-deterministic", season=2027, seed=600, config_version=None, config_fingerprint=None)
    first_status = service.rebuild_run_world(run_id="run-deterministic")
    first = [row.__dict__ for row in service.list_generated_player_provenance(run_id="run-deterministic")]
    second_status = service.rebuild_run_world(run_id="run-deterministic")
    second = [row.__dict__ for row in service.list_generated_player_provenance(run_id="run-deterministic")]

    assert first_status.stored_world_generation_fingerprint == second_status.stored_world_generation_fingerprint
    assert second_status.is_stale is False
    assert first == second
