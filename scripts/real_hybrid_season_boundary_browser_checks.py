"""Human-approved genuine Week-61 boundary Save on the SAME Full Simulation task.

Uses the production Admin browser/SQLite workflow, not invented Season ranking
or a direct Saved Revision insert. Exact terminal original task is never resumed.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

from real_hybrid_full_simulation_task_browser_checks import _task


def approve_real_week61_save_and_resume_same_full_task(
    *, request, page, run_url, simulation_scope, initial_parent,
    continuing, same_task_resume, official_week_two, artifacts,
):
    """Save real World Week 61, then resolve/retry *same* server task.

    At Week 61, a human Save is mandatory before canonical ordinary Season
    Transition. A missing season configuration remains an explicit blocker;
    the acceptance must not invent one. If preflight is ready, use the
    actual UI review-and-advance surface.
    """
    assert initial_parent and continuing and same_task_resume
    assert continuing["second_task_checkpoint"]=="season_transition_save_required"
    assert same_task_resume["checkpoint_after"]=="season_transition_save_required"
    assert same_task_resume["week_after"]=={"season_index":0,"week":61}
    task_id=continuing["second_full_simulation_task"]
    parent_id=continuing["second_parent"]
    existing=_task(request,simulation_scope,task_id)
    assert existing["task_id"]==task_id and existing["parent_command_id"]==parent_id
    assert existing["state"]=="awaiting_operator"
    assert existing["checkpoint"]=="season_transition_save_required"
    assert existing["original_command"]["command_id"]==parent_id
    assert _task(request,simulation_scope,initial_parent["task_id"])["state"]=="target_reached"
    position=request("GET",simulation_scope+"/position")
    assert position["current_week"]=={"season_index":0,"week":61}
    before_save=request("GET",simulation_scope+"/save/preview")
    assert before_save["saved_head_revision_id"]==continuing["saved_week2_revision_preserved"]
    assert before_save["has_unsaved_changes"] is True
    assert before_save["can_save"] is True
    replay=request("GET",simulation_scope+"/match-replays?limit=50")
    assert len(replay["matches"])==3
    assert len({match["match_id"] for match in replay["matches"]})==3
    viewer="/viewer/runs/"+quote(initial_parent["run_id"],safe="")+"/rankings"
    assert request("GET",viewer+"/current")==official_week_two
    archived_week2=request("GET",viewer+"/history/1")
    historical_week1=request("GET",viewer+"/history/0")

    # A real Admin explicitly approves the derived Saved Revision; this is
    # *not* an automatic Full Simulation operation or unreviewed API POST.
    from playwright.sync_api import expect
    page.goto(run_url+"/simulate?branch="+quote(initial_parent["branch_id"],safe=""))
    page.get_by_role("combobox",name="Language / Jazyk").select_option("en")
    save_button=page.get_by_role("button",name="Save authoritative simulation",exact=True)
    expect(save_button).to_be_enabled(timeout=30000)
    save_button.click()
    expect(page.get_by_text("Saved as revision",exact=False)).to_be_visible(timeout=30000)
    saved=request("GET",simulation_scope+"/save/preview")
    saved_head=saved["saved_head_revision_id"]
    assert saved_head and saved_head!=before_save["saved_head_revision_id"]
    assert saved["has_unsaved_changes"] is False
    published=request("GET",viewer+"/current")
    assert published["season_index"]==0 and published["week"]==61
    assert published["week_ordinal"]==60,published
    assert request("GET",viewer+"/history/1")==archived_week2
    assert request("GET",viewer+"/history/0")==historical_week1
    assert request("GET",simulation_scope+"/match-replays?limit=50")==replay

    preflight=request("GET",simulation_scope+"/season-transition/preflight")
    assert preflight["completed_week"]=={"season_index":0,"week":61}
    assert preflight["target_week"]=={"season_index":1,"week":1}
    assert preflight["saved_revision_id"]==saved_head
    assert preflight["final_season"] is False
    assert isinstance(preflight["ready_for_execution"],bool)
    actual_rollover=False
    if preflight["ready_for_execution"]:
        # The only legal Season Transition is an explicit Admin-reviewed one.
        review=page.get_by_role("button",name="Review Season Transition",exact=True)
        expect(review).to_be_enabled(timeout=30000)
        review.click()
        advance=page.get_by_role("button",name="Advance to next season",exact=True)
        expect(advance).to_be_enabled(timeout=30000)
        advance.click()
        expect(page.get_by_text("New Saved Revision",exact=False)).to_be_visible(timeout=30000)
        actual_rollover=True
        assert request("GET",simulation_scope+"/position")["current_week"]=={
            "season_index":1,"week":1
        }
    else:
        blockers=preflight["state_blockers"]+preflight["implementation_gaps"]
        assert blockers,preflight
        assert page.get_by_role("button",name="Advance to next season",exact=True).count()==0

    # The SAME immutable Full Simulation task still requires an explicit
    # operator continuation after the real manual Save/Season action.
    waiting=_task(request,simulation_scope,task_id)
    assert waiting["state"]=="awaiting_operator" and waiting["parent_command_id"]==parent_id
    ops=page.context.new_page()
    try:
        ops.goto(run_url.rsplit("/admin/runs/",1)[0]+"/admin/operations")
        ops.get_by_role("combobox",name="Language / Jazyk").select_option("en")
        card=ops.get_by_role("region",name="Server simulation tasks").locator(
            'li[data-task-id="'+task_id+'"]'
        )
        expect(card).to_have_count(1,timeout=30000)
        expect(card).to_contain_text("Waiting for operator")
        card.get_by_label("Task operator",exact=True).fill("Week 61 Save commissioner")
        card.get_by_label("Task audit reason",exact=True).fill(
            "Explicit continuation of same parent after real Week-61 Save and season preflight"
        )
        card.get_by_role("button",name="Explicitly resume server task").click()
        deadline=time.monotonic()+180
        after=None
        while time.monotonic()<deadline:
            after=_task(request,simulation_scope,task_id)
            if after["revision"]>waiting["revision"] and after["state"] in (
                "awaiting_operator","target_reached","complete","failed"
            ):
                break
            time.sleep(.1)
        else:
            raise AssertionError("Original ongoing parent failed to settle after Week-61 Save")
        assert after["state"] in ("awaiting_operator","target_reached","complete"),after
        assert after["task_id"]==task_id and after["parent_command_id"]==parent_id
        assert after["original_command"]==existing["original_command"]
        assert after["revision"]>waiting["revision"]
        if not actual_rollover:
            assert after["checkpoint"]=="season_transition_prerequisite",after
        ops.screenshot(path=str(artifacts/"hybrid-week61-saved-same-task.png"),full_page=True)
    finally:
        ops.close()

    final_pos=request("GET",simulation_scope+"/position")["current_week"]
    assert (final_pos["season_index"]*61+final_pos["week"]-1)>=60
    assert request("GET",simulation_scope+"/match-replays?limit=50")==replay
    assert request("GET",viewer+"/history/1")==archived_week2
    assert request("GET",viewer+"/history/0")==historical_week1
    assert _task(request,simulation_scope,initial_parent["task_id"])["state"]=="target_reached"
    evidence={
        "original_terminal_parent":initial_parent["parent_command_id"],
        "continuing_task_id":task_id,
        "continuing_parent_id":parent_id,
        "world_week_before_save":{"season_index":0,"week":61},
        "published_week_after_manual_save":{"season_index":0,"week":61},
        "new_saved_head":saved_head,
        "same_task_revision_before":waiting["revision"],
        "same_task_revision_after":after["revision"],
        "checkpoint_after":after["checkpoint"],
        "season_preflight_ready":preflight["ready_for_execution"],
        "season_preflight_state_blockers":preflight["state_blockers"],
        "season_preflight_engine_gaps":preflight["implementation_gaps"],
        "manual_season_transition_executed":actual_rollover,
        "world_week_after_retry":final_pos,
        "original_match_replays_unchanged":True,
        "historical_week1_and_week2_unchanged":True,
    }
    (artifacts/"hybrid-saved-week61-boundary-proof.json").write_text(
        json.dumps(evidence,indent=2)
    )
    return evidence
