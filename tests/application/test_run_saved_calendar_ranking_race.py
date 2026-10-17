"""A validated immutable Saved Run clock powers pure ranking math; no writes."""

from __future__ import annotations

import pytest

from beta_engine.application.run_calendar_read_authority import (
    resolve_saved_run_calendar, require_supported_full_simulation_calendar,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.engine import RankingRaceEngine
from beta_engine.domain.rankings.models import CompletedTournamentPointsInput
from tests.application.test_run_calendar_read_authority import (
    _setup, _signed_test_calendar,
)

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("weeks,offset", [(52, 1), (61, 37), (80, 37)])
def test_validated_saved_clock_drives_week_age_without_weakening_sport_gate(
    tmp_path, weeks, offset
):
    engine, factory, repository = _setup(tmp_path)
    try:
        clock = RunCalendar(weeks, offset, 2030, 3)
        _signed_test_calendar(factory, clock)
        original = repository.get_branch_revision_state(branch_id="branch-1")
        with factory() as session:
            session.connection().exec_driver_sql("BEGIN")
            saved = resolve_saved_run_calendar(
                session, run_id="run-1", branch_id="branch-1",
            )
        assert saved == clock
        completed = CompletedTournamentPointsInput(
            event_id="edition-prev", season=2030, week=weeks, template_id="test",
            point_distribution={"champion": 100},
            placements=[{"player_id": "p", "finish": "CHAMPION"}],
        )
        service = RankingRaceEngine(point_distributions_by_ref={})
        result = service.build_report(
            completed_tournaments=[completed],
            as_of_season=2031, as_of_week=weeks - 1,
            target_season=2031, run_calendar=saved,
        )
        assert result.ranking.standings[0].ranking_points == 100
        expired = service.build_report(
            completed_tournaments=[completed],
            as_of_season=2031, as_of_week=weeks,
            target_season=2031, run_calendar=saved,
        )
        assert expired.ranking.standings == []
        assert expired.run_calendar == clock.to_metadata()
        with factory() as session:
            with pytest.raises(ValueError, match="cannot execute this Run calendar"):
                require_supported_full_simulation_calendar(
                    resolve_saved_run_calendar(
                        session, run_id="run-1", branch_id="branch-1",
                    ),
                )
        assert repository.get_branch_revision_state(branch_id="branch-1") == original
        assert repository.verify_branch_saved_revision_hash(revision_id="revision-1")
    finally:
        engine.dispose()


def test_historical_year_zero_is_valid_only_with_explicit_clock():
    from beta_engine.domain.rankings.models import RunCalendarRankingRaceReport
    clock = RunCalendar(80, 1, 0, 3)
    engine = RankingRaceEngine(point_distributions_by_ref={})
    source = CompletedTournamentPointsInput(
        event_id="year-zero", season=0, week=80, template_id="test",
        point_distribution={"champion": 100},
        placements=[{"player_id": "p", "finish": "CHAMPION"}],
    )
    result = engine.build_report(
        completed_tournaments=[source],
        as_of_season=1, as_of_week=79, target_season=1,
        run_calendar=clock,
    )
    assert isinstance(result, RunCalendarRankingRaceReport)
    assert result.ranking.standings[0].ranking_points == 100
    with pytest.raises(ValueError, match="Legacy"):
        engine.resolve_point_awards(completed_tournaments=[source])
