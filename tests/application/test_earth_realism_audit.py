from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_realism_audit import (
    audit_earth_realism,
    audit_earth_world,
)
from beta_engine.domain.countries.rating_history import CountryRatingHistory
from tests.domain.test_country_rating_history import history


def _history(values: dict[int, float], *, confidence: str = "medium") -> CountryRatingHistory:
    raw = history(values).model_dump()
    for entry in raw["years"].values():
        for rating in entry["ratings"].values():
            rating["confidence"] = confidence
    return CountryRatingHistory.model_validate(raw)


def _change_one_value(
    authored: CountryRatingHistory,
    *,
    year: int,
    attribute: str = "elite_support",
    value: float,
) -> CountryRatingHistory:
    raw = authored.model_dump()
    raw["years"][year]["ratings"][attribute]["value"] = value
    return CountryRatingHistory.model_validate(raw)


def test_cross_world_exact_numeric_history_is_a_review_signal():
    identical = _history({1955: 3.0, 1956: 3.1, 1957: 3.2})
    different = _change_one_value(identical, year=1957, value=3.3)

    report = audit_earth_realism(
        fifa_countries={"AAA": identical, "BBB": identical},
        atp_countries={"AAA": identical, "BBB": different},
        long_flat_run_years=12,
    )

    assert report["realism_validated"] is False
    assert report["review_required"] is True
    assert report["cross_world"]["shared_country_count"] == 2
    assert report["cross_world"]["identical_numeric_histories"] == ["AAA"]
    assert report["worlds"]["fifa_earth"]["same_world_identical_numeric_history_groups"] == [
        ["AAA", "BBB"]
    ]


def test_large_jump_and_low_confidence_are_reported_without_becoming_validation():
    authored = _history({1955: 2.0, 1956: 4.0, 1957: 4.1}, confidence="low")

    report = audit_earth_world(
        world_id="fifa_earth",
        countries={"AAA": authored},
        low_confidence_share=0.75,
        large_annual_jump=1.5,
        long_flat_run_years=12,
    )

    assert report["realism_validated"] is False
    assert report["countries_requiring_review"] == ["AAA"]
    assert report["countries"]["AAA"]["review_flags"] == [
        "low_confidence_share",
        "large_annual_jump",
    ]
    assert report["large_annual_jump_count"] == 6
    assert report["large_annual_jumps"][0]["from_year"] == 1955
    assert report["large_annual_jumps"][0]["to_year"] == 1956
    assert report["large_annual_jumps"][0]["delta"] == 2.0


def test_long_flat_runs_use_consecutive_years_and_report_boundaries():
    values = {year: 4.0 for year in range(1955, 1967)}
    authored = _history(values, confidence="medium")

    report = audit_earth_world(
        world_id="atp_earth",
        countries={"AAA": authored},
        long_flat_run_years=12,
    )

    assert report["long_flat_run_count"] == 6
    assert report["countries"]["AAA"]["review_flags"] == ["long_flat_run"]
    assert {
        (item["attribute"], item["start_year"], item["end_year"], item["length"])
        for item in report["long_flat_runs"]
    } == {
        (attribute, 1955, 1966, 12)
        for attribute in (
            "squash_popularity",
            "squash_access",
            "development_quality",
            "competition_quality",
            "elite_support",
            "squash_tradition",
        )
    }


def test_clean_short_history_has_no_review_flags():
    fifa = _history({1955: 2.0, 1956: 2.2, 1957: 2.4}, confidence="medium")
    atp = _history({1955: 3.0, 1956: 3.2, 1957: 3.4}, confidence="medium")

    report = audit_earth_realism(
        fifa_countries={"AAA": fifa},
        atp_countries={"AAA": atp},
        long_flat_run_years=12,
    )

    assert report["review_required"] is False
    assert report["cross_world"]["identical_numeric_history_count"] == 0
    assert report["worlds"]["fifa_earth"]["countries_requiring_review"] == []
    assert report["worlds"]["atp_earth"]["countries_requiring_review"] == []
