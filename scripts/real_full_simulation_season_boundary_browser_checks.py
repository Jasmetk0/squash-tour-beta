"""One real Full Simulation parent crosses the first season boundary via Admin.

The input is the proven real hybrid browser world with genuine group/knockout
MatchEngine receipts. Week 2..61 were already executed by the same pending
Full Simulation task, across two actual process restarts.
"""
from __future__ import annotations

import json
import time
from urllib.parse import quote

from real_hybrid_full_simulation_task_browser_checks import _task


def approve_and_resume_same_full_parent_across_season(
    *, request, page, run_url, simulation_scope, initial, continuing,
    restored, official_week_two, artifacts,
):
    """Explicit Saved boundary + reviewed canonical rollover, then SAME task."""
    assert initial is not None and continuing is not None and restored is not None
    task_id = continuing["second_full_simulation_task"]
    parent_id = continuing["second_parent"]
    assert restored["task_id_after_restart"] == task_id
    assert restored["continued_parent"] == parent_id
    assert continuing["start_week"] == {"season_index": 0, "week": 2}

    task = _task(request, simulation_scope, task_id)
    assert task["task_id"] == task_id
    assert task["parent_command_id"] == parent_id
    assert task["original_command"]["command_id"] == parent_id
    assert task["state"] == "awaiting_operator", task
    assert task["checkpoint"] == "season_transition_save_required", task
    assert task["current_week"] == {"season_index": 0, "week": 61}, task
    original = _task(request, simulation_scope, initial["task_id"])
    assert original["state"] == "target_reached"
    assert original["parent_command_id"] == initial["parent_command_id"]

    world = request("GET", simulation_scope + "/position")
    assert world["current_week"] == {"season_index": 0, "week": 61}, world
    before_replays = request("GET", simulation_scope + "/match-replays?limit=50")
    assert len(before_replays["matches"]) == 3
    assert len({x["match_id"] for x in before_replays["matches"]}) == 3
    viewer = "/viewer/runs/" + quote(initial["run_id"], safe="") + "/rankings"
    assert request("GET", viewer + "/history/1") == official_week_two

    before_save = request("GET", simulation_scope + "/save/preview")
    assert before_save["has_unsaved_changes"] is True, before_save
    assert before_save["can_save"] is True, before_save
    old_head = before_save["saved_head_revision_id"]
    assert old_head == continuing["saved_week2_revision_preserved"]

    from playwright.sync_api import expect

    # A genuine browser-reviewed Save. No API shortcut or database patch.
    page.goto(run_url + "/simulate?branch=" + quote(initial["branch_id"], safe=""))
    page.get_by_role("combobox", name="Language / Jazyk").select_option("en")
    save = page.get_by_role("button", name="Save authoritative simulation", exact=True)
    expect(save).to_be_enabled(timeout=30000)
    save.click()
    expect(page.get_by_text("Saved as revision", exact=False)).to_be_visible(timeout=30000)
    saved = request("GET", simulation_scope + "/save/preview")
    assert saved["saved_head_revision_id"] != old_head
    assert saved["has_unsaved_changes"] is False
    boundary_saved_head = saved["saved_head_revision_id"]
    # A Save cannot skip the boundary or finish Full Simulation on its own.
    assert request("GET", simulation_scope + "/position")["current_week"] == {
        "season_index": 0, "week": 61
    }
    assert _task(request, simulation_scope, task_id)["state"] == "awaiting_operator"

    preflight = request("GET", simulation_scope + "/season-transition/preflight")
    (artifacts / "season-boundary-reviewed-preflight.json").write_text(
        json.dumps(preflight, indent=2)
    )
    assert preflight["completed_week"] == {"season_index": 0, "week": 61}, preflight
    assert preflight["target_week"] == {"season_index": 1, "week": 1}, preflight
    assert preflight["saved_revision_id"] == boundary_saved_head, preflight
    assert not preflight["final_season"]
    assert preflight["ready_for_execution"], preflight
    assert not preflight["state_blockers"] and not preflight["implementation_gaps"], preflight

    # Human review and confirmation through the actual production component.
    button = page.get_by_role("button", name="Review Season Transition", exact=True)
    expect(button).to_be_enabled(timeout=30000)
    button.click()
    commit = page.get_by_role("button", name="Advance to next season", exact=True)
    expect(commit).to_be_enabled(timeout=30000)
    commit.click()
    expect(page.get_by_text("New Saved Revision", exact=False)).to_be_visible(timeout=30000)

    transition_world = request("GET", simulation_scope + "/position")
    assert transition_world["current_week"] == {"season_index": 1, "week": 1}, transition_world
    transition_saved = request("GET", simulation_scope + "/save/preview")
    season_saved_head = transition_saved["saved_head_revision_id"]
    assert season_saved_head not in (None, old_head, boundary_saved_head)
    after_season_viewer = request("GET", viewer + "/current")
    assert after_season_viewer["season_index"] == 1
    assert after_season_viewer["week"] == 1
    assert request("GET", viewer + "/history/1") == official_week_two
    assert request("GET", simulation_scope + "/match-replays?limit=50") == before_replays

    # Season Transition is operator-authorized. Full Simulation itself still
    # needs an explicit task-center resume, retaining exact frozen task ID.
    waiting = _task(request, simulation_scope, task_id)
    assert waiting["task_id"] == task_id
    assert waiting["parent_command_id"] == parent_id
    assert waiting["state"] == "awaiting_operator", waiting
    operator = page.context.new_page()
    try:
        operator.goto(run_url.rsplit("/admin/runs/", 1)[0] + "/admin/operations")
        operator.get_by_role("combobox", name="Language / Jazyk").select_option("en")
        region = operator.get_by_role("region", name="Server simulation tasks")
        card = region.locator('li[data-task-id="' + task_id + '"]')
        expect(card).to_have_count(1, timeout=30000)
        expect(card).to_contain_text("Waiting for operator")
        expect(region.locator('li[data-task-id="' + initial["task_id"] + '"]')).to_have_count(1)
        card.get_by_label("Task operator", exact=True).fill("Cross-season Full Simulation Admin")
        card.get_by_label("Task audit reason", exact=True).fill(
            "Continue the original nonterminal parent across approved Season Transition"
        )
        card.get_by_role("button", name="Explicitly resume server task").click()
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            after = _task(request, simulation_scope, task_id)
            if after["revision"] > waiting["revision"] and after["state"] in (
                "awaiting_operator", "target_reached", "complete", "failed"
            ):
                break
            time.sleep(.15)
        else:
            raise AssertionError("Cross-season Full Simulation task still active: " + str(after))
        assert after["state"] in ("awaiting_operator", "target_reached", "complete"), after
        assert after["task_id"] == task_id
        assert after["parent_command_id"] == parent_id
        assert after["original_command"] == waiting["original_command"]
        assert after["revision"] > waiting["revision"]
        operator.screenshot(path=str(artifacts / "full-simulation-same-parent-next-season.png"), full_page=True)
    finally:
        operator.close()
    final_world = request("GET", simulation_scope + "/position")["current_week"]
    assert final_world["season_index"] >= 1, final_world
    assert final_world["season_index"] * 61 + final_world["week"] - 1 >= 61
    assert request("GET", simulation_scope + "/match-replays?limit=50") == before_replays
    assert request("GET", viewer + "/history/1") == official_week_two
    assert request("GET", viewer + "/current") == after_season_viewer
    assert request("GET", simulation_scope + "/save/preview")["saved_head_revision_id"] == season_saved_head
    assert _task(request, simulation_scope, initial["task_id"])["state"] == "target_reached"
    evidence = {
        "same_nonterminal_task_id": task_id,
        "same_full_simulation_parent": parent_id,
        "season_zero_boundary": {"season_index": 0, "week": 61},
        "human_saved_week61_revision": boundary_saved_head,
        "approved_season_saved_revision": season_saved_head,
        "approved_new_season_week": {"season_index": 1, "week": 1},
        "task_state_after_explicit_resume": after["state"],
        "task_checkpoint_after_resume": after["checkpoint"],
        "final_world_week": final_world,
        "immutable_full_simulation_command": True,
        "unchanged_original_match_engine_replays": True,
        "unchanged_historical_official_week2": True,
        "no_hidden_saves_or_season_approvals": True,
    }
    (artifacts / "full-simulation-cross-season-same-parent.json").write_text(
        json.dumps(evidence, indent=2)
    )
    return evidence
