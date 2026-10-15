"""Actual browser Group Match Days while original Full Simulation task awaits approval.

Starts a real production Full Simulation server task against the *same* Run
and Branch before group Match Day 1. No result mocking or worker monkeypatching.
The existing real MatchEngine browser journey subsequently plays and freezes
group→hybrid knockout→ranking; this helper verifies the original server task
never invented a bracket or ran matches while awaiting human decisions.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

from playwright.sync_api import expect


def _task(request, scope, task_id):
    result = request("GET", scope + "/full-simulation/tasks/" + quote(task_id, safe=""))
    assert len(result["tasks"]) == 1
    return result["tasks"][0]


def start_real_group_handoff_task(
    *, request, page, run_url, run_id, branch_id, simulation_scope,
    schedule_fingerprint, artifacts,
):
    preview = request("POST", simulation_scope + "/full-simulation/preview", {
        "command_id": "real-hybrid-full-simulation-parent",
        "operator_label": "Real browser commissioner",
        "audit_reason": "Do not freeze a future group-to-knockout bracket",
    })
    assert preview["initial_action"] == "next_season", preview
    assert preview["expected_revision_id"]
    assert preview["expected_position_fingerprint"]
    command = {
        "command_id": "real-hybrid-full-simulation-parent",
        "run_id": run_id,
        "branch_id": branch_id,
        "operator_label": "Real browser commissioner",
        "audit_reason": "Do not freeze a future group-to-knockout bracket",
        "expected_start_week": preview["start_week"],
        "expected_position_fingerprint": preview["expected_position_fingerprint"],
        "expected_revision_id": preview["expected_revision_id"],
        "expected_preview_fingerprint": preview["preview_fingerprint"],
    }
    original = request("GET", simulation_scope + "/match-replays?limit=50")
    assert original["matches"] == [], "No sporting receipt before group Match Day"
    start = {
        "request_id": "real-hybrid-full-simulation-start",
        "command": command,
    }
    accepted = request("POST", simulation_scope + "/full-simulation/tasks", start, status=202)
    assert accepted["parent_command_id"] == command["command_id"]
    assert request("POST", simulation_scope + "/full-simulation/tasks", start, status=202) == accepted
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        task = _task(request, simulation_scope, accepted["task_id"])
        if task["state"] in ("awaiting_operator", "failed"):
            break
        time.sleep(.10)
    else:
        raise AssertionError("Full Simulation did not reach the group human checkpoint")
    assert task["state"] == "awaiting_operator", task
    assert task["checkpoint"] == "group_phase_review_required", task
    assert task["needs_operator_action"] is True
    assert task["progress"]["blockers"] == ["group_phase_review_required"]
    assert task["original_command"]["command_id"] == command["command_id"]
    assert request("GET", simulation_scope + "/match-replays?limit=50") == original
    assert request("GET", simulation_scope + "/position")["current_slot_kind"] == "match"
    # The real Admin task UI must explain the outstanding group authority,
    # never suggest it has auto-approved group or knockout sporting results.
    page.goto(run_url + "/simulate?branch=" + quote(branch_id, safe=""))
    page.get_by_role("combobox",name="Language / Jazyk").select_option("en")
    # Task Center is the canonical cross-Run UI, regardless of current page.
    page.goto(run_url.rsplit("/admin/runs/", 1)[0] + "/admin/operations")
    task_region = page.get_by_role("region", name="Server simulation tasks")
    expect(task_region).to_contain_text(accepted["task_id"],timeout=30000)
    expect(task_region).to_contain_text("unresolved group phase")
    expect(task_region).not_to_contain_text("Failed; inspect before recovery")
    page.screenshot(path=str(artifacts / "real-hybrid-task-awaiting-group-review.png"),full_page=True)
    frozen = {
        "task_id": accepted["task_id"],
        "parent_command_id": command["command_id"],
        "run_id":run_id,
        "branch_id":branch_id,
        "revision":task["revision"],
        "original_schedule_fingerprint":schedule_fingerprint,
        "original_replay_count":len(original["matches"]),
        "checkpoint":task["checkpoint"],
    }
    (artifacts / "hybrid-task-group-checkpoint.json").write_text(
        json.dumps(frozen,indent=2)
    )
    return frozen


def assert_handoff_task_still_pending(*, request, simulation_scope, frozen, artifacts):
    task = _task(request, simulation_scope, frozen["task_id"])
    assert task["task_id"] == frozen["task_id"]
    assert task["parent_command_id"] == frozen["parent_command_id"]
    assert task["state"] == "awaiting_operator", task
    assert task["checkpoint"] == frozen["checkpoint"]
    assert task["revision"] == frozen["revision"]
    assert task["needs_operator_action"]
    assert task["error"] is None
    # The human-authorized MatchEngine produced two real group and one
    # knockout receipts, not the idle Full Simulation worker.
    replay = request("GET", simulation_scope + "/match-replays?limit=50")
    assert len(replay["matches"]) == 3, replay
    assert len({item["match_id"] for item in replay["matches"]}) == 3
    evidence = {
        **frozen,
        "real_committed_match_count": len(replay["matches"]),
        "task_remained_awaiting_operator": True,
        "automatic_knockout_approval": False,
        "automatic_task_resume": False,
    }
    (artifacts / "hybrid-task-after-real-knockout.json").write_text(
        json.dumps(evidence,indent=2)
    )
    return evidence
