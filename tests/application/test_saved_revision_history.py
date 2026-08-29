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
from beta_engine.application.run_saved_revision_history_service import (
    RunSavedRevisionHistoryService,
)
from beta_engine.application.run_working_draft_service import (
    RunWorkingDraftService,
)
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SavedRevisionHistoryConflictError,
    SavedRevisionHistoryNotFoundError,
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


def _create_run_and_fork(repository: SimulationPersistenceRepository) -> None:
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory("run-one", "branch-one", "revision-one", "draft-one"),
    ).create_empty_run(display_name="Revision History")
    RunBranchCreationService(
        repository=repository,
        id_factory=_id_factory("branch-two", "draft-two"),
    ).create_from_saved_revision(
        run_id="run-one",
        source_branch_id="branch-one",
        source_saved_revision_id="revision-one",
    )


def _save_twice_on_fork(repository: SimulationPersistenceRepository) -> None:
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory(
            "revision-two",
            "audit-one",
            "revision-three",
            "audit-two",
        ),
    )
    first_draft = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-two",
        viewer_branch_id="branch-two",
        expected_draft_version=0,
    )
    first_save = service.save(
        run_id="run-one",
        branch_id="branch-two",
        expected_draft_version=first_draft.draft_version,
    )
    second_draft = service.stage_viewer_branch(
        run_id="run-one",
        branch_id="branch-two",
        viewer_branch_id="branch-one",
        expected_draft_version=first_save.working_draft.draft_version,
    )
    service.save(
        run_id="run-one",
        branch_id="branch-two",
        expected_draft_version=second_draft.draft_version,
    )


@pytest.mark.smoke
def test_history_reads_shared_lineage_oldest_first_without_mutation(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'revision-history.db'}")
    _create_run_and_fork(repository)
    _save_twice_on_fork(repository)
    service = RunSavedRevisionHistoryService(repository=repository)

    before = (
        repository.get_run_container(run_id="run-one"),
        repository.get_branch_revision_state(branch_id="branch-two"),
        repository.list_branch_saved_revisions(branch_id="branch-two"),
        repository.list_branch_revision_audit_events(branch_id="branch-two"),
    )
    history = service.list_history(run_id="run-one", branch_id="branch-two")
    detail = service.get_revision(
        run_id="run-one",
        branch_id="branch-two",
        revision_id="revision-one",
    )
    after = (
        repository.get_run_container(run_id="run-one"),
        repository.get_branch_revision_state(branch_id="branch-two"),
        repository.list_branch_saved_revisions(branch_id="branch-two"),
        repository.list_branch_revision_audit_events(branch_id="branch-two"),
    )

    assert history.run_id == "run-one"
    assert history.branch_id == "branch-two"
    assert history.saved_head_revision_id == "revision-three"
    assert [item.revision_id for item in history.saved_revisions] == [
        "revision-one",
        "revision-two",
        "revision-three",
    ]
    assert [item.branch_id for item in history.saved_revisions] == [
        "branch-one",
        "branch-two",
        "branch-two",
    ]
    assert [item.sequence for item in history.saved_revisions] == [1, 2, 3]
    assert detail.saved_head_revision_id == "revision-three"
    assert detail.saved_revision.revision_id == "revision-one"
    assert detail.saved_revision.payload["branch"]["branch_id"] == "branch-one"
    assert before == after


def test_history_hides_revisions_outside_selected_branch_lineage(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'revision-history-scope.db'}")
    _create_run_and_fork(repository)
    RunContainerCreationService(
        repository=repository,
        id_factory=_id_factory(
            "run-other",
            "branch-other",
            "revision-other",
            "draft-other",
        ),
    ).create_empty_run(display_name="Other History")
    service = RunSavedRevisionHistoryService(repository=repository)

    with pytest.raises(SavedRevisionHistoryNotFoundError, match="was not found"):
        service.list_history(run_id="run-one", branch_id="branch-other")
    with pytest.raises(SavedRevisionHistoryNotFoundError, match="history"):
        service.get_revision(
            run_id="run-one",
            branch_id="branch-two",
            revision_id="revision-other",
        )
    with pytest.raises(SavedRevisionHistoryNotFoundError, match="was not found"):
        service.list_history(run_id="missing-run", branch_id="branch-two")


def test_history_rejects_tampered_shared_ancestor_fail_closed(tmp_path) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'revision-history-hash.db'}")
    _create_run_and_fork(repository)
    _save_twice_on_fork(repository)

    with repository._engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE branch_saved_revisions "
                "SET payload_json = :payload_json "
                "WHERE revision_id = :revision_id"
            ),
            {
                "payload_json": '{"tampered":true}',
                "revision_id": "revision-one",
            },
        )

    service = RunSavedRevisionHistoryService(repository=repository)
    with pytest.raises(SavedRevisionHistoryConflictError, match="Saved Revision"):
        service.list_history(run_id="run-one", branch_id="branch-two")
    with pytest.raises(SavedRevisionHistoryConflictError, match="Saved Revision"):
        service.get_revision(
            run_id="run-one",
            branch_id="branch-two",
            revision_id="revision-three",
        )


def test_history_validates_shared_fork_origin_after_branch_has_own_revisions(
    tmp_path,
) -> None:
    repository = _repository(f"sqlite:///{tmp_path / 'revision-history-fork.db'}")
    _create_run_and_fork(repository)
    _save_twice_on_fork(repository)

    with repository._engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE run_branches "
                "SET forked_from_saved_revision_id = :revision_id "
                "WHERE branch_id = :branch_id"
            ),
            {"revision_id": "revision-two", "branch_id": "branch-two"},
        )

    service = RunSavedRevisionHistoryService(repository=repository)
    with pytest.raises(SavedRevisionHistoryConflictError, match="shared fork origin"):
        service.list_history(run_id="run-one", branch_id="branch-two")
