"""Paired scientific observations; these are NOT pre-alpha realism thresholds."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "validate_match_seed_blocks.py"
SPEC = importlib.util.spec_from_file_location("validate_match_seed_blocks", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def synthetic_rows(blocks=1, root_seed=42):
    """One complete factorial without running the engine; for arithmetic guards."""
    rows = []
    for i in range(blocks):
        for seat in audit.SEATS:
            for arm in audit.ARMS:
                rows.append({
                    "block": i, "seat": seat, "arm": arm,
                    "match_id": f"paired-validation-v1:{i}:{seat}",
                    "seed": audit._seed(root_seed, i, seat),
                    "player_a": "X" if seat == "x_left" else "Y",
                    "winner": "Y" if arm == "y_stronger" else "X",
                    "sets": 3, "rallies": 70 if arm == "equal" else 60,
                    "duration_seconds": 2100 if arm == "equal" else 1800,
                    "result_sha256": f"hash:{i}:{seat}:{arm}",
                    "rally_log_hash": f"rally:{i}:{seat}:{arm}",
                })
    return rows


def test_experiment_has_stable_identity_and_matched_seed_across_arms():
    for seat in audit.SEATS:
        contexts = [audit._context(1, seat, arm) for arm in audit.ARMS]
        assert len({x.match_id for x in contexts}) == 1
        assert [x.player_a.player.player_id for x in contexts] == [
            "X" if seat == "x_left" else "Y"
        ] * 3
        assert audit._seed(42, 1, seat) == audit._seed(42, 1, seat)
        assert audit._seed(42, 1, seat) != audit._seed(42, 2, seat)
        assert audit._seed(42, 1, "x_left") != audit._seed(42, 1, "y_left")
    assert audit._context(1, "x_left", "x_stronger").player_a.player.technique == 90
    assert audit._context(1, "x_left", "y_stronger").player_a.player.technique == 84


def test_complete_paired_summary_uses_matched_differences_and_seat_split():
    rows = synthetic_rows(blocks=3)
    summary = audit.summarize(rows, blocks=3, root_seed=42)
    assert summary["arms"]["equal"]["matches"] == 6
    assert summary["arms"]["equal"]["x_win_fraction"] == 1
    assert summary["arms"]["y_stronger"]["x_win_fraction"] == 0
    contrast = summary["paired_contrasts"]["y_stronger_minus_equal"]
    assert contrast == {
        "matched_pairs": 6, "mean_x_win_change": -1,
        "mean_duration_seconds_change": -300,
        "mean_rallies_change": -10,
        "x_loses_to_wins": 0, "x_wins_to_loses": 6,
    }
    assert summary["paired_contrasts"]["x_stronger_minus_equal"]["mean_x_win_change"] == 0
    assert summary["arms"]["equal"]["x_win_fraction_by_orientation"] == {
        "x_left": 1, "y_left": 1
    }


@pytest.mark.parametrize("modify", [
    lambda rows: rows.pop(),
    lambda rows: rows.append(dict(rows[0])),
    lambda rows: rows[0].update(seat="foreign"),
    lambda rows: rows[0].update(seed=1234),
    lambda rows: rows[0].update(match_id="other"),
    lambda rows: rows[0].update(player_a="Y"),
    lambda rows: rows[0].update(arm="unknown"),
    lambda rows: rows[0].update(winner="Z"),
    lambda rows: rows[0].update(duration_seconds=float("nan")),
    lambda rows: rows[0].update(rallies=-1),
    lambda rows: rows[0].update(sets=6),
    lambda rows: rows[0].update(result_sha256=""),
])
def test_missing_duplicate_foreign_or_corrupt_cells_fail_closed(modify):
    rows = synthetic_rows()
    modify(rows)
    with pytest.raises(ValueError):
        audit.summarize(rows, blocks=1, root_seed=42)


@pytest.mark.parametrize("blocks,seed", [(0, 42), (501, 42), (True, 42),
                                           (1, -1), (1, 2**63), (1, True)])
def test_invalid_run_configuration_is_rejected(blocks, seed):
    with pytest.raises(ValueError):
        audit.collect(blocks=blocks, root_seed=seed)


def test_canonical_observation_digest_ignores_dict_key_order_only():
    a = [{"a": 1, "b": 2}]
    b = [{"b": 2, "a": 1}]
    assert audit._digest(a) == audit._digest(b)
    assert audit._digest(a) != audit._digest([{"a": 1, "b": 3}])
    assert len(audit._digest(a)) == 64
    with pytest.raises(ValueError):
        audit._digest({"nan": math.nan})


def test_replay_or_order_drift_is_a_hard_error(monkeypatch):
    counter = [0]
    def drifting(block, seat, arm, root_seed):
        counter[0] += 1
        row = next(r for r in synthetic_rows(root_seed=root_seed)
                   if (r["block"], r["seat"], r["arm"]) == (block, seat, arm))
        if counter[0] > 6:
            row["result_sha256"] = "changed"
        return row
    monkeypatch.setattr(audit, "_simulate_cell", drifting)
    with pytest.raises(ValueError, match="Replay/order mismatch"):
        audit.collect(blocks=1, root_seed=42)


def test_real_engine_replays_six_cells_in_opposite_execution_order():
    # Actual domain MatchEngine and seeded RNG; NO mocked simulation here.
    report = audit.collect(blocks=1, root_seed=314159)
    rows = report["observations"]
    assert report["replay_checked"] is True
    assert report["replay_mismatches"] == 0
    assert len(rows) == 6
    assert {r["winner"] for r in rows} <= {"X", "Y"}
    assert all(r["rallies"] > 0 and r["duration_seconds"] > 0 for r in rows)
    assert report["observations_sha256"] == audit._digest(rows)
    assert report["summary"]["arms"]["equal"]["matches"] == 2


def test_cli_report_exclusive_output_no_rewrite(monkeypatch, tmp_path):
    mock_report = {"schema_version": audit.SCHEMA, "blocks": 1}
    monkeypatch.setattr(audit, "collect", lambda **_: mock_report)
    target = tmp_path / "report.json"
    assert audit.main(["--output", str(target), "--blocks", "1"]) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == mock_report
    assert audit.main(["--output", str(target), "--blocks", "1"]) == 1
    assert json.loads(target.read_text(encoding="utf-8")) == mock_report


def test_cli_fails_without_ever_publishing_bad_measurement(monkeypatch, tmp_path):
    def fail(**kwargs):
        raise ValueError("replay drift")
    monkeypatch.setattr(audit, "collect", fail)
    target = tmp_path / "report.json"
    assert audit.main(["--output", str(target)]) == 1
    assert not target.exists()


def test_report_do_not_claim_empirical_sporting_calibration(monkeypatch):
    monkeypatch.setattr(audit, "_simulate_cell", lambda block, seat, arm, root_seed:
                        next(r for r in synthetic_rows(root_seed=root_seed)
                             if (r["block"], r["seat"], r["arm"]) == (block, seat, arm)))
    report = audit.collect(blocks=1, root_seed=42)
    assert "performance_gate" not in report
    assert "calibrated" not in report
    assert report["root_seed"] == 42
    assert any("not" in x.lower() for x in report["limitations"])
