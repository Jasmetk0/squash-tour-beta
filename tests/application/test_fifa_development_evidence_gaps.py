from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.audit_fifa_development_evidence_gaps import build_gap_audit


def test_gap_audit_exposes_missing_core_development_families_without_scores() -> None:
    audit = build_gap_audit()

    assert audit["schema_version"] == "fifa_development_evidence_gap_audit.v1"
    assert audit["country_count"] == 250
    assert audit["rating_ready"] is False
    assert audit["canonical_authoring_allowed"] is False

    development = audit["development_facet_coverage"]
    for facet in (
        "talent_identification",
        "playing_opportunities",
        "youth_to_senior_transition",
        "coaching_capacity",
    ):
        assert development[facet] == {
            "review": 0,
            "held_out_validation": 0,
            "all_canonical": 0,
        }

    assert development["training_environment"] == {
        "review": 4,
        "held_out_validation": 2,
        "all_canonical": 6,
    }
    assert development["academy_pathway_coverage"] == {
        "review": 5,
        "held_out_validation": 1,
        "all_canonical": 6,
    }


def test_tradition_gap_audit_shows_history_without_cultural_embedding() -> None:
    tradition = build_gap_audit()["tradition_facet_coverage"]

    assert tradition["institutional_roots"] == {
        "review": 8,
        "held_out_validation": 4,
        "all_canonical": 12,
    }
    assert tradition["organised_competition_roots"] == {
        "review": 4,
        "held_out_validation": 3,
        "all_canonical": 7,
    }
    assert tradition["club_roots"] == {
        "review": 1,
        "held_out_validation": 1,
        "all_canonical": 2,
    }
    assert tradition["continuity_discontinuity_context"] == {
        "review": 2,
        "held_out_validation": 0,
        "all_canonical": 2,
    }
    assert tradition["cultural_audience_embedding"] == {
        "review": 0,
        "held_out_validation": 0,
        "all_canonical": 0,
    }


def test_country_level_gap_view_keeps_presence_distinct_from_quality() -> None:
    audit = build_gap_audit()

    japan = audit["countries"]["JPN"]
    assert japan["validation_role"] == "review"
    assert japan["fit_allowed"] is True
    assert japan["development_facets"]["training_environment"]["evidence_present"] is True
    assert japan["development_facets"]["academy_pathway_coverage"]["evidence_present"] is False
    assert japan["development_facets"]["coaching_capacity"]["evidence_present"] is False

    germany = audit["countries"]["DEU"]
    assert germany["validation_role"] == "held_out_validation"
    assert germany["fit_allowed"] is False
    assert germany["development_facets"]["training_environment"]["evidence_present"] is True
    assert germany["development_facets"]["coaching_capacity"]["evidence_present"] is False

    rendered = repr(japan).lower()
    assert "'score'" not in rendered
    assert "'rating'" not in rendered


def test_no_seed_country_means_unknown_evidence_not_low_capability() -> None:
    france = build_gap_audit()["countries"]["FRA"]

    assert france["validation_role"] == "none"
    assert france["fit_allowed"] is False
    assert all(
        facet["coverage_interpretation"] == "no_canonical_facet_evidence"
        for facet in france["development_facets"].values()
    )
    assert all(
        facet["coverage_interpretation"] == "no_canonical_facet_evidence"
        for facet in france["tradition_facets"].values()
    )


def test_gap_audit_priorities_match_missing_source_families() -> None:
    audit = build_gap_audit()

    assert audit["next_source_priorities"] == [
        "talent_identification",
        "playing_opportunities",
        "youth_to_senior_transition",
        "coaching_capacity",
        "academy_pathway_coverage_depth",
        "cultural_audience_embedding",
    ]
    assert any(
        "not nationwide quality" in limitation
        for limitation in audit["limitations"]
    )
    assert any(
        "unknown, not negative evidence" in safeguard
        for safeguard in audit["safeguards"]
    )
