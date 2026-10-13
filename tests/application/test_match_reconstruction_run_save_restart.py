"""A real Match Reconstruction selection survives production Run Save and restart.

This closes the genuine MatchEngine -> Run-owned Slot -> immutable Saved Revision
boundary. No forged scorelines, monkeypatched result loaders or direct INSERTs.
The source-package service is the same test setup as the existing HTTP
reconstruction acceptance. This is a *single knockout match*, not yet the
unresolved pure-group tie scenario exercised at lower layers.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from beta_engine.api.deps import get_season_match_service, get_season_point_awards_service
from beta_engine.infrastructure.db.models import SimulationEventGroupModel
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from test_authoritative_simulation_api import _server_state, _install_owned_state

pytestmark = pytest.mark.pr_critical


def _replay(base_url: str, group_id: str) -> tuple[dict, dict]:
    status, collection = _request(
        "GET", base_url + "/match-replays?limit=50"
    )
    assert status == 200
    assert collection["read_only"] is True
    matches = [
        row for row in collection["matches"]
        if row["group_id"] == group_id
    ]
    assert len(matches) == 1, collection
    match = matches[0]
    assert match["replay_available"] is True
    assert match["total_rallies"] > 0
    status, context = _request(
        "GET", base_url + "/match-replay/context?group_id=" + group_id
    )
    assert status == 200, context
    assert context["verified"] is True
    assert context["rng_rerun"] is False
    assert context["replay_source"] == "stored_authoritative_events"
    assert context["result_fingerprint"] == match["result_fingerprint"]
    return match, context


def test_reconstruction_real_match_saved_revision_and_sqlite_reopen(tmp_path):
    root = tmp_path / "reconstruction-run-save"
    server, package = _server_state(root)
    matches = server.app.dependency_overrides[get_season_match_service]()
    awards = server.app.dependency_overrides[get_season_point_awards_service]()
    database_url = f"sqlite:///{root / 'api.sqlite'}"

    with server:
        run_id, branch_id, ancestor = _create_run(
            server, display_name="Review natural squash match then Save",
        )
        week = _install_owned_state(server, package, run_id, branch_id)
        sim = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        status, position = _request("GET", sim + "/position")
        assert status == 200
        assert position["current_slot_kind"] == "match"
        group_id = position["eligible_match_ids"][0]
        status, target = _request(
            "GET", sim + "/match-reconstruction/state?group_id=" + group_id,
        )
        assert status == 200, target
        assert target["group_id"] == group_id
        assert target["expected_revision_id"] == ancestor
        assert target["player_a_id"] != target["player_b_id"]

        preview_request = {
            "expected_week": week.model_dump(mode="json"),
            "expected_position_fingerprint": position["position_fingerprint"],
            "expected_revision_id": ancestor,
            "group_id": group_id,
            "candidate_count": 1,
            "constraints": {"winner_player_id": target["player_a_id"]},
        }
        status, preview = _request(
            "POST", sim + "/match-reconstruction/preview", preview_request,
        )
        assert status == 200
        assert preview["candidate_count_found"] == 1
        selected = preview["candidates"][0]
        assert selected["winner_player_id"] == target["player_a_id"]
        assert selected["detail"]["rally_log"]["events"], (
            "A genuine MatchEngine result must include an authentic rally log"
        )
        assert selected["result_fingerprint"] != ""

        command = {
            **preview_request,
            "command_id": "authentic-reviewed-match-before-run-save",
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "selected_candidate_fingerprint": selected["candidate_fingerprint"],
            "operator_label": "Fixture commissioner",
            "audit_reason": "Selected natural MatchEngine evidence for a real Run.",
        }
        status, committed = _request(
            "POST", sim + "/match-reconstruction/commit", command,
        )
        assert status == 201, committed
        assert committed["result_fingerprint"] == selected["result_fingerprint"]
        assert committed["candidate_fingerprint"] == selected["candidate_fingerprint"]
        before_save_match, before_save_context = _replay(sim, group_id)
        assert before_save_match["result_fingerprint"] == committed["result_fingerprint"]
        assert before_save_match["match_id"] == target["match_id"]
        with server.app.state.runtime.repository._session_factory() as session:
            rows = session.scalars(select(SimulationEventGroupModel).where(
                SimulationEventGroupModel.run_id == run_id,
                SimulationEventGroupModel.branch_id == branch_id,
                SimulationEventGroupModel.group_id == group_id,
            )).all()
            assert len(rows) == 1
            receipt = json.loads(rows[0].payload_json)
            assert receipt["match_reconstruction"]["preview_fingerprint"] == (
                preview["preview_fingerprint"]
            )
            assert receipt["match_reconstruction"]["candidate_fingerprint"] == (
                selected["candidate_fingerprint"]
            )
            assert receipt["match_reconstruction"]["audit_reason"] == (
                command["audit_reason"]
            )

        status, save_preview = _request("GET", sim + "/save/preview")
        assert status == 200
        assert save_preview["can_save"] is True
        assert save_preview["has_unsaved_changes"] is True
        assert save_preview["saved_head_revision_id"] == ancestor
        status, saved = _request("POST", sim + "/save", {
            "expected_draft_version": save_preview["draft_version"],
            "expected_simulation_fingerprint": save_preview["simulation_fingerprint"],
        })
        assert status == 201, saved
        saved_revision = saved["saved_revision"]["revision_id"]
        assert saved_revision != ancestor
        assert saved["saved_revision"]["parent_revision_id"] == ancestor
        assert saved["working_draft"]["base_saved_revision_id"] == saved_revision
        assert saved["working_draft"]["status"] == "clean"
        status, idle = _request("GET", sim + "/save/preview")
        assert status == 200 and idle["can_save"] is False
        assert idle["saved_head_revision_id"] == saved_revision

        before_restart_match, before_restart_context = _replay(sim, group_id)
        assert before_restart_match == before_save_match
        assert before_restart_context == before_save_context

    # New FastAPI service, new SQLAlchemy connections, same real saved Run DB.
    reopened = ApiServer(database_url=database_url)
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: awards
    with reopened:
        sim = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        status, history = _request(
            "GET",
            f"{reopened.base_url}/run-containers/{run_id}/branches/"
            f"{branch_id}/saved-revisions",
        )
        assert status == 200, history
        assert history["saved_head_revision_id"] == saved_revision
        assert [item["revision_id"] for item in history["saved_revisions"]] == [
            ancestor, saved_revision,
        ]
        assert history["saved_revisions"][-1]["is_branch_head"] is True
        assert history["saved_revisions"][0]["is_branch_head"] is False

        after_restart_match, after_restart_context = _replay(sim, group_id)
        assert after_restart_match == before_save_match
        assert after_restart_context == before_save_context

        # Command retry is replayed from the old committed receipt, not re-run
        # at a now-stale Position/Saved Revision or regenerated RNG outcome.
        status, retry = _request(
            "POST", sim + "/match-reconstruction/commit", command,
        )
        assert status == 201 and retry == committed
        status, changed = _request(
            "POST", sim + "/match-reconstruction/commit",
            {**command, "audit_reason": "An incompatible overwrite attempt."},
        )
        assert status == 409, changed
        assert changed["detail"]["code"] == "match_reconstruction_commit_conflict"
        assert _replay(sim, group_id) == (
            after_restart_match, after_restart_context
        )
        status, idle = _request("GET", sim + "/save/preview")
        assert status == 200 and idle["can_save"] is False
        assert idle["saved_head_revision_id"] == saved_revision
