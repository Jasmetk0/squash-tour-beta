"""Audit instrumentation tests, not empirical realism acceptance thresholds."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_match_realism.py"
spec = importlib.util.spec_from_file_location("audit_match_realism", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_single_match_audit_metrics_and_deterministic_hash():
    task = (audit.SCENARIOS[0], 0, 20260908)
    first = audit.run_match(task)
    second = audit.run_match(task)
    first.pop("runtime_seconds")
    second.pop("runtime_seconds")
    assert first == second
    assert 3 <= first["games"] <= 5
    assert first["intervals"] > 0
    assert first["interval_seconds"] > 0
    assert first["minutes"] * 60 > first["rally_seconds"]
    assert first["under_10"] + first["over_21"] <= first["rallies"]
    assert first["server_points"] <= first["scored_rallies"] <= first["rallies"]


def test_scenario_summary_preserves_sample_counts_and_rates():
    rows = [audit.run_match((scenario, 0, 20260908)) for scenario in audit.SCENARIOS]
    summaries = audit.summarize(rows)
    assert len(summaries) == 6
    for row in rows:
        summary = summaries[row["scenario"]]
        assert summary["matches"] == 1
        assert summary["a_win_rate"] == row["a_won"]
        assert summary["rallies"] == row["rallies"]
        assert sum(summary["game_counts"].values()) == 1
        assert summary["mean_minutes"] == row["minutes"]


def test_wilson_interval_at_equal_and_extreme_win_rates():
    low, high = audit.wilson(250, 500)
    assert 0.45 < low < 0.5 < high < 0.55
    low, high = audit.wilson(0, 500)
    assert abs(low) < 1e-10
    assert 0 < high < 0.01
