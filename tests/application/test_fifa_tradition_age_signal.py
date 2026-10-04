from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_tradition_age_signal import (
    FIRST_YEAR,
    LAST_YEAR,
    build_tradition_age_signal,
)


def test_tradition_age_signal_is_annual_complete_and_noncanonical() -> None:
    result = build_tradition_age_signal()

    assert result["schema_version"] == "fifa_tradition_age_signal.v1"
    assert result["years"] == {"from": 1955, "to": 2026}
    assert result["country_count"] == 250
    assert result["country_count_with_tradition_age_evidence"] == 13
    assert result["rating_ready"] is False

    for country in result["countries"].values():
        assert country["rating_ready"] is False
        assert len(country["annual"]) == LAST_YEAR - FIRST_YEAR + 1
        assert set(country["annual"]) == {
            str(year) for year in range(FIRST_YEAR, LAST_YEAR + 1)
        }
        for row in country["annual"].values():
            assert row["rating_ready"] is False
            assert "rating" not in row
            assert "score" not in row


def test_review_country_tradition_age_uses_first_available_anchor_not_event_count() -> None:
    result = build_tradition_age_signal()

    cze = result["countries"]["CZE"]
    assert cze["evidence_role"] == "review"
    assert cze["earliest_documented_tradition_year"] == 1901
    assert cze["annual"]["1955"]["years_since_first_tradition_anchor"] == 54
    assert cze["annual"]["2026"]["years_since_first_tradition_anchor"] == 125

    japan = result["countries"]["JPN"]
    assert japan["earliest_documented_tradition_year"] == 1921
    assert japan["annual"]["1955"]["years_since_first_tradition_anchor"] == 34
    assert japan["annual"]["1955"]["available_anchor_count"] == 1
    assert japan["annual"]["1993"]["available_anchor_count"] == 3

    # Anchor count changes provenance coverage, not the age calculation.
    assert japan["annual"]["1993"]["years_since_first_tradition_anchor"] == 72


def test_tradition_age_stays_missing_before_first_documented_anchor() -> None:
    result = build_tradition_age_signal()

    senegal = result["countries"]["SEN"]
    assert senegal["earliest_documented_tradition_year"] == 1960
    assert senegal["annual"]["1955"]["years_since_first_tradition_anchor"] is None
    assert senegal["annual"]["1955"]["available_anchor_count"] == 0
    assert senegal["annual"]["1960"]["years_since_first_tradition_anchor"] == 0
    assert senegal["annual"]["2026"]["years_since_first_tradition_anchor"] == 66

    south_africa = result["countries"]["ZAF"]
    assert south_africa["earliest_documented_tradition_year"] == 1991
    assert south_africa["annual"]["1990"]["years_since_first_tradition_anchor"] is None
    assert south_africa["annual"]["1991"]["years_since_first_tradition_anchor"] == 0


def test_unseeded_country_is_unknown_for_all_years_not_zero_tradition() -> None:
    result = build_tradition_age_signal()

    france = result["countries"]["FRA"]
    assert france["evidence_role"] == "none"
    assert france["tradition_event_count"] == 0
    assert france["earliest_documented_tradition_year"] is None
    assert all(
        row["years_since_first_tradition_anchor"] is None
        and row["first_tradition_anchor_year"] is None
        and row["available_anchor_count"] == 0
        for row in france["annual"].values()
    )


def test_heldout_countries_are_labelled_and_have_expected_historical_depth() -> None:
    result = build_tradition_age_signal()

    expected = {
        "DEU": (1900, 55, 126),
        "BRA": (1914, 41, 112),
        "ISL": (1912, 43, 114),
        "SMR": (1928, 27, 98),
    }
    for code, (first, age_1955, age_2026) in expected.items():
        country = result["countries"][code]
        assert country["evidence_role"] == "held_out_validation"
        assert country["earliest_documented_tradition_year"] == first
        assert country["annual"]["1955"]["years_since_first_tradition_anchor"] == age_1955
        assert country["annual"]["2026"]["years_since_first_tradition_anchor"] == age_2026
        assert all(
            row["evidence_role"] == "held_out_validation"
            for row in country["annual"].values()
        )


def test_san_marino_later_league_anchor_does_not_rewrite_historical_start() -> None:
    result = build_tradition_age_signal()
    san_marino = result["countries"]["SMR"]

    assert san_marino["annual"]["1955"]["first_tradition_anchor_year"] == 1928
    assert san_marino["annual"]["1955"]["available_anchor_count"] == 3
    assert san_marino["annual"]["1984"]["available_anchor_count"] == 3
    assert san_marino["annual"]["1985"]["available_anchor_count"] == 4
    assert san_marino["annual"]["1985"]["first_tradition_anchor_year"] == 1928


def test_limitations_forbid_using_heldout_or_anchor_count_as_quality() -> None:
    result = build_tradition_age_signal()

    assert any(
        "Anchor count is provenance coverage" in limitation
        for limitation in result["limitations"]
    )
    assert any(
        "Held-out validation countries" in limitation
        and "must not be used to fit" in limitation
        for limitation in result["limitations"]
    )
