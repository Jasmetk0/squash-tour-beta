from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.review_fifa_dimension_evidence_v2 import build_review


def test_v2_review_reproduces_measured_v1_to_v2_improvement() -> None:
    review = build_review()

    assert review["schema_version"] == "fifa_dimension_evidence_v2_review.v1"
    assert review["baseline_model_id"] == "fifa-dimension-evidence-v1"
    assert review["candidate_model_id"] == "fifa-dimension-evidence-v2"
    assert review["rating_ready"] is False
    assert review["policy_checks_pass"] is True
    assert review["regression_checks_pass"] is True
    assert review["review_pass"] is True

    assert review["measured_improvement"] == {
        "competition_quality_mean_absolute_delta": 2.083,
        "elite_support_mean_absolute_delta": 1.934,
    }


def test_v2_competition_recipe_is_review_passed_but_not_authoring_approved() -> None:
    review = build_review()
    competition = review["recipes"]["competition_quality@2023"]

    assert competition["decision"] == "quantitative_review_passed"
    assert competition["policy_checks_pass"] is True
    assert competition["canonical_authoring_allowed"] is False

    assert competition["v1_metrics"]["mean_absolute_delta"] == 2.683
    assert competition["v2_metrics"]["mean_absolute_delta"] == 0.6
    assert competition["v2_metrics"]["mean_signed_delta"] == -0.567
    assert competition["v2_metrics"]["maximum_absolute_delta"] == 1.9
    assert competition["v2_metrics"]["review_count"] == 1
    assert competition["v2_metrics"]["review_country_codes"] == ["ZAF"]


def test_v2_elite_support_stays_context_blocked_despite_large_improvement() -> None:
    review = build_review()
    elite = review["recipes"]["elite_support@2023"]

    assert elite["decision"] == "context_required"
    assert elite["policy_checks_pass"] is True
    assert elite["canonical_authoring_allowed"] is False

    assert elite["v1_metrics"]["mean_absolute_delta"] == 2.917
    assert elite["v2_metrics"]["mean_absolute_delta"] == 0.983
    assert elite["v2_metrics"]["mean_signed_delta"] == -0.983
    assert elite["v2_metrics"]["maximum_absolute_delta"] == 2.5
    assert elite["v2_metrics"]["review_count"] == 1
    assert elite["v2_metrics"]["review_country_codes"] == ["ZAF"]
    assert any("systematically below" in blocker for blocker in elite["blockers"])


def test_access_is_retained_provisional_and_known_review_outliers_remain_visible() -> None:
    review = build_review()
    access = review["recipes"]["squash_access@2006"]

    assert access["decision"] == "retain_provisional"
    assert access["policy_checks_pass"] is True
    assert access["canonical_authoring_allowed"] is False
    assert access["v2_metrics"]["mean_absolute_delta"] == 0.7
    assert access["v2_metrics"]["maximum_absolute_delta"] == 2.0
    assert access["v2_metrics"]["review_count"] == 2
    assert access["v2_metrics"]["review_country_codes"] == ["IND", "USA"]


def test_review_policy_explicitly_forbids_overfitting_same_prototype() -> None:
    review = build_review()

    assert any(
        "Do not tune V2 weights further" in safeguard
        for safeguard in review["safeguards"]
    )
    assert all(
        recipe["canonical_authoring_allowed"] is False
        for recipe in review["recipes"].values()
    )
