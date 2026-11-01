"""Source-only ATP Tour Category and Series historical reference contracts (1990–2026)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from beta_engine.domain.run_packages import CanonicalPackageDocument, PackageType
from scripts.build_atp_tour_historical_seasons import build, canonical_output

pytestmark = pytest.mark.pr_critical

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "config" / "reference_packages" / "atp_tour_1990_2026"


def _source(kind: str) -> dict:
    return json.loads((SOURCE / f"{kind}.json").read_text(encoding="utf-8"))


def test_canonical_source_boundaries_and_type_identities() -> None:
    categories, series = _source("category"), _source("series")
    category_doc = CanonicalPackageDocument.model_validate(categories)
    series_doc = CanonicalPackageDocument.model_validate(series)
    assert category_doc.package_type == PackageType.CATEGORY
    assert series_doc.package_type == PackageType.SERIES
    assert category_doc.package_id == "atp_tour_1990_2026_category"
    assert series_doc.package_id == "atp_tour_1990_2026_series"
    assert category_doc.source_fingerprint == category_doc.source_fingerprint
    assert not category_doc.children and not series_doc.children
    assert len(categories["entities"]) == 11
    assert len(series["entities"]) == 59
    assert categories["provenance"]["reference_span"] == {"from": 1990, "to": 2026}
    assert series["provenance"]["runtime_status"].startswith("data_only_")
    assert all(e["payload"].get("not_squash_rules") for e in series["entities"])


def test_no_external_tennis_or_separate_challenger_tour_entries() -> None:
    cats, series = _source("category"), _source("series")
    ids = {e["source_entity_id"] for e in cats["entities"]} | {
        e["source_entity_id"] for e in series["entities"]
    }
    for forbidden in (
        "grand_slam", "australian_open", "roland_garros", "wimbledon",
        "us_open", "challenger_50", "challenger_75", "challenger_100",
        "challenger_125", "challenger_175", "challenger_pre2023",
        "itf_m15", "itf_m25", "davis_cup", "laver_cup", "united_cup",
        "pre_open_amateur_circuit", "pre_open_professional_circuit",
        "wct_historical_circuit", "grand_prix_historical_circuit",
    ):
        assert forbidden not in ids
    cats_by_id = {x["source_entity_id"]: x for x in cats["entities"]}
    for entity in series["entities"]:
        refs = {r["source_entity_id"] for r in entity["references"]}
        periods = entity["payload"]["history_periods"]
        assert len(periods) > 0
        assert refs == {p["category_id"] for p in periods}
        assert all(p["category_id"] in cats_by_id for p in periods)
        assert all(1990 <= p["from"] <= p["to"] <= 2026 for p in periods)
        assert all(p["source_url"].startswith("https://") for p in periods)
        assert all(r["source_package_id"] == cats["package_id"] for r in entity["references"])
        assert all(r["expected_entity_kind"] == "tennis.category.reference.v1" for r in entity["references"])


def test_2026_tour_event_roster_is_ranked_tour_plus_atp_operated_finals() -> None:
    rows = build(_source("category"), _source("series"))["seasons"]
    current = rows[-1]
    assert current["year"] == 2026
    assert Counter(current["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 16,
        "atp_250": 29,
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert current["source_coverage"].startswith("partial_")
    assert current["edition_assertion"].startswith("none;")


def test_37_annual_snapshots_historical_category_transitions_and_unchanged_source() -> None:
    categories, series = _source("category"), _source("series")
    snapshot = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    assert snapshot == build(categories, series)
    assert len(snapshot["seasons"]) == 37
    assert canonical_output(snapshot) == (SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8")
    by_year = {s["year"]: s for s in snapshot["seasons"]}
    assert set(by_year) == set(range(1990, 2027))
    assert "atp_championship_single_week" in by_year[1990]["category_ids"]
    assert "atp_world_series" in by_year[1990]["category_ids"]
    assert "tennis_masters_series" in by_year[2000]["category_ids"]
    assert "atp_international_series_gold" in by_year[2008]["category_ids"]
    assert "atp_masters_1000" in by_year[2009]["category_ids"]
    assert "atp_500" in by_year[2026]["category_ids"]
    assert "grand_slam" not in by_year[2026]["category_ids"]
    assert by_year[1994]["series_category_ids"]["stockholm"] == "atp_championship_single_week"
    assert by_year[1995]["series_category_ids"]["essen_masters"] == "atp_championship_single_week"
    assert by_year[1996]["series_category_ids"]["stuttgart_indoor_masters"] == "atp_championship_single_week"
    assert by_year[2002]["series_category_ids"]["madrid"] == "tennis_masters_series"
    assert by_year[2008]["series_category_ids"]["hamburg"] == "tennis_masters_series"
    assert by_year[2009]["series_category_ids"]["hamburg"] == "atp_500"
    assert by_year[2024]["series_category_ids"]["munich"] == "atp_250"
    assert by_year[2025]["series_category_ids"]["munich"] == "atp_500"
    assert by_year[2026]["series_category_ids"]["munich"] == "atp_500"
    assert "unverified" in snapshot["historical_absence_semantics"]


def test_builder_rejects_corrupted_history_without_modifying_source() -> None:
    categories, series = _source("category"), _source("series")
    import copy
    corrupted = copy.deepcopy(series)
    corrupted["entities"][0]["payload"]["history_periods"][0]["category_id"] = "grand_slam"
    with pytest.raises(ValueError, match="Invalid Series Category reference"):
        build(categories, corrupted)
    assert build(categories, series)["seasons_count"] == 37


def test_all_37_years_have_nine_historical_top_tier_series_identity_slots() -> None:
    seasons = build(_source("category"), _source("series"))["seasons"]
    top_category = {
        "atp_championship_single_week",
        "tennis_masters_series",
        "atp_masters_1000",
    }
    for season in seasons:
        year = season["year"]
        top = {
            series_id for series_id, category_id in season["series_category_ids"].items()
            if category_id in top_category
        }
        assert len(top) == 9, (year, top)
        assert "hamburg" in top if year <= 2008 else "shanghai" in top
        if year <= 1994:
            assert "stockholm" in top
        elif year == 1995:
            assert "essen_masters" in top
        elif year <= 2001:
            assert "stuttgart_indoor_masters" in top
        elif year <= 2008:
            assert "madrid" in top
        else:
            assert "madrid" in top


def test_2024_to_2026_500_upgrades_match_official_atp_tier_counts() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    for year, count in ((2024, 13), (2025, 16), (2026, 16)):
        level = years[year]["series_category_ids"]
        assert sum(v == "atp_500" for v in level.values()) == count
    for id in ("dallas", "doha", "munich"):
        assert years[2024]["series_category_ids"][id] == "atp_250"
        assert years[2025]["series_category_ids"][id] == "atp_500"
    for id in ("halle", "queens_club"):
        assert years[2014]["series_category_ids"][id] == "atp_250"
        assert years[2015]["series_category_ids"][id] == "atp_500"
    assert years[2014]["series_category_ids"]["rio"] == "atp_500"


def test_recorded_cancelled_2020_series_are_members_but_not_played_editions() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    y2020 = years[2020]
    assert {
        "indian_wells", "miami", "monte_carlo", "madrid", "canadian_open",
        "shanghai", "halle", "queens_club", "beijing", "chengdu",
        "next_gen_atp_finals",
    }.issubset(set(y2020["known_not_held_series_ids"]))
    assert all(series_id in y2020["series_category_ids"]
               for series_id in y2020["known_not_held_series_ids"])
    assert "hangzhou" not in y2020["known_not_held_series_ids"]
    assert y2020["edition_assertion"].startswith("none;")


def test_cancelled_year_without_effective_category_fails_closed() -> None:
    import copy
    categories, series = _source("category"), _source("series")
    bad = copy.deepcopy(series)
    entity = next(e for e in bad["entities"] if e["source_entity_id"] == "hangzhou")
    entity["payload"]["not_held_years_known"] = [2020]
    with pytest.raises(ValueError, match="Cancellation without effective Series category"):
        build(categories, bad)


def test_st_petersburg_one_off_2020_upgrade_and_2022_boundary() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    assert years[1999]["series_category_ids"]["st_petersburg"] == "atp_world_series"
    assert years[2000]["series_category_ids"]["st_petersburg"] == "atp_international_series"
    assert years[2009]["series_category_ids"]["st_petersburg"] == "atp_250"
    assert "st_petersburg" not in years[2014]["series_category_ids"]
    assert years[2019]["series_category_ids"]["st_petersburg"] == "atp_250"
    assert years[2020]["series_category_ids"]["st_petersburg"] == "atp_500"
    assert years[2021]["series_category_ids"]["st_petersburg"] == "atp_250"
    assert "st_petersburg" not in years[2022]["series_category_ids"]
    assert "next_gen_atp_finals" in years[2020]["known_not_held_series_ids"]
