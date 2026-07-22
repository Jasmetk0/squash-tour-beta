from __future__ import annotations

from test_simulation_api import ApiServer, _request


def test_viewer_official_context_resolves_current_official_branch_and_is_read_only(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'viewer-context.db'}") as server:
        assert _request("POST", f"{server.base_url}/runs", {"run_id": "run/a #1", "seed": 47, "season": 2027})[0] == 201
        status, branches = _request("GET", f"{server.base_url}/run-branches?run_id=run%2Fa%20%231")
        assert status == 200
        branch = branches["run_branches"][0]
        status, checkpoint = _request("POST", f"{server.base_url}/branch-checkpoints/capture-initial", {"simulation_run_id": "run/a #1"})
        assert status == 200
        status, context = _request("GET", f"{server.base_url}/viewer/runs/run%2Fa%20%231/official-context")
        assert status == 200
        assert context == {
            "product_run_id": "run/a #1", "product_run_display_name": "run/a #1",
            "product_run_status": "active", "product_run_storage_kind": "custom_local",
            "product_run_read_only": False, "official_branch_id": branch["branch_id"],
            "official_branch_display_name": "Main", "official_branch_status": "active",
            "official_branch_read_only": False, "official_branch_seed": 47,
            "legacy_simulation_run_id": "run/a #1", "head_checkpoint_id": checkpoint["checkpoint_id"],
            "head_checkpoint_kind": "initial", "current_season": 2027, "current_week": None,
            "current_event_id": None, "current_event_sequence": None,
            "resolution_version": "viewer_official_branch_v1",
        }
        assert _request("GET", f"{server.base_url}/viewer/runs/missing/official-context")[0] == 404
