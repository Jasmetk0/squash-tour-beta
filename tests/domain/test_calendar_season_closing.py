"""Unit contracts: outgoing policy, exact W-based expiry and no extra week."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.calendar_season_closing import (
    calculate_calendar_season_closing,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("weeks,offset", [(4, 4), (52, 35), (61, 37), (80, 80)])
def test_native_closing_expires_at_boundary_and_uses_outgoing_best_n(weeks, offset):
    clock = RunCalendar(weeks, offset, 2100, 2)
    week = CalendarRankingWeek(season_index=1, week=weeks)
    player = CalendarRankingPlayer(player_id="p", tie_break_token="p", tour_entry_week=CalendarRankingWeek(season_index=0, week=1))
    old = CalendarRankingResult(edition_id="old", player_id="p", source_fingerprint="actual-unit-source-old",
        completed_week=CalendarRankingWeek(season_index=0, week=weeks),
        first_publication_week=CalendarRankingWeek(season_index=1, week=1), main_points=100)
    new = CalendarRankingResult(edition_id="new", player_id="p", source_fingerprint="actual-unit-source-new",
        completed_week=CalendarRankingWeek(season_index=1, week=weeks-1), first_publication_week=week, main_points=60)
    policy = OfficialRankingPolicy(policy_id="outgoing-best-one", best_n=1)
    published = calculate_calendar_official_ranking(run_id="run", branch_id="branch", run_calendar=clock,
        week=week, policy=policy, players=(player,), results=(old, new))
    assert published.rows[0].points == 100
    closed = calculate_calendar_season_closing(calendar=clock, completed_week=week, policy=policy,
        players=(player,), results=(old, new), previous=published)
    assert closed["rows"][0]["points"] == 60
    assert closed["rows"][0]["counted_results"][0]["edition_id"] == "new"
    assert closed["eligibility_boundary_ordinal"] == 2 * weeks
    assert closed["execution_calendar"] == clock.to_metadata()
    assert closed["policy"]["policy_id"] == "outgoing-best-one"
    assert published.week == week
    assert closed == calculate_calendar_season_closing(calendar=clock, completed_week=week, policy=policy,
        players=(player,), results=(new, old), previous=published)
