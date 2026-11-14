from __future__ import annotations

from collections.abc import Callable, Iterator
import json

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
    BranchRevisionStateConflictError,
    DatabaseSettings,
    SavedRevisionHistoryConflictError,
    SavedRevisionHistoryNotFoundError,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel
from beta_engine.domain.run_revisions import saved_revision_content_hash


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


@pytest.mark.pr_critical
@pytest.mark.parametrize("corruption", ["payload", "summary", "sequence", "owner", "rehashed_component"])
def test_cached_revision_validation_still_rejects_ancestor_corruption(tmp_path, corruption):
    repository = _repository(f"sqlite:///{tmp_path / 'cached-history.db'}")
    _create_run_and_fork(repository)
    _save_twice_on_fork(repository)
    repository.get_branch_revision_state(branch_id="branch-two")
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, "revision-one")
        if corruption == "payload":
            row.payload_json = row.payload_json.replace("Revision History", "Tampered History")
        elif corruption == "summary":
            row.change_summary_json = '{"tampered":true}'
        elif corruption == "sequence":
            row.sequence = 19
        elif corruption == "owner":
            session.get(RunBranchModel, "branch-one").run_id = "missing-run"
        else:
            payload = json.loads(row.payload_json)
            payload["content"]["run_package_state"] = {"fingerprint": "0" * 64, "state": {}}
            row.payload_json = json.dumps(payload)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                kind=row.kind, payload_schema_version=row.payload_schema_version,
                payload=payload, change_summary=json.loads(row.change_summary_json),
            )
    with pytest.raises(BranchRevisionStateConflictError):
        repository.get_branch_revision_state(branch_id="branch-two")


@pytest.mark.pr_critical
def test_revision_validation_cache_keeps_no_payloads_and_returns_independent_reads(tmp_path):
    repository = _repository(f"sqlite:///{tmp_path / 'cached-independent.db'}")
    _create_run_and_fork(repository)
    _save_twice_on_fork(repository)
    first = repository.get_branch_revision_state(branch_id="branch-two")
    first.saved_revision.payload["run"]["display_name"] = "changed returned object"
    second = repository.get_branch_revision_state(branch_id="branch-two")
    assert second.saved_revision.payload["run"]["display_name"] == "Revision History"
    assert repository._revision_validation_cache
    assert all(not item.payload and not item.change_summary
               for item in repository._revision_validation_cache.values())
    # Public history still returns every complete revision, including ancestors.
    history = repository.get_branch_saved_revision_history(run_id="run-one", branch_id="branch-two")
    assert len(history.saved_revisions) == 3
    assert all(item.payload["run"]["display_name"] == "Revision History"
               for item in history.saved_revisions)


def _save_many(repository: SimulationPersistenceRepository, count: int) -> None:
    """Ordinary explicit Viewer-selection Saves on branch-two (real Saved rows)."""
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory(*(f"{kind}-{index}" for index in range(count) for kind in ("long-revision", "long-audit"))),
    )
    version = 0
    for index in range(count):
        draft = service.stage_viewer_branch(
            run_id="run-one", branch_id="branch-two",
            viewer_branch_id="branch-one" if index % 2 else "branch-two",
            expected_draft_version=version,
        )
        version = service.save(
            run_id="run-one", branch_id="branch-two", expected_draft_version=draft.draft_version,
        ).working_draft.draft_version


@pytest.fixture(scope="module")
def long_lineage_database(tmp_path_factory):
    """150 ordinary explicit Saves (151 revisions), built once and only copied."""
    path = tmp_path_factory.mktemp("long-lineage") / "source.db"
    repository = _repository(f"sqlite:///{path}")
    _create_run_and_fork(repository)
    _save_many(repository, 150)
    repository._engine.dispose()
    return path


@pytest.mark.pr_critical
@pytest.mark.parametrize("corruption", ["payload", "summary", "content_hash", "parent"])
def test_long_lineage_keeps_proofs_yet_rejects_changed_ancestor_after_success(
        tmp_path, monkeypatch, long_lineage_database, corruption):
    """A lineage longer than the former 128-entry FIFO bound stays proven.

    The first-in-first-out bound evicted each proof right before the next walk
    needed it. Now a repeated read re-decodes only the HEAD, yet a changed old
    ancestor (bytes, summary, declared hash or lineage edge) is still rejected
    after the successful reads.
    """
    from beta_engine.infrastructure.db import repositories

    import sqlite3

    copy = tmp_path / "long-history.db"
    source, target = sqlite3.connect(long_lineage_database), sqlite3.connect(copy)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    repository = _repository(f"sqlite:///{copy}")
    first = RunSavedRevisionHistoryService(repository=repository).list_history(
        run_id="run-one", branch_id="branch-two")
    assert len(first.saved_revisions) == 151
    decoded = []
    original = repositories.SimulationPersistenceRepository._to_branch_saved_revision

    def counting(model, *args, **kwargs):
        decoded.append(model.revision_id)
        return original(model, *args, **kwargs)

    monkeypatch.setattr(repositories.SimulationPersistenceRepository, "_to_branch_saved_revision",
                        staticmethod(counting))
    state = repository.get_branch_revision_state(branch_id="branch-two")
    assert decoded == [state.saved_head_revision_id]
    with repository._session_factory.begin() as session:
        row = session.get(BranchSavedRevisionModel, "long-revision-3")
        if corruption == "payload":
            row.payload_json = row.payload_json.replace("Revision History", "Tampered History")
        elif corruption == "summary":
            row.change_summary_json = '{"tampered":true}'
        elif corruption == "content_hash":
            row.content_hash = "0" * 64
        else:
            row.parent_revision_id = "long-revision-1"
    with pytest.raises(BranchRevisionStateConflictError):
        repository.get_branch_revision_state(branch_id="branch-two")
