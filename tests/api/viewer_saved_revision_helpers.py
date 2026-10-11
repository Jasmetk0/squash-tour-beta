from urllib.parse import quote

from test_simulation_api import _request


def canonical_product_run(server, run_id: str = "run") -> tuple[str, str]:
    status, created = _request(
        "POST",
        f"{server.base_url}/run-containers",
        {"display_name": f"Viewer {run_id}"},
    )
    assert status == 201
    assert created["run_id"]
    return created["viewer_branch_id"], created["run_id"]


def save_simulation(server, run_id: str, branch_id: str) -> dict:
    root = f"{server.base_url}/admin/runs/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/authoritative-simulation/save"
    status, preview = _request("GET", root + "/preview")
    assert status == 200 and preview["can_save"], (status, preview)
    status, saved = _request(
        "POST",
        root,
        {
            "expected_draft_version": preview["draft_version"],
            "expected_simulation_fingerprint": preview["simulation_fingerprint"],
        },
    )
    assert status == 201, (status, saved)
    return saved


def save_ranking(server, run_id: str, branch_id: str) -> dict:
    root = f"{server.base_url}/admin/runs/{quote(run_id, safe='')}/branches/{quote(branch_id, safe='')}/ranking-candidates/save"
    status, preview = _request("GET", root + "/preview")
    assert status == 200 and preview["can_save"], (status, preview)
    status, saved = _request(
        "POST",
        root,
        {
            "expected_draft_version": preview["draft_version"],
            "expected_ranking_fingerprint": preview["ranking_fingerprint"],
        },
    )
    assert status == 201, (status, saved)
    return saved
