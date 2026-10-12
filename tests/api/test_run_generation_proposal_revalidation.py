"""F79-02: immutable SQLite historical inspection versus explicit fresh revalidation."""
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from beta_engine.api.routers import admin_players
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldService,
)
from tests.api.test_run_generation_proposals import _runtime, _payload
from tests.application.test_run_world_session_keep import service

pytestmark = pytest.mark.pr_critical


def _saved(tmp_path, monkeypatch):
    runtime, engine = _runtime(tmp_path)
    payload, old = _payload()
    monkeypatch.setattr(
        admin_players, "_assert_reviewed_generation_context",
        lambda **kwargs: None,
    )
    admin_players.save_run_generation_proposal(
        "run-one", "branch-one", payload,
        package_service=NS(),
        preview_service=RunWorldInitialWorldService(service()),
        runtime=runtime,
    )
    return runtime, engine, payload, old


def _move_target(runtime, *, head="changed-head", draft_version=2, status="dirty"):
    runtime.repository.get_run_branch = lambda *, branch_id: (
        NS(run_id="run-one", read_only=False, status="active",
           saved_head_revision_id=head) if branch_id == "branch-one" else None
    )
    runtime.repository.get_branch_revision_state = lambda *, branch_id: NS(
        saved_revision=NS(revision_id=head),
        working_draft=NS(
            draft_version=draft_version, base_revision_id=head, status=status,
        ),
    )


def test_stale_head_draft_world_still_inspectable_without_generation(tmp_path, monkeypatch):
    runtime, engine, payload, old = _saved(tmp_path, monkeypatch)
    _move_target(runtime)
    class NoGenerator:
        def preview(self, **kwargs):
            raise AssertionError("Inspection must not generate any new players")
    # Strict current Open still fails; new inspection cannot call the preview service.
    monkeypatch.setattr(
        admin_players, "_assert_reviewed_generation_context",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("Current target changed")),
    )
    with pytest.raises(HTTPException, match="Current target changed"):
        admin_players.read_run_generation_proposal(
            "run-one", "branch-one", payload.proposal_id,
            package_service=NS(), runtime=runtime,
        )
    current_package = NS(get=lambda **kwargs: NS(fingerprint="b" * 64))
    read = admin_players.inspect_run_generation_proposal(
        "run-one", "branch-one", payload.proposal_id,
        package_service=current_package, runtime=runtime,
    )
    assert read["historical_only"] is True
    assert read["proposal"]["preview"]["fingerprint"] == old.fingerprint
    assert len(read["proposal"]["preview"]["state"]["players"]) == 32
    assert read["context"]["head_matches"] is False
    assert read["context"]["draft_matches"] is False
    assert read["context"]["package_matches"] is False
    assert read["context"]["revalidation_required"] is True
    # The unchanged bytes can be inspected again after a new runtime/restart.
    reopened, _ = _runtime(tmp_path)
    _move_target(reopened)
    assert admin_players.inspect_run_generation_proposal(
        "run-one", "branch-one", payload.proposal_id,
        package_service=current_package, runtime=reopened,
    )["proposal"] == read["proposal"]


def test_explicit_clean_revalidation_does_not_mutate_saved_candidate_or_adopt(tmp_path, monkeypatch):
    runtime, engine, payload, old = _saved(tmp_path, monkeypatch)
    _move_target(runtime, status="clean")
    context = admin_players.RunGenerationProposalRevalidation(
        expected_head="changed-head", expected_draft_version=2,
        expected_package_fingerprint="b" * 64,
    )
    seen = []
    monkeypatch.setattr(
        admin_players, "_assert_reviewed_generation_context",
        lambda **kwargs: (
            seen.append(kwargs),
            None,
        ) if kwargs["expected_head"] == "changed-head" and
             kwargs["expected_package_fingerprint"] == "b" * 64 and
             kwargs["expected_draft_version"] == 2 else
        (_ for _ in ()).throw(ValueError("Stale generation target")),
    )
    class PreviewSpy:
        called = 0
        def preview(self, **kwargs):
            self.called += 1
            return RunWorldInitialWorldService(service()).preview(**kwargs)
    preview = PreviewSpy()
    before = admin_players.inspect_run_generation_proposal(
        "run-one", "branch-one", payload.proposal_id,
        package_service=NS(get=lambda **kwargs: NS(fingerprint="b"*64)),
        runtime=runtime,
    )["proposal"]
    refreshed = admin_players.revalidate_run_generation_proposal(
        "run-one", "branch-one", payload.proposal_id, context,
        package_service=NS(), preview_service=preview, runtime=runtime,
    )
    assert preview.called == 1 and len(seen) == 1
    assert refreshed["preview_only"] is True
    assert refreshed["original_preview_fingerprint"] == old.fingerprint
    assert refreshed["preview"]["fingerprint"] == old.fingerprint
    assert refreshed["comparison"] == {
        "old_count": 32, "new_count": 32,
        "added_identities": 0, "removed_identities": 0,
        "changed_profiles": 0, "unchanged_profiles": 32,
    }
    after = admin_players.inspect_run_generation_proposal(
        "run-one", "branch-one", payload.proposal_id,
        package_service=NS(get=lambda **kwargs: NS(fingerprint="b"*64)),
        runtime=runtime,
    )["proposal"]
    assert after == before
    assert not hasattr(runtime.repository, "adopt_initial_world")
    with pytest.raises(HTTPException, match="Stale generation target"):
        admin_players.revalidate_run_generation_proposal(
            "run-one", "branch-one", payload.proposal_id,
            context.model_copy(update={"expected_head": "forged-head"}),
            package_service=NS(), preview_service=preview, runtime=runtime,
        )
    assert preview.called == 1


def test_inspection_rejects_foreign_run_branch_and_corrupted_sqlite(tmp_path, monkeypatch):
    runtime, engine, payload, _ = _saved(tmp_path, monkeypatch)
    _move_target(runtime)
    packages = NS(get=lambda **kwargs: NS(fingerprint="b" * 64))
    for run_id, branch_id in [("other-run", "branch-one"), ("run-one", "foreign")]:
        with pytest.raises(HTTPException) as err:
            admin_players.inspect_run_generation_proposal(
                run_id, branch_id, payload.proposal_id,
                package_service=packages, runtime=runtime,
            )
        assert err.value.status_code == 409
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE run_generation_proposals SET payload_json='{}' "
            "WHERE run_id='run-one' AND branch_id='branch-one'"
        ))
    with pytest.raises(HTTPException, match="checksum"):
        admin_players.inspect_run_generation_proposal(
            "run-one", "branch-one", payload.proposal_id,
            package_service=packages, runtime=runtime,
        )


def test_revalidation_stays_blocked_with_existing_initial_world(tmp_path, monkeypatch):
    runtime, _, payload, _ = _saved(tmp_path, monkeypatch)
    _move_target(runtime, status="clean")
    runtime.repository.get_initial_world = lambda **kwargs: NS(players=[])
    with pytest.raises(HTTPException, match="Existing InitialWorld"):
        admin_players.revalidate_run_generation_proposal(
            "run-one", "branch-one", payload.proposal_id,
            admin_players.RunGenerationProposalRevalidation(
                expected_head="changed-head", expected_draft_version=2,
                expected_package_fingerprint="b" * 64,
            ),
            package_service=NS(), preview_service=NS(), runtime=runtime,
        )
