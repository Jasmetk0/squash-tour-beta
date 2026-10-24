"""Pure ranking contracts. Synthetic rule inputs are not sporting acceptance."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.calendar_season_closing import (
    calculate_calendar_season_closing,
)
from beta_engine.domain.rankings.calendar_terminal_result import (
    CalendarTerminalRankingResult,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy

pytestmark = pytest.mark.pr_critical


def terminal(clock, player='p', points=60, **extra):
    return CalendarTerminalRankingResult(
        **{'run_id': 'run', 'branch_id': 'branch', 'edition_id': 'last-cup', 'player_id': player,
            'completed_week': RunWeekPosition(calendar=clock, season_index=clock.season_count-1, week=clock.weeks_per_year),
            'closing_eligibility_ordinal': clock.season_count*clock.weeks_per_year,
            'created_saved_head': 'actual-created-head', 'played_saved_head': 'actual-played-head',
            'edition_fingerprint': '1'*64, 'execution_fingerprint': '2'*64, 'played_fingerprint': '3'*64,
            'source_fingerprint': '4'*64, 'main_points': points, 'validity_weeks': clock.weeks_per_year, 'ranked': True} | extra)


@pytest.mark.parametrize('weeks,offset', [(1,1), (4,2), (52,1), (61,37), (80,79)])
def test_terminal_result_has_real_clock_and_only_scalar_eligibility(weeks, offset):
    clock = RunCalendar(weeks, offset, 2040, 2)
    result = terminal(clock)
    assert 'first_publication_week' not in result.model_dump(mode='json')
    assert CalendarTerminalRankingResult.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValueError, match='horizon'):
        clock.position_at_ordinal(result.closing_eligibility_ordinal)
    with pytest.raises(ValueError, match='extension'):
        result.for_publication(clock)
    longer = RunCalendar(weeks, offset, 2040, 3)
    published = result.for_publication(longer)
    assert published.source_fingerprint == result.source_fingerprint
    assert published.first_publication_week == CalendarRankingWeek(season_index=2, week=1)
    assert result.completed_week.calendar == clock
    with pytest.raises(ValueError, match='boundary'):
        terminal(clock, closing_eligibility_ordinal=result.closing_eligibility_ordinal-1)
    with pytest.raises(ValueError, match='extension'):
        result.for_publication(RunCalendar(weeks, offset, 2041, 3))


@pytest.mark.parametrize('best_n', [1, 2, 3])
def test_closing_best_n_ties_retirement_duplicate_future_and_foreign_sources(best_n):
    clock = RunCalendar(4, 2, 2040, 2)
    end = CalendarRankingWeek(season_index=1, week=4)
    players = tuple(CalendarRankingPlayer(player_id=pid, tie_break_token=pid,
        tour_entry_week=CalendarRankingWeek(season_index=0, week=1), retired=pid=='retired') for pid in ('p','q','retired'))
    policy = OfficialRankingPolicy(policy_id='outgoing', best_n=best_n)
    old = tuple(CalendarRankingResult(edition_id='previous-cup', player_id=p.player_id, source_fingerprint=p.player_id+'-old',
        completed_week=CalendarRankingWeek(season_index=1, week=2), first_publication_week=CalendarRankingWeek(season_index=1, week=3), main_points=70) for p in players)
    results = tuple(terminal(clock, p.player_id) for p in players)
    previous = calculate_calendar_official_ranking(run_id='run', branch_id='branch', run_calendar=clock, week=end, policy=policy, players=players, results=old)
    def close(inputs=(*old,*results)):
        return calculate_calendar_season_closing(calendar=clock, completed_week=end, policy=policy, players=players, results=inputs, previous=previous)
    closed = close()
    assert [r['player_id'] for r in closed['rows']] == ['p','q']
    assert [r['points'] for r in closed['rows']] == [70 if best_n==1 else 130]*2
    assert all(len(r['counted_results']) == min(best_n,2) for r in closed['rows'])
    assert close(tuple(reversed((*old,*results)))) == closed
    with pytest.raises(ValueError, match='unique'):
        close((*old,*results,results[0]))
    with pytest.raises(ValueError, match='owner'):
        close((terminal(clock, branch_id='foreign'),))
    with pytest.raises(ValueError, match='calendar'):
        close((terminal(RunCalendar(4,1,2040,2)),))
    with pytest.raises(ValueError, match='horizon|future'):
        close((terminal(RunCalendar(4,2,2040,3)),))
    assert all(r.points == 70 for r in previous.rows)
