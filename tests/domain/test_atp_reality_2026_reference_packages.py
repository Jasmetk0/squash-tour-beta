"""Boundary tests for optional, source-only ATP 2026 Category/Series documents."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageType

ROOT = Path(__file__).resolve().parents[2] / "config" / "reference_packages" / "atp_reality_2026"


def _load(name: str) -> CanonicalPackageDocument:
    data = json.loads((ROOT / f"{name}.json").read_text(encoding="utf-8"))
    return CanonicalPackageDocument.model_validate(data)


def test_atp_reality_2026_documents_are_source_only_canonical_packages() -> None:
    categories, series = _load("category"), _load("series")
    assert categories.package_type == PackageType.CATEGORY
    assert series.package_type == PackageType.SERIES
    assert categories.package_id == "atp_reality_2026_category"
    assert series.package_id == "atp_reality_2026_series"
    assert categories.package_id != series.package_id
    assert categories.source_version == series.source_version == 1
    assert categories.provenance["runtime_status"].startswith("data_only_")
    assert series.provenance["runtime_status"].startswith("data_only_")
    assert categories.source_fingerprint == categories.source_fingerprint
    assert series.source_fingerprint == series.source_fingerprint
    assert not categories.children and not series.children


def test_atp_reality_series_reference_only_existing_categories_with_matching_kind() -> None:
    categories, series = _load("category"), _load("series")
    category_ids = {entity.source_entity_id for entity in categories.entities}
    assert len(categories.entities) == 16
    assert len(category_ids) == len(categories.entities)
    assert all(entity.entity_kind == "tennis.category.reference.v1" for entity in categories.entities)
    assert len(series.entities) == 63
    assert len({entity.source_entity_id for entity in series.entities}) == 63
    for entity in series.entities:
        assert entity.entity_kind == "tennis.series.reference.v1"
        assert entity.payload["reference_year"] == 2026
        assert entity.payload["not_calendar_editions"] is True
        assert len(entity.references) == 1
        reference = entity.references[0]
        assert reference.source_package_id == categories.package_id
        assert reference.source_entity_id in category_ids
        assert reference.source_entity_id == entity.payload["category_id_2026"]
        assert reference.expected_entity_kind == "tennis.category.reference.v1"
        assert reference.minimum_schema_version == 1


def test_atp_reality_2026_event_structure_and_external_governance_are_not_conflated() -> None:
    categories, series = _load("category"), _load("series")
    by_type = Counter(e.payload["category_id_2026"] for e in series.entities)
    assert by_type == {
        "grand_slam": 4,
        "atp_masters_1000": 9,
        "atp_500": 16,
        "atp_250": 29,
        "atp_finals": 1,
        "next_gen_finals": 1,
        "united_cup": 1,
        "laver_cup": 1,
        "davis_cup": 1,
    }
    cat = {e.source_entity_id: e.payload for e in categories.entities}
    assert cat["grand_slam"]["event_family"] == "external"
    assert cat["grand_slam"]["singles_winner_or_maximum_points_2026"] == 2000
    assert cat["atp_finals"]["points_interpretation"] == "undefeated_round_robin_maximum"
    assert cat["atp_finals"]["singles_winner_or_maximum_points_2026"] == 1500
    assert cat["united_cup"]["points_interpretation"] == "conditional_match_based_maximum"
    assert cat["laver_cup"]["singles_winner_or_maximum_points_2026"] == 0
    assert cat["davis_cup"]["governing_body"] == "ITF"
    assert cat["itf_m25"]["governing_body"] == "ITF"
    assert all(e.payload["not_squash_rules"] for e in categories.entities)
    assert all(e.payload["not_squash_rules"] for e in series.entities)
    assert all("TBD" not in e.payload["name"] for e in series.entities)
