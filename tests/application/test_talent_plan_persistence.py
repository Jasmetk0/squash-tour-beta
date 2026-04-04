from __future__ import annotations

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _service(tmp_path) -> SimulationApiService:
    db_file = tmp_path / "talent_plan_persistence.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(repository=repository)


def test_initialize_run_persists_talent_plan_and_provenance(tmp_path) -> None:
    service = _service(tmp_path)

    service.initialize_run(
        run_id="run-a",
        season=2028,
        seed=42,
        config_version="v1",
        config_fingerprint="fp-1",
    )

    plan = service.get_run_talent_plan_summary(run_id="run-a")
    provenance = service.list_generated_player_provenance(run_id="run-a")

    assert plan.run_id == "run-a"
    assert plan.total_talents > 0
    assert len(plan.countries) > 0
    assert sum(country.planned_count for country in plan.countries) == plan.total_talents
    assert len(provenance) == plan.total_talents
    assert {row.player_id for row in provenance}
    assert all(row.run_id == "run-a" for row in provenance)
    assert all(row.source_type == "planner_generated" for row in provenance)


def test_same_seed_and_config_produces_identical_persisted_plan_and_provenance(tmp_path) -> None:
    service = _service(tmp_path)

    service.initialize_run(run_id="run-left", season=2030, seed=777, config_version="v2", config_fingerprint="fp")
    service.initialize_run(run_id="run-right", season=2030, seed=777, config_version="v2", config_fingerprint="fp")

    left_plan = service.get_run_talent_plan_summary(run_id="run-left")
    right_plan = service.get_run_talent_plan_summary(run_id="run-right")
    assert left_plan.total_talents == right_plan.total_talents
    assert [record.__dict__ for record in left_plan.countries] == [record.__dict__ for record in right_plan.countries]

    left_provenance = service.list_generated_player_provenance(run_id="run-left")
    right_provenance = service.list_generated_player_provenance(run_id="run-right")
    normalized_left = [{k: v for k, v in row.__dict__.items() if k != "run_id"} for row in left_provenance]
    normalized_right = [{k: v for k, v in row.__dict__.items() if k != "run_id"} for row in right_provenance]
    assert normalized_left == normalized_right


def test_bootstrap_run_does_not_claim_fresh_generation_provenance(tmp_path) -> None:
    service = _service(tmp_path)

    service.initialize_run(run_id="parent", season=2028, seed=101, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="parent")
    service.rollover_to_next_season(run_id="parent")
    service.bootstrap_next_season_run(run_id="parent", child_run_id="child", child_seed=202)

    try:
        service.get_run_talent_plan_summary(run_id="child")
    except KeyError:
        pass
    else:
        raise AssertionError("bootstrapped child run should not have fresh annual talent plan persisted")

    child_provenance = service.list_generated_player_provenance(run_id="child")
    assert child_provenance == []
