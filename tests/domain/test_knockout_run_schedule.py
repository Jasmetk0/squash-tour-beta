import pytest
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition, KnockoutRunSchedule, plan_knockout_run_matches
from tests.domain.test_native_canonical_knockout_contracts import fax_source, _authority

pytestmark = pytest.mark.pr_critical


def position(clock, week, slot, season=0):
    return KnockoutRoundPosition(week=RunWeekPosition(calendar=clock, season_index=season, week=week),slot=slot)


@pytest.mark.parametrize('w',[52,61,80])
def test_real_canonical_nodes_keep_qualification_before_main_across_weeks(fax_source,w):
    draw=_authority(fax_source).draw
    clock=RunCalendar(w,1,2025,2)
    s=KnockoutRunSchedule(calendar=clock,
        qualification=tuple(position(clock,5,n) for n in (1,2,3)),
        main=tuple(position(clock,6,n) for n in range(1,6)))
    plan=plan_knockout_run_matches(draw=draw,schedule=s)
    assert len(plan['matches']) == 51
    assert len(plan['bye_match_ids']) == 8
    assert not set(plan['bye_match_ids']) & {m['match_id'] for m in plan['matches']}
    assert {m['position']['week']['week'] for m in plan['matches'] if m['draw_type']=='qualification'} == {5}
    assert {m['position']['week']['week'] for m in plan['matches'] if m['draw_type']=='main'} == {6}
    assert plan_knockout_run_matches(draw=draw,schedule=s) == plan
    assert KnockoutRunSchedule.model_validate_json(s.model_dump_json()) == s


@pytest.mark.parametrize('damage',['reversed','duplicate','foreign_clock','season_boundary','empty_main'])
def test_invalid_chronology_is_rejected(damage):
    clock=RunCalendar.earth_default(start_year=2025,season_count=2)
    q=[position(clock,5,1),position(clock,5,2)]
    main=[position(clock,6,n) for n in range(1,6)]
    if damage=='reversed': q.reverse()
    if damage=='duplicate': q[1]=q[0]
    if damage=='foreign_clock': main[0]=position(RunCalendar.fax_default(start_year=2025,season_count=2),6,1)
    if damage=='season_boundary': main=[position(clock,1,n,season=1) for n in range(1,6)]
    if damage=='empty_main': main=[]
    with pytest.raises(ValueError): KnockoutRunSchedule(calendar=clock,qualification=tuple(q),main=tuple(main))


def test_slots_do_not_reset_chronology_inside_one_week():
    clock=RunCalendar.earth_default(start_year=2025,season_count=2)
    s=KnockoutRunSchedule(calendar=clock,qualification=(position(clock,6,10),),main=(position(clock,6,11),))
    s.validate_capacities(main_capacity=2,qualification_capacities=(2,2))
    with pytest.raises(ValueError): s.validate_capacities(main_capacity=32,qualification_capacities=(4,4))
    with pytest.raises(ValueError): s.validate_capacities(main_capacity=2,qualification_capacities=())


def test_calendar_year_rollover_is_allowed_inside_one_offset_season(fax_source):
    clock=RunCalendar(52,37,2025,2)
    s=KnockoutRunSchedule(calendar=clock,
        qualification=tuple(position(clock,16,n) for n in (1,2,3)),
        main=tuple(position(clock,17,n) for n in range(1,6)))
    assert s.qualification[-1].week.calendar_position.calendar_year==2025
    assert s.main[0].week.calendar_position.calendar_year==2026
    assert s.main[0].week.calendar_position.year_week==1
    assert len(plan_knockout_run_matches(draw=_authority(fax_source).draw,schedule=s)['matches'])==51


def test_horizon_and_week_bounds_cannot_be_wrapped_or_clipped():
    clock=RunCalendar(52,1,2025,1)
    for week,season in ((53,0),(1,1),(0,0)):
        with pytest.raises(ValueError): position(clock,week,1,season)
    with pytest.raises(ValueError): position(clock,5,True)


def test_legacy_clock_cannot_become_modern_by_extending_the_consumer():
    legacy=RunCalendar.legacy_fax()
    schedule=KnockoutRunSchedule.on_one_week(week=position(legacy,5,1).week,
        qualification=(1,),main=(2,))
    schedule.validate_runtime_calendar(legacy)
    with pytest.raises(ValueError,match='only extend'):
        schedule.validate_runtime_calendar(RunCalendar(61,37,2000,51))
