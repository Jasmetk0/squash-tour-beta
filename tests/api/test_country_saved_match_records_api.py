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
        assert empty["available_seasons"]==[]
        assert empty["season_index"] is None
        assert empty["result_kind"]=="all" and empty["outcome"]=="all"
        assert empty["filtered_match_count"]==0
        status,filtered=_request("GET",url(server,run,branch,rev,
            extra="&season_index=2&result_kind=walkover&outcome=loss&offset=5"))
        assert status==200,filtered
        assert filtered["season_index"]==2
        assert filtered["result_kind"]=="walkover" and filtered["outcome"]=="loss"
        assert filtered["offset"]==5 and filtered["filtered_match_count"]==0
        assert empty["country_match_count"]==filtered["country_match_count"]
        assert _request("GET",url(server,run,branch,"wrong-id"))[0]==404
        assert _request("GET",url(server,run,branch,foreign_rev))[0]==404
        assert _request("GET",url(server,foreign,fb,rev))[0]==404
        assert _request("GET",url(server,run,fb,rev))[0]==404
        assert _request("GET",url(server,run,branch,rev,"cze"))[0]==422
        assert _request("GET",url(server,run,branch,rev,extra="&limit=51"))[0]==422
        assert _request("GET",url(server,run,branch,rev,extra="&season_index=50"))[0]==422
        assert _request("GET",url(server,run,branch,rev,extra="&result_kind=bye"))[0]==422
        assert _request("GET",url(server,run,branch,rev,extra="&outcome=draw"))[0]==422
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,rev))==(200,empty)


def test_country_match_history_distinguishes_real_saved_calendar_from_pre_save_history(tmp_path):
    """Old Saved Revision remains frozen while newly saved Calendar has no results."""
    from itertools import count
    from beta_engine.application.run_working_draft_service import RunWorkingDraftService
    from beta_engine.infrastructure.db.run_package_state import put_run_package_state
    from tests.application.test_viewer_tournament_history_read_model import _state

    db=f"sqlite:///{tmp_path / 'match-records-history.sqlite'}"
    with ApiServer(database_url=db) as server:
        run,branch,first_rev=_create_run(server,display_name="Country match records actual history")
        repository=server.app.state.runtime.repository
        first=_request("GET",url(server,run,branch,first_rev))
        assert first[0]==200 and first[1]["calendar_status"]=="empty"
        with repository._session_factory.begin() as session:
            put_run_package_state(session,_state(run_id=run,branch_id=branch))
        # The working Run Calendar is NOT an immutable tournament publication.
        assert _request("GET",url(server,run,branch,first_rev))==first
        ids=count(1)
        service=RunWorkingDraftService(repository,lambda kind:f"{kind}-country-{next(ids)}")
        draft=service.get_viewer_branch_draft(run_id=run,branch_id=branch)
        service.save(run_id=run,branch_id=branch,expected_draft_version=draft.draft_version)
        current_branch=_request("GET",f"{server.base_url}/run-branches/{branch}")[1]
        saved_rev=current_branch["saved_head_revision_id"]
        assert saved_rev!=first_rev
        status,current=_request("GET",url(server,run,branch,saved_rev))
        assert status==200,current
        assert current["calendar_status"]=="ready"
        assert current["published_event_count"]==0 and current["total_played_matches"]==0
        assert current["country_match_count"]==0 and current["matches"]==[]
        assert _request("GET",url(server,run,branch,first_rev))==first
        assert _request("GET",f"{server.base_url}/run-branches/{branch}")[1]["saved_head_revision_id"]==saved_rev
    with ApiServer(database_url=db) as reopened:
        assert _request("GET",url(reopened,run,branch,first_rev))==first
        assert _request("GET",url(reopened,run,branch,saved_rev))==(200,current)
