from __future__ import annotations

from collections.abc import Callable

import pytest

from test_simulation_api import ApiServer, _request

from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import (
    BranchCheckpointModel, BranchForkCommandModel, BranchStateModel,
    LegacySimulationRunMappingModel, OfficialBranchSelectionCommandModel,
    RunBranchModel, RunContainerModel, SimulationRunModel,
)


def _repository(url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def _snapshot(repository: SimulationPersistenceRepository) -> dict[str, list[dict[str, object]]]:
    models = (RunContainerModel, RunBranchModel, BranchStateModel, BranchCheckpointModel,
              SimulationRunModel, LegacySimulationRunMappingModel,
              OfficialBranchSelectionCommandModel, BranchForkCommandModel)
    with repository._session_factory() as session:
        return {model.__tablename__: [
            {column.name: getattr(row, column.name) for column in model.__table__.columns}
            for row in session.query(model).order_by(*model.__table__.primary_key.columns).all()
        ] for model in models}


def _coherent_run(server: ApiServer, run_id: str = "run/a #1") -> tuple[str, str]:
    assert _request("POST", f"{server.base_url}/runs", {"run_id": run_id, "seed": 47, "season": 2027})[0] == 201
    status, branches = _request("GET", f"{server.base_url}/run-branches?run_id={run_id.replace('/', '%2F').replace(' ', '%20').replace('#', '%23')}")
    assert status == 200
    branch_id = branches["run_branches"][0]["branch_id"]
    status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": run_id})
    assert status == 200
    return branch_id, checkpoint["checkpoint_id"]


def _context_url(server: ApiServer, run_id: str = "run/a #1") -> str:
    return f"{server.base_url}/viewer/runs/{run_id.replace('/', '%2F').replace(' ', '%20').replace('#', '%23')}/official-context"


def test_viewer_official_context_exact_contract_and_successful_get_is_pure_read(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'viewer-context.db'}"
    with ApiServer(database_url=url) as server:
        branch_id, checkpoint_id = _coherent_run(server)
        repository = _repository(url)
        before = _snapshot(repository)
        status, context = _request("GET", _context_url(server))
        assert status == 200
        assert context == {
            "product_run_id": "run/a #1", "product_run_display_name": "run/a #1",
            "product_run_status": "active", "product_run_storage_kind": "custom_local",
            "product_run_read_only": False, "official_branch_id": branch_id,
            "official_branch_display_name": "Main", "official_branch_status": "active",
            "official_branch_read_only": False, "official_branch_seed": 47,
            "legacy_simulation_run_id": "run/a #1", "head_checkpoint_id": checkpoint_id,
            "head_checkpoint_kind": "initial", "current_season": 2027, "current_week": None,
            "current_event_id": None, "current_event_sequence": None,
            "resolution_version": "viewer_official_branch_v1",
        }
        assert _snapshot(repository) == before
        assert _request("GET", _context_url(server, "missing"))[0] == 404


def test_viewer_official_context_follows_current_official_branch(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'dynamic.db'}"
    with ApiServer(database_url=url) as server:
        source, checkpoint = _coherent_run(server, "run")
        fork = {"source_branch_id": source, "source_checkpoint_id": checkpoint, "target_branch_id": "branch-b", "target_branch_display_name": "Branch B", "target_legacy_simulation_run_id": "legacy-b", "target_branch_seed": 99, "command_id": "fork-b"}
        fork_status, fork_result = _request("POST", f"{server.base_url}/admin/runs/run/branches/fork", fork)
        assert fork_status == 200
        assert _request("GET", _context_url(server, "run"))[1]["official_branch_id"] == source
        select = {"expected_current_official_branch_id": source, "command_id": "official-b", "audit_reason": "Publish B", "explicit_confirmation": True}
        assert _request("POST", f"{server.base_url}/admin/runs/run/branches/branch-b/make-official", select)[0] == 200
        status, context = _request("GET", _context_url(server, "run"))
        assert status == 200
        assert context["official_branch_id"] == "branch-b"
        assert context["legacy_simulation_run_id"] == "legacy-b"
        assert context["head_checkpoint_id"] == fork_result["target_checkpoint_id"]


@pytest.mark.parametrize("field, value", [("read_only", 1), ("storage_kind", "built_in"), ("status", "inactive")])
def test_viewer_context_permits_read_only_builtin_and_inactive_product_runs(tmp_path, field: str, value: object) -> None:
    url = f"sqlite:///{tmp_path / field}.db"
    with ApiServer(database_url=url) as server:
        _coherent_run(server, "run")
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            setattr(session.get(RunContainerModel, "run"), field, value)
        before = _snapshot(repository)
        assert _request("GET", _context_url(server, "run"))[0] == 200
        assert _snapshot(repository) == before


def test_viewer_context_permits_read_only_official_branch(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'branch-read-only.db'}"
    with ApiServer(database_url=url) as server:
        branch, _ = _coherent_run(server, "run")
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            session.get(RunBranchModel, branch).read_only = 1
        before = _snapshot(repository)
        assert _request("GET", _context_url(server, "run"))[0] == 200
        assert _snapshot(repository) == before


def _null_pointer(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(RunContainerModel, "run").official_branch_id = None


def _blank_pointer(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(RunContainerModel, "run").official_branch_id = "  "


def _missing_branch(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(RunContainerModel, "run").official_branch_id = "gone"


def _wrong_branch_run(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(RunBranchModel, branch).run_id = "other"


def _missing_binding(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(RunBranchModel, branch).legacy_simulation_run_id = None


def _missing_legacy(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.delete(session.get(SimulationRunModel, "run"))


def _missing_state(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.delete(session.get(BranchStateModel, branch))


def _wrong_state_run(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(BranchStateModel, branch).run_id = "other"


def _head_mismatch(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(BranchStateModel, branch).head_checkpoint_id = "other-head"


def _null_head(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session:
        session.get(BranchStateModel, branch).head_checkpoint_id = None
        session.get(RunBranchModel, branch).head_checkpoint_id = None


def _missing_checkpoint(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(BranchStateModel, branch).head_checkpoint_id = "gone"; session.get(RunBranchModel, branch).head_checkpoint_id = "gone"


def _wrong_checkpoint_branch(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(BranchCheckpointModel, session.get(BranchStateModel, branch).head_checkpoint_id).branch_id = "other"


def _wrong_checkpoint_run(repository: SimulationPersistenceRepository, branch: str) -> None:
    with repository._session_factory.begin() as session: session.get(BranchCheckpointModel, session.get(BranchStateModel, branch).head_checkpoint_id).run_id = "other"


@pytest.mark.parametrize("mutation", [_null_pointer, _blank_pointer, _missing_branch, _wrong_branch_run, _missing_binding, _missing_legacy, _missing_state, _wrong_state_run, _head_mismatch, _null_head, _missing_checkpoint, _wrong_checkpoint_branch, _wrong_checkpoint_run])
def test_viewer_context_rejects_incoherent_official_state_without_mutation(tmp_path, mutation: Callable[[SimulationPersistenceRepository, str], None]) -> None:
    url = f"sqlite:///{tmp_path / mutation.__name__}.db"
    with ApiServer(database_url=url) as server:
        branch, _ = _coherent_run(server, "run")
        repository = _repository(url)
        mutation(repository, branch)
        before = _snapshot(repository)
        assert _request("GET", _context_url(server, "run"))[0] == 409
        assert _snapshot(repository) == before
