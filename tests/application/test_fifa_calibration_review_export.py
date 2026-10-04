from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.export_fifa_calibration_review import export_review


def test_fifa_calibration_review_export_is_self_consistent(tmp_path) -> None:
    output = tmp_path / "review"
    summary = export_review(output)

    assert summary["schema_version"] == "fifa_calibration_review_bundle.v1"
    assert summary["rating_ready"] is False
    assert summary["country_count"] == 250
    assert summary["evidence_model_id"] == "fifa-dimension-evidence-v1"

    expected_files = {
        "fifa_dimension_evidence_scores.json",
        "fifa_prototype_signal_audit.json",
        "fifa_dimension_score_prototype_audit.json",
        "summary.json",
    }
    assert {path.name for path in output.iterdir()} == expected_files

    stored_summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert stored_summary == summary

    scores = json.loads(
        (output / "fifa_dimension_evidence_scores.json").read_text(encoding="utf-8")
    )
    score_audit = json.loads(
        (output / "fifa_dimension_score_prototype_audit.json").read_text(
            encoding="utf-8"
        )
    )
    signal_audit = json.loads(
        (output / "fifa_prototype_signal_audit.json").read_text(encoding="utf-8")
    )

    assert scores["rating_ready"] is False
    assert score_audit["rating_ready"] is False
    assert signal_audit["rating_ready"] is False

    assert set(summary["dimension_score_audit"]) == set(score_audit["recipes"])
    assert set(summary["signal_audit"]) == set(signal_audit["comparisons"])
