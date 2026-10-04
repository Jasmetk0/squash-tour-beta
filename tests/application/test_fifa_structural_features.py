from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_structural_features import build_features


def test_structural_features_cover_all_earth_countries_without_scores() -> None:
    result = build_features()

    assert result["schema_version"] == "fifa_structural_features.v1"
    assert result["country_count"] == 250
    assert result["rating_ready"] is False
    assert result["validation_role_counts"] == {
        "review": 9,
        "held_out_validation": 4,
        "none": 237,
    }

    for country in result["countries"].values():
        assert country["rating_ready"] is False
        payload = repr(country).lower()
        assert "'score'" not in payload
        assert "'rating'" not in payload


def test_heldout_countries_are_never_fit_allowed() -> None:
    result = build_features()

    for code in ("DEU", "BRA", "ISL", "SMR"):
        country = result["countries"][code]
        assert country["validation_role"] == "held_out_validation"
        assert country["fit_allowed"] is False
        assert country["structural_event_count"] > 0

    for code in ("CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"):
        country = result["countries"][code]
        assert country["validation_role"] == "review"
        assert country["fit_allowed"] is True


def test_germany_heldout_features_preserve_old_tradition_and_recent_development() -> None:
    germany = build_features()["countries"]["DEU"]

    tradition = germany["tradition"]
    development = germany["development"]

    assert tradition["earliest_event_year"] == 1900
    assert tradition["evidence_span_years_to_2026"] == 126
    assert tradition["institutional_foundation_year"] == 1900
    assert tradition["first_competition_year"] == 1903
    assert tradition["pre_1955_event_count"] == 2

    assert development["first_event_year"] == 2022
    assert development["latest_event_year"] == 2022
    assert development["first_training_centre_year"] == 2022
    assert development["years_since_latest_evidence"] == 4


def test_brazil_heldout_features_preserve_training_history_and_partial_2026_evidence() -> None:
    brazil = build_features()["countries"]["BRA"]

    assert brazil["tradition"]["earliest_event_year"] == 1914
    assert brazil["tradition"]["institutional_foundation_year"] == 1914
    assert brazil["tradition"]["evidence_span_years_to_2026"] == 112

    development = brazil["development"]
    assert development["first_event_year"] == 1987
    assert development["latest_event_year"] == 2026
    assert development["first_training_centre_year"] == 1987
    assert development["provisional_not_outcome_years"] == [2026]


def test_iceland_absent_development_seed_is_unknown_not_zero() -> None:
    iceland = build_features()["countries"]["ISL"]

    assert iceland["tradition"]["earliest_event_year"] == 1912
    assert iceland["tradition"]["first_competition_year"] == 1912
    assert iceland["tradition"]["institutional_foundation_year"] == 1947
    assert iceland["tradition"]["pre_1955_event_count"] == 2

    assert iceland["development"]["evidence_present"] is False
    assert iceland["development"]["first_event_year"] is None
    assert iceland["development"]["event_types"] == []


def test_san_marino_preserves_long_tradition_and_1963_youth_pathway() -> None:
    san_marino = build_features()["countries"]["SMR"]

    tradition = san_marino["tradition"]
    assert tradition["earliest_event_year"] == 1928
    assert tradition["first_club_year"] == 1928
    assert tradition["institutional_foundation_year"] == 1931
    assert tradition["first_competition_year"] == 1937

    development = san_marino["development"]
    assert development["first_event_year"] == 1963
    assert development["first_pathway_or_academy_year"] == 1963


def test_review_features_keep_negative_breaks_and_source_conflicts() -> None:
    result = build_features()

    usa = result["countries"]["USA"]
    assert usa["competition_context"]["negative_break_years"] == [1984]
    assert usa["elite_support_context"]["negative_break_years"] == [1984]
    assert usa["development"]["first_training_centre_year"] == 2003
    assert usa["development"]["first_pathway_or_academy_year"] == 2007
    assert 2024 in usa["development"]["provisional_not_outcome_years"]

    morocco = result["countries"]["MAR"]
    assert morocco["conflict_groups"] == ["mar-mohammed-vi-academy-timing"]
    assert morocco["development"]["first_event_year"] == 2009
    assert morocco["development"]["latest_event_year"] == 2019


def test_no_evidence_country_stays_none_and_not_fit_allowed() -> None:
    france = build_features()["countries"]["FRA"]

    assert france["validation_role"] == "none"
    assert france["fit_allowed"] is False
    assert france["structural_event_count"] == 0
    assert france["tradition"]["evidence_present"] is False
    assert france["development"]["evidence_present"] is False
