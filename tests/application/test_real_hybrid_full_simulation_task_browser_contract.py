"""Fail-closed pure acceptance contract for the genuine browser task handoff.

The integration browser runs with production HTTP, SQLite, and actual MatchEngine.
These PR-critical tests verify the observer cannot claim handoff if task
identity/state or observed real match receipts have drifted.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def handoff():
    path = Path(__file__).resolve().parents[2] / "scripts" / "real_hybrid_full_simulation_task_browser_checks.py"
    spec = importlib.util.spec_from_file_location("hybrid_task_browser", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.assert_handoff_task_still_pending


def data():
    frozen = {
        "task_id": "task-1",
        "parent_command_id": "full-parent",
        "run_id": "run",
        "branch_id": "branch",
        "revision": 3,
        "original_schedule_fingerprint": "a" * 64,
        "original_replay_count": 0,
        "checkpoint": "group_phase_review_required",
    }
    task = {
        "task_id": "task-1",
        "parent_command_id": "full-parent",
        "state": "awaiting_operator",
        "checkpoint": "group_phase_review_required",
        "revision": 3,
        "needs_operator_action": True,
        "error": None,
    }
    matches = [{"match_id": "group-1"}, {"match_id": "group-2"}, {"match_id": "hybrid-final"}]
    return frozen, task, matches


@pytest.mark.pr_critical
def test_handoff_requires_same_pending_original_parent_and_three_unique_receipts(tmp_path, handoff):
    frozen, task, matches = data()
    observations = []

    def request(method, path, *args, **kwargs):
        observations.append((method, path))
        if "/full-simulation/tasks/" in path:
            return {"tasks": [task]}
        return {"matches": matches}

    result = handoff(request=request, simulation_scope="/scope", frozen=frozen, artifacts=tmp_path)
    assert result["real_committed_match_count"] == 3
    assert result["task_remained_awaiting_operator"] is True
    assert result["automatic_task_resume"] is False
    assert result["automatic_knockout_approval"] is False
    assert json.loads((tmp_path / "hybrid-task-after-real-knockout.json").read_text()) == result
    assert all(method == "GET" for method, _ in observations)


@pytest.mark.pr_critical
@pytest.mark.parametrize("alter_task,alter_matches", [
    ({"task_id": "foreign"}, {}),
    ({"parent_command_id": "foreign"}, {}),
    ({"state": "active"}, {}),
    ({"checkpoint": "other"}, {}),
    ({"revision": 4}, {}),
    ({"needs_operator_action": False}, {}),
    ({"error": "worker failed"}, {}),
    ({}, {"matches": [{"match_id": "group-1"}, {"match_id": "group-1"}, {"match_id": "hybrid-final"}]}),
    ({}, {"matches": [{"match_id": "group-1"}, {"match_id": "hybrid-final"}]}),
])
def test_handoff_rejects_identity_drift_or_unproven_match_history(
    tmp_path, handoff, alter_task, alter_matches
):
    frozen, task, matches = data()
    task.update(alter_task)
    matches = alter_matches.get("matches", matches)

    def request(method, path, *args, **kwargs):
        if "/full-simulation/tasks/" in path:
            return {"tasks": [task]}
        return {"matches": matches}

    with pytest.raises(AssertionError):
        handoff(request=request, simulation_scope="/scope", frozen=frozen, artifacts=tmp_path)
    assert not (tmp_path / "hybrid-task-after-real-knockout.json").exists()


@pytest.fixture
def resume():
    """Load the actual browser contract without requiring Playwright to import."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "real_hybrid_full_simulation_task_browser_checks.py"
    spec = importlib.util.spec_from_file_location("hybrid_task_resume_browser", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resume_real_hybrid_task_at_explicit_week_two_target


@pytest.mark.pr_critical
@pytest.mark.parametrize("wrong", [
    "task_state",
    "task_checkpoint",
    "task_id",
    "parent_command_id",
    "task_revision",
    "week_not_published",
    "missing_match",
    "duplicate_match",
])
def test_original_hybrid_task_resume_never_approves_invalid_external_state(
    tmp_path, resume, wrong
):
    """Real workflow must reject mismatch *before* POST target or UI interaction."""
    frozen, task, matches = data()
    position = {"current_week": {"season_index": 0, "week": 2}}
    if wrong == "task_state":
        task["state"] = "failed"
    elif wrong == "task_checkpoint":
        task["checkpoint"] = "week_preparation_required"
    elif wrong == "task_id":
        task["task_id"] = "another-task"
    elif wrong == "parent_command_id":
        task["parent_command_id"] = "another-full-parent"
    elif wrong == "task_revision":
        task["revision"] += 1
    elif wrong == "week_not_published":
        position["current_week"] = {"season_index": 0, "week": 1}
    elif wrong == "missing_match":
        matches.pop()
    elif wrong == "duplicate_match":
        matches[2]["match_id"] = matches[0]["match_id"]

    operations = []

    def request(method, path, *args, **kwargs):
        operations.append((method, path))
        assert method == "GET", "No mutation before fully verified real Week-2 sporting state"
        if "/full-simulation/tasks/" in path:
            return {"tasks": [task]}
        if path.endswith("/position"):
            return position
        if path.endswith("/match-replays?limit=50"):
            return {"matches": matches}
        raise AssertionError(f"Unexpected read before guard: {path}")

    with pytest.raises(AssertionError):
        resume(
            request=request, page=None, run_url="http://host/admin/runs/run",
            simulation_scope="/scope", frozen=frozen, artifacts=tmp_path,
        )
    assert operations and all(method == "GET" for method, _ in operations)
    assert not (tmp_path / "real-hybrid-original-task-terminal.json").exists()
