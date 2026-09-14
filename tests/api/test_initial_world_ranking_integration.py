"""Real HTTP/SQLite integration for initial world ownership and ranking derivation."""

import json
from urllib import request

import pytest

from test_saved_revision_history_api import ApiServer, _create_run, _request


def _post_headers(url, payload, headers):
    req = request.Request(url, data=json.dumps(payload).encode(), method="POST",
                          headers={"Content-Type": "application/json", **headers})
    with request.urlopen(req) as response:
        return response.status, json.loads(response.read())


@pytest.mark.smoke
def test_production_pool_to_owned_world_derived_ranking_save_reopen_restore(tmp_path):
    db = tmp_path / "world.db"
    pool = tmp_path / "initial-player-pool.json"
    active = tmp_path / "unused-active-players.json"
    with ApiServer(database_url=f"sqlite:///{db}") as server:
        server.app.state.initial_player_pool_config_path = pool
        server.app.state.season_active_players_config_path = active
        assert _request("POST", server.base_url + "/admin/players/initial-pool/generate", {
            "season": "2000/2001", "seed": 723, "target_pool_size": 12, "dry_run": False,
        })[0] == 200
        run_id, branch_id, empty_revision = _create_run(server, display_name="Initial world integration")
        world_root = f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world"
        adoption = {"command_id": "adopt-production-pool", "source_season": "2000/2001",
                    "bootstrap_seed": 44, "audit_label": "Integration admin",
                    "audit_reason": "Adopt complete generated source", "official_run": False, "best_n": 9}
        status, preview = _request("POST", world_root + "/preview", adoption)
        assert status == 200 and preview["preview_only"] and len(preview["state"]["players"]) == 12
        status, adopted = _post_headers(world_root, adoption, {
            "X-Initial-World-Preview-Fingerprint": preview["fingerprint"]})
        assert status == 201 and adopted["policies"][0]["best_n"] == 9

        # Mutating the disposable global source after adoption cannot alter owned state.
        original_owned = _request("GET", world_root)[1]
        assert _request("POST", server.base_url + "/admin/players/initial-pool/generate", {
            "season": "2000/2001", "seed": 999, "target_pool_size": 5, "dry_run": False,
        })[0] == 200
        assert _request("GET", world_root)[1] == original_owned

        status, save_preview = _request("GET", world_root + "/save/preview")
        assert status == 200 and save_preview["can_save"]
        status, world_saved = _request("POST", world_root + "/save", {
            "expected_draft_version": save_preview["draft_version"],
            "expected_initial_world_fingerprint": save_preview["initial_world_fingerprint"]})
        assert status == 201
        world_revision = world_saved["saved_revision"]["revision_id"]

        ranking_root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        preparation = {"command_id": "derive-initial-ranking",
                       "audit": {"actor_label": "Integration admin", "reason": "Derive from owned players"}}
        status, ranking_preview = _request("POST", ranking_root + "/prepare/initial/derived/preview", preparation)
        assert status == 200 and ranking_preview["candidate"]["snapshot"]["rows"] == []
        status, candidate = _post_headers(ranking_root + "/prepare/initial/derived", preparation, {
            "X-Ranking-Preview-Fingerprint": ranking_preview["candidate"]["fingerprint"],
            "X-Ranking-Preview-Request": ranking_preview["request_fingerprint"]})
        assert status == 201 and candidate == ranking_preview["candidate"]
        status, ranking_save = _request("GET", ranking_root + "/save/preview")
        status, ranked_saved = _request("POST", ranking_root + "/save", {
            "expected_draft_version": ranking_save["draft_version"],
            "expected_ranking_fingerprint": ranking_save["ranking_fingerprint"]})
        assert status == 201
        ranked_revision = ranked_saved["saved_revision"]["revision_id"]

        restore_empty = (f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
                         f"/saved-revisions/{empty_revision}/restore")
        status, restored = _request("POST", restore_empty, {
            "expected_head_saved_revision_id": ranked_revision,
            "expected_draft_version": ranked_saved["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True})
        assert status == 201, restored
        assert _request("GET", world_root)[0] == 404
        restore_ranked = (f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
                          f"/saved-revisions/{ranked_revision}/restore")
        status, restored_again = _request("POST", restore_ranked, {
            "expected_head_saved_revision_id": restored["saved_revision"]["revision_id"],
            "expected_draft_version": restored["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True})
        assert status == 201 and _request("GET", world_root)[1] == original_owned
        assert _request("GET", ranking_root + "/0/1")[1] == candidate

    with ApiServer(database_url=f"sqlite:///{db}") as reopened:
        assert _request("GET", f"{reopened.base_url}/admin/players/runs/{run_id}/branches/{branch_id}/initial-world")[1] == original_owned
        assert _request("GET", f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates/0/1")[1] == candidate
