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

def _task(request, scope, task_id):
    result = request("GET", scope + "/full-simulation/tasks/" + quote(task_id, safe=""))
    assert len(result["tasks"]) == 1
    return result["tasks"][0]


def start_real_group_handoff_task(
    *, request, page, run_url, run_id, branch_id, simulation_scope,
    schedule_fingerprint, artifacts,
):
    from playwright.sync_api import expect

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
    # Keep Task Center's 2-second polling in an *independent tab*. Otherwise
    # the original browser-smoke page carries polling requests into the Match
    # Day navigation and its network-idle tracking can never settle.
    task_page = page.context.new_page()
    try:
        task_page.goto(run_url.rsplit("/admin/runs/", 1)[0] + "/admin/operations")
        task_page.get_by_role("combobox",name="Language / Jazyk").select_option("en")
        task_region = task_page.get_by_role("region", name="Server simulation tasks")
        expect(task_region).to_contain_text(accepted["task_id"],timeout=30000)
        expect(task_region).to_contain_text("unresolved group phase")
        expect(task_region).not_to_contain_text("Failed; inspect before recovery")
        task_page.screenshot(path=str(artifacts / "real-hybrid-task-awaiting-group-review.png"),full_page=True)
    finally:
        task_page.close()
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


def resume_real_hybrid_task_at_explicit_week_two_target(
    *, request, page, run_url, simulation_scope, frozen, artifacts,
):
    """End the same original task only after humans have published real Week 2.

    No sports, ranking transition or Saved Revision is fabricated by the
    target mutation. The human Run browser already approved the authoritative
    tournament and Week Transition; this task continuation observes the
    *reached* target and preserves all match/revision evidence.
    """
    waiting = _task(request, simulation_scope, frozen["task_id"])
    assert waiting["state"] == "awaiting_operator", waiting
    assert waiting["checkpoint"] == "group_phase_review_required", waiting
    assert waiting["revision"] == frozen["revision"]
    assert waiting["parent_command_id"] == frozen["parent_command_id"]
    position = request("GET", simulation_scope + "/position")
    assert position["current_week"] == {"season_index": 0, "week": 2}, position
    before_replays = request("GET", simulation_scope + "/match-replays?limit=50")
    assert len(before_replays["matches"]) == 3
    assert len({m["match_id"] for m in before_replays["matches"]}) == 3
    before_save = request("GET", simulation_scope + "/save/preview")
    # The parent is not allowed to mutate already Saved sporting or ranking
    # authority just to report that the chosen target was reached.
    target = {
        "control_command_id": "real-hybrid-task-reviewed-target-week2",
        "target_command_id": frozen["parent_command_id"],
        "target_week": {"season_index": 0, "week": 2},
        "operator_label": "Explicit hybrid task operator",
        "audit_reason": "Finish unchanged original server task at verified real Week 2",
    }
    approved = request("POST", simulation_scope + "/full-simulation/target", target)
    assert approved["effective_target_week"] == target["target_week"]
    assert approved["target_revision"] >= 1
    retry = request("POST", simulation_scope + "/full-simulation/target", target)
    assert retry["replayed"] is True
    assert retry["effective_target_week"] == target["target_week"]
    assert request("GET", simulation_scope + "/match-replays?limit=50") == before_replays
    assert request("GET", simulation_scope + "/save/preview") == before_save

    # Real UI, deliberate operator + reason, original Task ID. No API bypass
    # or automatic approval after clicking target.
    from playwright.sync_api import expect

    ui = page.context.new_page()
    try:
        ui.goto(run_url.rsplit("/admin/runs/", 1)[0] + "/admin/operations")
        ui.get_by_role("combobox", name="Language / Jazyk").select_option("en")
        tasks = ui.get_by_role("region", name="Server simulation tasks")
        card = tasks.locator('li[data-task-id="'+frozen["task_id"]+'"]')
        expect(card).to_have_count(1, timeout=30000)
        expect(card.get_by_role("button",name="Explicitly resume server task")).to_be_visible()
        card.get_by_label("Task operator",exact=True).fill("Explicit hybrid task operator")
        card.get_by_label("Task audit reason",exact=True).fill(
            "Review confirmed real Week-2 authority; terminate original task"
        )
        card.get_by_role("button",name="Explicitly resume server task").click()
        deadline = time.monotonic()+90
        while time.monotonic()<deadline:
            finished = _task(request,simulation_scope,frozen["task_id"])
            if finished["state"] in ("target_reached", "failed", "awaiting_operator"):
                if finished["state"] != "awaiting_operator" or finished["revision"] > waiting["revision"]:
                    break
            time.sleep(.1)
        else:
            raise AssertionError("Original hybrid Full Simulation did not settle at Week-2 target")
        assert finished["state"]=="target_reached", finished
        assert finished["parent_command_id"]==frozen["parent_command_id"]
        assert finished["original_command"]["command_id"]==frozen["parent_command_id"]
        assert finished["current_week"]==target["target_week"]
        expect(card).to_contain_text("Target reached", timeout=30000)
        ui.screenshot(path=str(artifacts/"real-hybrid-original-task-target-reached.png"),full_page=True)
    finally:
        ui.close()

    assert request("GET",simulation_scope+"/position")["current_week"]==target["target_week"]
    assert request("GET",simulation_scope+"/match-replays?limit=50")==before_replays
    assert request("GET",simulation_scope+"/save/preview")==before_save
    history=request("GET",simulation_scope+"/full-simulation/history")
    assert any(item["command_id"]==frozen["parent_command_id"] and item["status"]=="target_reached"
               for item in history["items"]), history
    evidence={
        "task_id":frozen["task_id"],
        "parent_command_id":frozen["parent_command_id"],
        "real_match_receipt_count":len(before_replays["matches"]),
        "target_week":target["target_week"],
        "target_revision":approved["target_revision"],
        "task_state":finished["state"],
        "target_replay_safe":True,
        "no_additional_matches_or_unsaved_changes":True,
        "original_full_simulation_target_reached":True,
        "operator_explicit_resume":True,
        "human_performed_week_transition":True,
    }
    (artifacts/"real-hybrid-original-task-terminal.json").write_text(json.dumps(evidence,indent=2))
    return evidence
