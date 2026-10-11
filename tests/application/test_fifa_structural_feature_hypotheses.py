from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.audit_fifa_structural_feature_hypotheses import (
    MIN_ABS_SPEARMAN_FOR_CANDIDATE,
    build_audit,
)


def test_simple_structural_hypotheses_are_rejected_on_review_set() -> None:
    audit = build_audit()

    assert audit["schema_version"] == "fifa_structural_feature_hypothesis_audit.v1"
    assert audit["rating_ready"] is False
    assert audit["canonical_authoring_allowed"] is False
    assert audit["heldout_used_for_fit"] is False
    assert audit["review_country_codes"] == [
        "CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"
    ]
    assert audit["heldout_country_codes"] == ["BRA", "DEU", "ISL", "SMR"]

    expected = {
        "tradition_span_only": 0.0169,
        "pre1955_event_count_only": -0.0151,
        "development_history_span_only": -0.0840,
        "development_recency_only": -0.0252,
    }
    assert set(audit["hypotheses"]) == set(expected)

    for hypothesis_id, expected_rho in expected.items():
        payload = audit["hypotheses"][hypothesis_id]
        assert payload["sample_count"] == 9
        assert payload["spearman_rho"] == pytest.approx(expected_rho, abs=1e-4)
        assert abs(payload["spearman_rho"]) < MIN_ABS_SPEARMAN_FOR_CANDIDATE
        assert payload["decision"] == "rejected_as_single_factor_transfer"


def test_tradition_age_alone_does_not_explain_prototype_tradition() -> None:
    audit = build_audit()

    span = audit["hypotheses"]["tradition_span_only"]
    pre1955 = audit["hypotheses"]["pre1955_event_count_only"]

    assert abs(span["spearman_rho"]) < 0.05
    assert abs(pre1955["spearman_rho"]) < 0.05

    rows = {row["country_code"]: row for row in span["countries"]}
    assert rows["FRO"]["raw_feature_value"] > rows["CZE"]["raw_feature_value"]
    assert rows["FRO"]["prototype_rating_2026"] < rows["CZE"]["prototype_rating_2026"]

    assert rows["ZAF"]["raw_feature_value"] < rows["SEN"]["raw_feature_value"]
    assert rows["ZAF"]["prototype_rating_2026"] > rows["SEN"]["prototype_rating_2026"]


def test_development_history_or_recency_alone_do_not_explain_quality() -> None:
    audit = build_audit()

    history = audit["hypotheses"]["development_history_span_only"]
    recency = audit["hypotheses"]["development_recency_only"]

    assert abs(history["spearman_rho"]) < 0.10
    assert abs(recency["spearman_rho"]) < 0.10

    history_rows = {
        row["country_code"]: row for row in history["countries"]
    }
    assert (
        history_rows["JPN"]["raw_feature_value"]
        > history_rows["CZE"]["raw_feature_value"]
    )
    assert (
        history_rows["JPN"]["prototype_rating_2026"]
        > history_rows["CZE"]["prototype_rating_2026"]
    )

    assert (
        history_rows["FRO"]["raw_feature_value"]
        > history_rows["MAR"]["raw_feature_value"]
    )
    assert (
        history_rows["FRO"]["prototype_rating_2026"]
        < history_rows["MAR"]["prototype_rating_2026"]
    )


def test_heldout_validation_countries_never_enter_hypothesis_fit_rows() -> None:
    audit = build_audit()
    heldout = set(audit["heldout_country_codes"])

    for payload in audit["hypotheses"].values():
        fitted = {row["country_code"] for row in payload["countries"]}
        assert fitted.isdisjoint(heldout)


def test_rejection_does_not_claim_structural_features_are_irrelevant() -> None:
    audit = build_audit()

    assert any(
        "does not prove a structural feature is irrelevant" in limitation
        for limitation in audit["limitations"]
    )
    assert all(
        payload["decision"] == "rejected_as_single_factor_transfer"
        for payload in audit["hypotheses"].values()
    )

    rendered = repr(audit).lower()
    assert "'recommended_rating'" not in rendered
    assert "'canonical_rating'" not in rendered
