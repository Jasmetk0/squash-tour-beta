from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.audit_fifa_prototype_against_signals import build_audit


def test_prototype_signal_audit_uses_expected_samples_without_authoring_ratings() -> None:
    audit = build_audit()

    assert audit["schema_version"] == "fifa_prototype_signal_audit.v1"
    assert audit["prototype_country_count"] == 9
    assert audit["comparison_count"] == 7
    assert audit["rating_ready"] is False

    expected_samples = {
        "participation_intensity_2006__squash_popularity": 9,
        "registered_intensity_2006__squash_access": 9,
        "club_footprint_2006__squash_access": 9,
        "professional_player_density_2023__competition_quality": 6,
        "professional_player_density_2023__elite_support": 6,
        "professional_club_density_2023__competition_quality": 8,
        "professional_club_density_2023__elite_support": 8,
    }

    assert set(audit["comparisons"]) == set(expected_samples)
    for key, expected_count in expected_samples.items():
        comparison = audit["comparisons"][key]
        assert comparison["sample_count"] == expected_count
        rho = comparison["spearman_rho"]
        assert rho is None or -1 <= rho <= 1
        assert comparison["review_inversion_count"] == len(
            comparison["review_inversions"]
        )
        assert all(
            "prototype_rating" in row
            and "signal_percentile" in row
            and "source_observation_ids" in row
            for row in comparison["countries"]
        )


def test_2006_audit_preserves_measured_signal_vs_attribute_distinction() -> None:
    audit = build_audit()

    participation = audit["comparisons"][
        "participation_intensity_2006__squash_popularity"
    ]
    access = audit["comparisons"][
        "registered_intensity_2006__squash_access"
    ]

    participation_by_country = {
        row["country_code"]: row for row in participation["countries"]
    }
    access_by_country = {
        row["country_code"]: row for row in access["countries"]
    }

    assert participation_by_country["FRO"]["signal_percentile"] > 95
    assert access_by_country["FRO"]["signal_percentile"] > 95

    assert (
        access_by_country["CZE"]["signal_percentile"]
        > access_by_country["USA"]["signal_percentile"]
        > access_by_country["IND"]["signal_percentile"]
    )

    # Prototype values remain project-authored estimates alongside measured evidence;
    # the audit does not replace them with signal percentiles.
    assert participation_by_country["USA"]["prototype_rating"] != pytest.approx(
        participation_by_country["USA"]["signal_percentile"] / 10
    )
    assert access_by_country["CZE"]["prototype_rating"] != pytest.approx(
        access_by_country["CZE"]["signal_percentile"] / 10
    )


def test_professional_audit_excludes_missing_source_countries_instead_of_zero_filling() -> None:
    audit = build_audit()

    players = audit["comparisons"][
        "professional_player_density_2023__competition_quality"
    ]["countries"]
    clubs = audit["comparisons"][
        "professional_club_density_2023__elite_support"
    ]["countries"]

    player_codes = {row["country_code"] for row in players}
    club_codes = {row["country_code"] for row in clubs}

    assert "FRO" not in player_codes
    assert "FRO" not in club_codes
    assert "MAR" not in player_codes
    assert "SEN" not in player_codes
    assert "MAR" in club_codes
    assert "SEN" in club_codes

    assert {"CZE", "IND", "JPN", "SVK", "ZAF", "USA"}.issubset(player_codes)


def test_review_inversions_are_diagnostic_pairs_not_failure_flags() -> None:
    audit = build_audit()

    for comparison in audit["comparisons"].values():
        for flag in comparison["review_inversions"]:
            assert flag["signal_percentile_gap"] >= 25
            assert flag["prototype_rating_gap"] <= -0.5

    assert audit["limitations"]
    assert any(
        "automatically changes a rating" in limitation
        for limitation in audit["limitations"]
    )
