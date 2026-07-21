from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from beta_engine.application.api_services import SimulationApiService
from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID, REAL_WORLD_ID
from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


class _RegistryStub:
    def __init__(self, known: set[str]) -> None:
        self.known = known

    def get_package(self, world_id: str):
        if world_id in self.known:
            return SimpleNamespace(world_id=world_id)
        return None


def _repository(tmp_path):
    db_file = tmp_path / "runs.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    repository.bootstrap_schema()
    return repository


def _service(tmp_path, *, known_worlds: set[str] | None = None) -> SimulationApiService:
    return SimulationApiService(
        repository=_repository(tmp_path),
        world_package_registry_service=_RegistryStub(known_worlds or {OFFICIAL_FAX_WORLD_ID}),
    )


def test_create_run_defaults_to_official_world_id_and_exposes_it(tmp_path) -> None:
    service = _service(tmp_path)

    summary = service.initialize_run(run_id="run-default-world", season=2027, seed=1001, config_version=None, config_fingerprint=None)

    assert summary.world_id == OFFICIAL_FAX_WORLD_ID
    assert service.repository.get_simulation_run(run_id="run-default-world").world_id == OFFICIAL_FAX_WORLD_ID
    assert service.get_run_summary(run_id="run-default-world").world_id == OFFICIAL_FAX_WORLD_ID
    assert service.list_runs_index()[0].world_id == OFFICIAL_FAX_WORLD_ID


def test_create_run_accepts_explicit_official_world_id(tmp_path) -> None:
    service = _service(tmp_path)

    summary = service.initialize_run(
        run_id="run-explicit-official",
        season=2027,
        seed=1002,
        config_version=None,
        config_fingerprint=None,
        world_id=OFFICIAL_FAX_WORLD_ID,
    )

    assert summary.world_id == OFFICIAL_FAX_WORLD_ID


def test_create_run_accepts_real_world_and_uses_package_countries(tmp_path) -> None:
    registry = WorldPackageRegistryService(
        countries_service=CountriesConfigService(),
        manual_overrides_service=ManualPlayerOverridesService(),
    )
    service = SimulationApiService(repository=_repository(tmp_path), world_package_registry_service=registry)

    summary = service.initialize_run(
        run_id="run-real-world",
        season=2027,
        seed=1008,
        config_version=None,
        config_fingerprint=None,
        world_id=REAL_WORLD_ID,
    )

    allocations = service.repository.list_run_talent_country_allocations(run_id="run-real-world")
    assert summary.world_id == REAL_WORLD_ID
    assert len(allocations) > 4


def test_create_run_rejects_unknown_world_id(tmp_path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="world package 'missing_world' was not found"):
        service.initialize_run(
            run_id="run-unknown-world",
            season=2027,
            seed=1003,
            config_version=None,
            config_fingerprint=None,
            world_id="missing_world",
        )


def test_create_run_rejects_known_custom_world_id_until_generation_is_package_scoped(tmp_path) -> None:
    service = _service(tmp_path, known_worlds={OFFICIAL_FAX_WORLD_ID, "custom_world"})

    with pytest.raises(ValueError, match="custom world package run creation is not enabled yet"):
        service.initialize_run(
            run_id="run-custom-world",
            season=2027,
            seed=1004,
            config_version=None,
            config_fingerprint=None,
            world_id="custom_world",
        )


def test_list_simulation_runs_preserves_non_null_stored_world_id(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.upsert_simulation_run(
        SimulationRunInfo(run_id="run-custom-row", season=2027, seed=1, world_id="custom_world")
    )

    runs = repository.list_simulation_runs()

    assert len(runs) == 1
    assert runs[0].world_id == "custom_world"


def test_run_index_preserves_repository_world_id_lock(tmp_path) -> None:
    service = _service(tmp_path)
    service.repository.upsert_simulation_run(
        SimulationRunInfo(run_id="run-custom-index", season=2027, seed=2, world_id="custom_world")
    )
    state = service._build_orchestrator(season=2027, seed=2, run_info=None).initialize_state()
    service.repository.save_season_state(run_id="run-custom-index", state=state)

    index = service.list_runs_index()

    assert len(index) == 1
    assert index[0].world_id == "custom_world"


def test_legacy_run_without_world_id_reads_as_official_world_id(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-legacy", season=2027, seed=1005))
    with repository._engine.begin() as connection:
        connection.execute(text("UPDATE simulation_runs SET world_id = NULL WHERE run_id = 'run-legacy'"))

    run = repository.get_simulation_run(run_id="run-legacy")
    runs = repository.list_simulation_runs()
    lineage = repository.get_run_lineage(run_id="run-legacy")

    assert run is not None
    assert run.world_id == OFFICIAL_FAX_WORLD_ID
    assert runs[0].world_id == OFFICIAL_FAX_WORLD_ID
    assert lineage is not None
    assert lineage.world_id == OFFICIAL_FAX_WORLD_ID


def test_upsert_preserves_existing_world_id_lock(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-lock", season=2027, seed=1006, world_id=OFFICIAL_FAX_WORLD_ID))
    repository.upsert_simulation_run(SimulationRunInfo(run_id="run-lock", season=2027, seed=1007, world_id="custom_world"))

    run = repository.get_simulation_run(run_id="run-lock")

    assert run is not None
    assert run.seed == 1007
    assert run.world_id == OFFICIAL_FAX_WORLD_ID
