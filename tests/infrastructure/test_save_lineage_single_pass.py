"""A Save review must not revalidate identical lineage twice inside one transaction.

The optimization never persists verification between HTTP requests: each new
transaction still checks the stored revision bytes, metadata and component hash.
"""
import json

import pytest

from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
from tests.application.test_run_working_draft_save import (
    _empty_run,
    _id_factory,
    _repository,
    _second_branch,
)

pytestmark = pytest.mark.pr_critical


def test_saved_component_previews_validate_lineage_once(tmp_path, monkeypatch):
    repository = _repository(f"sqlite:///{tmp_path / 'preview-once.db'}")
    _empty_run(repository)
    original = repository._validated_branch_revision_lineage_in_session
    calls = []

    def counted(*, session, branch, **kwargs):
        calls.append((id(session), branch.branch_id))
        return original(session=session, branch=branch, **kwargs)

    monkeypatch.setattr(repository, "_validated_branch_revision_lineage_in_session", counted)
    for method in (repository.preview_simulation_save, repository.preview_calendar_match_save):
        calls.clear()
        review = method(run_id="run-one", branch_id="branch-one")
        assert review["saved_head_revision_id"] == "revision-one"
        assert review["draft_version"] == 0
        assert len(calls) == 1, "one read transaction must validate Saved lineage once"

    # A second request MUST re-read and validate the stored bytes, not blindly
    # trust an earlier in-memory result or the revision proof cache.
    with repository._session_factory.begin() as session:
        revision = session.get(BranchSavedRevisionModel, "revision-one")
        payload = json.loads(revision.payload_json)
        payload["run"]["display_name"] = "tampered"
        revision.payload_json = json.dumps(payload)
    calls.clear()
    with pytest.raises(ValueError):
        repository.preview_calendar_match_save(run_id="run-one", branch_id="branch-one")
    assert len(calls) == 1


def test_save_reuses_reviewed_state_but_revalidates_after_commit(tmp_path, monkeypatch):
    repository = _repository(f"sqlite:///{tmp_path / 'save-once.db'}")
    _empty_run(repository)
    _second_branch(repository)
    service = RunWorkingDraftService(
        repository=repository,
        id_factory=_id_factory("revision-two", "audit-one"),
    )
    staged = service.stage_viewer_branch(
        run_id="run-one", branch_id="branch-one",
        viewer_branch_id="branch-two", expected_draft_version=0,
    )
    original = repository._validated_branch_revision_lineage_in_session
    calls = []

    def counted(*, session, branch, **kwargs):
        calls.append((id(session), branch.branch_id))
        return original(session=session, branch=branch, **kwargs)

    monkeypatch.setattr(repository, "_validated_branch_revision_lineage_in_session", counted)
    saved = service.save(
        run_id="run-one", branch_id="branch-one",
        expected_draft_version=staged.draft_version,
    )
    assert saved.saved_revision.parent_revision_id == "revision-one"
    assert saved.working_draft.base_saved_revision_id == "revision-two"
    assert repository.verify_branch_saved_revision_hash(revision_id="revision-two")
    # Service preflight, atomic Save, and post-commit response reload are three
    # separate transactions. Previously the atomic Save alone validated twice.
    assert len(calls) == 3
    assert len({session_id for session_id, _ in calls}) == 3
