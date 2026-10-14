"""Exact Saved match-record highlights over real FastAPI and persisted SQLite."""
from urllib.parse import quote

import pytest
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark = pytest.mark.pr_critical


def url(server, run, branch, revision, extra="", code="CZE"):
    prefix=(f"{server.base_url}/admin/runs/{quote(run,safe='')}/branches/"
            f"{quote(branch,safe='')}/country-match-record-highlights/{code}")
    return (prefix+f"?revision_id={quote(revision,safe='')}"
            "&from_season=0&from_week=1&to_season=0&to_week=61"+extra)


def test_country_record_scope_validation_and_restart(tmp_path):
    db=f"sqlite:///{tmp_path / 'match-record-highlights.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, revision=_create_run(server,display_name="Country Match Records")
        other, other_branch, other_rev=_create_run(server,display_name="Foreign Records")
        status, result=_request("GET",url(server,run,branch,revision))
        assert status==200,result
        assert result["schema_version"]=="country_match_record_highlights.v1"
        assert result["source"]=="reachable_saved_revision"
        assert result["run_id"]==run and result["branch_id"]==branch
        assert result["revision_branch_id"]==branch
        assert result["saved_revision_id"]==revision
        assert result["country_code"]=="CZE"
        assert (result["from_season"],result["from_week"],result["to_season"],result["to_week"])==(0,1,0,61)
        assert result["period_country_matches"]==result["period_played_matches"]==result["period_walkovers"]==0
        assert [record["key"] for record in result["records"]]==["played_wins","played_matches"]
        assert all(record["value"]==0 and record["holders"]==[] for record in result["records"])
        assert result["selected_record"] is None and result["evidence"]==[]
        status,page=_request("GET",url(server,run,branch,revision,
            "&record_key=played_wins&offset=4&limit=1"))
        assert status==200,page
        assert page["selected_record"]=="played_wins" and page["offset"]==4 and page["limit"]==1
        assert page["evidence_count"]==0 and page["has_more"] is False
        assert _request("GET",url(server,run,branch,other_rev))[0]==404
        assert _request("GET",url(server,other,other_branch,revision))[0]==404
        assert _request("GET",url(server,run,branch,"missing"))[0]==404
        assert _request("GET",url(server,run,branch,revision,code="cze"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&from_week=0"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&to_season=50"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&to_week=0"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&from_week=61&to_week=1"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&record_key=bye"))[0]==422
        assert _request("GET",url(server,run,branch,revision,"&limit=51"))[0]==422
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,revision))==(200,result)
        assert _request("GET",url(reopened,run,branch,revision,
            "&record_key=played_wins&offset=4&limit=1"))==(200,page)
