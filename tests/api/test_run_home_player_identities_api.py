"""Actual FastAPI/SQLite Saved Revision boundary for Admin Player names."""
from urllib.parse import quote, urlencode
import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.api.test_initial_world_ranking_integration import _create_saved_world


def endpoint(server, run, branch, ids=()):
    path = f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/{quote(branch, safe='')}/home-player-identities"
    if ids:
        return path + "?" + urlencode([("player_id", identity) for identity in ids])
    return path


@pytest.mark.pr_critical
def test_saved_identity_empty_unknown_and_foreign_scope(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'empty-identities.sqlite'}") as server:
        run, branch, _ = _create_run(server, display_name="Identity empty")
        other_run, other_branch, _ = _create_run(server, display_name="Identity other")
        status, result = _request("GET", endpoint(server, run, branch, ("x",)))
        assert status == 200, result
        assert result["saved_revision_id"]
        assert result["players"] == [] and result["unresolved_ids"] == ["x"]
        assert _request("GET", endpoint(server, run, other_branch, ("x",)))[0] == 404
        assert _request("GET", endpoint(server, other_run, branch, ("x",)))[0] == 404


@pytest.mark.pr_critical
def test_saved_initial_world_names_match_adopted_players_after_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'saved-identities.sqlite'}"
    with ApiServer(database_url=url) as server:
        run, branch, _, _ = _create_saved_world(
            server, tmp_path, suffix="home-names", with_ranking=False,
        )
        world = server.app.state.runtime.repository.get_initial_world(run_id=run, branch_id=branch)
        player = world.players[0]
        status, result = _request("GET", endpoint(server, run, branch, (player.player_id, "missing")))
        assert status == 200, result
        assert result["players"] == [{
            "player_id": player.player_id, "name": player.name,
            "country_code": player.country_code,
            "identity_source": "initial_world",
        }]
        assert result["unresolved_ids"] == ["missing"]
        assert result["source"] == "selected_branch_saved_revision"
        assert _request("GET", endpoint(server, run, branch, tuple("p-"+str(i) for i in range(31))))[0] == 422
    with ApiServer(database_url=url) as reopened:
        assert _request("GET", endpoint(reopened, run, branch, (player.player_id, "missing")))[1] == result
