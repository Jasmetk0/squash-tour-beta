"""Real HTTP and SQLite boundary for exact Country Records Saved Revision."""
from urllib.parse import quote
import pytest
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

pytestmark=pytest.mark.pr_critical


def url(server,run,branch,revision,country="CZE"):
    return (f"{server.base_url}/admin/runs/{quote(run,safe='')}"
            f"/branches/{quote(branch,safe='')}"
            f"/country-records/{country}?revision_id={quote(revision,safe='')}")


def test_country_records_read_only_reachable_revision_and_sqlite_restart(tmp_path):
    db=f"sqlite:///{tmp_path / 'country-records.sqlite'}"
    with ApiServer(database_url=db) as server:
        run,branch,rev=_create_run(server,display_name="Country Records saved evidence")
        foreign,foreign_branch,foreign_rev=_create_run(server,display_name="Other Records Run")
        status,empty=_request("GET",url(server,run,branch,rev))
        assert status==200,empty
        assert empty["schema_version"]=="run_country_records.v1"
        assert empty["saved_revision_id"]==rev
        assert empty["source"]=="reachable_saved_revision"
        assert empty["calendar_status"]=="empty"
        assert empty["player_results"]==[] and empty["hosted_results"]==[]
        assert empty["country_titles"]==0 and empty["hosted_published_results"]==0
        assert _request("GET",url(server,run,branch,"unknown-revision"))[0]==404
        assert _request("GET",url(server,foreign,foreign_branch,rev))[0]==404
        assert _request("GET",url(server,run,branch,foreign_rev))[0]==404
        assert _request("GET",url(server,run,foreign_branch,rev))[0]==404
        assert _request("GET",url(server,run,branch,rev,"cze"))[0]==422
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,rev))==(200,empty)
