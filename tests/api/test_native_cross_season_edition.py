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
        # Only the completed *saved* season is available. The current
        # season and any future season must remain invisible in Admin/Viewer.
        admin_season=tour_url(server)+"/seasons/0"
        viewer_season=viewer+"/seasons/0"
        code,empty_admin=_request("GET",admin_season)
        assert code==200,empty_admin
        assert empty_admin["selected"]["completed_edition_count"]==0
        code,empty_viewer=_request("GET",viewer_season)
        assert code==200,empty_viewer
        assert empty_viewer["selected"]["countries"]==[]
        assert _request("GET",viewer+"/seasons/1")[0]==409
        assert _request("GET",tour_url(server)+"/seasons/1")[0]==409
        # Signed S1 closure is visible without inventing a first-year Cup.
        # S2 remains invisible until its *actual* terminal Saved transition.
        code,early_records=_request("GET",viewer+"/records")
        assert code==200,early_records
        assert early_records["as_of_season_index"]==0
        assert early_records["completed_edition_count"]==0
        assert all(record["value"]==0 for record in early_records["records"])
        assert _request("GET",viewer+"/records?as_of_season_index=1")[0]==409
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
        # Publish more real Official weeks and close season two. This
        # admits the *actual* Season 2 match awards into signed historical
        # country comparisons instead of fabricated synthetic ranking data.
        _advance(server,"transition","season2-week2-to-week3")
        _advance(server,"transition","season2-week3-to-week4")
        _advance(server,"season-transition","season2-to-season3")
        country_url=tour_url(server)+"/seasons/1?compare_to=0"
        code,comparison=_request("GET",country_url)
        assert code==200,comparison
        assert comparison["selected"]["completed_edition_count"]==1
        assert comparison["comparison"]["completed_edition_count"]==0
        assert comparison["selected"]["editions"][0]["edition_id"]=="season2-cup"
        assert comparison["selected"]["editions"][0]["champion_name"]
        assert sum(c["titles"] for c in comparison["selected"]["countries"])==1
        assert sum(c["finals"] for c in comparison["selected"]["countries"])==1
        assert sum(c["awarded_points"] for c in comparison["selected"]["countries"])==220
        assert sum(c["titles_delta"] for c in comparison["country_deltas"])==1
        code,public_comparison=_request(
            "GET", viewer+"/seasons/1?compare_to=0"
        )
        assert code==200,public_comparison
        assert public_comparison["selected"]==comparison["selected"]
        assert public_comparison["country_deltas"]==comparison["country_deltas"]
        assert _request("GET",viewer+"/seasons/2")[0]==409
        assert _request("GET",tour_url(server)+"/seasons/2")[0]==409
        records_url=tour_url(server)+"/records"
        code,complete_records=_request(
            "GET",records_url+"?as_of_season_index=1"
        )
        assert code==200,complete_records
        assert complete_records["completed_seasons"]==[0,1]
        assert complete_records["completed_edition_count"]==1
        player_titles=next(r for r in complete_records["records"]
                           if r["record_id"]=="native_tour.player.titles.v1")
        assert player_titles["value"]==1
        assert len(player_titles["holders"])==1
        assert len(player_titles["holder_history"])==1
        assert player_titles["holder_history"][0]["season_index"]==1
        country_titles=next(r for r in complete_records["records"]
                            if r["record_id"]=="native_tour.country.titles.v1")
        assert country_titles["value"]==1
        assert sum(r["value"] for r in complete_records["records"]
                   if r["scope"]=="country" and r["metric"]=="titles")==1
        code,public_records=_request("GET",viewer+"/records")
        assert code==200,public_records
        assert public_records==complete_records
        code,first_year=_request("GET",viewer+"/records?as_of_season_index=0")
        assert code==200,first_year
        assert first_year["completed_edition_count"]==0
        assert all(r["value"]==0 for r in first_year["records"])
        assert _request("GET",viewer+"/records?as_of_season_index=2")[0]==409
        assert _request("GET",records_url+"?from_season_index=2")[0]==409
        champion_country=player_titles["holders"][0]["country_code"]
        code,filtered=_request("GET",viewer+"/records?country_code="+champion_country)
        assert code==200,filtered
        assert filtered["country_code"]==champion_country
        assert all(row["country_code"]==champion_country
                   for record in filtered["records"]
                   for row in record["leaderboard"])
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
        assert fresh["state"]["week"]["season_index"]==2
        assert fresh["state"]["week"]["week"]==1
        status,restarted_summary=_request(
            "GET", restarted.base_url+"/viewer/runs/run/calendar-tour/seasons/1?compare_to=0"
        )
        assert status==200,restarted_summary
        assert restarted_summary["selected"]==comparison["selected"]
        assert restarted_summary["country_deltas"]==comparison["country_deltas"]
        code,restarted_records=_request(
            "GET",restarted.base_url+"/viewer/runs/run/calendar-tour/records"
        )
        assert code==200,restarted_records
        assert restarted_records==complete_records

        status,published=_request("GET",restarted.base_url+"/viewer/runs/run/calendar-tour")
        assert status==200,published
        assert published["official_ranking"]["week"]["season_index"]==2
