from __future__ import annotations

import json
from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import event, func, select, text

from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    CONTENT_HASH_ALGORITHM,
    INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION,
    saved_revision_content_hash,
)
from beta_engine.infrastructure.db import (
    BranchCreationIdentityConflictError,
    BranchDisplayNameConflictError,
    BranchRevisionStateConflictError,
    DatabaseSettings,
    SavedRevisionBranchForkConflictError,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    BranchWorkingDraftModel,
    RunBranchModel,
    RunContainerModel,
)


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


def _empty_run(
    repository: SimulationPersistenceRepository,
    *,
    run_id: str = "run-one",
    branch_id: str = "branch-one",
    revision_id: str = "revision-one",
    draft_id: str = "draft-one",
    display_name: str = "History",
):
    run = RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(run_id, branch_id, revision_id, draft_id),
    ).create_empty_run(display_name=display_name)
    return run, repository.get_branch_revision_state(branch_id=branch_id)


@pytest.mark.smoke
def test_branch_from_saved_revision_shares_history_and_owns_clean_draft(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'saved-revision-fork.db'}"
    repository = _repository(database_url)
    run, source_state = _empty_run(repository)
    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory(
            "branch-two",
            "draft-two",
            "branch-custom",
            "draft-custom",
            "branch-three",
            "draft-three",
            "branch-nested",
            "draft-nested",
        ),
    )

    created = service.create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-one",
        source_saved_revision_id=source_state.saved_head_revision_id,
    )
    custom = service.create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-one",
        source_saved_revision_id=source_state.saved_head_revision_id,
        display_name="  Alternative  ",
    )
    third = service.create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-one",
        source_saved_revision_id=source_state.saved_head_revision_id,
    )
    nested = service.create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-two",
        source_saved_revision_id=source_state.saved_head_revision_id,
    )

    assert created.display_name == "Timeline 2"
    assert created.branch_id == "branch-two"
    assert created.forked_from_branch_id == "branch-one"
    assert created.forked_from_saved_revision_id == "revision-one"
    assert created.saved_head_revision_id == "revision-one"
    assert created.head_checkpoint_id is None
    assert created.legacy_simulation_run_id is None
    assert created.is_viewer_branch is False
    assert custom.display_name == "Alternative"
    assert third.display_name == "Timeline 3"
    assert nested.display_name == "Timeline 4"
    assert nested.forked_from_branch_id == "branch-two"
    assert nested.forked_from_saved_revision_id == "revision-one"
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-nested"
        ).saved_head_revision_id
        == "revision-one"
    )
    assert (
        repository.get_run_container(run_id=run.run_id).viewer_branch_id == "branch-one"
    )

    child_state = repository.get_branch_revision_state(branch_id="branch-two")
    assert child_state.branch_id == "branch-two"
    assert child_state.saved_revision == source_state.saved_revision
    assert child_state.working_draft.branch_id == "branch-two"
    assert child_state.working_draft.base_revision_id == "revision-one"
    assert child_state.working_draft.status == CLEAN_WORKING_DRAFT_STATUS
    assert child_state.working_draft.change_count == 0
    assert child_state.working_draft.draft_version == 0
    assert child_state.working_draft.changes == []
    assert (
        child_state.working_draft.draft_schema_version
        == SAVED_REVISION_FORK_WORKING_DRAFT_SCHEMA_VERSION
    )

    with repository._session_factory() as session:
        revision_count = session.scalar(
            select(func.count(BranchSavedRevisionModel.revision_id))
        )
    assert revision_count == 1
    assert repository.list_branch_saved_revisions(branch_id="branch-two") == []

    reloaded = _repository(database_url)
    assert reloaded.get_run_branch(branch_id="branch-two") == created
    assert reloaded.get_branch_revision_state(branch_id="branch-two") == child_state
    assert (
        reloaded.get_run_container(run_id=run.run_id).viewer_branch_id == "branch-one"
    )


def test_duplicate_custom_name_rejects_the_complete_branch_aggregate(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'duplicate-branch-name.db'}")
    run, source_state = _empty_run(repository)
    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-rejected", "draft-rejected"),
    )

    with pytest.raises(BranchDisplayNameConflictError, match="already reserved"):
        service.create_from_saved_revision(
            run_id=run.run_id,
            source_branch_id="branch-one",
            source_saved_revision_id=source_state.saved_head_revision_id,
            display_name="Timeline 1",
        )

    assert repository.get_run_branch(branch_id="branch-rejected") is None
    assert repository.get_branch_working_draft(branch_id="branch-rejected") is None
    assert repository.get_branch_state(branch_id="branch-rejected") is None
    assert (
        repository.get_run_container(run_id=run.run_id).viewer_branch_id == "branch-one"
    )


@pytest.mark.parametrize(
    ("branch_id", "draft_id", "message"),
    [
        ("branch-one", "draft-rejected", "branch_id"),
        ("branch-rejected", "draft-one", "draft_id"),
    ],
)
def test_generated_identity_collision_rolls_back_the_branch_aggregate(
    tmp_path,
    branch_id: str,
    draft_id: str,
    message: str,
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / f'branch-identity-{message}.db'}")
    run, source_state = _empty_run(repository)
    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory(branch_id, draft_id),
    )

    with pytest.raises(BranchCreationIdentityConflictError, match=message):
        service.create_from_saved_revision(
            run_id=run.run_id,
            source_branch_id="branch-one",
            source_saved_revision_id=source_state.saved_head_revision_id,
        )

    assert [
        branch.branch_id for branch in repository.list_run_branches(run_id=run.run_id)
    ] == ["branch-one"]
    assert repository.get_branch_working_draft(branch_id="branch-rejected") is None
    assert repository.get_branch_state(branch_id="branch-rejected") is None


def test_cross_run_source_revision_is_rejected_without_mutation(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'cross-run-source.db'}")
    _, first_state = _empty_run(repository)
    second_run, _ = _empty_run(
        repository,
        run_id="run-two",
        branch_id="branch-other",
        revision_id="revision-other",
        draft_id="draft-other",
        display_name="Other History",
    )
    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-rejected", "draft-rejected"),
    )

    with pytest.raises(
        SavedRevisionBranchForkConflictError,
        match="belongs to another Run",
    ):
        service.create_from_saved_revision(
            run_id=second_run.run_id,
            source_branch_id="branch-other",
            source_saved_revision_id=first_state.saved_head_revision_id,
        )

    assert repository.get_run_branch(branch_id="branch-rejected") is None
    assert repository.get_branch_working_draft(branch_id="branch-rejected") is None
    assert (
        repository.get_run_container(run_id="run-two").viewer_branch_id
        == "branch-other"
    )


def test_source_revision_need_not_be_the_source_branch_current_head(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'historical-source.db'}")
    run, source_state = _empty_run(repository)
    payload = source_state.saved_revision.payload
    change_summary = {"kind": "test_save", "summary": "Later saved state"}
    later_revision_id = "revision-later"
    later_hash = saved_revision_content_hash(
        revision_id=later_revision_id,
        run_id=run.run_id,
        branch_id="branch-one",
        sequence=2,
        parent_revision_id="revision-one",
        kind="test_save",
        payload_schema_version=INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
        payload=payload,
        change_summary=change_summary,
    )
    with repository._session_factory.begin() as session:
        session.add(
            BranchSavedRevisionModel(
                revision_id=later_revision_id,
                run_id=run.run_id,
                branch_id="branch-one",
                sequence=2,
                parent_revision_id="revision-one",
                kind="test_save",
                payload_schema_version=INITIAL_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
                content_hash_algorithm=CONTENT_HASH_ALGORITHM,
                content_hash=later_hash,
                payload_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
                change_summary_json=json.dumps(
                    change_summary, sort_keys=True, separators=(",", ":")
                ),
            )
        )
        session.get(
            RunBranchModel, "branch-one"
        ).saved_head_revision_id = later_revision_id
        session.get(
            BranchWorkingDraftModel, "draft-one"
        ).base_revision_id = later_revision_id

    created = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-from-past", "draft-from-past"),
    ).create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-one",
        source_saved_revision_id="revision-one",
    )

    assert created.saved_head_revision_id == "revision-one"
    assert created.forked_from_saved_revision_id == "revision-one"
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-one"
        ).saved_head_revision_id
        == later_revision_id
    )
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-from-past"
        ).saved_head_revision_id
        == "revision-one"
    )
    with pytest.raises(
        SavedRevisionBranchForkConflictError,
        match="not part of the selected Branch history",
    ):
        RunBranchCreationService(
            repository=repository,
            id_factory=_id_factory("branch-rejected", "draft-rejected"),
        ).create_from_saved_revision(
            run_id=run.run_id,
            source_branch_id="branch-from-past",
            source_saved_revision_id=later_revision_id,
        )
    assert repository.get_run_branch(branch_id="branch-rejected") is None


def test_tampered_source_revision_cannot_be_forked(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'tampered-source.db'}")
    run, source_state = _empty_run(repository)
    with repository._engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE branch_saved_revisions "
                'SET change_summary_json = \'{"summary":"tampered"}\' '
                "WHERE revision_id = 'revision-one'"
            )
        )

    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-rejected", "draft-rejected"),
    )
    with pytest.raises(
        SavedRevisionBranchForkConflictError,
        match="failed content integrity validation",
    ):
        service.create_from_saved_revision(
            run_id=run.run_id,
            source_branch_id="branch-one",
            source_saved_revision_id=source_state.saved_head_revision_id,
        )

    assert repository.get_run_branch(branch_id="branch-rejected") is None
    assert repository.get_branch_working_draft(branch_id="branch-rejected") is None


def test_shared_revision_requires_exact_persisted_fork_pointer(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'fork-pointer-integrity.db'}")
    run, source_state = _empty_run(repository)
    RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-two", "draft-two"),
    ).create_from_saved_revision(
        run_id=run.run_id,
        source_branch_id="branch-one",
        source_saved_revision_id=source_state.saved_head_revision_id,
    )
    with repository._session_factory.begin() as session:
        session.get(
            RunBranchModel, "branch-two"
        ).forked_from_saved_revision_id = "revision-tampered"

    with pytest.raises(
        BranchRevisionStateConflictError,
        match="declared shared fork origin",
    ):
        repository.get_branch_revision_state(branch_id="branch-two")


def test_late_draft_failure_rolls_back_branch_and_state(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'fork-rollback.db'}")
    run, source_state = _empty_run(repository)
    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-rollback", "draft-rollback"),
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
            raise RuntimeError("simulated late fork draft failure")

    event.listen(repository._engine, "before_cursor_execute", fail_draft_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated late fork draft failure"):
            service.create_from_saved_revision(
                run_id=run.run_id,
                source_branch_id="branch-one",
                source_saved_revision_id=source_state.saved_head_revision_id,
            )
    finally:
        event.remove(repository._engine, "before_cursor_execute", fail_draft_insert)

    assert draft_insert_reached is True
    assert repository.get_run_branch(branch_id="branch-rollback") is None
    assert repository.get_branch_working_draft(branch_id="branch-rollback") is None
    assert repository.get_branch_state(branch_id="branch-rollback") is None
    assert (
        repository.get_run_container(run_id=run.run_id).viewer_branch_id == "branch-one"
    )
    with repository._session_factory() as session:
        assert session.scalar(select(func.count(RunBranchModel.branch_id))) == 1
        assert session.scalar(select(func.count(BranchWorkingDraftModel.draft_id))) == 1


def test_read_only_run_rejects_new_branch(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'read-only-run.db'}")
    run, source_state = _empty_run(repository)
    with repository._session_factory.begin() as session:
        session.get(RunContainerModel, run.run_id).read_only = 1

    service = RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-rejected", "draft-rejected"),
    )
    with pytest.raises(SavedRevisionBranchForkConflictError, match="read-only"):
        service.create_from_saved_revision(
            run_id=run.run_id,
            source_branch_id="branch-one",
            source_saved_revision_id=source_state.saved_head_revision_id,
        )

    assert repository.get_run_branch(branch_id="branch-rejected") is None
