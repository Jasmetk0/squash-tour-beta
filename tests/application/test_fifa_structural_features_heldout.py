from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.audit_fifa_structural_features_heldout import build_audit


def test_heldout_audit_keeps_review_and_validation_sets_disjoint() -> None:
    audit = build_audit()

    assert audit["schema_version"] == "fifa_structural_heldout_audit.v1"
    assert audit["rating_ready"] is False
    assert audit["review_country_codes"] == [
        "CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"
    ]
    assert audit["heldout_country_codes"] == ["BRA", "DEU", "ISL", "SMR"]
    assert set(audit["review_country_codes"]).isdisjoint(
        audit["heldout_country_codes"]
    )
    assert audit["reference_sample_sizes"] == {
        "tradition_span_years": 9,
        "development_history_span_years": 9,
        "development_recency": 9,
    }
    assert all(
        payload["fit_allowed"] is False
        for payload in audit["heldout"].values()
    )


def test_heldout_tradition_span_is_placed_against_review_only_distribution() -> None:
    heldout = build_audit()["heldout"]

    assert heldout["DEU"]["tradition_span_years"] == 126
    assert heldout["DEU"]["tradition_span_review_percentile"] == 93.75

    assert heldout["BRA"]["tradition_span_years"] == 112
    assert heldout["BRA"]["tradition_span_review_percentile"] == 68.75

    assert heldout["ISL"]["tradition_span_years"] == 114
    assert heldout["ISL"]["tradition_span_review_percentile"] == 81.25

    assert heldout["SMR"]["tradition_span_years"] == 98
    assert heldout["SMR"]["tradition_span_review_percentile"] == 43.75


def test_heldout_development_history_and_recency_remain_separate_features() -> None:
    heldout = build_audit()["heldout"]

    germany = heldout["DEU"]
    assert germany["development_history_span_years"] == 4
    assert germany["development_history_span_review_percentile"] == 0.0
    assert germany["development_years_since_latest_evidence"] == 4
    assert germany["development_recency_review_percentile"] == 81.25

    brazil = heldout["BRA"]
    assert brazil["development_history_span_years"] == 39
    assert brazil["development_history_span_review_percentile"] == 81.25
    assert brazil["development_years_since_latest_evidence"] == 0
    assert brazil["development_recency_review_percentile"] == 100.0

    san_marino = heldout["SMR"]
    assert san_marino["development_history_span_years"] == 63
    assert san_marino["development_history_span_review_percentile"] == 100.0
    assert san_marino["development_years_since_latest_evidence"] == 63
    assert san_marino["development_recency_review_percentile"] == 0.0


def test_missing_heldout_development_evidence_is_not_scored() -> None:
    iceland = build_audit()["heldout"]["ISL"]

    assert iceland["development_history_span_years"] is None
    assert iceland["development_history_span_review_percentile"] is None
    assert iceland["development_years_since_latest_evidence"] is None
    assert iceland["development_recency_review_percentile"] is None
    assert iceland["development_event_types"] == []


def test_audit_limitations_forbid_quality_interpretation() -> None:
    audit = build_audit()

    assert any(
        "not fitted rating curves" in limitation
        for limitation in audit["limitations"]
    )
    assert any(
        "not equivalent to higher current football quality" in limitation
        for limitation in audit["limitations"]
    )

    payload = repr(audit).lower()
    assert "'canonical_rating'" not in payload
    assert "'recommended_rating'" not in payload
