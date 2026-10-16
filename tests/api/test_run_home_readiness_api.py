"""Production HTTP/SQLite saved-content readiness across Branches and restart."""

from urllib.parse import urlencode

import pytest

from tests.api.test_run_working_draft_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _get(server, run, branch):
    return _request("GET", f"{server.base_url}/admin/runs/{run}/branches/{branch}/home-readiness")


def test_real_http_run_readiness_is_saved_branch_owned_and_persists_restart(tmp_path):
    database = f"sqlite:///{tmp_path / 'run-readiness.db'}"
    with ApiServer(database_url=database) as server:
        code, new = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Run readiness W52",
            "calendar": {
                "weeks_per_year": 52, "season_start_year_week": 35,
                "start_year": 2030, "season_count": 3,
            },
        })
        assert code == 201, new
        rid, bid = new["run_id"], new["viewer_branch_id"]
        code, initial = _get(server, rid, bid)
        assert code == 200, initial
        assert initial["source"] == "validated_selected_branch_saved_head"
        assert initial["items"][0]["status"] == "missing"
        assert initial["items"][-1]["status"] == "saved"
        assert initial["sporting_calendar_supported_by_legacy_writers"] is False
        assert initial["requires_operation_preflight"] is True
        assert initial["simulation_started"] is False
        assert _get(server, rid, "nonexistent")[0] == 404

        code, listing = _request(
            "GET", server.base_url + "/run-branches?" + urlencode({"run_id": rid}),
        )
        assert code == 200, listing
        ancestor_id = listing["run_branches"][0]["saved_head_revision_id"]
        code, fork = _request(
            "POST", f"{server.base_url}/run-containers/{rid}/branches",
            {"source_branch_id": bid, "source_saved_revision_id": ancestor_id},
        )
        assert code == 201, fork
        code, second = _get(server, rid, fork["branch_id"])
        assert code == 200, second
        assert second["branch_id"] == fork["branch_id"]
        assert second["saved_revision_id"] == ancestor_id
        assert second["items"][0]["status"] == "missing"
        assert _get(server, rid, bid) == (200, initial)

        code, other = _request("POST", server.base_url + "/run-containers", {
            "display_name": "Another Run",
        })
        assert code == 201, other
        assert _get(server, other["run_id"], bid)[0] == 404
        assert _get(server, rid, other["viewer_branch_id"])[0] == 404

    with ApiServer(database_url=database) as server:
        assert _get(server, rid, bid) == (200, initial)
        assert _get(server, rid, fork["branch_id"]) == (200, second)
