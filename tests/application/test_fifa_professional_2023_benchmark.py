from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_fifa_professional_2023_benchmark import build_benchmark

pytestmark = pytest.mark.pr_critical

EARTH_ROOT = Path("config/world_packages/real_world/countries")


def _population(code: str) -> int:
    payload = json.loads(
        (EARTH_ROOT / code / "attributes" / "population.json").read_text(encoding="utf-8")
    )
    return int(payload["values_by_year"]["2023"])


def test_professional_2023_benchmark_keeps_only_safely_reconciled_earth_entities() -> None:
    benchmark = build_benchmark()

    assert benchmark["source_row_count"] == 211
    assert benchmark["safe_earth_entity_count"] == 207
    assert len(benchmark["unobserved_earth_codes"]) == 43
    assert benchmark["manual_review_pages"] == [38]

    assert "KWT" in benchmark["entities"]
    assert benchmark["entities"]["KWT"]["source_pages"] == [37]
    assert "KGZ" in benchmark["unobserved_earth_codes"]


def test_professional_2023_benchmark_preserves_missing_as_null() -> None:
    benchmark = build_benchmark()

    senegal = benchmark["entities"]["SEN"]
    assert senegal["values"]["professional_players"] is None
    assert senegal["values"]["professional_clubs"] == 18
    assert senegal["metrics"]["professional_players_per_million"] is None
    assert senegal["metrics"]["professional_clubs_per_million"] == round(
        18 / _population("SEN") * 1_000_000, 3
    )
    assert senegal["metrics"]["professional_players_per_club"] is None

    faroes = benchmark["entities"]["FRO"]
    assert faroes["values"] == {
        "professional_players": None,
        "professional_clubs": None,
    }
    assert faroes["metrics"] == {
        "professional_players_per_million": None,
        "professional_clubs_per_million": None,
        "professional_players_per_club": None,
    }


def test_professional_2023_benchmark_normalises_complete_rows_without_turning_them_into_ratings() -> None:
    benchmark = build_benchmark()

    cze = benchmark["entities"]["CZE"]
    assert cze["values"] == {
        "professional_players": 2959,
        "professional_clubs": 30,
    }
    assert cze["metrics"]["professional_players_per_million"] == round(
        2959 / _population("CZE") * 1_000_000, 3
    )
    assert cze["metrics"]["professional_clubs_per_million"] == round(
        30 / _population("CZE") * 1_000_000, 3
    )
    assert cze["metrics"]["professional_players_per_club"] == round(2959 / 30, 3)

    usa = benchmark["entities"]["USA"]
    assert usa["values"] == {
        "professional_players": 2791,
        "professional_clubs": 101,
    }
    assert usa["metrics"]["professional_players_per_million"] == round(
        2791 / _population("USA") * 1_000_000, 3
    )


def test_professional_2023_gbr_aggregate_does_not_convert_missing_home_nation_data_to_zero() -> None:
    benchmark = build_benchmark()
    gbr = benchmark["entities"]["GBR"]

    assert gbr["identity_status"] == "aggregate"
    assert gbr["source_associations"] == [
        "ENGLAND",
        "SCOTLAND",
        "WALES",
        "NORTHERN IRELAND",
    ]
    assert gbr["values"] == {
        "professional_players": None,
        "professional_clubs": None,
    }
    assert gbr["known_partial_sums"] == {
        "professional_players": 10791,
        "professional_clubs": 181,
    }
    assert gbr["missing_associations"] == {
        "professional_players": ["NORTHERN IRELAND"],
        "professional_clubs": ["NORTHERN IRELAND"],
    }
    assert gbr["metrics"]["professional_players_per_million"] is None
    assert gbr["metrics"]["professional_clubs_per_million"] is None


def test_professional_2023_benchmark_preserves_global_total_discrepancy() -> None:
    benchmark = build_benchmark()

    assert benchmark["published_global_totals"] == {
        "professional_players": 128694,
        "professional_clubs": 3986,
    }
    assert benchmark["extracted_national_sums"] == {
        "professional_players": 129388,
        "professional_clubs": 3997,
    }
    assert benchmark["published_global_totals"] != benchmark["extracted_national_sums"]
