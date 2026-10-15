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
