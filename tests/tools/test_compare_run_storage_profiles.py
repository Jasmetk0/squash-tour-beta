"""Read-only storage comparison uses existing profile v1, not raw SQLite."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

PATH = Path(__file__).resolve().parents[2] / "scripts" / "compare_run_storage_profiles.py"
spec = importlib.util.spec_from_file_location("compare_run_storage_profiles", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def report(revisions=2, *, scope="run1"):
    return {
        "schema_version": "run_storage_profile.v1", "run_id_scope": scope,
        "label": "example", "logical_snapshot_end_utc": "2026-11-01T11:00:00+00:00",
        "physical_sizes": {"db": {"status": "observed", "bytes": 1024},
                           "wal": {"status": "absent", "bytes": None},
                           "shm": {"status": "absent", "bytes": None}},
        "page_metrics": {"scope": "whole_database", "page_size": 1024,
                         "page_count": 1, "freelist_count": 0, "allocated_bytes": 1024,
                         "nonfreelist_page_bytes": 1024, "free_page_bytes": 0},
        "tables": {"branch_saved_revisions": {"status": "observed",
                                               "scope": "selected_run", "row_count": revisions},
                   "full_simulation_tasks": {"status": "unavailable", "reason": "table_absent"}},
        "saved_revision_totals": {"count": revisions, "payload_bytes_sum": revisions * 100,
                                  "change_summary_bytes_sum": 0, "payload_bytes_max": 100},
        "branch_saved_revisions": {"branch1": {"count": revisions,
                                               "payload_bytes_sum": revisions * 100,
                                               "change_summary_bytes_sum": 0,
                                               "payload_bytes_max": 100}},
        "branch_heads": {},
    }


def test_growth_without_inventing_release_gate():
    a, b = report(2), report(5)
    b["physical_sizes"]["db"]["bytes"] = 4096
    b["page_metrics"]["page_count"] = 4
    result = module.compare(a, b)
    assert result["saved_revision_totals"]["count"] == {
        "before": 2, "after": 5, "delta": 3, "percent_change": 150.0}
    assert result["physical_sizes"]["db"]["delta"] == 3072
    assert result["metric_scopes"]["physical.db"] == "whole_database_non_atomic"
    assert result["tables"]["branch_saved_revisions"]["scope"] == "selected_run"
    assert result["common_branch_owner_metrics"]["branch1"]["count"]["delta"] == 3
    assert "pass" not in result and "budget" not in result


def test_zero_baseline_and_shrinking():
    a, b = report(0), report(0)
    a["physical_sizes"]["db"]["bytes"] = 4096
    b["physical_sizes"]["db"]["bytes"] = 1024
    result = module.compare(a, b)
    assert result["saved_revision_totals"]["count"]["percent_change"] is None
    assert result["physical_sizes"]["db"]["delta"] == -3072
    assert result["physical_sizes"]["db"]["percent_change"] == -75.0


def test_no_false_zero_for_missing_wal_and_added_branch():
    a, b = report(1), report(3)
    b["physical_sizes"]["wal"] = {"status": "observed", "bytes": 999}
    b["branch_saved_revisions"]["branch2"] = dict(b["branch_saved_revisions"]["branch1"])
    result = module.compare(a, b)
    assert "wal" not in result["physical_sizes"]
    assert result["branch_inventory"]["added"] == ["branch2"]
    assert "branch2" not in result["common_branch_owner_metrics"]


@pytest.mark.parametrize("mutate", [
    lambda a, b: b.update(run_id_scope="another"),
    lambda a, b: b.update(schema_version="old"),
    lambda a, b: b["page_metrics"].update(scope="selected_run"),
    lambda a, b: b["page_metrics"].update(page_count=-1),
    lambda a, b: b["physical_sizes"]["db"].update(bytes=3.5),
    lambda a, b: b["saved_revision_totals"].update(count=True),
    lambda a, b: b["tables"]["branch_saved_revisions"].update(row_count="2"),
])
def test_bad_or_incompatible_evidence_is_rejected(mutate):
    a, b = report(), report()
    mutate(a, b)
    with pytest.raises(ValueError):
        module.compare(a, b)


def test_unavailable_table_is_not_a_fake_measurement():
    a, b = report(), report()
    b["tables"]["branch_saved_revisions"]["status"] = "unavailable"
    result = module.compare(a, b)
    assert "branch_saved_revisions" not in result["tables"]
    assert any("tables.branch_saved_revisions" in item for item in result["unavailable"])


def test_cli_creates_new_json_without_overwriting_existing(tmp_path):
    before, after, target = (tmp_path / name for name in ("before.json", "after.json", "out.json"))
    before.write_text(json.dumps(report(1)), encoding="utf-8")
    after.write_text(json.dumps(report(2)), encoding="utf-8")
    args = [str(before), str(after), "--output", str(target)]
    assert module.main(args) == 0
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["saved_revision_totals"]["count"]["delta"] == 1
    assert module.main(args) == 1
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_cli_rejects_nonfinite_input_json(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text(json.dumps(report()), encoding="utf-8")
    b.write_text(json.dumps(report()).replace("1024", "NaN", 1), encoding="utf-8")
    assert module.main([str(a), str(b)]) == 1
