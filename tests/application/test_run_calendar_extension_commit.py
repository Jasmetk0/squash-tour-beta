"""Real SQLite V83 all-Branch extension, immutable history and conflict tests."""

import json

import pytest

from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_calendar_extension_commit import (
    review_run_calendar_extension, save_run_calendar_extension,
)
from beta_engine.application.run_calendar_read_authority import resolve_saved_run_calendar
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import (
    BranchWorkingDraftModel, RunCalendarExtensionReceiptModel,
)
from tests.application.test_run_calendar_read_authority import _setup, _signed_test_calendar

pytestmark = pytest.mark.pr_critical


def _review(factory, repo, count):
    with factory() as session:
        session.connection().exec_driver_sql("BEGIN")
        return review_run_calendar_extension(
            session, repo, run_id="run-1", new_season_count=count
        )


def _save(repo, review, command="extend-1", confirm=True):
    return save_run_calendar_extension(
        repo, run_id="run-1", command_id=command,
        new_season_count=review["proposed_calendar"]["season_count"],
        review_fingerprint=review["review_fingerprint"],
        explicit_confirmation=confirm,
    )


def test_reviewed_two_branch_save_restart_and_idempotent_retry(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 1, 2030, 3))
        RunBranchCreationService(repo, lambda kind: {
            "branch": "branch-2", "working-draft": "draft-2",
        }[kind]).create_from_saved_revision(
            run_id="run-1", source_branch_id="branch-1",
            source_saved_revision_id="revision-1", display_name="Alternative",
        )
        old = repo.get_branch_saved_revision(revision_id="revision-1")
        review = _review(factory, repo, 5)
        assert review["can_save"], review["blockers"]
        assert review["branch_count"] == 2 and review["added_weeks"] == 104
        with pytest.raises(ValueError, match="Explicit confirmation"):
            _save(repo, review, confirm=False)
        receipt = _save(repo, review)
        assert receipt["saved"] and receipt["branch_count"] == 2
        assert receipt["simulation_started"] is False
        assert receipt == _save(repo, review)
        assert repo.get_run_container(run_id="run-1").timeline_end_season == 2034

        for branch_id in ("branch-1", "branch-2"):
            state = repo.get_branch_revision_state(branch_id=branch_id)
            assert state.saved_revision.kind == "run_calendar_horizon_extension"
            assert state.saved_revision.parent_revision_id == "revision-1"
            assert state.saved_revision.payload["run"]["run_calendar"]["season_count"] == 5
            assert state.working_draft.status == "clean"
            assert state.working_draft.base_revision_id == state.saved_revision.revision_id
            assert repo.verify_branch_saved_revision_hash(
                revision_id=state.saved_revision.revision_id
            )
        assert repo.get_branch_saved_revision(revision_id="revision-1") == old
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
        with factory() as session:
            assert session.query(RunCalendarExtensionReceiptModel).count() == 1
            for branch_id in ("branch-1", "branch-2"):
                assert resolve_saved_run_calendar(
                    session, run_id="run-1", branch_id=branch_id
                ) == RunCalendar(52, 1, 2030, 5)

        from beta_engine.infrastructure.db import SimulationPersistenceRepository
        reopened = SimulationPersistenceRepository(engine=engine, session_factory=factory)
        assert _save(reopened, review) == receipt
    finally:
        engine.dispose()


def test_stale_review_and_dirty_draft_have_no_partial_effect(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 35, 2030, 3))
        initial_review = _review(factory, repo, 4)
        assert initial_review["can_save"], initial_review["blockers"]
        with factory.begin() as session:
            draft = session.query(BranchWorkingDraftModel).filter_by(
                branch_id="branch-1"
            ).one()
            draft.status = "dirty"
            draft.change_count = 1
            draft.draft_version += 1
            draft.changes_json = json.dumps([{"kind": "pending"}])
        dirty = _review(factory, repo, 4)
        assert not dirty["can_save"]
        with pytest.raises(ValueError, match="blocked"):
            _save(repo, initial_review)
        with factory.begin() as session:
            draft = session.query(BranchWorkingDraftModel).filter_by(
                branch_id="branch-1"
            ).one()
            draft.status = "clean"
            draft.change_count = 0
            draft.changes_json = "[]"
            draft.draft_version += 1
        with pytest.raises(ValueError, match="changed since review"):
            _save(repo, initial_review)
        assert repo.get_run_container(run_id="run-1").timeline_end_season == 2032
        assert _save(repo, _review(factory, repo, 4))["saved"]
    finally:
        engine.dispose()


def test_reused_command_id_different_intent_rejected(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        review = _review(factory, repo, 51)
        assert review["can_save"], review["blockers"]
        _save(repo, review, command="same-key")
        with pytest.raises(ValueError, match="already used"):
            save_run_calendar_extension(
                repo, run_id="run-1", command_id="same-key",
                new_season_count=52,
                review_fingerprint=review["review_fingerprint"],
                explicit_confirmation=True,
            )
        assert repo.get_run_container(run_id="run-1").timeline_end_season == 2050
    finally:
        engine.dispose()



def test_new_branch_between_review_and_commit_is_conflict(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        review = _review(factory, repo, 51)
        assert review["can_save"]
        RunBranchCreationService(repo, lambda kind: {
            "branch": "late-branch", "working-draft": "late-draft",
        }[kind]).create_from_saved_revision(
            run_id="run-1", source_branch_id="branch-1",
            source_saved_revision_id="revision-1", display_name="Late branch",
        )
        with pytest.raises(ValueError, match="changed since review"):
            _save(repo, review)
        assert repo.get_run_container(run_id="run-1").timeline_end_season == 2049
        assert repo.get_branch_revision_state(branch_id="late-branch").saved_revision.revision_id == "revision-1"
    finally:
        engine.dispose()


def test_injected_second_branch_failure_rolls_back_everything(tmp_path, monkeypatch):
    from beta_engine.application import run_calendar_extension_commit as subject

    engine, factory, repo = _setup(tmp_path)
    try:
        RunBranchCreationService(repo, lambda kind: {
            "branch": "branch-2", "working-draft": "draft-2",
        }[kind]).create_from_saved_revision(
            run_id="run-1", source_branch_id="branch-1",
            source_saved_revision_id="revision-1", display_name="Alternative",
        )
        review = _review(factory, repo, 51)
        assert review["can_save"], review["blockers"]
        original = subject.saved_revision_content_hash
        calls = []

        def fail_second(**kwargs):
            calls.append(kwargs["branch_id"])
            if len(calls) == 2:
                raise RuntimeError("injected failure during second Branch")
            return original(**kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(subject, "saved_revision_content_hash", fail_second)
            with pytest.raises(RuntimeError, match="second Branch"):
                _save(repo, review)
        assert calls == ["branch-1", "branch-2"]
        for branch_id in ("branch-1", "branch-2"):
            state = repo.get_branch_revision_state(branch_id=branch_id)
            assert state.saved_revision.revision_id == "revision-1"
            assert state.working_draft.status == "clean"
        with factory() as session:
            assert session.query(RunCalendarExtensionReceiptModel).count() == 0
        assert repo.get_run_container(run_id="run-1").timeline_end_season == 2049
        assert _save(repo, review)["saved"]
    finally:
        engine.dispose()


def test_w80_completed_run_preserved_and_not_started(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(80, 40, 2040, 2))
        with factory.begin() as session:
            run = session.get(__import__(
                "beta_engine.infrastructure.db.models", fromlist=["RunContainerModel"]
            ).RunContainerModel, "run-1")
            run.status = "completed"
        review = _review(factory, repo, 4)
        assert review["can_save"], review["blockers"]
        receipt = _save(repo, review)
        assert receipt["current_calendar"]["weeks_per_year"] == 80
        assert receipt["current_calendar"]["season_start_year_week"] == 40
        assert receipt["simulation_started"] is False
        assert repo.get_run_container(run_id="run-1").status == "completed"
        with factory() as session:
            assert resolve_saved_run_calendar(
                session, run_id="run-1", branch_id="branch-1"
            ) == RunCalendar(80, 40, 2040, 4)
    finally:
        engine.dispose()



def test_historical_restore_and_fork_keep_old_revision_immutable(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        historical = repo.get_branch_saved_revision(revision_id="revision-1")
        assert historical.payload["run"]["run_calendar"]["season_count"] == 50
        _save(repo, _review(factory, repo, 52))
        before_restore = repo.get_branch_revision_state(branch_id="branch-1")
        restored = repo.restore_branch_saved_revision_atomically(
            run_id="run-1", branch_id="branch-1",
            target_saved_revision_id="revision-1",
            expected_head_saved_revision_id=before_restore.saved_head_revision_id,
            expected_draft_version=before_restore.working_draft.draft_version,
            expected_current_viewer_branch_id="branch-1",
            checkpoint_id="restore-checkpoint-old-clock",
            restore_saved_revision_id="restore-revision-current-clock",
            audit_event_id="restore-audit-current-clock",
        )
        assert restored.saved_revision.payload["run"]["run_calendar"]["season_count"] == 52
        assert restored.saved_revision.parent_revision_id == before_restore.saved_head_revision_id
        assert repo.get_branch_saved_revision(revision_id="revision-1") == historical
        fork = RunBranchCreationService(repo, lambda kind: {
            "branch": "fork-after-extension",
            "working-draft": "fork-after-extension-draft",
            "saved-revision": "fork-rebased-current-clock",
        }[kind]).create_from_saved_revision(
            run_id="run-1", source_branch_id="branch-1",
            source_saved_revision_id="revision-1",
            display_name="Historical source",
        )
        assert fork.saved_head_revision_id == "fork-rebased-current-clock"
        with factory() as session:
            assert resolve_saved_run_calendar(
                session, run_id="run-1", branch_id="fork-after-extension"
            ).season_count == 52
        assert repo.get_branch_saved_revision(revision_id="revision-1") == historical
    finally:
        engine.dispose()



def test_pending_legacy_authoritative_command_blocks_even_without_server_task(tmp_path):
    from beta_engine.infrastructure.db.models import AuthoritativeSimulationCommandModel

    engine, factory, repo = _setup(tmp_path)
    try:
        with factory.begin() as session:
            session.add(AuthoritativeSimulationCommandModel(
                run_id="run-1", branch_id="branch-1",
                command_id="legacy-parent", request_fingerprint="a" * 64,
                status="pending", result_json='{"control_state":"paused"}',
            ))
        review = _review(factory, repo, 51)
        assert review["can_save"] is False
        assert "pending_authoritative_simulation_command" in review["blockers"]
        assert review["pending_authoritative_command_count"] == 1
        with pytest.raises(ValueError, match="blocked"):
            _save(repo, review)
        assert repo.get_branch_revision_state(branch_id="branch-1").saved_revision.revision_id == "revision-1"
    finally:
        engine.dispose()

