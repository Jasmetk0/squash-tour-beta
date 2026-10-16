"""Real SQLite extension preview: immutable history and zero writes."""

import pytest

from beta_engine.application.run_calendar_target_preview import (
    preview_saved_run_calendar_extension,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.application.test_run_calendar_read_authority import (
    _setup,
    _signed_test_calendar,
)

pytestmark = pytest.mark.pr_critical


def test_extension_preview_uses_saved_clock_without_changing_database(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(52, 35, 2030, 3))
        run_before = repo.get_run_container(run_id="run-1")
        revision_before = repo.get_branch_revision_state(branch_id="branch-1")
        with factory() as session:
            result = preview_saved_run_calendar_extension(
                session, run_id="run-1", branch_id="branch-1",
                new_season_count=5,
            )
        assert result["read_only"] is True
        assert result["state_changed"] is False
        assert result["save_performed"] is False
        assert result["simulation_started"] is False
        assert result["commit_supported"] is False
        assert result["original_calendar"]["season_count"] == 3
        assert result["proposed_calendar"]["season_count"] == 5
        assert result["previous_last_week"]["season_index"] == 2
        assert result["first_added_week"]["season_index"] == 3
        assert result["first_added_week"]["season_week"] == 1
        assert result["new_last_week"]["season_index"] == 4
        assert result["new_last_week"]["season_week"] == 52
        assert result["added_seasons"] == 2
        assert result["added_weeks"] == 104
        assert repo.get_run_container(run_id="run-1") == run_before
        assert repo.get_branch_revision_state(branch_id="branch-1") == revision_before
        assert repo.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_extension_preview_rejects_non_growth_and_historical_legacy(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        _signed_test_calendar(factory, RunCalendar(80, 75, 0, 2))
        with factory() as session:
            with pytest.raises(ValueError, match="exceed current horizon"):
                preview_saved_run_calendar_extension(
                    session, run_id="run-1", branch_id="branch-1",
                    new_season_count=2,
                )
            result = preview_saved_run_calendar_extension(
                session, run_id="run-1", branch_id="branch-1",
                new_season_count=3,
            )
            assert result["added_weeks"] == 80
            assert result["first_added_week"]["calendar_year"] == 2
        _signed_test_calendar(factory, None)
        with factory() as session:
            with pytest.raises(ValueError, match="legacy calendar extension"):
                preview_saved_run_calendar_extension(
                    session, run_id="run-1", branch_id="branch-1",
                    new_season_count=51,
                )
    finally:
        engine.dispose()
