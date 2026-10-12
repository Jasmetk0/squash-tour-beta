"""Cheap contract and pure invariant regression for real Week-2 browser acceptance.

Extract the actual pure comparator without importing Playwright (which is
installed only in the dedicated production-browser workflow).
"""
import ast
from copy import deepcopy
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "admin_week2_integrity_browser.py"
WORKFLOW = ROOT / ".github" / "workflows" / "prealpha-week2-ranking-integrity-browser.yml"


def _pure_comparator():
    source = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    functions = [node for node in source.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"player_ids", "verify_transition"}]
    assert len(functions) == 2
    ns = {}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(SCRIPT), "exec"), ns)
    return ns["verify_transition"]


def _fixture():
    ids = [f"P-2000-BOG-{i:04d}" for i in range(1, 65)]
    profiles = [{"player_id": pid} for pid in ids]
    source = "a" * 64
    def projection(week):
        return {
            "fingerprint": f"{week + 1}" * 64,
            "state": {
                "week": {"season_index": 0, "week": week + 1},
                "source_initial_world_fingerprint": source,
                "predecessor_fingerprint": None if week == 0 else "1" * 64,
                "players": deepcopy(profiles),
            },
        }
    projections = {
        name: {0: projection(0), 1: projection(1)} for name in (
            "player_lifecycle_week_states", "player_sporting_week_states",
            "player_health_week_states",
        )
    }
    revision1 = {
        "revision_id": "saved-initial-rank", "parent_revision_id": "predecessor",
        "content_hash": "9" * 64, "payload_json": "old bytes",
    }
    revision2 = {
        "revision_id": "saved-week2", "parent_revision_id": "saved-initial-rank",
        "content_hash": "8" * 64, "payload_json": "new bytes",
    }
    before = {
        "run_id": "run", "branch_id": "branch",
        "initial_world_fingerprint": source, "initial_world_raw": "immutable",
        "players": profiles, "revisions": [revision1],
        "published": {0: {"payload_json": "initial-rank", "snapshot_fingerprint": source}},
        "candidates": {0: {"payload_json": "candidate", "fingerprint": source}},
        "clock": [{"current_ordinal": 0, "ranking_fingerprint": source}],
        "projections": {key: {0: value[0]} for key, value in projections.items()},
    }
    after = deepcopy(before)
    after["revisions"] = [deepcopy(revision1), deepcopy(revision2)]
    after["published"][1] = {"payload_json": "week2 rank", "snapshot_fingerprint": "3" * 64}
    after["clock"][0]["current_ordinal"] = 1
    after["clock"][0]["ranking_fingerprint"] = "3" * 64
    after["projections"] = deepcopy(projections)
    return before, after


def test_week2_comparator_accepts_64_identical_historical_ids_and_new_revision():
    before, after = _fixture()
    result = _pure_comparator()(before, after)
    assert result["initial_players"] == 64
    assert result["week2_ranking_published"]
    assert result["preserved_initial_saved_revision_count"] == 1
    assert set(result["week2_roster_sizes"].values()) == {64}


@pytest.mark.parametrize("corruption", (
    "changed_old_revision", "changed_original_ranking",
    "invented_player", "lost_health", "wrong_predecessor",
    "no_week2_ranking", "missing_week2_save", "wrong_clock",
))
def test_week2_comparator_rejects_stale_or_damaged_historical_authority(corruption):
    before, after = _fixture()
    if corruption == "changed_old_revision":
        after["revisions"][0]["content_hash"] = "f" * 64
    elif corruption == "changed_original_ranking":
        after["published"][0]["payload_json"] = "tampered"
    elif corruption == "invented_player":
        after["projections"]["player_lifecycle_week_states"][1]["state"]["players"][-1] = {
            "player_id": "Z-foreign"
        }
    elif corruption == "lost_health":
        after["projections"]["player_health_week_states"][1]["state"]["players"].pop()
    elif corruption == "wrong_predecessor":
        after["projections"]["player_sporting_week_states"][1]["state"]["predecessor_fingerprint"] = None
    elif corruption == "no_week2_ranking":
        del after["published"][1]
    elif corruption == "missing_week2_save":
        after["revisions"].pop()
    else:
        after["clock"][0]["current_ordinal"] = 0
    with pytest.raises(AssertionError):
        _pure_comparator()(before, after)


@pytest.mark.parametrize("table", (
    "player_lifecycle_week_states",
    "player_sporting_week_states",
    "player_health_week_states",
))
def test_week2_rejects_nonempty_incorrect_predecessor_per_projection(table):
    before, after = _fixture()
    after["projections"][table][1]["state"]["predecessor_fingerprint"] = "f" * 64
    with pytest.raises(AssertionError):
        _pure_comparator()(before, after)


@pytest.mark.parametrize("week", (0, 1))
def test_week2_rejects_world_clock_ranking_mismatch(week):
    before, after = _fixture()
    target = before if week == 0 else after
    target["clock"][0]["ranking_fingerprint"] = "f" * 64
    with pytest.raises(AssertionError):
        _pure_comparator()(before, after)


def test_real_browser_workflow_runs_only_for_its_specific_scenario():
    source = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for token in (
        "setup_run(", "finish_tournament(", "verify_viewer(",
        "inspect_sqlite(", "verify_transition(", "before-restart.zip",
        "same_sqlite_bytes_after_restart",
    ):
        assert token in source
    assert "workflow_dispatch:" in workflow
    assert "scripts/admin_week2_integrity_browser.py" in workflow
    assert "if: always()" in workflow
    assert "retention-days: 14" in workflow
