from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import RatingEvidence
from scripts.build_fifa_2006_anchor_candidates import (
    RESEARCH,
    SUPPORTED_ATTRIBUTES,
    build_candidates,
)


def test_2006_anchor_candidates_cover_exactly_nine_countries_and_two_attributes() -> None:
    result = build_candidates()

    assert result["schema_version"] == "fifa_partial_rating_anchor_candidates.v1"
    assert result["year"] == 2006
    assert result["country_count"] == 9
    assert result["candidate_count"] == 18
    assert result["supported_attributes"] == list(SUPPORTED_ATTRIBUTES)
    assert result["promotion_ready"] is False

    for country in result["countries"].values():
        assert set(country["candidate_attributes"]) == {
            "squash_popularity",
            "squash_access",
        }
        assert set(country["unsupported_attributes_for_this_candidate"]) == {
            "development_quality",
            "competition_quality",
            "elite_support",
            "squash_tradition",
        }
        assert country["promotion_ready"] is False


def test_candidates_use_production_rating_evidence_contract_and_exact_observations() -> None:
    result = build_candidates()
    bundle = load_earth_research_bundle(RESEARCH)

    for code, country in result["countries"].items():
        for attribute, candidate in country["candidate_attributes"].items():
            evidence = RatingEvidence.model_validate(candidate["rating_evidence"])
            assert evidence.method == "sourced_estimate"
            assert evidence.anchor_years == [2006]
            assert "fifa-big-count-2006" in evidence.source_ids
            assert all(source_id in bundle.research.sources for source_id in evidence.source_ids)
            assert evidence.observation_ids

            expected_count = 1 if attribute == "squash_popularity" else 2
            assert len(evidence.observation_ids) == expected_count
            for observation_id in evidence.observation_ids:
                observation = bundle.observations[observation_id]
                assert observation.source_id == "fifa-big-count-2006"
                assert observation.observation_year == 2006

            assert candidate["promotion_ready"] is False
            assert candidate["review_required"] == (
                abs(candidate["prototype_minus_evidence_score_delta"]) >= 1.5
            )


def test_candidate_values_preserve_reviewed_2006_prototype_anchors() -> None:
    result = build_candidates()

    assert result["countries"]["CZE"]["candidate_attributes"]["squash_popularity"][
        "rating_evidence"
    ]["value"] == 8.0
    assert result["countries"]["CZE"]["candidate_attributes"]["squash_access"][
        "rating_evidence"
    ]["value"] == 8.6

    assert result["countries"]["FRO"]["candidate_attributes"]["squash_popularity"][
        "rating_evidence"
    ]["value"] == 9.2
    assert result["countries"]["FRO"]["candidate_attributes"]["squash_access"][
        "rating_evidence"
    ]["value"] == 9.5

    assert result["countries"]["IND"]["candidate_attributes"]["squash_popularity"][
        "rating_evidence"
    ]["value"] == 5.2
    assert result["countries"]["IND"]["candidate_attributes"]["squash_access"][
        "rating_evidence"
    ]["value"] == 4.3


def test_candidate_observation_ids_match_dimension_semantics() -> None:
    result = build_candidates()
    bundle = load_earth_research_bundle(RESEARCH)

    expected_measurements = {
        "squash_popularity": {
            "players_all_registered_and_unregistered",
        },
        "squash_access": {
            "players_registered_or_association_reported",
            "clubs_reported",
        },
    }

    for country in result["countries"].values():
        for attribute, candidate in country["candidate_attributes"].items():
            evidence = RatingEvidence.model_validate(candidate["rating_evidence"])
            actual = {
                bundle.observations[observation_id].measurement_type
                for observation_id in evidence.observation_ids
            }
            assert actual == expected_measurements[attribute]


def test_promoted_context_sources_are_registered_without_fabricating_observation_datasets() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    expected_context_sources = {
        "aiff-history",
        "caf-senegal-academies-league",
        "caf-south-africa",
        "fifa-senegal-generation-foot-2000",
        "fifa-south-africa-history",
        "frmf-history",
        "jfa-history",
        "uefa-czechia-history",
        "uefa-faroe-history",
        "uefa-slovakia-hattrick-review",
        "uefa-slovakia-history",
        "ussoccer-history-framework",
        "ussoccer-timeline",
    }
    assert expected_context_sources.issubset(bundle.research.sources)

    observation_source_ids = {
        dataset.source_id for dataset in bundle.datasets.values()
    }

    # Czechia is the first contextual source family intentionally promoted from URL
    # metadata into exact normalized observations. The remaining contextual sources
    # must still not acquire fabricated datasets merely because they are registered.
    assert "uefa-czechia-history" in observation_source_ids
    assert sum(
        dataset.source_id == "uefa-czechia-history"
        for dataset in bundle.datasets.values()
    ) == 1
    still_metadata_only = expected_context_sources - {"uefa-czechia-history"}
    assert still_metadata_only.isdisjoint(observation_source_ids)
