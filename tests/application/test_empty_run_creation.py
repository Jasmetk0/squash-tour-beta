from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text

from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.domain.run_containers import (
    RUN_TIMELINE_END_SEASON,
    RUN_TIMELINE_START_SEASON,
    RunDisplayNameValidationError,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    RunDisplayNameConflictError,
    RunIdentityConflictError,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import RunContainerModel


def _repository(database_url: str) -> SimulationPersistenceRepository:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()
    return repository


def _id_factory(*values: str) -> Callable[[str], str]:
    identities: Iterator[str] = iter(values)
    return lambda _kind: next(identities)


def test_empty_run_is_a_durable_product_root_with_one_viewer_branch(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty-run.db'}"
    repository = _repository(database_url)
    service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-stable", "branch-stable"),
    )

    created = service.create_empty_run(display_name="  Test Run  ")

    assert created.run_id == "run-stable"
    assert created.display_name == "Test Run"
    assert created.status == "working"
    assert created.storage_kind == "custom_local"
    assert created.read_only is False
    assert created.world_id is None
    assert created.global_seed is None
    assert created.timeline_start_season == RUN_TIMELINE_START_SEASON == 2000
    assert created.timeline_end_season == RUN_TIMELINE_END_SEASON == 2049
    assert created.viewer_branch_id == "branch-stable"
    assert created.mapped_simulation_run_count == 0
    assert repository.list_simulation_runs() == []

    branches = repository.list_run_branches(run_id=created.run_id)
    assert len(branches) == 1
    assert branches[0].branch_id == "branch-stable"
    assert branches[0].display_name == "Timeline 1"
    assert branches[0].is_viewer_branch is True
    assert branches[0].legacy_simulation_run_id is None
    assert branches[0].head_checkpoint_id is None

    state = repository.get_branch_state(branch_id="branch-stable")
    assert state is not None
    assert state.run_id == "run-stable"
    assert state.head_checkpoint_id is None
    assert state.current_season is None
    assert state.current_week is None

    # Reconstructing the adapter models a process restart, not an in-memory read.
    reloaded_repository = _repository(database_url)
    reloaded = reloaded_repository.get_run_container(run_id="run-stable")
    assert reloaded == created
    assert reloaded_repository.list_run_branches(run_id="run-stable") == branches
    assert reloaded_repository.get_branch_state(branch_id="branch-stable") == state


def test_blank_name_is_rejected_without_writing_any_aggregate_member(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'blank-name.db'}")
    service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("unused-run", "unused-branch"),
    )

    with pytest.raises(RunDisplayNameValidationError, match="must not be blank"):
        service.create_empty_run(display_name="   ")

    assert repository.list_run_containers() == []
    assert repository.list_run_branches() == []


def test_archived_run_still_reserves_its_display_name(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'reserved-name.db'}")
    first = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one"),
    ).create_empty_run(display_name="Reserved")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, first.run_id).status = "archived"

    second_service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-two", "branch-two"),
    )
    with pytest.raises(RunDisplayNameConflictError, match="already reserved"):
        second_service.create_empty_run(display_name="Reserved")

    assert [run.run_id for run in repository.list_run_containers()] == ["run-one"]
    assert [branch.branch_id for branch in repository.list_run_branches()] == [
        "branch-one"
    ]


def test_identity_conflict_rolls_back_the_complete_new_run(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'atomic-conflict.db'}")
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "shared-branch"),
    ).create_empty_run(display_name="First")

    conflicting_service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-two", "shared-branch"),
    )
    with pytest.raises(RunIdentityConflictError, match="branch_id"):
        conflicting_service.create_empty_run(display_name="Second")

    assert repository.get_run_container(run_id="run-two") is None
    assert repository.list_branch_states(run_id="run-two") == []
    assert [run.display_name for run in repository.list_run_containers()] == ["First"]


def test_bootstrap_migrates_legacy_required_world_id_without_data_loss(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy-world-lock.db'}"
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE runs (
                    run_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    display_name VARCHAR(256),
                    storage_kind VARCHAR(32) NOT NULL,
                    read_only INTEGER NOT NULL,
                    world_id VARCHAR(128) NOT NULL,
                    world_package_fingerprint VARCHAR(256),
                    config_version VARCHAR(128),
                    config_fingerprint VARCHAR(256),
                    global_seed INTEGER,
                    timeline_start_season INTEGER NOT NULL,
                    timeline_end_season INTEGER NOT NULL,
                    official_branch_id VARCHAR(128),
                    status VARCHAR(32) NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO runs (
                    run_id, display_name, storage_kind, read_only, world_id,
                    timeline_start_season, timeline_end_season, status, metadata_json
                ) VALUES (
                    'legacy-run', NULL, 'custom_local', 0, 'legacy-world',
                    2027, 2027, 'active', '{}'
                )
                """
            )
        )

    repository = SimulationPersistenceRepository(
        engine=engine,
        session_factory=create_session_factory(engine),
    )
    repository.bootstrap_schema()

    with repository._engine.connect() as connection:
        world_column = next(
            row
            for row in connection.execute(text("PRAGMA table_info(runs)"))
            if row[1] == "world_id"
        )
    assert int(world_column[3]) == 0
    assert repository.get_run_container(run_id="legacy-run").world_id == "legacy-world"

    created = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("empty-run", "empty-branch"),
    ).create_empty_run(display_name="Empty")
    assert created.world_id is None
