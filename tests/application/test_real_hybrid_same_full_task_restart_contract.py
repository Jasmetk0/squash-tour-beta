"""Critical fail-closed coverage for durable same Full Simulation task resume."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

@pytest.fixture
def checker():
    file=Path(__file__).resolve().parents[2]/"scripts"/"real_hybrid_full_simulation_task_browser_checks.py"
    spec=importlib.util.spec_from_file_location("same_parent_restart",file)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.prove_same_full_task_survives_second_restart

@pytest.mark.pr_critical
@pytest.mark.parametrize("invalid",[
    "first_not_terminal","first_wrong_parent","second_wrong_task",
    "second_wrong_parent","second_wrong_command","second_failed",
    "second_wrong_checkpoint","second_wrong_week","duplicate_match",
    "missing_match","saved_head_changed","viewer_changed",
])
def test_second_parent_requires_exact_original_saved_sport_and_checkpoint(
    checker,tmp_path,invalid
):
    first={"task_id":"t1","parent_command_id":"p1","run_id":"run"}
    continuing={
        "second_full_simulation_task":"t2","second_parent":"p2",
        "start_week":{"season_index":0,"week":2},
        "observed_week":{"season_index":0,"week":3},
        "second_task_state":"awaiting_operator","second_task_checkpoint":"week_preparation_required",
        "saved_week2_revision_preserved":"saved2",
    }
    terminal={"state":"target_reached","parent_command_id":"p1"}
    second={"task_id":"t2","parent_command_id":"p2",
            "original_command":{"command_id":"p2"},
            "state":"awaiting_operator","checkpoint":"week_preparation_required",
            "revision":7,"current_week":{"season_index":0,"week":3}}
    position={"current_week":{"season_index":0,"week":3}}
    replays={"matches":[{"match_id":x} for x in ("group1","group2","final")]}
    saved={"saved_head_revision_id":"saved2"}
    public={"week_ordinal":1}
    changed=dict(public)
    if invalid=="first_not_terminal":terminal["state"]="awaiting_operator"
    elif invalid=="first_wrong_parent":terminal["parent_command_id"]="foreign"
    elif invalid=="second_wrong_task":second["task_id"]="foreign"
    elif invalid=="second_wrong_parent":second["parent_command_id"]="foreign"
    elif invalid=="second_wrong_command":second["original_command"]["command_id"]="foreign"
    elif invalid=="second_failed":second["state"]="failed"
    elif invalid=="second_wrong_checkpoint":second["checkpoint"]="foreign"
    elif invalid=="second_wrong_week":second["current_week"]["week"]=4
    elif invalid=="duplicate_match":replays["matches"][-1]["match_id"]="group1"
    elif invalid=="missing_match":replays["matches"].pop()
    elif invalid=="saved_head_changed":saved["saved_head_revision_id"]="foreign"
    elif invalid=="viewer_changed":changed["week_ordinal"]=2

    operations=[]
    def request(method,path,body=None,status=200):
        operations.append((method,path))
        assert method=="GET","Never resume an untrusted task"
        if path.endswith("/full-simulation/tasks/t1"):return {"tasks":[terminal]}
        if path.endswith("/full-simulation/tasks/t2"):return {"tasks":[second]}
        if path.endswith("/position"):return position
        if path.endswith("/match-replays?limit=50"):return replays
        if path.endswith("/save/preview"):return saved
        if path.endswith("/rankings/current"):return changed
        raise AssertionError("unknown read "+path)
    with pytest.raises(AssertionError):
        checker(request=request,page=None,run_url="http://server/admin/runs/run",
                simulation_scope="/scope",initial_parent=first,continuing=continuing,
                official_week_two=public,artifacts=tmp_path)
    assert all(method=="GET" for method,_ in operations)
    assert not (tmp_path/"same-parent-after-second-sqlite-restart.json").exists()
