"""Real HTTP/SQLite immutable saved player profile boundary and restart."""
from urllib.parse import quote

import pytest

from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.application.test_viewer_people_read_model import _world


def url(server, run, branch, player="P1"):
    return (f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
            f"{quote(branch, safe='')}/player-profiles/{quote(player, safe='')}")


@pytest.mark.pr_critical
def test_saved_player_profile_excludes_live_state_and_foreign_branches_after_restart(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'player-profile.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run, branch, _ = _create_run(server, display_name="Player profile")
        other, foreign_branch, _ = _create_run(server, display_name="Other player profile")
        status, empty = _request("GET", url(server, run, branch))
        assert status == 200, empty
        assert empty["identity"] is None
        assert empty["ranking_status"] == "identity_unavailable"
        assert empty["final_appearances"] == 0

        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_initial_world(session, _world().model_copy(update={"run_id": run, "branch_id": branch}))
        assert _request("GET", url(server, run, branch))[1] == empty

        save_root = (f"{server.base_url}/admin/players/runs/{quote(run, safe='')}"
                     f"/branches/{quote(branch, safe='')}/initial-world/save")
        status, preview = _request("GET", save_root + "/preview")
        assert status == 200 and preview["can_save"], (status, preview)
        status, _saved = _request("POST", save_root, {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
        })
        assert status == 201, (status, _saved)
        status, saved = _request("GET", url(server, run, branch))
        assert status == 200, saved
        assert saved["identity"]["display_name"] == "Initial One"
        assert saved["ranking_status"] == "unpublished"
        assert saved["rank"] is None and saved["points"] is None
        assert saved["saved_revision_id"] != empty["saved_revision_id"]
        assert saved["tournament_results"] == []
        assert "current_ability" not in str(saved)
        assert _request("GET", url(server, run, foreign_branch))[0] == 404
        assert _request("GET", url(server, other, branch))[0] == 404

    with ApiServer(database_url=database_url) as reopened:
        assert _request("GET", url(reopened, run, branch))[1] == saved
