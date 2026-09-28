from __future__ import annotations

import pytest

from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import BranchSimulateNextMatchCommand, BranchSimulateNextMatchResult, DatabaseSettings, SimulationPersistenceRepository, create_session_factory, create_sqlite_engine
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.models import BranchCheckpointModel, BranchSimulationCommandModel, BranchStateModel, RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.run_package_state import put_run_package_state


def _setup(tmp_path):
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'next-match.db'}"))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    service = SimulationApiService(repository=repository)
    service.initialize_run(run_id="source", season=2027, seed=47, config_version="v1", config_fingerprint="cfg")
    branch = repository.list_run_branches(run_id="source")[0]
    checkpoint = repository.capture_initial_checkpoint_for_legacy_simulation_run(simulation_run_id="source")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, "source").storage_kind = "custom_local"
    return repository, service, branch.branch_id, checkpoint.checkpoint_id


def test_branch_next_match_is_atomic_and_replay_is_journal_only(tmp_path):
    repository, service, branch_id, head = _setup(tmp_path)
    command = BranchSimulateNextMatchCommand("source", branch_id, head, "next-match-1", "test execution", True)
    result = service.simulate_next_match_on_branch_atomically(command)
    assert isinstance(result, BranchSimulateNextMatchResult)
    assert result.idempotent_replay is False
    assert result.previous_head_checkpoint_id == head
    assert result.previous_season == 2027
    with repository._session_factory() as session:
        journal = session.get(BranchSimulationCommandModel, command.command_id)
        assert journal.action_kind == "simulate_next_match"
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2
        checkpoint = session.get(BranchCheckpointModel, result.new_head_checkpoint_id)
        assert checkpoint.command_kind == "simulate_next_match_branch"
        assert checkpoint.command_boundary == "after_branch_next_match_persisted"
        assert session.get(RunBranchModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(BranchStateModel, branch_id).head_checkpoint_id == result.new_head_checkpoint_id
        assert session.get(RunContainerModel, "source").official_branch_id == branch_id
    # A completed journal replay must not resolve an executable Branch or calculate a match.
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, branch_id).read_only = 1
    replay = service.simulate_next_match_on_branch_atomically(command)
    assert replay.idempotent_replay is True
    assert replay.new_head_checkpoint_id == result.new_head_checkpoint_id
    with repository._session_factory() as session:
        assert session.query(BranchCheckpointModel).filter_by(branch_id=branch_id).count() == 2


@pytest.mark.pr_critical
def test_package_backed_branch_does_not_read_legacy_entry_sidecars(tmp_path, monkeypatch):
    repository, service, branch_id, head = _setup(tmp_path)
    with repository._session_factory.begin() as session:
        put_run_package_state(
            session,
            RunPackageState(run_id="source", branch_id=branch_id),
        )

    def poisoned(*args, **kwargs):
        raise AssertionError("legacy Entry/WC/pre-draw sidecar must not be read")

    monkeypatch.setattr(repository, "get_wildcard_assignments_for_run", poisoned)
    monkeypatch.setattr(repository, "get_pre_draw_withdrawal_replacements_for_run", poisoned)
    monkeypatch.setattr(repository, "get_late_replacements_for_run", poisoned)

    result = service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand(
            "source", branch_id, head, "package-fence-next-match", "ownership fence", True
        )
    )
    assert isinstance(result, BranchSimulateNextMatchResult)


@pytest.mark.pr_critical
def test_non_package_branch_preserves_legacy_entry_sidecar_compatibility(tmp_path, monkeypatch):
    repository, service, branch_id, head = _setup(tmp_path)
    calls = {"wildcards": 0, "pre_draw": 0, "late": 0}

    def wildcards(*, run_id):
        calls["wildcards"] += 1
        return {}

    def pre_draw(*, run_id):
        calls["pre_draw"] += 1
        return {}

    def late(*, run_id):
        calls["late"] += 1
        return {}

    monkeypatch.setattr(repository, "get_wildcard_assignments_for_run", wildcards)
    monkeypatch.setattr(repository, "get_pre_draw_withdrawal_replacements_for_run", pre_draw)
    monkeypatch.setattr(repository, "get_late_replacements_for_run", late)

    service.simulate_next_match_on_branch_atomically(
        BranchSimulateNextMatchCommand(
            "source", branch_id, head, "legacy-sidecar-next-match", "compatibility", True
        )
    )
    assert calls == {"wildcards": 1, "pre_draw": 1, "late": 1}
