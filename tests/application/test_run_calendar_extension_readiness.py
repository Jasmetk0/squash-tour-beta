"""Real SQLite all-Branch Run extension readiness checks."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from beta_engine.application.run_calendar_extension_readiness import (
    inspect_run_calendar_extension_readiness,
)
from beta_engine.api.routers.run_containers import inspect_calendar_extension_readiness
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import RunContainerModel, RunBranchModel
from tests.application.test_run_calendar_read_authority import _setup, _signed_test_calendar

pytestmark = pytest.mark.pr_critical


def test_all_branch_inspection_preserves_real_saved_revision_and_run(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 35, 2030, 3))
        with factory.begin() as session:
            run = session.get(RunContainerModel, "run-1")
            run.storage_kind = "custom_local"
            run.read_only = 0
        before = repo.get_run_container(run_id="run-1")
        revision_before = repo.get_branch_revision_state(branch_id="branch-1")
        with factory() as session:
            result = inspect_run_calendar_extension_readiness(
                session, run_id="run-1", new_season_count=5
            )
        assert result["read_only"] is True
        assert result["state_changed"] is False
        assert result["commit_supported"] is False
        assert result["ready_for_future_commit_preflight"] is True
        assert result["branch_count"] == 1
        assert result["branches"][0]["saved_head_revision_id"] == "revision-1"
        assert result["added_weeks"] == 104
        assert repo.get_run_container(run_id="run-1") == before
        assert repo.get_branch_revision_state(branch_id="branch-1") == revision_before
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_missing_second_branch_saved_head_blocks_future_commit(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 1, 2030, 3))
        with factory.begin() as session:
            run = session.get(RunContainerModel, "run-1")
            run.storage_kind = "custom_local"
            run.read_only = 0
            session.add(RunBranchModel(
                branch_id="unprepared-branch", run_id="run-1",
                display_name="Unprepared", status="active", read_only=0,
                metadata_json="{}", saved_head_revision_id=None
            ))
        runtime = SimpleNamespace(repository=SimpleNamespace(_session_factory=factory))
        result = inspect_calendar_extension_readiness("run-1", 4, runtime)
        assert result["ready_for_future_commit_preflight"] is False
        assert result["branch_count"] == 2
        assert "missing_saved_head" in result["blockers"]
        assert "saved_calendar_authority_failed" in result["blockers"]
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
        with pytest.raises(HTTPException) as exc:
            inspect_calendar_extension_readiness("run-1", 3, runtime)
        assert exc.value.status_code == 409
    finally:
        engine.dispose()
