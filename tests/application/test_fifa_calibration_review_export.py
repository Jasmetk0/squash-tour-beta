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
    assert summary["evidence_model_id"] == "fifa-dimension-evidence-v2"

    expected_files = {
        "fifa_dimension_evidence_scores.json",
        "fifa_prototype_signal_audit.json",
        "fifa_dimension_score_prototype_audit.json",
        "fifa_dimension_evidence_v2_review.json",
        "fifa_structural_features.json",
        "fifa_structural_heldout_audit.json",
        "fifa_structural_feature_hypothesis_audit.json",
        "fifa_competition_outcome_validation.json",
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

    v2_review = json.loads(
        (output / "fifa_dimension_evidence_v2_review.json").read_text(
            encoding="utf-8"
        )
    )
    structural_features = json.loads(
        (output / "fifa_structural_features.json").read_text(encoding="utf-8")
    )
    heldout_audit = json.loads(
        (output / "fifa_structural_heldout_audit.json").read_text(encoding="utf-8")
    )
    hypothesis_audit = json.loads(
        (output / "fifa_structural_feature_hypothesis_audit.json").read_text(
            encoding="utf-8"
        )
    )
    competition_outcome_audit = json.loads(
        (output / "fifa_competition_outcome_validation.json").read_text(
            encoding="utf-8"
        )
    )

    assert scores["rating_ready"] is False
    assert score_audit["rating_ready"] is False
    assert signal_audit["rating_ready"] is False
    assert v2_review["rating_ready"] is False
    assert structural_features["rating_ready"] is False
    assert heldout_audit["rating_ready"] is False
    assert hypothesis_audit["rating_ready"] is False
    assert competition_outcome_audit["rating_ready"] is False
    assert competition_outcome_audit["fit_allowed"] is False

    assert set(summary["dimension_score_audit"]) == set(score_audit["recipes"])
    assert set(summary["signal_audit"]) == set(signal_audit["comparisons"])
    assert summary["dimension_v2_review"]["review_pass"] is True
    assert summary["structural_features"]["validation_role_counts"] == {
        "review": 9,
        "held_out_validation": 4,
        "none": 237,
    }
    assert summary["structural_heldout_audit"]["heldout_country_codes"] == [
        "BRA", "DEU", "ISL", "SMR"
    ]
    assert all(
        value["decision"] == "rejected_as_single_factor_transfer"
        for value in summary["structural_hypothesis_audit"].values()
    )

    assert summary["competition_outcome_audit"] == {
        role: {
            "ranking_outcome_count": value["ranking_outcome_count"],
            "numeric_comparison_count": value["numeric_comparison_count"],
            "spearman_score_vs_better_rank": value["spearman_score_vs_better_rank"],
            "pairwise": value["pairwise"],
            "missing_competition_score_country_codes": value[
                "missing_competition_score_country_codes"
            ],
        }
        for role, value in competition_outcome_audit["groups"].items()
    }
