from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.review_fifa_competition_outcomes import DEFAULT_POLICY, build_review


def test_competition_outcome_review_policy_is_fixed_and_non_authoring() -> None:
    policy = json.loads(DEFAULT_POLICY.read_text(encoding="utf-8"))

    assert policy["schema_version"] == "fifa_competition_outcome_review_policy.v1"
    assert policy["competition_recipe"] == "competition_quality@2023"
    assert policy["review"] == {
        "minimum_numeric_country_count": 6,
        "minimum_spearman_score_vs_better_rank": 0.60,
        "minimum_pairwise_concordance_rate": 0.70,
    }
    assert policy["held_out_validation"] == {
        "minimum_numeric_country_count": 3,
        "minimum_spearman_score_vs_better_rank": 0.50,
        "minimum_pairwise_concordance_rate": 0.6666,
    }
    assert policy["canonical_authoring_allowed"] is False


def test_independent_competition_outcome_review_is_supportive_without_authoring() -> None:
    review = build_review()

    assert review["schema_version"] == "fifa_competition_outcome_review.v1"
    assert review["policy_id"] == "fifa-competition-outcome-review-v1"
    assert review["competition_recipe"] == "competition_quality@2023"

    assert review["decision"] == "independent_outcome_supportive"
    assert review["review_pass"] is True
    assert review["held_out_validation_pass"] is True

    assert review["fit_allowed"] is False
    assert review["canonical_authoring_allowed"] is False


def test_outcome_review_preserves_missing_scores_instead_of_zero_filling() -> None:
    review = build_review()

    assert set(review["review_missing_competition_score_country_codes"]) == {
        "FRO",
        "MAR",
        "SEN",
    }
    assert review["heldout_missing_competition_score_country_codes"] == ["SMR"]


def test_review_and_heldout_threshold_checks_are_all_explicit() -> None:
    review = build_review()

    for group in ("review", "held_out_validation"):
        payload = review[group]
        assert set(payload["checks"]) == {
            "numeric_country_count",
            "spearman_score_vs_better_rank",
            "pairwise_concordance_rate",
        }
        assert payload["pass"] is all(
            check["pass"] for check in payload["checks"].values()
        )

    assert review["review"]["checks"]["numeric_country_count"]["actual"] == 6
    assert review["held_out_validation"]["checks"]["numeric_country_count"]["actual"] == 3


def test_supportive_outcome_decision_does_not_create_rating_permission() -> None:
    review = build_review()

    assert review["canonical_authoring_allowed"] is False
    assert review["fit_allowed"] is False
    assert "cannot itself promote" in review["interpretation"]
    assert any(
        "must never be added to V2 model components" in safeguard
        for safeguard in review["safeguards"]
    )
