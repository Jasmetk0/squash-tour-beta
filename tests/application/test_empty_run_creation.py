from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import event, text

from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.domain.run_containers import (
    RUN_TIMELINE_END_SEASON,
    RUN_TIMELINE_START_SEASON,
    RunDisplayNameValidationError,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    INITIAL_SAVED_REVISION_KIND,
    INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    INITIAL_SAVED_REVISION_SEQUENCE,
    WORKING_DRAFT_SCHEMA_VERSION,
)
from beta_engine.infrastructure.db import (
    BranchRevisionStateConflictError,
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


@pytest.mark.smoke
def test_empty_run_is_a_durable_product_root_with_one_viewer_branch(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'empty-run.db'}"
    repository = _repository(database_url)
    service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-stable",
            "branch-stable",
            "revision-stable",
            "draft-stable",
        ),
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
    assert branches[0].saved_head_revision_id == "revision-stable"

    state = repository.get_branch_state(branch_id="branch-stable")
    assert state is not None
    assert state.run_id == "run-stable"
    assert state.head_checkpoint_id is None
    assert state.current_season is None
    assert state.current_week is None

    revision_state = repository.get_branch_revision_state(branch_id="branch-stable")
    revision = revision_state.saved_revision
    draft = revision_state.working_draft
    assert revision_state.run_id == "run-stable"
    assert revision_state.branch_id == "branch-stable"
    assert revision_state.saved_head_revision_id == "revision-stable"
    assert revision.revision_id == "revision-stable"
    assert revision.sequence == INITIAL_SAVED_REVISION_SEQUENCE == 1
    assert revision.parent_revision_id is None
    assert revision.kind == INITIAL_SAVED_REVISION_KIND
    assert (
        revision.payload_schema_version
        == INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION
    )
    assert revision.content_hash_algorithm == CONTENT_HASH_ALGORITHM
    assert revision.payload == {
        "run": {
            "run_id": "run-stable",
            "display_name": "Test Run",
            "status": "working",
            "timeline_start_season": 2000,
            "timeline_end_season": 2049,
            "viewer_branch_id": "branch-stable",
        },
        "branch": {
            "branch_id": "branch-stable",
            "display_name": "Timeline 1",
            "status": "active",
            "forked_from_branch_id": None,
            "forked_from_saved_revision_id": None,
        },
        "content": {},
    }
    assert revision.change_summary == {
        "kind": INITIAL_SAVED_REVISION_KIND,
        "summary": "Created empty Run Test Run",
    }
    assert repository.verify_branch_saved_revision_hash(
        revision_id="revision-stable"
    )
    assert draft.draft_id == "draft-stable"
    assert draft.base_revision_id == "revision-stable"
    assert draft.status == CLEAN_WORKING_DRAFT_STATUS
    assert draft.change_count == 0
    assert draft.draft_version == 0
    assert draft.draft_schema_version == WORKING_DRAFT_SCHEMA_VERSION
    assert draft.changes == []
    assert draft.has_changes is False
    assert repository.list_branch_checkpoints(branch_id="branch-stable") == []

    # Reconstructing the adapter models a process restart, not an in-memory read.
    reloaded_repository = _repository(database_url)
    reloaded = reloaded_repository.get_run_container(run_id="run-stable")
    assert reloaded == created
    assert reloaded_repository.list_run_branches(run_id="run-stable") == branches
    assert reloaded_repository.get_branch_state(branch_id="branch-stable") == state
    assert (
        reloaded_repository.get_branch_revision_state(branch_id="branch-stable")
        == revision_state
    )
    assert reloaded_repository.verify_branch_saved_revision_hash(
        revision_id="revision-stable"
    )


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
    assert repository.list_branch_saved_revisions(branch_id="unused-branch") == []
    assert repository.get_branch_working_draft(branch_id="unused-branch") is None


def test_archived_run_still_reserves_its_display_name(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'reserved-name.db'}")
    first = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-one", "branch-one", "revision-one", "draft-one"
        ),
    ).create_empty_run(display_name="Reserved")
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, first.run_id).status = "archived"

    second_service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-two", "branch-two", "revision-two", "draft-two"
        ),
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
        id_factory=_id_factory(
            "run-one", "shared-branch", "revision-one", "draft-one"
        ),
    ).create_empty_run(display_name="First")

    conflicting_service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-two", "shared-branch", "revision-two", "draft-two"
        ),
    )
    with pytest.raises(RunIdentityConflictError, match="branch_id"):
        conflicting_service.create_empty_run(display_name="Second")

    assert repository.get_run_container(run_id="run-two") is None
    assert repository.list_branch_states(run_id="run-two") == []
    assert repository.list_branch_saved_revisions(branch_id="shared-branch") == [
        repository.get_branch_revision_state(
            branch_id="shared-branch"
        ).saved_revision
    ]
    assert repository.get_branch_working_draft(
        branch_id="shared-branch"
    ).draft_id == "draft-one"
    assert [run.display_name for run in repository.list_run_containers()] == ["First"]


def test_late_draft_insert_failure_rolls_back_every_aggregate_member(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'late-write-failure.db'}")
    service = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-rollback",
            "branch-rollback",
            "revision-rollback",
            "draft-rollback",
        ),
    )
    draft_insert_reached = False

    def fail_draft_insert(
        _connection,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        nonlocal draft_insert_reached
        if "insert into branch_working_drafts" in statement.lower():
            draft_insert_reached = True
            raise RuntimeError("simulated late Working Draft persistence failure")

    event.listen(repository._engine, "before_cursor_execute", fail_draft_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated late Working Draft"):
            service.create_empty_run(display_name="Rollback")
    finally:
        event.remove(repository._engine, "before_cursor_execute", fail_draft_insert)

    assert draft_insert_reached is True
    assert repository.list_run_containers() == []
    assert repository.list_run_branches() == []
    assert repository.list_branch_states(run_id="run-rollback") == []
    assert repository.list_branch_saved_revisions(branch_id="branch-rollback") == []
    assert repository.get_branch_working_draft(branch_id="branch-rollback") is None


def test_saved_revision_tampering_is_detected_before_state_is_returned(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'revision-integrity.db'}")
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-integrity",
            "branch-integrity",
            "revision-integrity",
            "draft-integrity",
        ),
    ).create_empty_run(display_name="Integrity")

    with repository._engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE branch_saved_revisions "
                "SET change_summary_json = "
                "'{\"kind\":\"initial_run_creation\",\"summary\":\"tampered\"}' "
                "WHERE revision_id = 'revision-integrity'"
            )
        )

    assert repository.verify_branch_saved_revision_hash(
        revision_id="revision-integrity"
    ) is False
    with pytest.raises(
        BranchRevisionStateConflictError,
        match="failed content integrity validation",
    ):
        repository.get_branch_revision_state(branch_id="branch-integrity")


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
        id_factory=_id_factory(
            "empty-run", "empty-branch", "empty-revision", "empty-draft"
        ),
    ).create_empty_run(display_name="Empty")
    assert created.world_id is None


def test_bootstrap_adds_revision_boundary_without_rewriting_legacy_branch(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'pre-revision-branch.db'}"
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
                    world_id VARCHAR(128),
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
                    timeline_start_season, timeline_end_season,
                    official_branch_id, status, metadata_json
                ) VALUES (
                    'legacy-container', 'Legacy Container', 'custom_local', 0,
                    'legacy-world', 2027, 2027, 'legacy-branch', 'active', '{}'
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE run_branches (
                    branch_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    run_id VARCHAR(128) NOT NULL,
                    display_name VARCHAR(256) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    read_only INTEGER NOT NULL,
                    branch_seed INTEGER,
                    forked_from_branch_id VARCHAR(128),
                    forked_from_checkpoint_id VARCHAR(128),
                    head_checkpoint_id VARCHAR(128),
                    legacy_simulation_run_id VARCHAR(128),
                    metadata_json TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO run_branches (
                    branch_id, run_id, display_name, status, read_only,
                    branch_seed, head_checkpoint_id,
                    legacy_simulation_run_id, metadata_json
                ) VALUES (
                    'legacy-branch', 'legacy-container', 'Legacy Timeline',
                    'active', 0, 19, NULL, NULL, '{}'
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
        branch_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(run_branches)"))
        }
    assert "saved_head_revision_id" in branch_columns
    branch = repository.get_run_branch(branch_id="legacy-branch")
    assert branch is not None
    assert branch.display_name == "Legacy Timeline"
    assert branch.branch_seed == 19
    assert branch.saved_head_revision_id is None
    assert repository.list_branch_saved_revisions(branch_id="legacy-branch") == []
    assert repository.get_branch_working_draft(branch_id="legacy-branch") is None
    with pytest.raises(
        BranchRevisionStateConflictError,
        match="has no Saved Revision boundary",
    ):
        repository.get_branch_revision_state(branch_id="legacy-branch")
