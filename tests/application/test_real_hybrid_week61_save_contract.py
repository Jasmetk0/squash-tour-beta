"""PR-critical fail-closed inputs for actual Week-61 operator Save journey."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def perform():
    scripts=Path(__file__).resolve().parents[2]/"scripts"
    sys.path.insert(0,str(scripts))
    spec=importlib.util.spec_from_file_location(
        "week61_browser_contract", scripts/"real_hybrid_season_boundary_browser_checks.py"
    )
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.approve_real_week61_save_and_resume_same_full_task


@pytest.mark.pr_critical
@pytest.mark.parametrize("fault",[
    "wrong_previous_checkpoint","wrong_previous_week","bad_second_task",
    "wrong_parent","failed_task","bad_checkpoint","terminal_first_lost",
    "wrong_week","wrong_saved_head","no_unsaved_changes",
    "save_blocked","duplicate_matches","missing_matches","viewer_changed",
])
def test_refuse_fake_week61_boundary_before_any_writes(perform,tmp_path,fault):
    first={"task_id":"old","parent_command_id":"old-parent",
           "run_id":"run","branch_id":"branch"}
    second={"second_full_simulation_task":"later",
            "second_parent":"later-parent",
            "second_task_checkpoint":"season_transition_save_required",
            "saved_week2_revision_preserved":"saved-week2"}
    previous={"checkpoint_after":"season_transition_save_required",
              "week_after":{"season_index":0,"week":61}}
    first_task={"task_id":"old","parent_command_id":"old-parent","state":"target_reached"}
    continuing={"task_id":"later","parent_command_id":"later-parent",
                "state":"awaiting_operator","checkpoint":"season_transition_save_required",
                "original_command":{"command_id":"later-parent"}}
    position={"current_week":{"season_index":0,"week":61}}
    save={"saved_head_revision_id":"saved-week2",
          "has_unsaved_changes":True,"can_save":True}
    matches={"matches":[{"match_id":key} for key in ("a","b","c")]}
    viewer={"week_ordinal":1}
    current=dict(viewer)
    if fault=="wrong_previous_checkpoint":previous["checkpoint_after"]="foreign"
    elif fault=="wrong_previous_week":previous["week_after"]["week"]=60
    elif fault=="bad_second_task":continuing["task_id"]="foreign"
    elif fault=="wrong_parent":continuing["parent_command_id"]="foreign"
    elif fault=="failed_task":continuing["state"]="failed"
    elif fault=="bad_checkpoint":continuing["checkpoint"]="season_transition_prerequisite"
    elif fault=="terminal_first_lost":first_task["state"]="awaiting_operator"
    elif fault=="wrong_week":position["current_week"]["week"]=60
    elif fault=="wrong_saved_head":save["saved_head_revision_id"]="foreign"
    elif fault=="no_unsaved_changes":save["has_unsaved_changes"]=False
    elif fault=="save_blocked":save["can_save"]=False
    elif fault=="duplicate_matches":matches["matches"][-1]["match_id"]="a"
    elif fault=="missing_matches":matches["matches"].pop()
    elif fault=="viewer_changed":current["week_ordinal"]=60

    calls=[]
    def request(method,path,body=None,status=200):
        calls.append((method,path))
        assert method=="GET","Never perform Save or Task Center action on invalid frozen evidence"
        if path.endswith("/full-simulation/tasks/old"):return {"tasks":[first_task]}
        if path.endswith("/full-simulation/tasks/later"):return {"tasks":[continuing]}
        if path.endswith("/position"):return position
        if path.endswith("/save/preview"):return save
        if path.endswith("/match-replays?limit=50"):return matches
        if path.endswith("/rankings/current"):return current
        if path.endswith("/rankings/history/1") or path.endswith("/rankings/history/0"):return {}
        raise AssertionError("unexpected request "+path)

    with pytest.raises(AssertionError):
        perform(
            request=request,page=None,run_url="http://example/admin/runs/run",
            simulation_scope="/scope",initial_parent=first,continuing=second,
            same_task_resume=previous,official_week_two=viewer,artifacts=tmp_path,
        )
    assert all(method=="GET" for method,_ in calls)
    assert not (tmp_path/"hybrid-saved-week61-boundary-proof.json").exists()
