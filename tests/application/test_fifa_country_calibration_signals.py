from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from scripts.build_fifa_country_calibration_signals import build_signals


def test_calibration_signals_cover_all_earth_countries_without_zero_filling() -> None:
    result = build_signals()

    assert result["schema_version"] == "fifa_country_calibration_signals.v1"
    assert result["rating_ready"] is False
    assert len(result["countries"]) == 250

    expected_observed = {
        "participation_intensity_2006": 201,
        "registered_intensity_2006": 201,
        "club_footprint_2006": 199,
        "professional_player_density_2023": 108,
        "professional_club_density_2023": 131,
    }
    for signal_id, expected_count in expected_observed.items():
        rows = result["signals"][signal_id]
        assert len(rows) == 250
        observed = [row for row in rows.values() if row["rate"] is not None]
        assert len(observed) == expected_count
        assert all(row["observed_entity_count"] == expected_count for row in observed)
        assert all(row["percentile"] is not None for row in observed)
        assert all(row["rank_desc"] is not None for row in observed)

        missing = [row for row in rows.values() if row["rate"] is None]
        assert all(row["percentile"] is None for row in missing)
        assert all(row["rank_desc"] is None for row in missing)
        assert all(row["completeness"] != "complete" for row in missing)


def test_big_count_signals_match_population_normalised_source_facts() -> None:
    result = build_signals()
    cze = result["countries"]["CZE"]
    faroes = result["countries"]["FRO"]
    usa = result["countries"]["USA"]
    india = result["countries"]["IND"]

    assert cze["participation_intensity_2006"]["source_value"] == 1_040_357
    assert round(cze["participation_intensity_2006"]["rate"], 2) == 100.96
    assert cze["registered_intensity_2006"]["source_value"] == 686_257
    assert round(cze["registered_intensity_2006"]["rate"], 2) == 66.60
    assert cze["club_footprint_2006"]["source_value"] == 4_108
    assert round(cze["club_footprint_2006"]["rate"], 2) == 398.66

    assert round(faroes["participation_intensity_2006"]["rate"], 2) == 167.04
    assert round(faroes["registered_intensity_2006"]["rate"], 2) == 117.51
    assert faroes["participation_intensity_2006"]["percentile"] > 95
    assert faroes["registered_intensity_2006"]["percentile"] > 95

    assert round(usa["participation_intensity_2006"]["rate"], 2) == 81.92
    assert round(usa["registered_intensity_2006"]["rate"], 2) == 14.02

    assert round(india["participation_intensity_2006"]["rate"], 2) == 17.55
    assert round(india["registered_intensity_2006"]["rate"], 2) == 0.33
    assert (
        cze["registered_intensity_2006"]["percentile"]
        > usa["registered_intensity_2006"]["percentile"]
        > india["registered_intensity_2006"]["percentile"]
    )


def test_professional_signals_keep_missing_and_partial_aggregates_missing() -> None:
    result = build_signals()

    cze = result["countries"]["CZE"]
    usa = result["countries"]["USA"]
    faroes = result["countries"]["FRO"]
    gbr = result["countries"]["GBR"]

    assert cze["professional_player_density_2023"]["source_value"] == 2_959
    assert cze["professional_club_density_2023"]["source_value"] == 30
    assert usa["professional_player_density_2023"]["source_value"] == 2_791
    assert usa["professional_club_density_2023"]["source_value"] == 101
    assert (
        cze["professional_player_density_2023"]["rate"]
        > usa["professional_player_density_2023"]["rate"]
    )

    assert faroes["professional_player_density_2023"]["rate"] is None
    assert faroes["professional_player_density_2023"]["completeness"] == "missing"
    assert faroes["professional_club_density_2023"]["rate"] is None

    assert gbr["professional_player_density_2023"]["rate"] is None
    assert gbr["professional_player_density_2023"]["completeness"] == "partial_aggregate"
    assert gbr["professional_player_density_2023"]["missing_source_entities"] == [
        "NORTHERN IRELAND"
    ]
    assert gbr["professional_club_density_2023"]["rate"] is None
    assert gbr["professional_club_density_2023"]["missing_source_entities"] == [
        "NORTHERN IRELAND"
    ]


def test_gbr_big_count_is_complete_non_overlapping_aggregate() -> None:
    result = build_signals()
    gbr = result["countries"]["GBR"]

    participation = gbr["participation_intensity_2006"]
    registered = gbr["registered_intensity_2006"]
    clubs = gbr["club_footprint_2006"]

    assert participation["completeness"] == "complete_aggregate"
    assert registered["completeness"] == "complete_aggregate"
    assert clubs["completeness"] == "complete_aggregate"

    assert participation["source_value"] == 4_850_569
    assert registered["source_value"] == 1_703_369
    assert clubs["source_value"] == 51_966
    assert len(participation["observation_ids"]) == 4
    assert set(participation["source_entities"]) == {
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
    }


def test_signal_percentiles_are_measurement_specific_not_one_hidden_strength_score() -> None:
    result = build_signals()

    # USA has a very large participation base but much lower registration density
    # than Czechia. The calibration layer must preserve that distinction rather than
    # collapsing both into one football-strength number.
    usa = result["countries"]["USA"]
    cze = result["countries"]["CZE"]

    assert usa["participation_intensity_2006"]["percentile"] != usa[
        "registered_intensity_2006"
    ]["percentile"]
    assert cze["registered_intensity_2006"]["percentile"] > usa[
        "registered_intensity_2006"
    ]["percentile"]

    assert set(result["signal_definitions"]) == {
        "participation_intensity_2006",
        "registered_intensity_2006",
        "club_footprint_2006",
        "professional_player_density_2023",
        "professional_club_density_2023",
    }
    assert all(
        "rating" not in signal_id
        for signal_id in result["signal_definitions"]
    )
