"""Signed Saved Run clock -> real read-only calendar Official candidate."""

from __future__ import annotations

import pytest

from beta_engine.application.calendar_official_ranking_preview import (
    preview_calendar_official_ranking_from_saved_run,
)
from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar, require_supported_full_simulation_calendar,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer, CalendarRankingResult, CalendarRankingWeek,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

from tests.application.test_run_calendar_read_authority import _setup, _signed_test_calendar

pytestmark = pytest.mark.pr_critical


def w(s, n):
    return CalendarRankingWeek(season_index=s, week=n)


@pytest.mark.parametrize("W,offset", [(52, 1), (61, 37), (80, 37)])
def test_preview_uses_exact_verified_sqlite_saved_head_and_never_writes(tmp_path, W, offset):
    engine, factory, repository = _setup(tmp_path)
    try:
        saved_clock = RunCalendar(W, offset, 2030, 3)
        _signed_test_calendar(factory, saved_clock)
        first_revision = repository.get_branch_revision_state(branch_id="branch-1")
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            candidate = preview_calendar_official_ranking_from_saved_run(
                session, run_id="run-1", branch_id="branch-1",
                expected_saved_head_revision_id="revision-1",
                week=w(1, W-1),
                policy=OfficialRankingPolicy(policy_id="test", best_n=1),
                players=(
                    CalendarRankingPlayer(
                        player_id="a", tie_break_token="a", tour_entry_week=w(0, 1),
                    ),
                ),
                results=(
                    CalendarRankingResult(
                        edition_id="edition", player_id="a",
                        source_fingerprint="saved-source",
                        completed_week=w(0, W-1),
                        first_publication_week=w(0, W),
                        main_points=100,
                    ),
                ),
            )
        assert candidate.rows[0].points == 100
        assert candidate.run_calendar == saved_clock.to_metadata()
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            with pytest.raises(ValueError, match="stale Saved HEAD"):
                preview_calendar_official_ranking_from_saved_run(
                    session, run_id="run-1", branch_id="branch-1",
                    expected_saved_head_revision_id="wrong",
                    week=w(1, W-1), policy=candidate.policy,
                    players=(), results=(),
                )
            with pytest.raises(ValueError, match="Run/Branch"):
                preview_calendar_official_ranking_from_saved_run(
                    session, run_id="foreign", branch_id="branch-1",
                    expected_saved_head_revision_id="revision-1",
                    week=w(1, W-1), policy=candidate.policy,
                    players=(), results=(),
                )
            assert resolve_saved_run_calendar(
                session, run_id="run-1", branch_id="branch-1",
            ) == saved_clock
            with pytest.raises(ValueError, match="cannot execute this Run calendar"):
                require_supported_full_simulation_calendar(saved_clock)
        assert repository.get_branch_revision_state(branch_id="branch-1") == first_revision
        assert repository.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_corrupt_saved_head_fingerprint_refuses_to_preview(tmp_path):
    engine, factory, repo = _setup(tmp_path)
    try:
        with factory.begin() as session:
            session.get(BranchSavedRevisionModel, "revision-1").content_hash = "e" * 64
        with factory() as session, pytest.raises(ValueError, match="hash"):
            session.connection().exec_driver_sql("BEGIN")
            preview_calendar_official_ranking_from_saved_run(
                session, run_id="run-1", branch_id="branch-1",
                expected_saved_head_revision_id="revision-1",
                week=w(0, 2), policy=OfficialRankingPolicy(policy_id="test"),
                players=(), results=(),
            )
    finally:
        engine.dispose()
