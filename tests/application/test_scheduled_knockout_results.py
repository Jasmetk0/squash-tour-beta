"""Actual match facts -> phase awards -> Run-calendar ranking candidates."""
import pytest

import json
from beta_engine.application.scheduled_knockout_results import complete_scheduled_knockout_result, scheduled_knockout_ranking_results, ScheduledKnockoutResult, scheduled_point_distribution
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import CalendarRankingPlayer, CalendarRankingWeek, calculate_calendar_official_ranking
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from tests.application.test_scheduled_knockout_feeders import played, plan, play_scheduled, PLAYERS

pytestmark=pytest.mark.pr_critical


def candidate(p, rows, season, week):
    return calculate_calendar_official_ranking(run_id=p.draw.run_id,branch_id=p.draw.branch_id,run_calendar=p.calendar,
        week=CalendarRankingWeek(season_index=season,week=week),policy=OfficialRankingPolicy(policy_id="explicit-test-best15"),
        players=tuple(CalendarRankingPlayer(player_id=pid,tie_break_token=pid,
            tour_entry_week=CalendarRankingWeek(season_index=p.schedule.main[0].week.season_index,week=1)) for pid in PLAYERS),results=rows)


def test_44_players_receive_exact_phase_points_once_and_publish_next_week(played):
    p,matches,positions,_=played
    result,rows=scheduled_knockout_ranking_results(plan=p,matches=matches,positions=positions)
    assert len(rows)==44 and len({r.player_id for r in rows})==44
    assert result.completed_week.week==6 and result.completed_week.calendar.weeks_per_year==52
    assert ScheduledKnockoutResult.model_validate_json(result.model_dump_json())==result
    with pytest.raises(ValueError,match='identities'):
        ScheduledKnockoutResult.model_validate_json(json.dumps({**result.model_dump(mode='json'),'finalist_player_id':result.champion_player_id}))
    # Independent values from actual match eliminations, not the point adapter.
    expected_main=dict.fromkeys(PLAYERS,0);expected_q=dict.fromkeys(PLAYERS,0)
    by_id={m.match_id:m for m in matches}
    for b in (*p.draw.qualification_brackets,p.draw.main):
        for n in b.nodes:
            m=by_id[n.node_id]
            if b.draw_type=='qualification':
                expected_q[m.result.loser_player_id]={1:0,2:13}[n.round_number]
                if n.round_number==2: expected_q[m.result.winner_player_id]=25
            else:
                expected_main[m.result.loser_player_id]={1:0,2:50,3:100,4:200,5:330}[n.round_number]
                if n.round_number==5: expected_main[m.result.winner_player_id]=500
    assert {r.player_id:r.main_points for r in rows}==expected_main
    assert {r.player_id:r.qualification_points for r in rows}==expected_q
    assert all(r.validity_weeks==52 and r.first_publication_week.week==7 for r in rows)
    with pytest.raises(ValueError,match='future leakage'):
        candidate(p,rows,0,6)
    published=candidate(p,rows,0,7)
    assert {r.player_id:r.points for r in published.rows}=={pid:expected_q[pid]+expected_main[pid] for pid in PLAYERS}
    assert any(r.points for r in candidate(p,rows,1,6).rows)
    assert all(r.points==0 for r in candidate(p,rows,1,7).rows)
    assert scheduled_knockout_ranking_results(plan=p,matches=tuple(reversed(matches)),positions=positions)==(result,rows)
    with pytest.raises(ValueError): candidate(p,rows+rows,0,7)


def test_partial_tournament_cannot_become_an_official_result(played):
    p,matches,positions,_=played
    missing=matches[-1].match_id
    with pytest.raises(ValueError):
        scheduled_knockout_ranking_results(plan=p,matches=matches[:-1],positions={k:v for k,v in positions.items() if k!=missing})


def test_modern_result_clock_has_no_legacy_week61_or_season49_limit():
    # Explicitly proposed generic Run timing; not an automatic Earth->W80 import.
    p,matches,positions,_=play_scheduled(plan(clock=RunCalendar(80,1,1970,60),season=55,q_week=69,main_week=70))
    result,rows=scheduled_knockout_ranking_results(plan=p,matches=matches,positions=positions)
    assert result.completed_week.week==70 and result.completed_week.season_index==55
    assert all(r.validity_weeks==80 and r.first_publication_week.week==71 for r in rows)
    assert any(r.points for r in candidate(p,rows,55,71).rows)


def test_terminal_horizon_does_not_invent_publication():
    p,matches,positions,_=play_scheduled(plan(clock=RunCalendar(52,1,2025,1),q_week=51,main_week=52))
    result=complete_scheduled_knockout_result(plan=p,matches=matches,positions=positions)
    assert result.completed_week.week==52
    with pytest.raises(ValueError,match='following publication week'):
        scheduled_knockout_ranking_results(plan=p,matches=matches,positions=positions)
    extended=RunCalendar(52,1,2025,2)
    recovered,rows=scheduled_knockout_ranking_results(plan=p,matches=matches,positions=positions,runtime_calendar=extended)
    assert recovered==result and recovered.fingerprint==result.fingerprint
    assert all(r.first_publication_week.season_index==1 and r.first_publication_week.week==1 for r in rows)
    assert result.completed_week.calendar.season_count==1
    with pytest.raises(ValueError,match='only extend'):
        scheduled_knockout_ranking_results(plan=p,matches=matches,positions=positions,runtime_calendar=RunCalendar(61,1,2025,2))


def test_distinct_deep_qualification_awards_cannot_be_silently_merged():
    p=plan()
    payload={**p.profile.model_dump(mode='json'),'qualification_entrants':64,
        'qualification_points':{'qualifier':25,'round_1_loss':0,'round_2_loss':5,'round_3_loss':10,'round_4_loss':13}}
    profile=ATPKnockoutProfile.model_validate_json(json.dumps(payload))
    with pytest.raises(ValueError,match='cannot collapse'):
        scheduled_point_distribution(profile)
