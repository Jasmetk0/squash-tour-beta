"""Real Saved Revision HTTP/SQLite player match history isolation and recovery."""
from urllib.parse import quote

import pytest

from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.application.test_viewer_people_read_model import _world


def url(server, run, branch, player="P1", query=""):
    return (f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
            f"{quote(branch, safe='')}/player-profiles/{quote(player, safe='')}/matches{query}")


@pytest.mark.pr_critical
def test_match_history_empty_unsaved_saved_restart_and_foreign_scope(tmp_path):
    db = f"sqlite:///{tmp_path / 'saved-player-matches.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(server, display_name="Saved Match Career")
        other, other_branch, _ = _create_run(server, display_name="Other Match Career")
        status, empty = _request("GET", url(server, run, branch))
        assert status == 200, empty
        assert empty["status"] == "identity_unavailable" and empty["matches"] == []
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_initial_world(session, _world().model_copy(update={"run_id": run, "branch_id": branch}))
        assert _request("GET", url(server, run, branch))[1] == empty
        save_root = (f"{server.base_url}/admin/players/runs/{quote(run, safe='')}"
                     f"/branches/{quote(branch, safe='')}/initial-world/save")
        status, preview = _request("GET", save_root + "/preview")
        assert status == 200 and preview["can_save"], (status, preview)
        status, _ = _request("POST", save_root, {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
        })
        assert status == 201
        status, saved = _request("GET", url(server, run, branch))
        assert status == 200, saved
        assert saved["status"] == "ready" and saved["total_results"] == 0
        assert saved["career_played_wins"] == saved["career_played_losses"] == 0
        assert saved["saved_revision_id"] != empty["saved_revision_id"]
        assert _request("GET", url(server, run, branch, query="?season_index=50"))[0] == 422
        assert _request("GET", url(server, run, branch, query="?limit=21"))[0] == 422
        assert _request("GET", url(server, run, other_branch))[0] == 404
        assert _request("GET", url(server, other, branch))[0] == 404
    with ApiServer(database_url=db) as reopened:
        assert _request("GET", url(reopened, run, branch))[1] == saved
