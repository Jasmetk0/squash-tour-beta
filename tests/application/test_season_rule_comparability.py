"""Read-only season comparison detects changed actual point tables and draw formats."""
from types import SimpleNamespace as NS
import pytest
from beta_engine.application.calendar_tour_season_archive import season_comparability
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical


def test_comparison_reports_doubled_point_tables_and_changed_draw_size():
    clock = RunCalendar(52, 1, 2030, 3)
    week = lambda s: RunWeekPosition(calendar=clock, season_index=s, week=4)
    policy = NS(effective_week=week(0), ranking=NS(policy_id='same', best_n=15),
                development=NS(model_dump=lambda **_: {'policy': 'same'}))
    def edition(s, points=100, size=4):
        return NS(edition=NS(week=week(s), point_table={'champion': points},
                            main_entrant_count=size, group_configuration=None))
    state = NS(week=week(1), policies=[policy], editions=[edition(0), edition(1)])
    assert season_comparability(state, 1, 0)['comparable'] is True
    state.editions[1] = edition(1, points=200)
    changed = season_comparability(state, 1, 0)
    assert changed['comparable'] is False
    assert {d['field'] for d in changed['differences']} == {'edition_point_tables_fingerprint'}
    state.editions[1] = edition(1, points=200, size=8)
    changed = season_comparability(state, 1, 0)
    assert {d['field'] for d in changed['differences']} == {
        'edition_point_tables_fingerprint', 'edition_formats_fingerprint'}
    assert 'edition_categories' in changed['not_compared']
