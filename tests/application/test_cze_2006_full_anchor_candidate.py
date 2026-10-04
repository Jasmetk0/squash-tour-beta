from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import CountryRatingHistory
from scripts.build_cze_2006_full_anchor_candidate import (
    ANCHOR_YEAR,
    COUNTRY_CODE,
    RESEARCH,
    build_candidate,
)


def _history() -> CountryRatingHistory:
    result = build_candidate()
    return CountryRatingHistory.model_validate(result["candidate_history"])


def test_cze_2006_candidate_is_a_complete_production_contract_rating_year() -> None:
    result = build_candidate()
    history = _history()

    assert result["schema_version"] == "fifa_complete_anchor_candidate.v1"
    assert result["country_code"] == "CZE"
    assert result["year"] == 2006
    assert result["candidate_attribute_count"] == 6
    assert result["full_year_complete"] is True
    assert result["history_coverage_complete"] is False
    assert result["promotion_ready"] is False

    assert history.schema_version == "country_rating_history.v2"
    assert history.rating_scale == "country_ratings_1_10.v2"
    assert history.reference_year == 2006
    assert set(history.years) == {2006}
    assert len(history.years[2006].ratings) == 6
    assert len(history.missing_earth_years) == 71
    assert 2006 not in history.missing_earth_years


def test_cze_2006_candidate_preserves_reviewed_attribute_values() -> None:
    ratings = _history().years[2006].ratings

    assert ratings["squash_popularity"].value == 8.0
    assert ratings["squash_access"].value == 8.6
    assert ratings["development_quality"].value == 7.6
    assert ratings["competition_quality"].value == 7.6
    assert ratings["elite_support"].value == 6.7
    assert ratings["squash_tradition"].value == 9.0

    assert ratings["elite_support"].confidence == "low"
    for attribute, evidence in ratings.items():
        assert evidence.method == "sourced_estimate"
        assert evidence.anchor_years == [2006]
        assert evidence.observation_ids, attribute


def test_cze_2006_candidate_uses_attribute_specific_observation_semantics() -> None:
    bundle = load_earth_research_bundle(RESEARCH)
    ratings = _history().years[2006].ratings

    measurements = {
        attribute: {
            bundle.observations[observation_id].measurement_type
            for observation_id in evidence.observation_ids
        }
        for attribute, evidence in ratings.items()
    }

    assert measurements["squash_popularity"] == {
        "players_all_registered_and_unregistered"
    }
    assert measurements["squash_access"] == {
        "players_registered_or_association_reported",
        "clubs_reported",
    }
    assert measurements["development_quality"] == {
        "structural_event",
        "youth_players_under_18_reported",
    }
    assert measurements["competition_quality"] == {
        "structural_event",
        "top_division_clubs_reported",
    }
    assert measurements["elite_support"] == {
        "professional_non_amateur_players_reported",
        "clubs_reported",
        "teams_reported",
        "top_division_clubs_reported",
    }
    assert measurements["squash_tradition"] == {"structural_event"}


def test_cze_2006_candidate_has_no_future_leakage_and_sources_match_observations() -> None:
    bundle = load_earth_research_bundle(RESEARCH)
    ratings = _history().years[2006].ratings

    for attribute, evidence in ratings.items():
        assert all(source_id in bundle.research.sources for source_id in evidence.source_ids)
        for observation_id in evidence.observation_ids:
            observation = bundle.observations[observation_id]
            assert observation.source_id in evidence.source_ids
            assert observation.earth_country_code in {None, COUNTRY_CODE}
            assert observation.observation_year is None or observation.observation_year <= ANCHOR_YEAR


def test_cze_2006_candidate_keeps_canonical_fifa_country_history_empty() -> None:
    bundle = load_earth_research_bundle(RESEARCH)
    result = build_candidate()

    assert COUNTRY_CODE not in bundle.research.countries
    assert result["promotion_ready"] is False
    assert result["missing_history_year_count"] == 71
    assert len(result["missing_history_years"]) == 71


def test_cze_historical_context_matches_independent_post_1993_period() -> None:
    year = _history().years[2006]

    assert year.historical_entity == "Czech Republic / Czechia"
    assert "Independent Czech association period" in year.territory_mapping_note
