"""Real FastAPI/SQLite empty and historical Country Player Standings contract."""
from urllib.parse import quote
import pytest
from tests.api.test_saved_revision_history_api import ApiServer,_create_run,_request

pytestmark=pytest.mark.pr_critical


def url(server,run,branch,rev,country="CZE",query=""):
    return (f"{server.base_url}/admin/runs/{quote(run,safe='')}/branches/"
            f"{quote(branch,safe='')}/country-player-standings/{country}"
            f"?revision_id={quote(rev,safe='')}{query}")


def test_saved_country_player_standings_fail_closed_and_restart(tmp_path):
    db=f"sqlite:///{tmp_path/'country-player-standings.sqlite'}"
    with ApiServer(database_url=db) as server:
        run,branch,rev=_create_run(server,display_name="Country players standings")
        other,other_branch,other_rev=_create_run(server,display_name="Foreign country players")
        status,empty=_request("GET",url(server,run,branch,rev))
        assert status==200,empty
        assert empty["schema_version"]=="country_player_standings.v1"
        assert empty["source"]=="reachable_saved_revision"
        assert empty["run_id"]==run and empty["branch_id"]==branch
        assert empty["revision_branch_id"]==branch
        assert empty["saved_revision_id"]==rev
        assert empty["total_players"]==0 and empty["players"]==[]
        assert empty["country_titles"]==empty["country_runner_up_finishes"]==0
        assert empty["country_played_wins"]==empty["country_walkover_wins"]==0
        assert empty["calendar_status"]=="empty" and not empty["has_more"]
        assert _request("GET",url(server,run,branch,other_rev))[0]==404
        assert _request("GET",url(server,other,other_branch,rev))[0]==404
        assert _request("GET",url(server,run,other_branch,rev))[0]==404
        assert _request("GET",url(server,run,branch,rev,country="cze"))[0]==422
        assert _request("GET",url(server,run,branch,rev,query="&limit=51"))[0]==422
        assert _request("GET",url(server,run,branch,rev,query="&offset=-1"))[0]==422
        status,page=_request("GET",url(server,run,branch,rev,query="&offset=25&limit=1"))
        assert status==200
        assert page["total_players"]==0 and page["players"]==[]
        assert page["offset"]==25 and page["limit"]==1
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,rev))==(200,empty)
