"""Real SQLite current-Branch readiness. Read-only, no simulation claims."""

from __future__ import annotations

import json

import pytest

from beta_engine.application.run_home_readiness import inspect_run_home_readiness
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel, BranchWorkingDraftModel,
)
from tests.application.test_run_calendar_read_authority import _setup, _signed_test_calendar

pytestmark = pytest.mark.pr_critical


def _inspect(factory, repo, branch_id="branch-1"):
    with factory() as session:
        session.connection().exec_driver_sql("BEGIN")
        return inspect_run_home_readiness(
            session, repo, run_id="run-1", branch_id=branch_id,
        )


def test_empty_default_fax_is_not_sporting_readiness_and_is_read_only(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        original = repo.get_branch_revision_state(branch_id="branch-1")
        first = _inspect(factory, repo)
        assert first.schema_version == "run_home_readiness.v1"
        assert first.saved_revision_id == original.saved_revision.revision_id
        assert first.saved_revision_content_hash == original.saved_revision.content_hash
        assert first.sporting_calendar_supported_by_legacy_writers
        assert first.requires_operation_preflight is True
        assert first.simulation_started is False
        assert first.phase == "preparation"
        assert [x.code for x in first.items] == [
            "world", "calendar_package", "population", "health",
            "official_ranking", "working_draft",
        ]
        assert [x.status for x in first.items] == [
            "missing", "missing", "missing", "optional", "missing", "saved",
        ]
        assert all(item.evidence_count == 0 for item in first.items)
        assert first == _inspect(factory, repo)
        assert repo.get_branch_revision_state(branch_id="branch-1") == original
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_w52_and_dirty_working_draft_never_show_false_green(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 35, 2030, 3))
        initial = _inspect(factory, repo)
        assert not initial.sporting_calendar_supported_by_legacy_writers
        assert initial.current_calendar["weeks_per_year"] == 52
        assert initial.current_calendar["season_start_year_week"] == 35
        with factory.begin() as session:
            draft = session.get(BranchWorkingDraftModel, "draft-1")
            draft.status = "dirty"
            draft.draft_version += 1
            draft.change_count = 1
            draft.changes_json = json.dumps([{"kind": "viewer_branch_selection", "viewer_branch_id": "branch-1"}])
        changed = _inspect(factory, repo)
        assert changed.draft_version > initial.draft_version
        assert changed.items[-1].status == "unsaved"
        assert changed.items[-1].evidence_count == 1
        assert changed.items[0].status == "missing"
        assert changed.simulation_started is False
    finally:
        engine.dispose()


def test_broken_hash_and_wrong_run_branch_are_fail_closed(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(KeyError):
                inspect_run_home_readiness(session, repo, run_id="run-1", branch_id="foreign")
        with factory.begin() as session:
            session.get(BranchSavedRevisionModel, "revision-1").content_hash = "f" * 64
        with pytest.raises(ValueError, match="hash|integrity"):
            _inspect(factory, repo)
    finally:
        engine.dispose()


def test_completed_phase_is_not_a_restarted_task(tmp_path):
    from beta_engine.infrastructure.db.models import RunContainerModel
    engine, factory, repo = _setup(tmp_path)
    try:
        with factory.begin() as session:
            session.get(RunContainerModel, "run-1").status = "completed"
        result = _inspect(factory, repo)
        assert result.phase == "completed"
        assert result.active_full_simulation_task_count == 0
        assert result.simulation_started is False
        assert result.requires_operation_preflight
    finally:
        engine.dispose()
