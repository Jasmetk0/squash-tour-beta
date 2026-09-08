"""Audit instrumentation tests, not empirical realism acceptance thresholds."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

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
    assert first["traced_rallies"] == first["rallies"]
    assert (
        sum(first[f"closure_{name}"] for name in audit.CLOSURE_NAMES)
        == first["rallies"]
    )
    assert first["estimated_shots"] >= first["rallies"]
    assert sum(
        first[f"{phase}_seconds"] for phase in ("opening", "control", "terminal")
    ) == pytest.approx(first["rally_seconds"], abs=0.01)


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
        assert summary["rally_diagnostics"]["trace_coverage"] == 1


def test_wilson_interval_at_equal_and_extreme_win_rates():
    low, high = audit.wilson(250, 500)
    assert 0.45 < low < 0.5 < high < 0.55
    low, high = audit.wilson(0, 500)
    assert abs(low) < 1e-10
    assert 0 < high < 0.01


def trace_rally(closure, shots, seconds, segments=()):
    return SimpleNamespace(
        control_trace=SimpleNamespace(
            closure_reason=SimpleNamespace(value=closure),
            estimated_shot_count=shots,
            opening_elapsed_seconds=seconds,
            terminal_elapsed_seconds=0,
            segments=segments,
        )
    )


def test_closures_missing_traces_and_weighted_pace():
    def segment(shots, seconds):
        return SimpleNamespace(
            phase_pace=SimpleNamespace(value="FAST"),
            estimated_shot_count=shots,
            elapsed_seconds=seconds,
        )

    rallies = [
        trace_rally("OPENING_TERMINAL", 1, 1),
        trace_rally("HARD_SEGMENT_CAP", 6, 2, (segment(1, 1), segment(3, 6))),
        SimpleNamespace(control_trace=None),
    ]
    metrics = audit.rally_diagnostics(rallies)
    result = audit.summarize_diagnostics([{**metrics, "rallies": 3}])
    assert result["trace_coverage"] == 2 / 3
    assert result["mean_estimated_shots"] == 3.5
    assert result["closure_fractions"]["HARD_SEGMENT_CAP"] == 0.5
    assert result["closure_fractions"]["NATURAL_TERMINAL"] == 0
    assert result["pace"]["FAST"]["seconds_per_estimated_shot"] == 7 / 4
    assert result["pace"]["PATIENT"]["seconds_per_estimated_shot"] is None


def test_missing_traces_are_unavailable_not_zero():
    metrics = audit.rally_diagnostics([SimpleNamespace(control_trace=None)])
    result = audit.summarize_diagnostics([{**metrics, "rallies": 1}])
    assert result["trace_coverage"] == 0
    assert result["mean_estimated_shots"] is None
    assert all(value is None for value in result["closure_fractions"].values())


def test_cli_refuses_to_overwrite_existing_evidence(tmp_path, monkeypatch):
    marker = tmp_path / "matches.csv"
    marker.write_text("preserve me")
    monkeypatch.setattr("sys.argv", [str(SCRIPT), "--output", str(tmp_path)])
    with pytest.raises(FileExistsError):
        audit.main()
    assert marker.read_text() == "preserve me"
