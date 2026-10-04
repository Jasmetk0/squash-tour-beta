from __future__ import annotations

import pytest

from scripts.build_fifa_big_count_benchmark import build_benchmark

pytestmark = pytest.mark.pr_critical


def test_big_count_benchmark_covers_only_safely_reconciled_earth_entities() -> None:
    benchmark = build_benchmark()

    assert benchmark["source_row_count"] == 208
    assert benchmark["safe_earth_entity_count"] == 201
    assert len(benchmark["unobserved_earth_codes"]) == 49
    assert benchmark["manual_review_associations"] == [
        "Curacao",
        "Netherlands Antilles",
        "Serbia",
        "Sudan",
    ]

    gbr = benchmark["entities"]["GBR"]
    assert gbr["identity_status"] == "aggregate"
    assert gbr["source_associations"] == [
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
    ]
    assert gbr["values"]["All Players"] == 4_850_569
    assert gbr["values"]["Registered players"] == 1_703_369
    assert gbr["values"]["Clubs"] == 51_966


def test_big_count_benchmark_normalises_participation_by_earth_population() -> None:
    benchmark = build_benchmark()
    entities = benchmark["entities"]

    assert entities["FRO"]["metrics"]["all_players_per_1000"] == 167.04
    assert entities["FRO"]["metrics"]["registered_players_per_1000"] == 117.51
    assert entities["FRO"]["metrics"]["clubs_per_million"] == 825.49

    assert entities["CZE"]["metrics"]["all_players_per_1000"] == 100.96
    assert entities["CZE"]["metrics"]["registered_players_per_1000"] == 66.60
    assert entities["CZE"]["metrics"]["clubs_per_million"] == 398.66

    assert entities["USA"]["metrics"]["all_players_per_1000"] == 81.92
    assert entities["USA"]["metrics"]["registered_players_per_1000"] == 14.02
    assert entities["USA"]["metrics"]["clubs_per_million"] == 30.13

    assert entities["IND"]["metrics"]["all_players_per_1000"] == 17.55
    assert entities["IND"]["metrics"]["registered_players_per_1000"] == 0.33
    assert entities["IND"]["metrics"]["clubs_per_million"] == 5.58


def test_big_count_benchmark_never_materialises_blocked_historical_rows() -> None:
    benchmark = build_benchmark()

    source_associations = {
        association
        for entity in benchmark["entities"].values()
        for association in entity["source_associations"]
    }
    assert "Netherlands Antilles" not in source_associations
    assert "Curacao" not in source_associations
    assert "Serbia" not in source_associations
    assert "Sudan" not in source_associations
