"""Fail-closed contract for real hybrid original-task Week Transition acceptance."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def advance():
    path=Path(__file__).resolve().parents[2]/"scripts"/"real_hybrid_full_simulation_task_browser_checks.py"
    spec=importlib.util.spec_from_file_location("hybrid_worker_browser",path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.resume_original_full_simulation_to_advance_real_hybrid_week


@pytest.mark.pr_critical
@pytest.mark.parametrize("alter",[
    "foreign_task","foreign_parent","failed_task","wrong_checkpoint",
    "stale_revision","unready_group","already_transitioned",
    "incomplete_replays","duplicate_replays","missing_saved_head",
])
def test_original_worker_refuses_unreviewed_hybrid_without_any_mutation(
    advance,tmp_path,alter
):
    frozen={
        "task_id":"original-task","parent_command_id":"original-parent",
        "run_id":"run","branch_id":"branch","revision":3,
        "checkpoint":"group_phase_review_required",
    }
    task={
        "task_id":frozen["task_id"],"parent_command_id":frozen["parent_command_id"],
        "state":"awaiting_operator","checkpoint":frozen["checkpoint"],
        "revision":frozen["revision"],
    }
    position={"current_week":{"season_index":0,"week":1},"week_ready_for_transition":True}
    replays=[{"match_id":x} for x in ("group-one","group-two","knockout-final")]
    save={"saved_head_revision_id":"saved-hybrid-group"}
    if alter=="foreign_task":task["task_id"]="somebody-else"
    elif alter=="foreign_parent":task["parent_command_id"]="somebody-else"
    elif alter=="failed_task":task["state"]="failed"
    elif alter=="wrong_checkpoint":task["checkpoint"]="entry_process_required"
    elif alter=="stale_revision":task["revision"]=4
    elif alter=="unready_group":position["week_ready_for_transition"]=False
    elif alter=="already_transitioned":position["current_week"]={"season_index":0,"week":2}
    elif alter=="incomplete_replays":replays.pop()
    elif alter=="duplicate_replays":replays[2]["match_id"]=replays[0]["match_id"]
    elif alter=="missing_saved_head":save["saved_head_revision_id"]=None
    seen=[]

    def request(method,path,body=None,status=200):
        seen.append((method,path))
        assert method=="GET","Invalid or stale input must never trigger target/resume mutations"
        if "/full-simulation/tasks/" in path:return {"tasks":[task]}
        if path.endswith("/position"):return position
        if path.endswith("/match-replays?limit=50"):return {"matches":replays}
        if path.endswith("/save/preview"):return save
        raise AssertionError("Unrecognized request "+path)

    with pytest.raises(AssertionError):
        advance(
            request=request,page=None,run_url="http://test/admin/runs/run",
            simulation_scope="/scope",frozen=frozen,artifacts=tmp_path,
            expected_ranking_fingerprint="f"*64,
            before_ranking={"week_ordinal":0},before_history={"publication_count":1},
        )
    assert seen and all(method=="GET" for method,_ in seen)
    assert not (tmp_path/"hybrid-worker-week-transition-proof.json").exists()
