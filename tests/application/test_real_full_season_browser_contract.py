"""Negative PR-critical guards on authentic Season-0 Week-61 rollover."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def transition():
    path = Path(__file__).resolve().parents[2] / "scripts" / "real_full_simulation_season_boundary_browser_checks.py"
    spec = importlib.util.spec_from_file_location("real_full_season_browser", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.approve_and_resume_same_full_parent_across_season


@pytest.mark.pr_critical
@pytest.mark.parametrize("invalid", [
    "first_nonterminal", "first_foreign_parent", "wrong_task_id",
    "wrong_parent_id", "changed_command", "wrong_task_state",
    "wrong_checkpoint", "wrong_task_week", "different_run_position",
    "missing_real_match", "duplicate_real_match", "saved_head_changed",
    "unsaved_changes_missing", "save_not_allowed", "week_two_history_changed",
])
def test_rollover_rejects_stale_original_full_task_or_sport_before_save(
    transition, tmp_path, invalid,
):
    original = {"task_id":"first","parent_command_id":"first-parent",
                "run_id":"run","branch_id":"branch"}
    second = {"second_full_simulation_task":"second",
              "second_parent":"second-parent",
              "start_week":{"season_index":0,"week":2},
              "saved_week2_revision_preserved":"saved2"}
    recovered = {"task_id_after_restart":"second","continued_parent":"second-parent"}
    parent = {"task_id":"second","parent_command_id":"second-parent",
              "original_command":{"command_id":"second-parent"},
              "state":"awaiting_operator",
              "checkpoint":"season_transition_save_required",
              "current_week":{"season_index":0,"week":61}}
    first = {"state":"target_reached","parent_command_id":"first-parent"}
    position = {"current_week":{"season_index":0,"week":61}}
    matches = {"matches":[{"match_id":"g1"},{"match_id":"g2"},{"match_id":"final"}]}
    saved = {"has_unsaved_changes":True,"can_save":True,
             "saved_head_revision_id":"saved2"}
    history = {"week_ordinal":1}
    expected = dict(history)
    if invalid=="first_nonterminal": first["state"]="awaiting_operator"
    elif invalid=="first_foreign_parent": first["parent_command_id"]="other"
    elif invalid=="wrong_task_id": parent["task_id"]="other"
    elif invalid=="wrong_parent_id": parent["parent_command_id"]="other"
    elif invalid=="changed_command": parent["original_command"]["command_id"]="other"
    elif invalid=="wrong_task_state": parent["state"]="failed"
    elif invalid=="wrong_checkpoint": parent["checkpoint"]="week_preparation_required"
    elif invalid=="wrong_task_week": parent["current_week"]["week"]=60
    elif invalid=="different_run_position": position["current_week"]["week"]=60
    elif invalid=="missing_real_match": matches["matches"].pop()
    elif invalid=="duplicate_real_match": matches["matches"][-1]["match_id"]="g1"
    elif invalid=="saved_head_changed": saved["saved_head_revision_id"]="other"
    elif invalid=="unsaved_changes_missing": saved["has_unsaved_changes"]=False
    elif invalid=="save_not_allowed": saved["can_save"]=False
    elif invalid=="week_two_history_changed": history["week_ordinal"]=2

    calls=[]
    def request(method,path,body=None,status=200):
        calls.append((method,path))
        assert method=="GET", "Invalid input must never reach a mutation"
        if path.endswith("/full-simulation/tasks/first"): return {"tasks":[first]}
        if path.endswith("/full-simulation/tasks/second"): return {"tasks":[parent]}
        if path.endswith("/position"): return position
        if path.endswith("/match-replays?limit=50"): return matches
        if path.endswith("/save/preview"): return saved
        if path.endswith("/rankings/history/1"): return history
        raise AssertionError("Unexpected request: "+path)

    with pytest.raises(AssertionError):
        transition(request=request,page=None,run_url="http://host/admin/runs/run",
                   simulation_scope="/scope",initial=original,continuing=second,
                   restored=recovered,official_week_two=expected,artifacts=tmp_path)
    assert calls and all(method=="GET" for method,_ in calls)
    assert not (tmp_path/"full-simulation-cross-season-same-parent.json").exists()
