"""Real HTTP/file-backed SQLite acceptance tests for atomic Week Transition."""

import sqlite3
import json

import pytest
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority

from test_admin_ranking_preparation_api import initial
from test_ranking_preparation_preview_api import dump
from test_saved_revision_history_api import ApiServer, _create_run, _request
import beta_engine.infrastructure.db.authoritative_week_transition as transition_module


def counts(path):
    with sqlite3.connect(path) as connection:
        return tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in (
            "published_official_rankings", "authoritative_world_states",
            "authoritative_world_events", "authoritative_week_transition_receipts"))


def prepared_transition(server, name):
    run_id, branch_id, empty_revision = _create_run(server, display_name=name)
    ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
    bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
    assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
    authority = {"run_id": run_id, "branch_id": branch_id, "base_revision_id": empty_revision,
        "completed_week": {"season_index": 0, "week": 1}, "target_week": {"season_index": 0, "week": 2},
        "players": bootstrap["players"], "policy": bootstrap["policy"], "provenance": "Frozen boundary",
        "adopted_by_command_id": "authority", "audit": bootstrap["audit"]}
    adopted = _request("POST", ranking + "/transition-authorities", authority)[1]
    review = _request("GET", ranking + "/save/preview")[1]
    saved = _request("POST", ranking + "/save", {"expected_draft_version": review["draft_version"],
        "expected_ranking_fingerprint": review["ranking_fingerprint"]})[1]
    command = {"command_id": "transition", "run_id": run_id, "branch_id": branch_id,
        "base_revision_id": saved["saved_revision"]["revision_id"], "completed_week": authority["completed_week"],
        "target_week": authority["target_week"], "authority_fingerprint": RankingTransitionAuthority.model_validate_json(json.dumps(adopted)).fingerprint,
        "tournaments": [], "audit": bootstrap["audit"]}
    return run_id, branch_id, command


@pytest.mark.parametrize("failure_point", ["after_ranking_staging", "before_publication", "after_publication"])
def test_failure_at_each_write_boundary_rolls_back_everything(tmp_path, monkeypatch, failure_point):
    path = tmp_path / f"rollback-{failure_point}.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, command = prepared_transition(server, failure_point)
        before = dump(path)
        def fail(name):
            if name == failure_point:
                raise RuntimeError("forced transition failure")
        monkeypatch.setattr(transition_module, "_fault_injection_point", fail)
        # Unhandled fault is deliberately asserted at the transaction owner level.
        runner = transition_module.AuthoritativeWeekTransitionRunner(
            server.app.state.runtime.repository._session_factory)
        with pytest.raises(RuntimeError, match="forced"):
            runner.execute(transition_module.AuthoritativeWeekTransitionCommand.model_validate_json(json.dumps(command)))
        assert dump(path) == before and counts(path) == (0, 0, 0, 0)


@pytest.mark.smoke
def test_atomic_publication_retry_save_reopen_and_bidirectional_restore(tmp_path):
    path = tmp_path / "week-transition.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        run_id, branch_id, empty_revision = _create_run(server, display_name="Atomic week")
        ranking = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates"
        bootstrap = initial() | {"run_id": run_id, "branch_id": branch_id}
        assert _request("POST", ranking + "/prepare/initial", bootstrap)[0] == 201
        authority = {
            "run_id": run_id, "branch_id": branch_id, "base_revision_id": empty_revision,
            "completed_week": {"season_index": 0, "week": 1},
            "target_week": {"season_index": 0, "week": 2},
            "players": bootstrap["players"], "policy": bootstrap["policy"],
            "provenance": "Frozen supported boundary", "adopted_by_command_id": "authority-2",
            "audit": bootstrap["audit"],
        }
        status, adopted = _request("POST", ranking + "/transition-authorities", authority)
        assert status == 201
        review = _request("GET", ranking + "/save/preview")[1]
        status, saved_base = _request("POST", ranking + "/save", {
            "expected_draft_version": review["draft_version"],
            "expected_ranking_fingerprint": review["ranking_fingerprint"],
        })
        assert status == 201
        base_revision = saved_base["saved_revision"]["revision_id"]
        command = {
            "command_id": "transition-week-2", "run_id": run_id, "branch_id": branch_id,
            "base_revision_id": base_revision,
            "completed_week": authority["completed_week"], "target_week": authority["target_week"],
            "authority_fingerprint": RankingTransitionAuthority.model_validate_json(json.dumps(adopted)).fingerprint,
            "tournaments": [],
            "audit": bootstrap["audit"],
        }
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/week-transitions"
        before = dump(path)
        status, preview = _request("POST", root + "/preview", command)
        assert status == 200 and dump(path) == before and counts(path) == (0, 0, 0, 0)
        assert _request("POST", root, command | {"base_revision_id": empty_revision})[0] == 409
        assert _request("POST", root, command | {"branch_id": "other"})[0] == 409
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE ranking_transition_authorities SET fingerprint = ?", ("0" * 64,))
        corrupted = dump(path)
        assert _request("POST", root, command)[0] == 409
        assert dump(path) == corrupted and counts(path) == (0, 0, 0, 0)
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE ranking_transition_authorities SET fingerprint = ?", (command["authority_fingerprint"],))
        status, confirmed = _request("POST", root, command)
        assert status == 201 and confirmed == preview
        assert counts(path) == (2, 1, 1, 1)
        after = dump(path)
        assert _request("POST", root, command) == (201, confirmed)
        assert dump(path) == after
        assert _request("POST", root, command | {"audit": bootstrap["audit"] | {"reason": "different"}})[0] == 409
        assert dump(path) == after

        review = _request("GET", ranking + "/save/preview")[1]
        status, transitioned_save = _request("POST", ranking + "/save", {
            "expected_draft_version": review["draft_version"],
            "expected_ranking_fingerprint": review["ranking_fingerprint"],
        })
        assert status == 201
        transition_revision = transitioned_save["saved_revision"]["revision_id"]
        status, restored = _request("POST", f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{base_revision}/restore", {
            "expected_head_saved_revision_id": transition_revision,
            "expected_draft_version": transitioned_save["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True,
        })
        assert status == 201 and counts(path) == (0, 0, 0, 0)
        status, forward = _request("POST", f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions/{transition_revision}/restore", {
            "expected_head_saved_revision_id": restored["saved_revision"]["revision_id"],
            "expected_draft_version": restored["working_draft"]["draft_version"],
            "expected_current_viewer_branch_id": branch_id, "explicit_confirmation": True,
        })
        assert status == 201 and counts(path) == (2, 1, 1, 1)
    with ApiServer(database_url=f"sqlite:///{path}"):
        assert counts(path) == (2, 1, 1, 1)
