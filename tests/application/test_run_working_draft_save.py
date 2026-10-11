from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import event, func, select

from beta_engine.application.run_branch_creation_service import (
    RunBranchCreationService,
)
from beta_engine.application.run_container_creation_service import (
    RunContainerCreationService,
)
from beta_engine.application.run_working_draft_service import (
    RunWorkingDraftService,
)
from beta_engine.domain.run_revisions import (
    CLEAN_WORKING_DRAFT_STATUS,
    DIRTY_WORKING_DRAFT_STATUS,
    RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION,
    RUN_WORKING_DRAFT_SCHEMA_VERSION,
    SAVED_REVISION_AUDIT_EVENT_KIND,
    VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    WorkingDraftConflictError,
    WorkingDraftIdentityConflictError,
    WorkingDraftNotFoundError,
    WorkingDraftVersionConflictError,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    BranchRevisionAuditEventModel,
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


def _empty_run(repository: SimulationPersistenceRepository) -> None:
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one", "revision-one", "draft-one"),
    ).create_empty_run(display_name="History")


def _second_branch(repository: SimulationPersistenceRepository) -> None:
    RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-two", "draft-two"),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-one",
    )


@pytest.mark.smoke
def test_viewer_branch_change_stays_in_draft_until_atomic_save(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-draft-save.db'}"
    repository = _repository(database_url)
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-two", "audit-one"),
    )

    initial = service.get_viewer_branch_draft(run_id="run-one", branch_id="branch-one")
    assert initial.status == CLEAN_WORKING_DRAFT_STATUS
    assert initial.draft_version == 0
    assert initial.saved_viewer_branch_id == "branch-one"
    assert initial.proposed_viewer_branch_id == "branch-one"
    assert initial.current_viewer_branch_id == "branch-one"
    assert initial.can_save is False

    staged = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    assert staged.status == DIRTY_WORKING_DRAFT_STATUS
    assert staged.change_count == 1
    assert staged.draft_version == 1
    assert staged.saved_viewer_branch_id == "branch-one"
    assert staged.proposed_viewer_branch_id == "branch-two"
    assert staged.current_viewer_branch_id == "branch-one"
    assert staged.can_save is True
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    assert (
        repository.get_run_branch(branch_id="branch-one").saved_head_revision_id
        == "revision-one"
    )
    assert (
        repository.list_branch_saved_revisions(branch_id="branch-one")[0].revision_id
        == "revision-one"
    )
    assert repository.list_branch_revision_audit_events(branch_id="branch-one") == []

    saved = service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=1,
    )

    assert saved.previous_viewer_branch_id == "branch-one"
    assert saved.viewer_branch_id == "branch-two"
    assert saved.saved_revision.revision_id == "revision-two"
    assert saved.saved_revision.sequence == 2
    assert saved.saved_revision.parent_revision_id == "revision-one"
    assert saved.saved_revision.kind == VIEWER_BRANCH_SELECTION_SAVED_REVISION_KIND
    assert (
        saved.saved_revision.payload_schema_version
        == RUN_SAVED_REVISION_PAYLOAD_SCHEMA_VERSION
    )
    assert saved.saved_revision.payload["run"]["viewer_branch_id"] == "branch-two"
    assert saved.saved_revision.payload["branch"]["branch_id"] == "branch-one"
    assert repository.verify_branch_saved_revision_hash(revision_id="revision-two")
    assert saved.working_draft.status == CLEAN_WORKING_DRAFT_STATUS
    assert saved.working_draft.change_count == 0
    assert saved.working_draft.draft_version == 2
    assert saved.working_draft.base_saved_revision_id == "revision-two"
    assert saved.working_draft.current_viewer_branch_id == "branch-two"
    assert saved.working_draft.saved_viewer_branch_id == "branch-two"
    assert saved.audit_event.event_kind == SAVED_REVISION_AUDIT_EVENT_KIND
    assert saved.audit_event.saved_revision_id == "revision-two"
    assert saved.audit_event.payload["draft_id"] == "draft-one"
    assert saved.audit_event.payload["saved_draft_version"] == 1
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-two"
    )
    assert (
        repository.get_run_branch(branch_id="branch-one").saved_head_revision_id
        == "revision-two"
    )

    reloaded = _repository(database_url)
    assert (
        reloaded.get_viewer_branch_working_draft(
            run_id="run-one", branch_id="branch-one"
        )
        == saved.working_draft
    )
    assert (
        reloaded.get_branch_saved_revision(revision_id="revision-two")
        == saved.saved_revision
    )
    assert (
        reloaded.get_branch_revision_audit_event(audit_event_id="audit-one")
        == saved.audit_event
    )


def test_reverting_selection_cleans_draft_and_disables_save(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'viewer-draft-cancel.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("unused-revision", "unused-audit"),
    )

    unchanged = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-one",
        expected_draft_version=0,
    )
    assert unchanged.status == CLEAN_WORKING_DRAFT_STATUS
    assert unchanged.draft_version == 0

    dirty = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    clean = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-one",
        expected_draft_version=dirty.draft_version,
    )
    assert clean.status == CLEAN_WORKING_DRAFT_STATUS
    assert clean.change_count == 0
    assert clean.draft_version == 2
    assert clean.can_save is False
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-one"
        ).working_draft.draft_schema_version
        == RUN_WORKING_DRAFT_SCHEMA_VERSION
    )

    with pytest.raises(WorkingDraftConflictError, match="nothing to save"):
        service.save(
            run_id="run-one",
            branch_id="branch-one",
            expected_draft_version=2,
        )
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    assert repository.list_branch_revision_audit_events(branch_id="branch-one") == []


def test_stage_rejects_stale_version_and_foreign_target_without_mutation(
    tmp_path,
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'viewer-stage-errors.db'}")
    _empty_run(repository)
    _second_branch(repository)
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-other", "branch-other", "revision-other", "draft-other"
        ),
    ).create_empty_run(display_name="Other History")
    service = RunWorkingDraftService(repository=repository, id_factory=_id_factory())

    with pytest.raises(
        WorkingDraftVersionConflictError, match="expected draft version"
    ):
        service.stage_viewer_branch(
            run_id="run-one",
            branch_id="branch-one",
            viewer_branch_id="branch-two",
            expected_draft_version=7,
        )
    with pytest.raises(WorkingDraftNotFoundError, match="was not found in Run"):
        service.stage_viewer_branch(
            run_id="run-one",
            branch_id="branch-one",
            viewer_branch_id="branch-other",
            expected_draft_version=0,
        )
    state = repository.get_branch_revision_state(branch_id="branch-one")
    assert state.working_draft.status == CLEAN_WORKING_DRAFT_STATUS
    assert state.working_draft.draft_version == 0
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )


def test_first_save_on_forked_branch_materializes_child_revision(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'forked-viewer-save.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-child", "audit-child"),
    )
    service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-two",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )

    saved = service.save(
        run_id="run-one",
        branch_id="branch-two",
        expected_draft_version=1,
    )

    assert saved.saved_revision.sequence == 2
    assert saved.saved_revision.parent_revision_id == "revision-one"
    assert saved.saved_revision.branch_id == "branch-two"
    assert saved.saved_revision.payload["branch"] == {
        "branch_id": "branch-two",
        "display_name": "Timeline 2",
        "status": "active",
        "forked_from_branch_id": "branch-one",
        "forked_from_saved_revision_id": "revision-one",
    }
    assert [
        revision.revision_id
        for revision in repository.list_branch_saved_revisions(branch_id="branch-two")
    ] == ["revision-child"]
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-two"
        ).saved_head_revision_id
        == "revision-child"
    )


def test_consecutive_saves_advance_one_immutable_lineage(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'consecutive-saves.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory(
            "revision-two",
            "audit-one",
            "revision-three",
            "audit-two",
        ),
    )

    first_dirty = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    first_save = service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=first_dirty.draft_version,
    )
    second_dirty = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-one",
        expected_draft_version=first_save.working_draft.draft_version,
    )
    second_save = service.save(
        run_id="run-one",
        branch_id="branch-one",
        expected_draft_version=second_dirty.draft_version,
    )

    assert second_save.saved_revision.sequence == 3
    assert second_save.saved_revision.parent_revision_id == "revision-two"
    assert second_save.viewer_branch_id == "branch-one"
    assert second_save.working_draft.base_saved_revision_id == "revision-three"
    assert second_save.working_draft.draft_version == 4
    assert [
        revision.revision_id
        for revision in repository.list_branch_saved_revisions(branch_id="branch-one")
    ] == ["revision-one", "revision-two", "revision-three"]
    assert [
        event.saved_revision_id
        for event in repository.list_branch_revision_audit_events(
            branch_id="branch-one"
        )
    ] == ["revision-two", "revision-three"]


def test_target_archived_after_staging_blocks_save_without_mutation(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'archived-target.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-rejected", "audit-rejected"),
    )
    staged = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    with repository._session_factory.begin() as session:
        session.get(RunBranchModel, "branch-two").status = "archived"

    with pytest.raises(WorkingDraftConflictError, match="not active"):
        service.save(
            run_id="run-one",
            branch_id="branch-one",
            expected_draft_version=staged.draft_version,
        )

    assert repository.get_branch_saved_revision(revision_id="revision-rejected") is None
    assert (
        repository.get_branch_revision_audit_event(audit_event_id="audit-rejected")
        is None
    )
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    draft = repository.get_branch_revision_state(branch_id="branch-one").working_draft
    assert draft.status == DIRTY_WORKING_DRAFT_STATUS
    assert draft.draft_version == 1
    assert draft.base_revision_id == "revision-one"


def test_late_audit_failure_rolls_back_complete_save(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'viewer-save-rollback.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-rollback", "audit-rollback"),
    )
    service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    audit_insert_reached = False

    def fail_audit_insert(
        _connection,
        _cursor,
        statement: str,
        _parameters,
        _context,
        _executemany,
    ) -> None:
        nonlocal audit_insert_reached
        if "insert into branch_revision_audit_events" in statement.lower():
            audit_insert_reached = True
            raise RuntimeError("simulated late audit failure")

    event.listen(repository._engine, "before_cursor_execute", fail_audit_insert)
    try:
        with pytest.raises(RuntimeError, match="simulated late audit failure"):
            service.save(
                run_id="run-one",
                branch_id="branch-one",
                expected_draft_version=1,
            )
    finally:
        event.remove(repository._engine, "before_cursor_execute", fail_audit_insert)

    assert audit_insert_reached is True
    assert repository.get_branch_saved_revision(revision_id="revision-rollback") is None
    assert (
        repository.get_branch_revision_audit_event(audit_event_id="audit-rollback")
        is None
    )
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    assert (
        repository.get_run_branch(branch_id="branch-one").saved_head_revision_id
        == "revision-one"
    )
    draft = repository.get_branch_revision_state(branch_id="branch-one").working_draft
    assert draft.status == DIRTY_WORKING_DRAFT_STATUS
    assert draft.draft_version == 1
    assert draft.base_revision_id == "revision-one"


def test_identity_collision_and_tampered_change_cannot_partially_save(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'viewer-save-integrity.db'}")
    _empty_run(repository)
    _second_branch(repository)
    stage_service = RunWorkingDraftService(
        repository=repository, id_factory=_id_factory()
    )
    stage_service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-one",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )

    collision_service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-one", "audit-unused"),
    )
    with pytest.raises(WorkingDraftIdentityConflictError, match="already in use"):
        collision_service.save(
            run_id="run-one", branch_id="branch-one", expected_draft_version=1
        )
    assert (
        repository.get_run_container(run_id="run-one").viewer_branch_id == "branch-one"
    )
    assert (
        repository.get_branch_revision_state(
            branch_id="branch-one"
        ).working_draft.draft_version
        == 1
    )

    with repository._session_factory.begin() as session:
        model = session.scalar(
            select(BranchWorkingDraftModel).where(
                BranchWorkingDraftModel.branch_id == "branch-one"
            )
        )
        model.changes_json = '[{"kind":"unsupported","viewer_branch_id":"branch-two"}]'
    with pytest.raises(WorkingDraftConflictError, match="unsupported change kind"):
        repository.get_viewer_branch_working_draft(
            run_id="run-one", branch_id="branch-one"
        )

    with repository._session_factory() as session:
        assert (
            session.scalar(select(func.count(BranchSavedRevisionModel.revision_id)))
            == 1
        )
        assert (
            session.scalar(
                select(func.count(BranchRevisionAuditEventModel.audit_event_id))
            )
            == 0
        )
        assert (
            session.get(RunContainerModel, "run-one").official_branch_id == "branch-one"
        )
        assert (
            session.get(RunBranchModel, "branch-one").saved_head_revision_id
            == "revision-one"
        )
