"""Fail-closed acceptance contract for advancing past real Saved hybrid Week 2."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def next_week():
    path=Path(__file__).resolve().parents[2]/"scripts"/"real_hybrid_full_simulation_task_browser_checks.py"
    spec=importlib.util.spec_from_file_location("real_hybrid_following_week",path)
    assert spec is not None and spec.loader is not None
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.prove_next_real_hybrid_week_from_restarted_saved_run


@pytest.mark.pr_critical
@pytest.mark.parametrize("wrong",[
    "foreign_task","foreign_parent","still_pending","position_week1",
    "position_week3","viewer_drift","missing_replay","duplicate_replay",
    "saved_head_drift","unsaved_draft","missing_saved_revision",
])
def test_restarted_saved_run_requires_exact_original_terminal_and_immutable_inputs(
    next_week,tmp_path,wrong,
):
    frozen={"task_id":"original-task","parent_command_id":"original-parent",
            "run_id":"run","branch_id":"branch"}
    saved_id="approved-week2"
    terminal={"task_id":"original-task","parent_command_id":"original-parent",
              "state":"target_reached"}
    week={"current_week":{"season_index":0,"week":2}}
    viewer={"week_ordinal":1,"snapshot_fingerprint":"a"*64}
    now=dict(viewer)
    replays={"matches":[{"match_id":"group-one"},{"match_id":"group-two"},{"match_id":"final"}]}
    save={"saved_head_revision_id":saved_id,"has_unsaved_changes":False,"can_save":False}
    if wrong=="foreign_task":terminal["task_id"]="other-task"
    elif wrong=="foreign_parent":terminal["parent_command_id"]="other-parent"
    elif wrong=="still_pending":terminal["state"]="awaiting_operator"
    elif wrong=="position_week1":week["current_week"]["week"]=1
    elif wrong=="position_week3":week["current_week"]["week"]=3
    elif wrong=="viewer_drift":now["week_ordinal"]=0
    elif wrong=="missing_replay":replays["matches"].pop()
    elif wrong=="duplicate_replay":replays["matches"][-1]["match_id"]="group-one"
    elif wrong=="saved_head_drift":save["saved_head_revision_id"]="foreign"
    elif wrong=="unsaved_draft":save["has_unsaved_changes"]=True
    elif wrong=="missing_saved_revision":saved_id=None

    operations=[]
    def request(method,path,body=None,status=200):
        operations.append((method,path))
        assert method=="GET", "Invalid source data must fail before any creation"
        if "/full-simulation/tasks/" in path: return {"tasks":[terminal]}
        if path.endswith("/position"):return week
        if path.endswith("/match-replays?limit=50"):return replays
        if path.endswith("/save/preview"):return save
        if "/viewer/runs/" in path and path.endswith("/rankings/current"):return now
        raise AssertionError("Unexpected read "+path)

    with pytest.raises(AssertionError):
        next_week(request=request,page=None,run_url="http://host/admin/runs/run",
                  simulation_scope="/scope",frozen=frozen,
                  official_week_two=viewer,saved_week_two_revision=saved_id,
                  artifacts=tmp_path)
    assert all(method=="GET" for method,_ in operations)
    assert not (tmp_path/"hybrid-second-week-worker-after-restart.json").exists()
