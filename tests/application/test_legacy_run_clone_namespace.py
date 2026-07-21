from __future__ import annotations

import pytest
from sqlalchemy import select

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import (
    DatabaseSettings, LegacyRunCloneError, LegacyRunCloneTargetExistsError,
    SimulationPersistenceRepository, create_session_factory, create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchStateModel, LegacySimulationRunMappingModel,
    RunBranchModel, RunContainerModel, SeasonStateModel, SimulationRunModel,
)


def _service(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'clone.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    return repository, service


def test_clone_namespace_creates_only_remapped_legacy_data(tmp_path) -> None:
    repository, service = _service(tmp_path)
    before = repository.inspect_legacy_run_clone_inventory(simulation_run_id="source")

    result = service.clone_legacy_simulation_run_namespace(
        source_simulation_run_id="source", target_simulation_run_id="target", target_seed=99
    )

    assert result.created_mapping is False
    assert result.created_branch is False
    assert result.source_product_run_id == "source"
    assert result.target_product_run_id is None
    assert result.source_inventory_hash == before.inventory.inventory_hash
    assert repository.get_simulation_run(run_id="source").seed == 47
    target = repository.get_simulation_run(run_id="target")
    assert target is not None and target.seed == 99
    assert target.parent_run_id == "source" and target.source_type == "branch_clone"
    assert target.world_id == repository.get_simulation_run(run_id="source").world_id
    assert repository.load_season_state(run_id="target") is not None
    assert repository.inspect_legacy_run_clone_inventory(simulation_run_id="target").clone_safe is True
    with repository._session_factory() as session:
        assert session.get(LegacySimulationRunMappingModel, "target") is None
        assert session.get(RunContainerModel, "target") is None
        assert session.execute(select(RunBranchModel).where(RunBranchModel.legacy_simulation_run_id == "target")).scalars().all() == []
        assert session.execute(select(BranchStateModel).where(BranchStateModel.branch_id == "target")).scalars().all() == []
        assert session.execute(select(BranchCheckpointModel).where(BranchCheckpointModel.checkpoint_id == "target")).scalars().all() == []


def test_clone_namespace_rejects_existing_or_same_target_without_partial_target(tmp_path) -> None:
    repository, service = _service(tmp_path)
    with pytest.raises(LegacyRunCloneError, match="differ"):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="source")
    service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    with pytest.raises(LegacyRunCloneTargetExistsError):
        service.clone_legacy_simulation_run_namespace(source_simulation_run_id="source", target_simulation_run_id="target")
    with repository._session_factory() as session:
        assert session.get(SimulationRunModel, "target") is not None
        assert session.get(SeasonStateModel, "target") is not None
