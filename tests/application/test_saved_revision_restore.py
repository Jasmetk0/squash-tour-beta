from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import event

from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_saved_revision_restore_service import (
    RunSavedRevisionRestoreService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.run_revisions import (
    BRANCH_RESTORE_AUDIT_EVENT_KIND,
    BRANCH_RESTORE_SAVED_REVISION_KIND,
    CLEAN_WORKING_DRAFT_STATUS,
    PRE_RESTORE_CHECKPOINT_KIND,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SavedRevisionRestoreConflictError,
    SavedRevisionRestoreNotFoundError,
    SavedRevisionRestoreUnsupportedError,
    SavedRevisionRestoreVersionConflictError,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
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


def _run_with_saved_viewer_change(
    repository: SimulationPersistenceRepository,
) -> None:
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one", "revision-one", "draft-one"),
    ).create_empty_run(display_name="Restore History")
    RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-two", "draft-two"),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-one",
    )
    save_service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-two", "audit-one"),
    )
    staged = save_service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    save_service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=staged.draft_version,
    )


@pytest.mark.smoke
def test_restore_preserves_history_and_creates_pre_restore_checkpoint(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'saved-revision-restore.db'}"
    repository = _repository(database_url)
    _run_with_saved_viewer_change(repository)
    service = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("checkpoint-one", "revision-three", "audit-two"),
    )

    restored = service.restore_current_branch(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id="revision-one",
        expected_head_saved_revision_id="revision-two",
        expected_draft_version=2,
        expected_current_viewer_branch_id="branch-two",
        explicit_confirmation=True,
    )

    assert restored.previous_saved_head_revision_id == "revision-two"
    assert restored.target_saved_revision_id == "revision-one"
    assert restored.previous_viewer_branch_id == "branch-two"
    assert restored.viewer_branch_id == "branch-one"
    assert restored.saved_revision.revision_id == "revision-three"
    assert restored.saved_revision.parent_revision_id == "revision-two"
    assert restored.saved_revision.sequence == 3
    assert restored.saved_revision.kind == BRANCH_RESTORE_SAVED_REVISION_KIND
    assert restored.saved_revision.payload["run"]["viewer_branch_id"] == "branch-one"
    assert restored.saved_revision.payload["branch"]["branch_id"] == "branch-one"
    assert repository.verify_branch_saved_revision_hash(revision_id="revision-three")

    checkpoint = restored.safety_checkpoint
    assert checkpoint.checkpoint_id == "checkpoint-one"
    assert checkpoint.kind == PRE_RESTORE_CHECKPOINT_KIND
    assert checkpoint.saved_revision_id == "revision-two"
    assert checkpoint.target_saved_revision_id == "revision-one"
    assert checkpoint.restore_saved_revision_id == "revision-three"
    assert checkpoint.draft_id == "draft-one"
    assert checkpoint.draft_version == 2
    assert checkpoint.viewer_branch_id == "branch-two"
    assert (
        repository.get_branch_saved_revision_checkpoint(checkpoint_id="checkpoint-one")
        == checkpoint
    )

    assert restored.working_draft.status == CLEAN_WORKING_DRAFT_STATUS
    assert restored.working_draft.change_count == 0
    assert restored.working_draft.draft_version == 3
    assert restored.working_draft.base_saved_revision_id == "revision-three"
    assert restored.audit_event.event_kind == BRANCH_RESTORE_AUDIT_EVENT_KIND
    assert restored.audit_event.payload["checkpoint_id"] == "checkpoint-one"
    assert restored.audit_event.payload["explicit_confirmation"] is True
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    assert [
        revision.revision_id
        for revision in repository.get_branch_saved_revision_history(
            run_id="run-one", branch_id="branch-one"
        ).saved_revisions
    ] == ["revision-one", "revision-two", "revision-three"]

    reloaded = _repository(database_url)
    assert (
        reloaded.get_branch_saved_revision_checkpoint(checkpoint_id="checkpoint-one")
        == checkpoint
    )
    assert (
        reloaded.get_branch_revision_state(
            branch_id="branch-one"
        ).saved_head_revision_id
        == "revision-three"
    )


def test_restore_requires_confirmation_before_generating_identities(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'restore-confirmation.db'}")
    _run_with_saved_viewer_change(repository)

    def unexpected_id_factory(_kind: str) -> str:
        raise AssertionError("identity factory must not run without confirmation")

    service = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=unexpected_id_factory,
    )
    with pytest.raises(SavedRevisionRestoreConflictError, match="confirmation"):
        service.restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id="revision-one",
            expected_head_saved_revision_id="revision-two",
            expected_draft_version=2,
            expected_current_viewer_branch_id="branch-two",
            explicit_confirmation=False,
        )
    assert (
        repository.list_branch_saved_revision_checkpoints(branch_id="branch-one") == []
    )


def test_restore_rejects_stale_or_dirty_state_without_partial_mutation(
    tmp_path,
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'restore-conflicts.db'}")
    _run_with_saved_viewer_change(repository)
    service = RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory(
            "unused-checkpoint-one",
            "unused-revision-one",
            "unused-audit-one",
            "unused-checkpoint-two",
            "unused-revision-two",
            "unused-audit-two",
        ),
    )

    with pytest.raises(SavedRevisionRestoreVersionConflictError, match="head changed"):
        service.restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id="revision-one",
            expected_head_saved_revision_id="stale-head",
            expected_draft_version=2,
            expected_current_viewer_branch_id="branch-two",
            explicit_confirmation=True,
        )

    draft_service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("unused-save-revision", "unused-save-audit"),
    )
    dirty = draft_service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-one",
        expected_draft_version=2,
    )
    with pytest.raises(SavedRevisionRestoreConflictError, match="dirty Working Draft"):
        service.restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id="revision-one",
            expected_head_saved_revision_id="revision-two",
            expected_draft_version=dirty.draft_version,
            expected_current_viewer_branch_id="branch-two",
            explicit_confirmation=True,
        )

    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-two"
    )
    assert (
        repository.get_run_branch(branch_id="branch-one").saved_head_revision_id
        == "revision-two"
    )
    assert (
        repository.list_branch_saved_revision_checkpoints(branch_id="branch-one") == []
    )
    assert [
        revision.revision_id
        for revision in repository.list_branch_saved_revisions(branch_id="branch-one")
    ] == ["revision-one", "revision-two"]


def test_restore_is_scoped_and_rolls_back_a_late_write_failure(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'restore-rollback.db'}")
    _run_with_saved_viewer_change(repository)
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-other", "branch-other", "revision-other", "draft-other"
        ),
    ).create_empty_run(display_name="Other Restore History")

    with pytest.raises(SavedRevisionRestoreNotFoundError, match="was not found"):
        RunSavedRevisionRestoreService(
            repository=repository,
            id_factory=_id_factory(
                "scoped-checkpoint", "scoped-revision", "scoped-audit"
            ),
        ).restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id="revision-other",
            expected_head_saved_revision_id="revision-two",
            expected_draft_version=2,
            expected_current_viewer_branch_id="branch-two",
            explicit_confirmation=True,
        )

    def fail_audit_insert(_conn, _cursor, statement, _params, _context, _many) -> None:
        if "INSERT INTO branch_revision_audit_events" in statement:
            raise RuntimeError("injected late restore failure")

    event.listen(repository._engine, "before_cursor_execute", fail_audit_insert)
    try:
        with pytest.raises(RuntimeError, match="injected late restore failure"):
            RunSavedRevisionRestoreService(
                repository=repository,
                id_factory=_id_factory(
                    "rollback-checkpoint", "rollback-revision", "rollback-audit"
                ),
            ).restore_current_branch(
                run_id="run-one",
                branch_id="branch-one",
                target_saved_revision_id="revision-one",
                expected_head_saved_revision_id="revision-two",
                expected_draft_version=2,
                expected_current_viewer_branch_id="branch-two",
                explicit_confirmation=True,
            )
    finally:
        event.remove(repository._engine, "before_cursor_execute", fail_audit_insert)

    assert (
        repository.get_branch_saved_revision_checkpoint(
            checkpoint_id="rollback-checkpoint"
        )
        is None
    )
    assert repository.get_branch_saved_revision(revision_id="rollback-revision") is None
    assert (
        repository.get_branch_revision_audit_event(audit_event_id="rollback-audit")
        is None
    )
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-two"
    )
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-one"
        ).saved_head_revision_id
        == "revision-two"
    )
    assert (
        repository.get_branch_working_draft(branch_id="branch-one").draft_version == 2
    )


def test_restore_fails_closed_for_state_not_captured_by_saved_revision(
    tmp_path,
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'restore-unsupported.db'}")
    _run_with_saved_viewer_change(repository)
    with repository._engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE runs SET world_id = ? WHERE run_id = ?",
            ("fax-world", "run-one"),
        )

    with pytest.raises(SavedRevisionRestoreUnsupportedError, match="complete sporting"):
        RunSavedRevisionRestoreService(
            repository=repository,
            id_factory=_id_factory(
                "unsupported-checkpoint",
                "unsupported-revision",
                "unsupported-audit",
            ),
        ).restore_current_branch(
            run_id="run-one",
            branch_id="branch-one",
            target_saved_revision_id="revision-one",
            expected_head_saved_revision_id="revision-two",
            expected_draft_version=2,
            expected_current_viewer_branch_id="branch-two",
            explicit_confirmation=True,
        )

    assert (
        repository.get_branch_saved_revision(revision_id="unsupported-revision") is None
    )
    assert (
        repository.get_branch_saved_revision_checkpoint(
            checkpoint_id="unsupported-checkpoint"
        )
        is None
    )
