from __future__ import annotations

import pytest

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import DatabaseSettings, SimulationRunInfo, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


def _service(tmp_path) -> SimulationApiService:
    db_file = tmp_path / "bootstrap_app.db"
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{db_file}"))
    session_factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=session_factory)
    return SimulationApiService(repository=repository)


def test_bootstrap_next_season_requires_persisted_rollover(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5151, config_version=None, config_fingerprint=None)

    with pytest.raises(ValueError, match="No persisted rollover"):
        service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child")


def test_bootstrap_next_season_creates_child_run_with_lineage_and_simulation(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5252, config_version="mvp", config_fingerprint="cfg-1")
    service.simulate_full_season(run_id="run-parent")
    service.rollover_to_next_season(run_id="run-parent")

    bootstrap = service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child")
    assert bootstrap.already_bootstrapped is False
    assert bootstrap.to_season == 2028

    child_summary = service.get_run_summary(run_id="run-child")
    assert child_summary.season == 2028

    lineage = service.get_run_lineage(run_id="run-parent")
    assert lineage.children == ["run-child"]

    child_source = service.get_run_source(run_id="run-child")
    assert child_source.source_type == "rollover_bootstrap"
    assert child_source.parent_run_id == "run-parent"
    assert child_source.source_rollover_to_season == 2028

    step = service.simulate_next_week(run_id="run-child")
    assert step.mode == "simulate_next_week"
    assert step.season_state.season == 2028

    child_plan = service.get_run_talent_plan_summary(run_id="run-child")
    assert child_plan.season == 2028
    assert child_plan.total_talents > 0

    child_provenance = service.list_generated_player_provenance(run_id="run-child")
    assert any(row.source_type == "rollover_carried" for row in child_provenance)
    assert any(row.source_type == "planner_generated" for row in child_provenance)


def test_bootstrap_next_season_is_idempotent_and_rejects_conflicting_child_seed(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5353, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-parent")
    service.rollover_to_next_season(run_id="run-parent")

    first = service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child", child_seed=999)
    second = service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child", child_seed=999)

    assert first.already_bootstrapped is False
    assert second.already_bootstrapped is True
    assert first.model_dump(exclude={"already_bootstrapped"}) == second.model_dump(exclude={"already_bootstrapped"})

    with pytest.raises(ValueError, match="conflicting bootstrap metadata"):
        service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child", child_seed=1000)


def test_child_run_uses_rollover_player_pool_for_next_rollover(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5454, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-parent")
    service.rollover_to_next_season(run_id="run-parent")

    parent_next_players = service.list_next_season_players(run_id="run-parent", to_season=2028)
    player_ages_2028 = {record.player_id: record.state.player.age for record in parent_next_players}

    service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child")
    service.simulate_full_season(run_id="run-child")
    service.rollover_to_next_season(run_id="run-child")

    child_transitions = service.list_player_transitions(run_id="run-child", to_season=2029)
    observed_age_before = {transition.player_id: transition.transition.age_before for transition in child_transitions}

    common_player_ids = sorted(set(player_ages_2028).intersection(observed_age_before))
    assert common_player_ids
    sample_id = common_player_ids[0]
    assert observed_age_before[sample_id] == player_ages_2028[sample_id]


def test_bootstrap_child_player_pool_merges_carried_and_intake_without_duplicates(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5656, config_version=None, config_fingerprint=None)
    service.simulate_full_season(run_id="run-parent")
    service.rollover_to_next_season(run_id="run-parent")

    carried = service.list_next_season_players(run_id="run-parent", to_season=2028)
    carried_ids = {record.player_id for record in carried}
    assert carried_ids

    service.bootstrap_next_season_run(run_id="run-parent", child_run_id="run-child")

    child_provenance = service.list_generated_player_provenance(run_id="run-child")
    child_run_info = service.repository.get_simulation_run(run_id="run-child")
    assert child_run_info is not None
    child_players = service._load_players_by_id_for_run(run_info=child_run_info)

    assert carried_ids.issubset(set(child_players))
    assert len(child_players) > len(carried_ids)
    assert len(child_players) == len(set(child_players))
    assert {row.source_type for row in child_provenance} >= {"rollover_carried", "planner_generated"}


def test_legacy_source_types_are_normalized_to_canonical_contract(tmp_path) -> None:
    service = _service(tmp_path)
    service.initialize_run(run_id="run-parent", season=2027, seed=5555, config_version=None, config_fingerprint=None)
    service.repository.upsert_simulation_run(
        SimulationRunInfo(
            run_id="run-legacy",
            season=2028,
            seed=5555,
            parent_run_id="run-parent",
            source_type="bootstrap",
        )
    )
    service.repository.save_season_state(run_id="run-legacy", state=service.get_season_state(run_id="run-parent"))

    legacy_source = service.get_run_source(run_id="run-legacy")
    assert legacy_source.source_type == "rollover_bootstrap"

    legacy_lineage = service.get_run_lineage(run_id="run-legacy")
    assert legacy_lineage.source.source_type == "rollover_bootstrap"

    runs_index = service.list_runs_index()
    legacy_index = next(row for row in runs_index if row.run_id == "run-legacy")
    assert legacy_index.source_type == "rollover_bootstrap"
