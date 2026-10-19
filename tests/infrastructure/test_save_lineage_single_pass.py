"""A Save review must not revalidate identical lineage twice inside one transaction.

The optimization never persists verification between HTTP requests: each new
transaction still checks the stored revision bytes, metadata and component hash.
"""
import json
from types import SimpleNamespace

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
        calls.append((session, branch.branch_id))
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
        calls.append((session, branch.branch_id))
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
    assert len({id(session) for session, _ in calls}) == 3


@pytest.mark.parametrize("has_saved_checkpoint", [False, True])
def test_continuation_reuses_already_verified_opening_sources(monkeypatch, has_saved_checkpoint):
    from beta_engine.application import calendar_continuation_service as continuation

    checkpoint = SimpleNamespace(fingerprint="c" * 64)
    signed = checkpoint if has_saved_checkpoint else None
    evidence = SimpleNamespace(fingerprint="m" * 64)
    revision = SimpleNamespace(saved_revision=SimpleNamespace(payload={"content": {}}))
    opening_calls = []

    def opening_context(*_args, **kwargs):
        opening_calls.append(kwargs)
        return (
            None, revision, None, None, checkpoint, (evidence,),
            signed, evidence if has_saved_checkpoint else None,
        )

    monkeypatch.setattr(
        continuation.CalendarOpeningKnockoutService, "_context", opening_context,
    )

    def forbidden_repeat(*_args, **_kwargs):
        raise AssertionError("Continuation must reuse Opening's checked sources")

    monkeypatch.setattr(continuation, "load_checkpoint", forbidden_repeat)
    monkeypatch.setattr(continuation, "load_match_rows", forbidden_repeat)
    service = continuation.CalendarContinuationService(object())
    result = service._context(None, run_id="r", branch_id="b")

    assert result[1] is revision
    assert result[4] is checkpoint
    assert result[5] is signed
    assert result[6] is evidence
    assert opening_calls == [{
        "run_id": "r", "branch_id": "b", "_include_sporting_sources": True,
    }]


@pytest.mark.parametrize("live_state", ["same", "unsaved", "missing", "changed-root"])
def test_opening_context_reuses_authenticated_saved_only_if_live_matches(
    monkeypatch, live_state,
):
    from beta_engine.application import calendar_opening_knockout_service as opening
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting
    from beta_engine.infrastructure.db import calendar_standalone_match_state as matches

    clock = SimpleNamespace(season_count=3)
    revision = SimpleNamespace(saved_revision=SimpleNamespace(payload={"content": {}}))
    world = object()
    root = SimpleNamespace(fingerprint="m" * 64)
    signed_checkpoint = SimpleNamespace(
        fingerprint="s" * 64,
        week=SimpleNamespace(calendar=SimpleNamespace(season_count=3)),
        played_continuations=(),
    )
    changed_checkpoint = SimpleNamespace(
        fingerprint="u" * 64,
        week=signed_checkpoint.week,
        played_continuations=(),
    )
    live_checkpoint = (
        changed_checkpoint if live_state == "unsaved"
        else None if live_state == "missing"
        else signed_checkpoint
    )
    live_root = (
        SimpleNamespace(fingerprint="f" * 64)
        if live_state == "changed-root" else root
    )

    monkeypatch.setattr(
        opening.CalendarStandaloneMatchService, "_context",
        lambda *_args, **_kw: (clock, revision, world),
    )
    monkeypatch.setattr(opening, "saved_knockout_health", lambda *_args, **_kw: None)
    monkeypatch.setattr(
        matches, "decode_prevalidated_calendar_sources",
        lambda *_args, **_kw: (root, signed_checkpoint, None),
    )

    def load_rows(*_args, **kwargs):
        assert kwargs["_verified_source"] is root
        return (live_root,)

    def load_sporting(*_args, **kwargs):
        assert kwargs["_verified_source"] is signed_checkpoint
        return live_checkpoint

    monkeypatch.setattr(opening, "load_match_rows", load_rows)
    monkeypatch.setattr(sporting, "load_checkpoint", load_sporting)
    folds = []

    def verify(*_args, **kwargs):
        folds.append(kwargs)
        assert kwargs["_verified_saved_prefix"] is signed_checkpoint

    monkeypatch.setattr(sporting, "verify_checkpoint", verify)
    service = opening.CalendarOpeningKnockoutService(object())

    if live_state in {"missing", "changed-root"}:
        with pytest.raises(ValueError, match="Saved history"):
            service._context(None, run_id="r", branch_id="b")
        assert not folds
    else:
        values = service._context(
            None, run_id="r", branch_id="b", _include_sporting_sources=True,
        )
        assert values[4] is live_checkpoint
        assert values[5] == (live_root,)
        assert values[6] is signed_checkpoint
        assert values[7] is root
        assert len(folds) == (1 if live_state == "unsaved" else 0)


def test_opening_without_saved_checkpoint_still_verifies_live_owner(monkeypatch):
    from beta_engine.application import calendar_opening_knockout_service as opening
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as sporting
    from beta_engine.infrastructure.db import calendar_standalone_match_state as matches

    clock = SimpleNamespace(season_count=3)
    revision = SimpleNamespace(saved_revision=SimpleNamespace(payload={"content": {}}))
    monkeypatch.setattr(
        opening.CalendarStandaloneMatchService, "_context",
        lambda *_args, **_kw: (clock, revision, object()),
    )
    monkeypatch.setattr(opening, "saved_knockout_health", lambda *_args, **_kw: None)
    monkeypatch.setattr(
        matches, "decode_prevalidated_calendar_sources",
        lambda *_args, **_kw: (None, None, None),
    )
    monkeypatch.setattr(opening, "load_match_rows", lambda *_args, **_kw: (object(),))
    monkeypatch.setattr(sporting, "load_checkpoint", lambda *_args, **_kw: None)
    checks = []

    def required_fold(*args, **kwargs):
        checks.append((args, kwargs))
        raise ValueError("Played v5 knockout requires its complete population sporting checkpoint")

    monkeypatch.setattr(sporting, "verify_checkpoint", required_fold)
    with pytest.raises(ValueError, match="requires its complete population"):
        opening.CalendarOpeningKnockoutService(object())._context(
            None, run_id="r", branch_id="b",
        )
    assert len(checks) == 1
    assert checks[0][1]["_verified_saved_prefix"] is None
