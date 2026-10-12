"""Exact-revision Country Match Records HTTP/SQLite isolation and restart."""
from urllib.parse import quote
import pytest
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark=pytest.mark.pr_critical


def url(server,run,branch,rev,code="CZE",extra=""):
    return (f"{server.base_url}/admin/runs/{quote(run,safe='')}/branches/"
            f"{quote(branch,safe='')}/country-match-records/{code}"
            f"?revision_id={quote(rev,safe='')}{extra}")


def test_exact_saved_match_records_empty_reachability_and_restart(tmp_path):
    db=f"sqlite:///{tmp_path / 'match-records.sqlite'}"
    with ApiServer(database_url=db) as server:
        run,branch,rev=_create_run(server,display_name="Saved country match records")
        foreign,fb,foreign_rev=_create_run(server,display_name="Foreign country matches")
        status,empty=_request("GET",url(server,run,branch,rev))
        assert status==200,empty
        assert empty["schema_version"]=="country_saved_match_records.v1"
        assert empty["source"]=="reachable_saved_revision"
        assert empty["run_id"]==run and empty["branch_id"]==branch
        assert empty["saved_revision_id"]==rev
        assert empty["calendar_status"]=="empty"
        assert empty["country_played_wins"]==empty["country_played_losses"]==0
        assert empty["country_walkover_wins"]==empty["country_walkover_losses"]==0
        assert empty["matches"]==[] and empty["has_more"] is False
        assert _request("GET",url(server,run,branch,"wrong-id"))[0]==404
        assert _request("GET",url(server,run,branch,foreign_rev))[0]==404
        assert _request("GET",url(server,foreign,fb,rev))[0]==404
        assert _request("GET",url(server,run,fb,rev))[0]==404
        assert _request("GET",url(server,run,branch,rev,"cze"))[0]==422
        assert _request("GET",url(server,run,branch,rev,extra="&limit=51"))[0]==422
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,rev))==(200,empty)
