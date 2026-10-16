"""Real FastAPI/SQLite manual all-Branch horizon Save, receipt and restart."""

from urllib.parse import urlencode

import pytest

from tests.api.test_run_working_draft_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def _url(server, run_id, suffix=""):
    return f"{server.base_url}/run-containers/{run_id}/calendar/{suffix}"


def _review(server, run_id, seasons):
    return _request(
        "GET", _url(server, run_id, "extension-review?") +
        urlencode({"new_season_count": seasons})
    )


def _save(server, run_id, review, command_id="reviewed-run-wide"):
    return _request("POST", _url(server, run_id, "extension-save"), {
        "command_id": command_id,
        "new_season_count": review["proposed_calendar"]["season_count"],
        "review_fingerprint": review["review_fingerprint"],
        "explicit_confirmation": True,
    })


def test_http_two_branches_review_save_history_retry_and_cold_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'reviewed-http.db'}"
    with ApiServer(database_url=db) as server:
        code, run = _request("POST", _url(server, "").removesuffix("/calendar/"), {
            "display_name": "Reviewed W52",
            "calendar": {
                "weeks_per_year": 52, "season_start_year_week": 35,
                "start_year": 2030, "season_count": 3,
            },
        })
        assert code == 201, run
        rid, bid = run["run_id"], run["viewer_branch_id"]
        code, branches = _request("GET", server.base_url +
            "/run-branches?" + urlencode({"run_id": rid}))
        assert code == 200, branches
        ancestor_id = branches["run_branches"][0]["saved_head_revision_id"]
        old_url = (f"{server.base_url}/run-containers/{rid}/branches/"
                   f"{bid}/saved-revisions/{ancestor_id}")
        code, original = _request("GET", old_url)
        assert code == 200, original
        code, fork = _request("POST", f"{server.base_url}/run-containers/{rid}/branches", {
            "source_branch_id": bid, "source_saved_revision_id": ancestor_id,
            "display_name": "Independent second Branch",
        })
        assert code == 201, fork
        code, reviewed = _review(server, rid, 6)
        assert code == 200, reviewed
        assert reviewed["branch_count"] == 2
        assert reviewed["can_save"] and reviewed["added_weeks"] == 156
        assert reviewed["simulation_started"] is False
        assert _request("POST", _url(server, rid, "extension-save"), {
            "command_id": "without-consent", "new_season_count": 6,
            "review_fingerprint": reviewed["review_fingerprint"],
            "explicit_confirmation": False,
        })[0] == 409
        code, result = _save(server, rid, reviewed)
        assert code == 200, result
        assert result["saved"] is True and result["simulation_started"] is False
        assert result["branch_count"] == 2
        assert _save(server, rid, reviewed) == (200, result)
        code, now = _request("GET", f"{server.base_url}/run-containers/{rid}")
        assert code == 200, now
        assert now["timeline_end_season"] == 2035
        assert now["metadata_json"]["run_calendar"]["season_count"] == 6
        code, after = _request("GET", old_url)
        assert code == 200, after
        assert after["content_hash"] == original["content_hash"]
        assert after["payload"] == original["payload"]
        assert after["change_summary"] == original["change_summary"]
        for branch in result["branches"]:
            code, current = _request("GET",
                f"{server.base_url}/run-containers/{rid}/branches/"
                f"{branch['branch_id']}/saved-revisions/{branch['saved_revision_id']}")
            assert code == 200, current
            assert current["payload"]["run"]["run_calendar"]["season_count"] == 6
            assert current["parent_revision_id"] == ancestor_id

    with ApiServer(database_url=db) as server:
        assert _save(server, rid, reviewed) == (200, result)
        assert _review(server, rid, 7)[1]["original_calendar"]["season_count"] == 6
        code, now = _request("GET", f"{server.base_url}/run-containers/{rid}")
        assert code == 200, now
        assert now["timeline_end_season"] == 2035


def test_http_late_branch_invalidates_old_review_and_is_not_dropped(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'late-branch-http.db'}") as server:
        code, run = _request("POST", f"{server.base_url}/run-containers", {
            "display_name": "Late branch",
        })
        assert code == 201, run
        rid, bid = run["run_id"], run["viewer_branch_id"]
        code, reviewed = _review(server, rid, 52)
        assert code == 200, reviewed
        code, listing = _request("GET", f"{server.base_url}/run-branches?" +
                                 urlencode({"run_id": rid}))
        assert code == 200, listing
        code, branch = _request("POST", f"{server.base_url}/run-containers/{rid}/branches", {
            "source_branch_id": bid,
            "source_saved_revision_id": listing["run_branches"][0]["saved_head_revision_id"],
        })
        assert code == 201, branch
        code, rejected = _save(server, rid, reviewed)
        assert code == 409, rejected
        assert rejected["detail"]["code"] == "calendar_extension_save_conflict"
        assert _review(server, rid, 52)[1]["branch_count"] == 2
