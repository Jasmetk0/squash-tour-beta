from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_country_calibration_signals import build_signals
from scripts.build_fifa_dimension_evidence_scores import (
    DEFAULT_MODEL,
    _load_model,
    build_dimension_evidence_scores,
    percentile_to_score,
)


def test_transfer_curve_is_explicit_monotone_and_hits_declared_points() -> None:
    model = _load_model()
    curve = model["percentile_transfer_curve"]

    assert curve[0] == {"percentile": 0.0, "score": 1.5}
    assert curve[-1] == {"percentile": 100.0, "score": 9.7}

    scores = [percentile_to_score(float(point["percentile"]), model) for point in curve]
    assert scores == [float(point["score"]) for point in curve]
    assert scores == sorted(scores)

    # Piecewise interpolation, not percentile / 10.
    assert percentile_to_score(50, model) == 5.5
    assert percentile_to_score(60, model) == 6.0
    assert percentile_to_score(95, model) == 8.5
    assert percentile_to_score(50, model) != 5.0


def test_dimension_evidence_scores_cover_all_earth_countries_and_stay_noncanonical() -> None:
    result = build_dimension_evidence_scores()

    assert result["schema_version"] == "fifa_dimension_evidence_scores.v2"
    assert result["rating_scale"] == "country_ratings_1_10.v2"
    assert result["rating_ready"] is False
    assert result["country_count"] == 250
    assert len(result["countries"]) == 250

    assert set(result["recipes"]) == {
        "squash_access@2006",
        "competition_quality@2023",
        "elite_support@2023",
    }
    assert set(result["unsupported_attributes"]) == {
        "squash_popularity",
        "development_quality",
        "squash_tradition",
    }

    for country in result["countries"].values():
        for score in country.values():
            assert score["rating_ready"] is False
            if score["evidence_score"] is not None:
                assert 1 <= score["evidence_score"] <= 10
                assert round(score["evidence_score"], 1) == score["evidence_score"]


def test_recipe_coverage_matches_required_signal_intersections() -> None:
    signals = build_signals()
    scores = build_dimension_evidence_scores()

    expected = {
        "squash_access@2006": sum(
            country["registered_intensity_2006"]["signal_value"] is not None
            and country["club_footprint_2006"]["signal_value"] is not None
            for country in signals["countries"].values()
        ),
        "competition_quality@2023": sum(
            country["professional_player_density_2023"]["signal_value"] is not None
            and country["professional_club_density_2023"]["signal_value"] is not None
            and country["professional_player_scale_2023"]["signal_value"] is not None
            and country["professional_club_scale_2023"]["signal_value"] is not None
            for country in signals["countries"].values()
        ),
        "elite_support@2023": sum(
            country["professional_player_density_2023"]["signal_value"] is not None
            and country["professional_club_density_2023"]["signal_value"] is not None
            and country["professional_player_scale_2023"]["signal_value"] is not None
            and country["professional_club_scale_2023"]["signal_value"] is not None
            for country in signals["countries"].values()
        ),
    }

    assert expected["squash_access@2006"] == 199
    assert scores["recipe_observed_counts"] == expected


def test_access_evidence_preserves_measured_country_ordering() -> None:
    result = build_dimension_evidence_scores()

    cze = result["countries"]["CZE"]["squash_access@2006"]
    usa = result["countries"]["USA"]["squash_access@2006"]
    india = result["countries"]["IND"]["squash_access@2006"]
    faroes = result["countries"]["FRO"]["squash_access@2006"]

    assert cze["evidence_score"] > usa["evidence_score"] > india["evidence_score"]
    assert faroes["evidence_score"] >= 8.5

    assert [component["weight"] for component in cze["components"]] == [0.65, 0.35]
    assert {component["signal_id"] for component in cze["components"]} == {
        "registered_intensity_2006",
        "club_footprint_2006",
    }


def test_professional_scores_require_both_components_and_never_fill_missing() -> None:
    result = build_dimension_evidence_scores()

    faroes_competition = result["countries"]["FRO"]["competition_quality@2023"]
    gbr_elite = result["countries"]["GBR"]["elite_support@2023"]
    cze_competition = result["countries"]["CZE"]["competition_quality@2023"]

    assert faroes_competition["evidence_score"] is None
    assert set(faroes_competition["missing_signal_ids"]) == {
        "professional_player_density_2023",
        "professional_club_density_2023",
        "professional_player_scale_2023",
        "professional_club_scale_2023",
    }

    assert gbr_elite["evidence_score"] is None
    assert set(gbr_elite["missing_signal_ids"]) == {
        "professional_player_density_2023",
        "professional_club_density_2023",
        "professional_player_scale_2023",
        "professional_club_scale_2023",
    }

    assert cze_competition["evidence_score"] is not None
    assert cze_competition["missing_signal_ids"] == []


def test_model_file_has_no_recipe_for_dimensions_not_measured_by_current_sources() -> None:
    model = json.loads(DEFAULT_MODEL.read_text(encoding="utf-8"))

    authored_attributes = {recipe["attribute"] for recipe in model["recipes"].values()}
    assert "squash_popularity" not in authored_attributes
    assert "development_quality" not in authored_attributes
    assert "squash_tradition" not in authored_attributes

    assert "squash_popularity" in model["unsupported_attributes"]
    assert "development_quality" in model["unsupported_attributes"]
    assert "squash_tradition" in model["unsupported_attributes"]


def test_professional_recipes_are_scale_dominant_in_model_v2() -> None:
    model = _load_model()

    competition = model["recipes"]["competition_quality@2023"]["components"]
    elite = model["recipes"]["elite_support@2023"]["components"]

    competition_weights = {item["signal_id"]: item["weight"] for item in competition}
    elite_weights = {item["signal_id"]: item["weight"] for item in elite}

    assert competition_weights["professional_player_scale_2023"] == 0.40
    assert competition_weights["professional_club_scale_2023"] == 0.35
    assert sum(
        weight
        for signal_id, weight in competition_weights.items()
        if "scale" in signal_id
    ) == pytest.approx(0.75)

    assert elite_weights["professional_club_scale_2023"] == 0.40
    assert elite_weights["professional_player_scale_2023"] == 0.30
    assert sum(
        weight
        for signal_id, weight in elite_weights.items()
        if "scale" in signal_id
    ) == pytest.approx(0.70)
