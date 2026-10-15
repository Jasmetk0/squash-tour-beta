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
    saved_revision_before = before_save["saved_head_revision_id"]
    draft_version_before = before_save["draft_version"]
    viewer = "/viewer/runs/" + quote(frozen["run_id"],safe="") + "/rankings/current"
    published_before = request("GET", viewer)
    # Target audit updates the pending parent receipt and may deliberately
    # change the full *preview fingerprint*. It must not create another Saved
    # Revision or alter the actual sporting/draft/ranking authorities.
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
    after_target = request("GET", simulation_scope + "/save/preview")
    assert after_target["saved_head_revision_id"] == saved_revision_before
    assert after_target["draft_version"] == draft_version_before
    assert request("GET", viewer) == published_before

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
    final_preview = request("GET",simulation_scope+"/save/preview")
    assert final_preview["saved_head_revision_id"] == saved_revision_before
    assert final_preview["draft_version"] == draft_version_before
    assert request("GET",viewer)==published_before
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
        "no_additional_matches_or_saved_head_change":True,
        "ranking_publication_identical":True,
        "original_full_simulation_target_reached":True,
        "operator_explicit_resume":True,
        "human_performed_week_transition":True,
    }
    (artifacts/"real-hybrid-original-task-terminal.json").write_text(json.dumps(evidence,indent=2))
    return evidence


def resume_original_full_simulation_to_advance_real_hybrid_week(
    *, request, page, run_url, simulation_scope, frozen, artifacts,
    expected_ranking_fingerprint, before_ranking, before_history,
):
    """Production worker, not Run Admin, performs the *real* hybrid Week Transition.

    Exact original parent Task ID, true MatchEngine receipts and authoritative
    ranking policy already exist. Operator narrows target BEFORE crossing week.
    No fabricated match, no direct storage writes and no Week Transition UI.
    """
    waiting = _task(request, simulation_scope, frozen["task_id"])
    assert waiting["task_id"] == frozen["task_id"], waiting
    assert waiting["state"] == "awaiting_operator", waiting
    assert waiting["checkpoint"] == frozen["checkpoint"]
    assert waiting["revision"] == frozen["revision"]
    assert waiting["parent_command_id"] == frozen["parent_command_id"]
    before_position = request("GET", simulation_scope + "/position")
    assert before_position["current_week"] == {"season_index":0,"week":1}, before_position
    assert before_position["week_ready_for_transition"], before_position
    replay_before = request("GET", simulation_scope + "/match-replays?limit=50")
    assert len(replay_before["matches"]) == 3
    assert len({m["match_id"] for m in replay_before["matches"]}) == 3
    save_before = request("GET", simulation_scope + "/save/preview")
    saved_head_before = save_before["saved_head_revision_id"]
    assert saved_head_before

    target={
        "control_command_id":"hybrid-real-worker-target-week2",
        "target_command_id":frozen["parent_command_id"],
        "target_week":{"season_index":0,"week":2},
        "operator_label":"Hybrid real worker Admin",
        "audit_reason":"Explicitly end original Full Simulation at first real hybrid Week Transition",
    }
    changed=request("POST",simulation_scope+"/full-simulation/target",target)
    assert changed["effective_target_week"]==target["target_week"],changed
    assert changed["replayed"] is False
    replay_target=request("POST",simulation_scope+"/full-simulation/target",target)
    assert replay_target["replayed"] is True
    assert replay_target["applied_revision"]==changed["applied_revision"]
    assert request("GET",simulation_scope+"/position")["current_week"]==before_position["current_week"]
    assert request("GET",simulation_scope+"/match-replays?limit=50")==replay_before
    assert request("GET",simulation_scope+"/save/preview")["saved_head_revision_id"]==saved_head_before

    from playwright.sync_api import expect

    operator_page=page.context.new_page()
    try:
        operator_page.goto(run_url.rsplit("/admin/runs/",1)[0]+"/admin/operations")
        operator_page.get_by_role("combobox",name="Language / Jazyk").select_option("en")
        tasks=operator_page.get_by_role("region",name="Server simulation tasks")
        card=tasks.locator('li[data-task-id="'+frozen["task_id"]+'"]')
        expect(card).to_have_count(1,timeout=30000)
        expect(card).to_contain_text("Waiting for operator")
        card.get_by_label("Task operator",exact=True).fill("Hybrid Week Transition commissioner")
        card.get_by_label("Task audit reason",exact=True).fill(
            "Run real, reviewed canonical Week Transition from original Full Simulation task"
        )
        card.get_by_role("button",name="Explicitly resume server task").click()
        deadline=time.monotonic()+100
        while time.monotonic()<deadline:
            done=_task(request,simulation_scope,frozen["task_id"])
            if done["state"] in ("target_reached","failed","recoverable"):
                break
            if done["state"]=="awaiting_operator" and done["revision"]>waiting["revision"]:
                raise AssertionError("Original worker blocked at: "+str(done))
            time.sleep(.1)
        else:
            raise AssertionError("Original worker failed to complete Week 1->2")
        assert done["state"]=="target_reached",done
        assert done["parent_command_id"]==frozen["parent_command_id"]
        assert done["original_command"]["command_id"]==frozen["parent_command_id"]
        assert done["current_week"]==target["target_week"]
        expect(card).to_contain_text("Target reached",timeout=30000)
        operator_page.screenshot(path=str(artifacts/"real-hybrid-worker-week2-target.png"),full_page=True)
    finally:
        operator_page.close()

    advanced=request("GET",simulation_scope+"/position")
    assert advanced["current_week"]==target["target_week"],advanced
    assert request("GET",simulation_scope+"/match-replays?limit=50")==replay_before
    # The worker commits the world/ranking Week Transition, but Viewer is
    # intentionally **Saved Revision backed**. Before the operator's separate
    # Save, public Week 1 must remain identical. Publication to Viewer Week 2
    # is asserted by publish_first_hybrid_official_week *after* explicit Save.
    viewer="/viewer/runs/"+quote(frozen["run_id"],safe="")+"/rankings"
    assert request("GET",viewer+"/current")==before_ranking
    assert request("GET",viewer+"/history")==before_history
    assert request("GET",viewer+"/history/0")==before_ranking
    assert request("GET",simulation_scope+"/save/preview")["saved_head_revision_id"]==saved_head_before
    proof={
        "original_task_id":frozen["task_id"],
        "original_parent_id":frozen["parent_command_id"],
        "task_state":"target_reached",
        "target_week":target["target_week"],
        "target_command_replayed":True,
        "worker_performed_week_transition":True,
        "real_match_engine_replay_count":3,
        "expected_ranking_week2_fingerprint":expected_ranking_fingerprint,
        "human_did_not_click_week_transition":True,
        "saved_revision_unchanged_until_explicit_admin_save":True,
        "public_viewer_stays_at_saved_week1_until_save":True,
    }
    (artifacts/"hybrid-worker-week-transition-proof.json").write_text(
        json.dumps(proof,indent=2)
    )
    return proof


def prove_next_real_hybrid_week_from_restarted_saved_run(
    *, request, page, run_url, simulation_scope, frozen,
    official_week_two, saved_week_two_revision, artifacts,
):
    """Second real server-owned Full Simulation on *same Run* after process restart.

    First immutable parent legitimately reached its operator-defined Week-2
    target, so cannot be extended or resumed. This is a *new*, auditably
    distinct Full Simulation parent beginning at a Saved Week-2 Run state.
    No fixture scores or synthetic published rankings.
    """
    assert frozen is not None and saved_week_two_revision
    original=_task(request,simulation_scope,frozen["task_id"])
    assert original["task_id"]==frozen["task_id"]
    assert original["parent_command_id"]==frozen["parent_command_id"]
    assert original["state"]=="target_reached",original
    position=request("GET",simulation_scope+"/position")
    assert position["current_week"]=={"season_index":0,"week":2},position
    viewer="/viewer/runs/"+quote(frozen["run_id"],safe="")+"/rankings"
    assert request("GET",viewer+"/current")==official_week_two
    original_replays=request("GET",simulation_scope+"/match-replays?limit=50")
    assert len(original_replays["matches"])==3
    assert len({row["match_id"] for row in original_replays["matches"]})==3
    saved_preview=request("GET",simulation_scope+"/save/preview")
    assert saved_preview["saved_head_revision_id"]==saved_week_two_revision
    assert saved_preview["has_unsaved_changes"] is False
    assert saved_preview["can_save"] is False

    proposed=request("POST",simulation_scope+"/full-simulation/preview",{
        "command_id":"real-hybrid-second-full-parent-after-restart",
        "operator_label":"Week 2 real continuation commissioner",
        "audit_reason":"Verify following canonical weeks after genuine hybrid and SQLite restart",
    })
    assert proposed["start_week"]=={"season_index":0,"week":2},proposed
    assert proposed["expected_revision_id"]==saved_week_two_revision
    assert proposed["initial_action"]=="next_season"
    command={
        "command_id":"real-hybrid-second-full-parent-after-restart",
        "run_id":frozen["run_id"],"branch_id":frozen["branch_id"],
        "operator_label":"Week 2 real continuation commissioner",
        "audit_reason":"Verify following canonical weeks after genuine hybrid and SQLite restart",
        "expected_start_week":proposed["start_week"],
        "expected_position_fingerprint":proposed["expected_position_fingerprint"],
        "expected_revision_id":proposed["expected_revision_id"],
        "expected_preview_fingerprint":proposed["preview_fingerprint"],
    }
    start={"request_id":"real-hybrid-second-start-after-process-restart","command":command}
    acknowledgement=request("POST",simulation_scope+"/full-simulation/tasks",start,status=202)
    assert acknowledgement["parent_command_id"]==command["command_id"]
    assert acknowledgement["task_id"]!=frozen["task_id"]
    assert request("POST",simulation_scope+"/full-simulation/tasks",start,status=202)==acknowledgement
    deadline=time.monotonic()+150
    task=None
    while time.monotonic()<deadline:
        task=_task(request,simulation_scope,acknowledgement["task_id"])
        if task["state"] in ("target_reached","complete","failed","recoverable","awaiting_operator"):
            break
        time.sleep(.15)
    else:
        raise AssertionError("Second Full Simulation worker did not reach a canonical checkpoint")
    assert task["state"] in ("awaiting_operator","target_reached","complete"),task
    assert task["parent_command_id"]==command["command_id"]
    assert task["original_command"]["command_id"]==command["command_id"]
    later=request("GET",simulation_scope+"/position")
    ordinal=later["current_week"]["season_index"]*61+later["current_week"]["week"]-1
    assert ordinal>=2, (later,task)
    assert request("GET",simulation_scope+"/match-replays?limit=50")==original_replays
    assert request("GET",viewer+"/current")==official_week_two, (
        "No separate Save: public Week-2 snapshot must stay unchanged"
    )
    assert request("GET",simulation_scope+"/save/preview")["saved_head_revision_id"]==saved_week_two_revision
    assert _task(request,simulation_scope,frozen["task_id"])["state"]=="target_reached"

    # Task Center supports the second, separate Run-owned parent without
    # collapsing the original terminal record or silently changing sport.
    from playwright.sync_api import expect
    task_page=page.context.new_page()
    try:
        task_page.goto(run_url.rsplit("/admin/runs/",1)[0]+"/admin/operations")
        task_page.get_by_role("combobox",name="Language / Jazyk").select_option("en")
        region=task_page.get_by_role("region",name="Server simulation tasks")
        expect(region).to_contain_text(acknowledgement["task_id"],timeout=30000)
        expect(region).to_contain_text(frozen["task_id"],timeout=30000)
        task_page.screenshot(path=str(artifacts/"hybrid-following-week-after-restart.png"),full_page=True)
    finally:
        task_page.close()
    report={
        "original_terminal_task":frozen["task_id"],
        "second_full_simulation_task":acknowledgement["task_id"],
        "second_parent":command["command_id"],
        "start_week":proposed["start_week"],
        "observed_week":later["current_week"],
        "second_task_state":task["state"],
        "second_task_checkpoint":task.get("checkpoint"),
        "identical_real_match_engine_replays":True,
        "saved_week2_revision_preserved":saved_week_two_revision,
        "viewer_week2_unchanged_until_save":True,
        "second_parent_is_distinct_from_terminal_original":True,
    }
    (artifacts/"hybrid-second-week-worker-after-restart.json").write_text(
        json.dumps(report,indent=2)
    )
    return report


def prove_same_full_task_survives_second_restart(
    *, request, page, run_url, simulation_scope,
    initial_parent, continuing, official_week_two, artifacts,
):
    """Reopen *the same* nonterminal second Full Simulation task after restart.

    Week 1's original command had a deliberately terminal target; the distinct
    Week-2+ parent from the prior acceptance is the one being resumed here.
    No new parent or sporting receipt is created.
    """
    assert initial_parent and continuing
    task_id=continuing["second_full_simulation_task"]
    parent_id=continuing["second_parent"]
    observed=continuing["observed_week"]
    assert continuing["start_week"]=={"season_index":0,"week":2}
    assert observed["season_index"]*61+observed["week"]-1>=2

    first=_task(request,simulation_scope,initial_parent["task_id"])
    assert first["state"]=="target_reached",first
    assert first["parent_command_id"]==initial_parent["parent_command_id"]
    before=_task(request,simulation_scope,task_id)
    assert before["task_id"]==task_id
    assert before["parent_command_id"]==parent_id
    assert before["original_command"]["command_id"]==parent_id
    assert before["state"]==continuing["second_task_state"]=="awaiting_operator",before
    assert before["checkpoint"]==continuing["second_task_checkpoint"]
    assert before["current_week"]==observed

    position=request("GET",simulation_scope+"/position")
    assert position["current_week"]==observed
    replay=request("GET",simulation_scope+"/match-replays?limit=50")
    assert len(replay["matches"])==3
    assert len({row["match_id"] for row in replay["matches"]})==3
    saved_head=continuing["saved_week2_revision_preserved"]
    assert request("GET",simulation_scope+"/save/preview")["saved_head_revision_id"]==saved_head
    viewer="/viewer/runs/"+quote(initial_parent["run_id"],safe="")+"/rankings"
    assert request("GET",viewer+"/current")==official_week_two

    from playwright.sync_api import expect
    from playwright.sync_api import expect
    operator=page.context.new_page()
    try:
        operator.goto(run_url.rsplit("/admin/runs/",1)[0]+"/admin/operations")
        operator.get_by_role("combobox",name="Language / Jazyk").select_option("en")
        region=operator.get_by_role("region",name="Server simulation tasks")
        task_card=region.locator('li[data-task-id="'+task_id+'"]')
        expect(task_card).to_have_count(1,timeout=30000)
        expect(task_card).to_contain_text("Waiting for operator")
        expect(region.locator('li[data-task-id="'+initial_parent["task_id"]+'"]')).to_have_count(1)
        task_card.get_by_label("Task operator",exact=True).fill("Commissioner post-restart")
        task_card.get_by_label("Task audit reason",exact=True).fill(
            "Retry canonical unchanged parent after real SQLite restart"
        )
        task_card.get_by_role("button",name="Explicitly resume server task").click()
        deadline=time.monotonic()+120
        while time.monotonic()<deadline:
            after=_task(request,simulation_scope,task_id)
            if after["revision"]>before["revision"] and after["state"] in (
                "awaiting_operator","target_reached","complete","failed"
            ):
                break
            time.sleep(.1)
        else:
            raise AssertionError("Same Full Simulation task never settled after explicit restart recovery")
        assert after["state"] in ("awaiting_operator","target_reached","complete"),after
        assert after["task_id"]==task_id and after["parent_command_id"]==parent_id
        assert after["original_command"]==before["original_command"]
        assert after["revision"]>before["revision"]
        operator.screenshot(path=str(artifacts/"same-full-task-after-restart.png"),full_page=True)
    finally:
        operator.close()
    final_position=request("GET",simulation_scope+"/position")["current_week"]
    old_ordinal=observed["season_index"]*61+observed["week"]-1
    new_ordinal=final_position["season_index"]*61+final_position["week"]-1
    assert new_ordinal>=old_ordinal
    assert request("GET",simulation_scope+"/match-replays?limit=50")==replay
    assert request("GET",simulation_scope+"/save/preview")["saved_head_revision_id"]==saved_head
    assert request("GET",viewer+"/current")==official_week_two
    assert _task(request,simulation_scope,initial_parent["task_id"])["state"]=="target_reached"
    proof={
        "original_terminal_parent":initial_parent["parent_command_id"],
        "continued_parent":parent_id,
        "task_id_before_restart":task_id,
        "task_id_after_restart":after["task_id"],
        "immutable_request_preserved":True,
        "revision_before":before["revision"],
        "revision_after":after["revision"],
        "checkpoint_before":before["checkpoint"],
        "checkpoint_after":after["checkpoint"],
        "week_before":observed,
        "week_after":final_position,
        "additional_week_transition_observed":new_ordinal>old_ordinal,
        "original_three_matches_unchanged":True,
        "published_week_two_unchanged":True,
    }
    (artifacts/"same-parent-after-second-sqlite-restart.json").write_text(
        json.dumps(proof,indent=2)
    )
    return proof
