"""Real Edition announced in the last week of one season and played in the next.

Uses genuine HTTP, immutable Save, SQLite, original MatchEngine and ranking
authority. Short W=4 prevents multi-hour PR suites; W52/W61/W80 date arithmetic
is independently tested in the Admin's native calendar module.
"""
import copy
import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.calendar_tour import saved_tour
from beta_engine.domain.run_packages import canonical_hash
from tests.api.test_calendar_tour_flow import (
    command, edition, execute, inspect, save_tour, setup, tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark=pytest.mark.smoke


def _advance(server, action, label):
    result, request=execute(
        server,command(inspect(server),action,name=label)
    )
    assert result["manual_save_required"]
    saved=save_tour(server)
    return result,saved


def test_real_cross_season_edition_preannounce_play_rank_and_saved_viewer(
    tmp_path,
):
    db=f"sqlite:///{tmp_path / 'cross-season-edition.db'}"
    with ApiServer(database_url=db) as server:
        repo,_=setup(server,RunCalendar(4,2,2030,3),count=8)
        _advance(server,"transition","finish-w2")
        w3=inspect(server)
        assert (w3["state"]["week"]["season_index"],w3["state"]["week"]["week"])==(0,3)

        # Admin creates a genuinely prospective Edition two weeks ahead,
        # and a full public week passes after its actual announcement.
        current=w3["state"]["week"]
        date={**current,"season_index":1,"week":1}
        announcement={**current,"week":4}
        configured={
            "edition_id":"season2-cup","name":"Season Two Cup",
            "week":date,"announcement_week":announcement,
            "start_slot":1,"main_entrant_count":4,"ranked":True,
            "validity_weeks":4,
            "point_table":{"champion":100,"finalist":60,"semifinal":30},
        }
        result,_=execute(server,command(w3,"create-edition",name="cross-season-plan",data=configured))
        assert result["manual_save_required"]
        planned_save=save_tour(server)
        planned=inspect(server)
        assert planned["state"]["editions"][0]["edition"]["week"]==date
        assert planned["state"]["editions"][0]["edition"]["announcement_week"]==announcement
        early=command(planned,"submit",name="premature",edition_id="season2-cup",
                      data={"player_ids":[p["player_id"] for p in planned["players"][:4]]})
        assert _request("POST",tour_url(server)+"/preview",early)[0]==409

        result,last_s1=_advance(server,"transition","publish-season2-announcement")
        assert result["impact"]["target_week"]["week"]==4
        at_w4=inspect(server)
        assert "season2-cup" in at_w4["state"]["transitions"][-1]["public_event"]["announced_edition_ids"]
        viewer=server.base_url+"/viewer/runs/run/calendar-tour"
        status,old_public=_request("GET",viewer+"?week_ordinal=2")
        assert status==200,old_public
        assert not any(e["edition_id"]=="season2-cup" for e in old_public["editions"])
        status,announced=_request("GET",viewer+"?week_ordinal=3")
        assert status==200,announced
        assert any(e["edition_id"]=="season2-cup" for e in announced["editions"])
        assert all(e["completed"] is False for e in announced["editions"])
        assert any(e["kind"]=="week_transition_completed" and
                   "season2-cup" in e["announced_edition_ids"]
                   for e in announced["public_events"])

        _advance(server,"season-transition","roll-over-to-season2")
        ready=inspect(server)
        assert ready["state"]["week"]["season_index"]==1
        assert ready["state"]["week"]["week"]==1
        assert ready["state"]["editions"][0]["edition"]["week"]==date
        assert ready["state"]["rankings"][-1]["rows"]==[]
        # Real Entry approvals, Saved draw, MatchEngine, frozen awards
        # and confirmed results must work after the season boundary.
        edition(server,"season2-cup",size=4)
        finished=inspect(server)
        authority=finished["state"]["editions"][0]
        assert authority["result_confirmed"] is True
        _advance(server,"transition","season2-post-edition-ranking")
        ranked=inspect(server)
        assert ranked["state"]["week"]["season_index"]==1
        assert ranked["state"]["week"]["week"]==2
        rows=ranked["state"]["rankings"][-1]["rows"]
        assert rows and max(row["points"] for row in rows)>=100
        status,post_public=_request("GET",viewer+"?week_ordinal=5")
        assert status==200,post_public
        assert any(e["edition_id"]=="season2-cup" and e["completed"] for e in post_public["editions"])
        saved=repo.get_branch_saved_revision(revision_id=ranked["saved_head_revision_id"])
        assert saved_tour(saved.payload,run_id="run",branch_id="branch") is not None
        planned_original=repo.get_branch_saved_revision(
            revision_id=planned_save["revision_id"]
        )
        assert repo.verify_branch_saved_revision_hash(revision_id=planned_original.revision_id)
        # Component rehash alone cannot legitimize a forged season schedule.
        forgery=copy.deepcopy(saved.payload)
        tour=forgery["content"]["calendar_tour_authority"]
        tour["state"]["editions"][0]["edition"]["announcement_week"]["week"]=3
        tour["fingerprint"]=canonical_hash(tour["state"])
        with pytest.raises((ValueError,TypeError)):
            saved_tour(forgery,run_id="run",branch_id="branch")
    with ApiServer(database_url=db) as restarted:
        fresh=inspect(restarted)
        assert fresh["saved"]
        assert fresh["state"]["week"]["season_index"]==1
        assert fresh["state"]["week"]["week"]==2
        assert fresh["state"]["rankings"][-1]["rows"]==rows
        status,published=_request("GET",restarted.base_url+"/viewer/runs/run/calendar-tour")
        assert status==200,published
        assert published["official_ranking"]["rows"]==rows
