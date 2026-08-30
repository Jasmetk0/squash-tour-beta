from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import text

from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_saved_revision_recovery_activity_service import (
    RunSavedRevisionRecoveryActivityConflictError,
    RunSavedRevisionRecoveryActivityNotFoundError,
    RunSavedRevisionRecoveryActivityService,
)
from beta_engine.application.run_saved_revision_restore_service import (
    RunSavedRevisionRestoreService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.run_revisions import BRANCH_RESTORE_AUDIT_EVENT_KIND
from beta_engine.infrastructure.db import (
    DatabaseSettings,
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


def _run_with_restore(repository: SimulationPersistenceRepository) -> None:
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one", "revision-one", "draft-one"),
    ).create_empty_run(display_name="Recovery Activity")
    RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-two", "draft-two"),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-one",
    )
    draft_service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-two", "audit-one"),
    )
    staged = draft_service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    saved = draft_service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=staged.draft_version,
    )
    RunSavedRevisionRestoreService(
        repository=repository,
        id_factory=_id_factory("checkpoint-one", "revision-three", "audit-two"),
    ).restore_current_branch(
        run_id="run-one",
        branch_id="branch-one",
        target_saved_revision_id="revision-one",
        expected_head_saved_revision_id="revision-two",
        expected_draft_version=saved.working_draft.draft_version,
        expected_current_viewer_branch_id="branch-two",
        explicit_confirmation=True,
    )


@pytest.mark.smoke
def test_recovery_activity_validates_restore_links_without_mutation(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'recovery-activity.db'}")
    _run_with_restore(repository)
    service = RunSavedRevisionRecoveryActivityService(repository=repository)
    before = (
        repository.get_run_container(run_id="run-one"),
        repository.get_branch_revision_state(branch_id="branch-one"),
        repository.list_branch_saved_revision_checkpoints(branch_id="branch-one"),
        repository.list_branch_revision_audit_events(branch_id="branch-one"),
    )

    activity = service.get_activity(run_id="run-one", branch_id="branch-one")

    after = (
        repository.get_run_container(run_id="run-one"),
        repository.get_branch_revision_state(branch_id="branch-one"),
        repository.list_branch_saved_revision_checkpoints(branch_id="branch-one"),
        repository.list_branch_revision_audit_events(branch_id="branch-one"),
    )
    assert activity.run_id == "run-one"
    assert activity.branch_id == "branch-one"
    assert activity.saved_head_revision_id == "revision-three"
    assert [item.checkpoint_id for item in activity.safety_checkpoints] == [
        "checkpoint-one"
    ]
    checkpoint = activity.safety_checkpoints[0]
    assert checkpoint.saved_revision_id == "revision-two"
    assert checkpoint.target_saved_revision_id == "revision-one"
    assert checkpoint.restore_saved_revision_id == "revision-three"
    assert [item.audit_event_id for item in activity.audit_events] == [
        "audit-one",
        "audit-two",
    ]
    assert activity.audit_events[-1].event_kind == BRANCH_RESTORE_AUDIT_EVENT_KIND
    assert before == after


def test_recovery_activity_is_scoped_and_allows_no_existing_activity(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'recovery-scope.db'}")
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one", "revision-one", "draft-one"),
    ).create_empty_run(display_name="Empty Recovery Activity")
    service = RunSavedRevisionRecoveryActivityService(repository=repository)

    activity = service.get_activity(run_id="run-one", branch_id="branch-one")
    assert activity.saved_head_revision_id == "revision-one"
    assert activity.safety_checkpoints == ()
    assert activity.audit_events == ()

    with pytest.raises(
        RunSavedRevisionRecoveryActivityNotFoundError, match="was not found"
    ):
        service.get_activity(run_id="run-one", branch_id="missing-branch")


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        (
            (
                "UPDATE branch_saved_revision_checkpoints "
                "SET content_hash = 'tampered' WHERE checkpoint_id = 'checkpoint-one'"
            ),
            "integrity validation",
        ),
        (
            (
                "UPDATE branch_revision_audit_events "
                'SET payload_json = \'{"checkpoint_id":"wrong"}\' '
                "WHERE audit_event_id = 'audit-two'"
            ),
            "unknown checkpoint",
        ),
        (
            (
                "UPDATE branch_revision_audit_events "
                'SET payload_json = \'{"base_saved_revision_id":"wrong"}\' '
                "WHERE audit_event_id = 'audit-one'"
            ),
            "does not match Saved Revision",
        ),
        (
            (
                "DELETE FROM branch_revision_audit_events "
                "WHERE audit_event_id = 'audit-two'"
            ),
            "no matching audit event",
        ),
    ],
)
def test_recovery_activity_rejects_corrupt_or_orphaned_restore_records(
    tmp_path, statement: str, message: str
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'recovery-corrupt.db'}")
    _run_with_restore(repository)
    with repository._engine.begin() as connection:
        connection.execute(text(statement))

    with pytest.raises(RunSavedRevisionRecoveryActivityConflictError, match=message):
        RunSavedRevisionRecoveryActivityService(repository=repository).get_activity(
            run_id="run-one", branch_id="branch-one"
        )
