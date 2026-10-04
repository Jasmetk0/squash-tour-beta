from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_structural_dimension_evidence import build_summary


def test_structural_dimension_summary_covers_all_earth_countries_without_scores() -> None:
    result = build_summary()

    assert result["schema_version"] == "fifa_structural_dimension_evidence.v1"
    assert result["country_count"] == 250
    assert result["structural_event_count"] == 43
    assert result["dimension_event_counts"] == {
        "development_quality": 19,
        "squash_tradition": 16,
    }
    assert result["conflict_groups"] == ["mar-mohammed-vi-academy-timing"]
    assert result["rating_ready"] is False

    for country in result["countries"].values():
        assert country["rating_ready"] is False
        assert set(country["dimensions"]) == {
            "development_quality",
            "squash_tradition",
        }
        for dimension in country["dimensions"].values():
            assert dimension["rating_ready"] is False
            assert "score" not in dimension
            assert "rating" not in dimension


def test_missing_structural_seed_is_unknown_not_zero_quality() -> None:
    result = build_summary()

    for code in ("DEU", "BRA", "ISL", "SMR"):
        country = result["countries"][code]
        assert country["structural_event_count"] == 0
        assert country["structural_observation_ids"] == []
        for dimension in country["dimensions"].values():
            assert dimension["evidence_present"] is False
            assert dimension["event_count"] == 0
            assert dimension["first_event_year"] is None
            assert dimension["last_event_year"] is None
            assert dimension["events"] == []


def test_japan_summary_keeps_pre_game_tradition_and_separate_development_fact() -> None:
    result = build_summary()
    japan = result["countries"]["JPN"]

    development = japan["dimensions"]["development_quality"]
    tradition = japan["dimensions"]["squash_tradition"]

    assert development["event_count"] == 1
    assert development["first_event_year"] == 1977
    assert development["last_event_year"] == 1977
    assert development["pre_1955_event_count"] == 0

    assert tradition["event_count"] == 3
    assert tradition["first_event_year"] == 1921
    assert tradition["last_event_year"] == 1993
    assert tradition["pre_1955_event_count"] == 1


def test_usa_development_summary_is_timeline_not_weighted_score() -> None:
    result = build_summary()
    usa = result["countries"]["USA"]

    development = usa["dimensions"]["development_quality"]
    assert development["event_count"] == 4
    assert development["first_event_year"] == 2003
    assert development["last_event_year"] == 2024
    assert [
        event["observation_year"] for event in development["events"]
    ] == [2003, 2007, 2018, 2024]

    tradition = usa["dimensions"]["squash_tradition"]
    assert tradition["event_count"] == 1
    assert tradition["first_event_year"] == 1913
    assert tradition["pre_1955_event_count"] == 1


def test_morocco_conflicting_academy_dates_remain_visible_in_development_summary() -> None:
    result = build_summary()
    development = result["countries"]["MAR"]["dimensions"]["development_quality"]

    assert development["event_count"] == 2
    assert development["first_event_year"] == 2009
    assert development["last_event_year"] == 2019
    assert development["conflict_groups"] == [
        "mar-mohammed-vi-academy-timing"
    ]
    assert {
        event["observation_year"] for event in development["events"]
    } == {2009, 2019}
    assert all(
        "source_timing_conflict" in event["quality_flags"]
        for event in development["events"]
    )


def test_summary_limitations_forbid_event_count_as_quality_proxy() -> None:
    result = build_summary()

    assert any(
        "Event count is documentation coverage" in limitation
        for limitation in result["limitations"]
    )
    assert any(
        "Absence of an event" in limitation
        for limitation in result["limitations"]
    )
