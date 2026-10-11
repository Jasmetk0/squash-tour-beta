from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.audit_fifa_dimension_scores_against_prototype import (
    REVIEW_ABSOLUTE_DELTA,
    build_audit,
)


def test_dimension_score_audit_uses_expected_prototype_samples() -> None:
    audit = build_audit()

    assert audit["schema_version"] == "fifa_dimension_score_prototype_audit.v1"
    assert audit["prototype_country_count"] == 9
    assert audit["rating_ready"] is False
    assert audit["review_absolute_delta_threshold"] == REVIEW_ABSOLUTE_DELTA == 1.5

    assert audit["evidence_model_id"] == "fifa-dimension-evidence-v2"

    expected_samples = {
        "squash_access@2006": 9,
        "competition_quality@2023": 6,
        "elite_support@2023": 6,
    }
    assert set(audit["recipes"]) == set(expected_samples)

    for recipe_id, expected_count in expected_samples.items():
        payload = audit["recipes"][recipe_id]
        assert payload["sample_count"] == expected_count
        assert payload["mean_absolute_delta"] is not None
        assert payload["maximum_absolute_delta"] is not None
        assert payload["maximum_absolute_delta"] >= payload["mean_absolute_delta"]
        assert payload["review_count"] == len(payload["review_country_codes"])
        assert len(payload["countries"]) == expected_count


def test_review_flags_are_exactly_large_absolute_deltas() -> None:
    audit = build_audit()

    for payload in audit["recipes"].values():
        for country in payload["countries"]:
            assert country["review_required"] == (
                country["absolute_delta"] >= REVIEW_ABSOLUTE_DELTA
            )
            assert country["absolute_delta"] == pytest.approx(
                abs(country["signed_delta"])
            )
            assert 1 <= country["evidence_score"] <= 10
            assert 1 <= country["prototype_rating"] <= 10


def test_audit_preserves_source_observation_provenance() -> None:
    audit = build_audit()

    access = audit["recipes"]["squash_access@2006"]
    cze = next(
        country
        for country in access["countries"]
        if country["country_code"] == "CZE"
    )

    assert cze["components"]
    assert {component["signal_id"] for component in cze["components"]} == {
        "registered_intensity_2006",
        "club_footprint_2006",
    }
    assert all(
        component["source_observation_ids"]
        for component in cze["components"]
    )
    assert cze["prototype_anchor_years"] == [2006]
    assert cze["prototype_method"] == "sourced_estimate"


def test_2023_audit_does_not_reintroduce_missing_professional_countries() -> None:
    audit = build_audit()

    competition_codes = {
        row["country_code"]
        for row in audit["recipes"]["competition_quality@2023"]["countries"]
    }
    elite_codes = {
        row["country_code"]
        for row in audit["recipes"]["elite_support@2023"]["countries"]
    }

    assert competition_codes == elite_codes
    assert "FRO" not in competition_codes
    assert "MAR" not in competition_codes
    assert "SEN" not in competition_codes
    assert {"CZE", "IND", "JPN", "SVK", "ZAF", "USA"}.issubset(
        competition_codes
    )


def test_audit_is_diagnostic_and_has_no_authoring_instruction() -> None:
    audit = build_audit()

    assert audit["rating_ready"] is False
    assert any(
        "No audit result automatically changes a rating" in limitation
        for limitation in audit["limitations"]
    )
    for payload in audit["recipes"].values():
        for row in payload["countries"]:
            assert "canonical_rating" not in row
            assert "recommended_rating" not in row
