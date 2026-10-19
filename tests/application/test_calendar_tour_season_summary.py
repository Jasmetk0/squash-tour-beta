"""Pure, fast national season-summary contracts. Real HTTP/SQLite proves sources."""
from types import SimpleNamespace as NS

import pytest

from beta_engine.application.calendar_tour_season_summary import (
    native_tour_season_summary,
    compare_completed_seasons,
    completed_season_indices,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition

pytestmark = pytest.mark.pr_critical


def fixture(*, closing=1, tamper=None):
    clock = RunCalendar(4, 2, 2030, 4)
    boundary = [
        NS(
            command_id=f"close-{i}",
            completed_week=RunWeekPosition(calendar=clock,season_index=i,week=4),
            target_week=RunWeekPosition(calendar=clock,season_index=i+1,week=1),
            public_event={"kind":"season_transition_completed"},
        )
        for i in range(closing)
    ]
    rank = [
        NS(
            week=NS(season_index=i,week=4),fingerprint=f"{i+1}"*64,
            rows=(NS(player_id="player-a",rank=1,points=100),)
        ) for i in range(closing)
    ]
    players=(
        NS(player_id="player-a",name="Alpha",country_code="CZE"),
        NS(player_id="player-b",name="Beta",country_code="USA"),
        NS(player_id="player-c",name="Gamma",country_code="CZE"),
        NS(player_id="player-d",name="Delta",country_code="USA"),
    )
    receipts=[]
    editions=[]
    for i in range(closing):
        eid=f"cup-{i}"
        awards=[
            {"player_id":"player-a","reached_stage":"champion","main_points":100},
            {"player_id":"player-b","reached_stage":"finalist","main_points":60},
            {"player_id":"player-c","reached_stage":"semifinal","main_points":30},
            {"player_id":"player-d","reached_stage":"semifinal","main_points":30},
        ] if i==0 else [
            {"player_id":"player-b","reached_stage":"champion","main_points":120},
            {"player_id":"player-a","reached_stage":"finalist","main_points":65},
            {"player_id":"player-c","reached_stage":"semifinal","main_points":30},
            {"player_id":"player-d","reached_stage":"semifinal","main_points":30},
        ]
        editions.append(NS(
            edition=NS(edition_id=eid,name=eid,week=RunWeekPosition(calendar=clock,season_index=i,week=2),
                       main_entrant_count=4),
            result_confirmed=True,tournament_fingerprint="f"*64,
        ))
        receipts.append(NS(
            request={"command":{"action":"play","edition_id":eid}},
            result={"played":{"fingerprint":"f"*64,
                              "winner_player_id":"player-a" if i==0 else "player-b",
                              "prepared_awards":awards}},
        ))
    if tamper=="winner":receipts[0].result["played"]["winner_player_id"]="player-d"
    if tamper=="field":receipts[0].result["played"]["prepared_awards"].pop()
    if tamper=="scope":players=players[:-1]
    state=NS(run_id="run",branch_id="branch",week=NS(calendar=clock),transitions=tuple(boundary),
             receipts=tuple(receipts),editions=tuple(editions),rankings=tuple(rank),
             fingerprint="a"*64)
    world=NS(run_id="run",branch_id="branch",players=players)
    return state,world


def test_only_real_signed_season_boundary_is_visible():
    state,world=fixture(closing=1)
    assert completed_season_indices(state)==(0,)
    result=native_tour_season_summary(state,world,0)
    assert result["season_index"]==0 and result["completed_edition_count"]==1
    assert result["editions"][0]["champion_country"]=="CZE"
    assert result["last_week_published_ranking"]["week"]==4
    assert result["countries"]==[
        {"country_code":"CZE","titles":1,"finals":0,"semifinals":1,"quarterfinals":0,
         "awarded_points":130,"distinct_players":2,"edition_appearances":1},
        {"country_code":"USA","titles":0,"finals":1,"semifinals":1,"quarterfinals":0,
         "awarded_points":90,"distinct_players":2,"edition_appearances":1},
    ]
    with pytest.raises(ValueError,match="no signed terminal"):
        native_tour_season_summary(state,world,1)
    with pytest.raises(ValueError):
        native_tour_season_summary(state,world,-1)


def test_compare_any_two_finished_seasons_with_absolute_national_deltas():
    state,world=fixture(closing=2)
    view=compare_completed_seasons(state,world,1,0)
    assert view["selected"]["completed_edition_count"]==1
    assert view["comparison"]["season_index"]==0
    assert view["country_deltas"]==[
        {"country_code":"CZE","titles_delta":-1,"finals_delta":1,"awarded_points_delta":-35},
        {"country_code":"USA","titles_delta":1,"finals_delta":-1,"awarded_points_delta":60},
    ]
    assert compare_completed_seasons(state,world,0)["comparison"] is None


@pytest.mark.parametrize("tamper",["winner","field","scope"])
def test_forged_play_placements_or_unknown_players_fail_closed(tamper):
    state,world=fixture(tamper=tamper)
    with pytest.raises(ValueError):
        native_tour_season_summary(state,world,0)


def test_unsigned_or_foreign_world_is_not_interpreted_as_our_season():
    state,world=fixture()
    world.branch_id="foreign"
    with pytest.raises(ValueError,match="Run/Branch"):
        native_tour_season_summary(state,world,0)
