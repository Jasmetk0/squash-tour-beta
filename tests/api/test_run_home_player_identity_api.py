"""Real HTTP/SQLite Saved Revision and fork isolation for Run Home player names."""
from __future__ import annotations

from urllib.parse import quote

import pytest

from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.application.test_viewer_people_read_model import _world


def _url(server, run: str, branch: str, players: str = "P1,P2,UNKNOWN"):
    return (f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
            f"{quote(branch, safe='')}/home-player-identities?player_ids={quote(players, safe='')}")


@pytest.mark.pr_critical
def test_identity_http_saved_head_no_live_leak_cross_run_and_restart(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'saved-identity.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run, branch, _ = _create_run(server, display_name="Run Home identities")
        other, other_branch, _ = _create_run(server, display_name="Other Run identities")
        repo = server.app.state.runtime.repository
        url = _url(server, run, branch)
        status, empty = _request("GET", url)
        assert status == 200, empty
        assert empty["status"] == "unavailable"
        assert empty["players"] == [] and empty["unresolved_ids"] == ["P1", "P2", "UNKNOWN"]
        assert empty["source"] == "selected_branch_saved_revision"

        with repo._session_factory.begin() as session:
            source = _world().model_copy(update={"run_id": run, "branch_id": branch})
            put_initial_world(session, source)
        assert _request("GET", url)[1] == empty

        service = RunWorkingDraftService(repo, lambda kind: kind + "-identity-test")
        draft = service.get_viewer_branch_draft(run_id=run, branch_id=branch)
        service.save(run_id=run, branch_id=branch, expected_draft_version=draft.draft_version)
        status, published = _request("GET", url)
        assert status == 200, published
        assert published["status"] == "partial"
        assert [(player["player_id"], player["display_name"], player["country_code"])
                for player in published["players"]] == [
                    ("P1", "Initial One", "CZE"), ("P2", "Initial Two", "EGY")]
        assert published["unresolved_ids"] == ["UNKNOWN"]
        assert published["saved_revision_id"] != empty["saved_revision_id"]
        assert "current_ability" not in str(published)
        assert _request("GET", _url(server, run, other_branch))[0] == 404
        assert _request("GET", _url(server, other, branch))[0] == 404
        assert _request("GET", _url(server, run, branch, "P1,P1"))[0] == 422
        assert _request("GET", _url(server, run, branch, ",".join(map(str, range(26)))))[0] == 422

    with ApiServer(database_url=database_url) as reopened:
        assert _request("GET", _url(reopened, run, branch))[1] == published
