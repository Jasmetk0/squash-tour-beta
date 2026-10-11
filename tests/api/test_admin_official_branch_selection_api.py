from __future__ import annotations

from test_simulation_api import ApiServer, _request

from beta_engine.infrastructure.db import DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.infrastructure.db.models import OfficialBranchSelectionCommandModel, RunBranchModel


def _repository(url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=url))
    return SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))


def _branches(server: ApiServer) -> tuple[str, str]:
    assert _request("POST", f"{server.base_url}/runs", {"run_id": "run", "seed": 47, "season": 2027})[0] == 201
    status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=run")
    assert status == 200
    source = branches["run_branches"][0]["branch_id"]
    status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run"})
    assert status == 200
    fork = {"source_branch_id": source, "source_checkpoint_id": checkpoint["checkpoint_id"], "target_branch_id": "target", "target_branch_display_name": "Target", "target_legacy_simulation_run_id": "target-legacy", "target_branch_seed": 99, "command_id": "fork"}
    assert _request("POST", f"{server.base_url}/admin/runs/run/branches/fork", fork)[0] == 200
    return source, "target"


def _payload(expected: str | None, **changes: object) -> dict[str, object]:
    result: dict[str, object] = {"expected_current_official_branch_id": expected, "command_id": "select-1", "audit_reason": "Publish reviewed timeline", "explicit_confirmation": True}
    result.update(changes)
    return result


def test_admin_selects_official_branch_atomically_and_idempotently(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        repository = _repository(url)
        endpoint = f"{server.base_url}/admin/runs/run/branches/{target}/make-official"
        status, result = _request("POST", endpoint, _payload(source))
        assert status == 200
        assert result["previous_official_branch_id"] == source and result["official_branch_id"] == target
        assert result["changed"] is True and result["idempotent_replay"] is False
        status, replay = _request("POST", endpoint, _payload(source))
        assert status == 200 and replay["idempotent_replay"] is True
        with repository._session_factory() as session:
            assert session.query(OfficialBranchSelectionCommandModel).count() == 1
            assert session.get(RunBranchModel, target).read_only == 0
        assert repository.get_run_container(run_id="run").official_branch_id == target


def test_admin_official_branch_selection_conflicts_and_noop(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official-conflict.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        endpoint = f"{server.base_url}/admin/runs/run/branches/{target}/make-official"
        status, noop = _request("POST", endpoint, _payload(source, expected_current_official_branch_id=source))
        # First switch establishes target; a stale expected pointer must not persist a command.
        assert status == 200 and noop["changed"] is True
        status, stale = _request("POST", endpoint, _payload(source, command_id="stale"))
        assert status == 409
        status, conflict = _request("POST", endpoint, _payload(target, audit_reason="different"))
        assert status == 409
        status, rejected = _request("POST", endpoint, _payload(target, command_id="confirm", explicit_confirmation=False))
        assert status == 400


def test_admin_official_branch_selection_already_official_noop(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official-noop.db'}"
    with ApiServer(database_url=url) as server:
        source, _ = _branches(server)
        status, result = _request("POST", f"{server.base_url}/admin/runs/run/branches/{source}/make-official", _payload(source, command_id="already-official"))
        assert status == 200
        assert result["changed"] is False and result["idempotent_replay"] is False
        repository = _repository(url)
        with repository._session_factory() as session:
            assert session.query(OfficialBranchSelectionCommandModel).count() == 1


def test_admin_official_branch_selection_replay_after_later_switch_is_conflict(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'official-replay-state.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        target_endpoint = f"{server.base_url}/admin/runs/run/branches/{target}/make-official"
        original = _payload(source, command_id="original")
        assert _request("POST", target_endpoint, original)[0] == 200
        source_endpoint = f"{server.base_url}/admin/runs/run/branches/{source}/make-official"
        assert _request("POST", source_endpoint, _payload(target, command_id="later"))[0] == 200
        status, _ = _request("POST", target_endpoint, original)
        assert status == 409
        assert _repository(url).get_run_container(run_id="run").official_branch_id == source


import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from beta_engine.infrastructure.db import SetOfficialRunBranchCommand, OfficialBranchSelectionConflictError
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchStateModel, LegacySimulationRunMappingModel, SimulationRunModel, RunContainerModel


@pytest.mark.parametrize("case", ["built-in", "read-only", "inactive"])
def test_admin_official_branch_selection_rejects_invalid_product_run(tmp_path, case: str) -> None:
    url = f"sqlite:///{tmp_path / f'{case}.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            container = session.get(RunContainerModel, "run")
            if case == "built-in": container.storage_kind = "built_in"
            elif case == "read-only": container.read_only = 1
            else: container.status = "inactive"
        status, _ = _request("POST", f"{server.base_url}/admin/runs/run/branches/{target}/make-official", _payload(source, command_id=case))
        assert status == 400
        assert repository.get_run_container(run_id="run").official_branch_id == source


def test_admin_official_branch_selection_missing_run_or_branch_is_404(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'not-found.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        assert _request("POST", f"{server.base_url}/admin/runs/missing/branches/{target}/make-official", _payload(source))[0] == 404
        assert _request("POST", f"{server.base_url}/admin/runs/run/branches/missing/make-official", _payload(source))[0] == 404


@pytest.mark.parametrize("case", ["wrong-run", "inactive", "missing-binding", "missing-legacy", "missing-state", "state-wrong-run", "heads-disagree", "null-head", "checkpoint-wrong-branch", "checkpoint-wrong-run"])
def test_admin_official_branch_selection_rejects_incoherent_target_without_command(tmp_path, case: str) -> None:
    url = f"sqlite:///{tmp_path / f'{case}.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        repository = _repository(url)
        with repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, target); state = session.get(BranchStateModel, target)
            checkpoint = session.get(BranchCheckpointModel, branch.head_checkpoint_id)
            if case == "wrong-run": branch.run_id = "other"
            elif case == "inactive": branch.status = "inactive"
            elif case == "missing-binding": branch.legacy_simulation_run_id = None
            elif case == "missing-legacy": session.delete(session.get(SimulationRunModel, branch.legacy_simulation_run_id))
            elif case == "missing-state": session.delete(state)
            elif case == "state-wrong-run": state.run_id = "other"
            elif case == "heads-disagree": state.head_checkpoint_id = "other-checkpoint"
            elif case == "null-head": branch.head_checkpoint_id = state.head_checkpoint_id = None
            elif case == "checkpoint-wrong-branch": checkpoint.branch_id = "unrelated-branch"
            elif case == "checkpoint-wrong-run": checkpoint.run_id = "other"
        status, _ = _request("POST", f"{server.base_url}/admin/runs/run/branches/{target}/make-official", _payload(source, command_id=case))
        assert status == 400
        assert repository.get_run_container(run_id="run").official_branch_id == source
        with repository._session_factory() as session:
            assert session.query(OfficialBranchSelectionCommandModel).filter_by(command_id=case).count() == 0


def test_admin_official_branch_selection_allows_read_only_branch_and_preserves_non_pointer_state(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'read-only-branch.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server); repository = _repository(url)
        with repository._session_factory.begin() as session:
            branch = session.get(RunBranchModel, target); branch.read_only = 1
            before = ({k: v for k, v in branch.__dict__.items() if k != "_sa_instance_state"}, {k: v for k, v in session.get(BranchStateModel, target).__dict__.items() if k != "_sa_instance_state"}, {k: v for k, v in session.get(BranchCheckpointModel, branch.head_checkpoint_id).__dict__.items() if k != "_sa_instance_state"}, session.query(SimulationRunModel).count(), session.query(LegacySimulationRunMappingModel).count())
        assert _request("POST", f"{server.base_url}/admin/runs/run/branches/{target}/make-official", _payload(source))[0] == 200
        with repository._session_factory() as session:
            branch = session.get(RunBranchModel, target)
            assert branch.read_only == 1
            assert {k: v for k, v in branch.__dict__.items() if k != "_sa_instance_state"} == before[0]
            assert {k: v for k, v in session.get(BranchStateModel, target).__dict__.items() if k != "_sa_instance_state"} == before[1]
            assert {k: v for k, v in session.get(BranchCheckpointModel, branch.head_checkpoint_id).__dict__.items() if k != "_sa_instance_state"} == before[2]
            assert (session.query(SimulationRunModel).count(), session.query(LegacySimulationRunMappingModel).count()) == before[3:]


@pytest.mark.parametrize("changes", [{"explicit_confirmation": False}, {"command_id": " "}, {"audit_reason": " "}])
def test_admin_official_branch_selection_validates_request(tmp_path, changes: dict[str, object]) -> None:
    url = f"sqlite:///{tmp_path / 'request.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server)
        status, _ = _request("POST", f"{server.base_url}/admin/runs/run/branches/{target}/make-official", _payload(source, **changes))
        assert status in {400, 422}


def test_official_branch_selection_flush_conflict_rolls_back_all_changes(tmp_path, monkeypatch) -> None:
    url = f"sqlite:///{tmp_path / 'flush.db'}"
    with ApiServer(database_url=url) as server:
        source, target = _branches(server); repository = _repository(url)
        original_flush = Session.flush
        def fail_flush(self, *args, **kwargs):
            raise IntegrityError("INSERT", {}, RuntimeError("duplicate"))
        monkeypatch.setattr(Session, "flush", fail_flush)
        with pytest.raises(OfficialBranchSelectionConflictError, match="conflicts with existing durable state"):
            repository.set_official_run_branch_atomically(SetOfficialRunBranchCommand("run", target, source, "flush-fail", "test rollback", True))
        monkeypatch.setattr(Session, "flush", original_flush)
        assert repository.get_run_container(run_id="run").official_branch_id == source
        with repository._session_factory() as session:
            assert session.query(OfficialBranchSelectionCommandModel).filter_by(command_id="flush-fail").count() == 0
