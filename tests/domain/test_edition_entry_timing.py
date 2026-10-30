import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.edition_entry_timing import (
    EditionEntryTiming, resolve_entry_timing, entry_window_at,
)

pytestmark = pytest.mark.pr_critical


def position(width=61, season=0, week=13):
    return RunWeekPosition(calendar=RunCalendar(width, 1, 2000, 3), season_index=season, week=week)


@pytest.mark.parametrize("width", [4, 52, 61, 80])
def test_windows_cross_seasons_on_actual_run_clock_without_scaling_durations(width):
    opening = position(width, week=width)
    play = position(width, season=1, week=4)
    resolved = resolve_entry_timing(EditionEntryTiming(main_open=opening), play)
    assert resolved["main_close"] == position(width, season=1, week=1)
    assert resolved["qualification_open"] == position(width, season=1, week=2)
    assert resolved["qualification_close"] == resolved["final_commitment"] == position(width, season=1, week=2)
    assert resolved["default_ranking_completed_week"] == opening
    assert resolved["ranking_publication_week"] == position(width, season=1, week=1)


@pytest.mark.parametrize("week,expected", [(12,"not_open"), (13,"main"), (14,"main"),
                                          (15,"qualification"), (16,"all_entries_closed")])
def test_main_q_and_closed_boundaries(week, expected):
    resolved = resolve_entry_timing(EditionEntryTiming(main_open=position()), position(week=20))
    assert entry_window_at(resolved, position(week=week)) == expected
    assert resolved["default_ranking_completed_week"].week == 13
    assert resolved["ranking_publication_week"].week == 14


def test_explicit_lengths_commitment_and_publication_override():
    timing = EditionEntryTiming(main_open=position(week=8), main_duration_weeks=3,
        qualification_duration_weeks=2, final_commitment=position(week=13),
        ranking_publication_override=position(week=4))
    resolved = resolve_entry_timing(timing, position(week=20))
    assert resolved["main_close"].week == 10
    assert resolved["qualification_close"].week == 12
    assert resolved["final_commitment"].week == 13
    assert resolved["ranking_publication_week"].week == 4
    assert resolved["ranking_source"] == "explicit_publication_override"


def test_missing_predecessor_is_not_a_week_zero_or_initial_ranking_fallback():
    resolved = resolve_entry_timing(EditionEntryTiming(main_open=position(week=1),
                                   main_duration_weeks=1), position(week=20))
    assert resolved["default_ranking_completed_week"] is None
    assert resolved["ranking_publication_week"] is None


@pytest.mark.parametrize("timing,play", [
    (EditionEntryTiming(main_open=position(52)), position(61, week=20)),
    (EditionEntryTiming(main_open=position(week=18)), position(week=20)),
    (EditionEntryTiming(main_open=position(), final_commitment=position(week=12)), position(week=20)),
    (EditionEntryTiming(main_open=position(), ranking_publication_override=position(week=20)), position(week=20)),
])
def test_invalid_clocks_or_pre_play_ranges_are_rejected(timing, play):
    with pytest.raises(ValueError):
        resolve_entry_timing(timing, play)
