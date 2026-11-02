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
    assert len(series["entities"]) == 95
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
    assert "hangzhou" in y2020["known_not_held_series_ids"]  # Zhuhai licence before 2024 move
    assert y2020["edition_assertion"].startswith("none;")


def test_cancelled_year_without_effective_category_fails_closed() -> None:
    import copy
    categories, series = _source("category"), _source("series")
    bad = copy.deepcopy(series)
    entity = next(e for e in bad["entities"] if e["source_entity_id"] == "hangzhou")
    entity["payload"]["not_held_years_known"] = [2017]  # Pre-Zhuhai history is not documented
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


def test_2024_and_2025_played_atp_250_rosters_reconcile_to_atp_archives() -> None:
    seasons = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    expected = {
        2024: {"atp_masters_1000": 9, "atp_500": 13, "atp_250": 38, "atp_finals": 1, "next_gen_finals": 1},
        2025: {"atp_masters_1000": 9, "atp_500": 16, "atp_250": 30, "atp_finals": 1, "next_gen_finals": 1},
        2026: {"atp_masters_1000": 9, "atp_500": 16, "atp_250": 29, "atp_finals": 1, "next_gen_finals": 1},
    }
    for year, category_counts in expected.items():
        assert Counter(seasons[year]["series_category_ids"].values()) == category_counts
    assert len(seasons[2024]["series_category_ids"]) == 62
    assert len(seasons[2025]["series_category_ids"]) == 57
    assert len(seasons[2026]["series_category_ids"]) == 56

    # ATP published June 2025 overview omitted Hangzhou; its own 2025
    # results archive and tournament article establish that edition.
    assert seasons[2024]["series_category_ids"]["hangzhou"] == "atp_250"
    assert seasons[2025]["series_category_ids"]["hangzhou"] == "atp_250"
    assert seasons[2026]["series_category_ids"]["hangzhou"] == "atp_250"


def test_2024_2025_2026_historical_tour_licences_and_discontinued_events() -> None:
    seasons = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    d24, d25, d26 = (seasons[year]["series_category_ids"] for year in (2024, 2025, 2026))
    # Two DIFFERENT ATP 250 identities operated from Lyon in 2024 and 2026:
    # 2024 clay Lyon licence versus Marseille indoor event moved in 2026.
    assert d24["lyon_old"] == "atp_250"
    assert d24["lyon"] == "atp_250"  # Marseille licence, NOT 2024 Lyon clay
    assert d25["lyon"] == "atp_250"  # Marseille 2025
    assert d26["lyon"] == "atp_250"  # Relocated to Lyon 2026
    assert "lyon_old" not in d25 and "lyon_old" not in d26
    assert d24["brussels"] == "atp_250"  # Played in Antwerp in 2024
    assert d25["brussels"] == "atp_250"  # Relocated to Brussels in 2025

    for discontinued in ("cordoba", "newport", "atlanta"):
        assert d24[discontinued] == "atp_250"
        assert discontinued not in d25
    assert d24["estoril"] == "atp_250"
    assert "estoril" not in d25
    assert d26["estoril"] == "atp_250"
    for historic in ("belgrade", "metz"):
        assert d24[historic] == "atp_250"
        assert d25[historic] == "atp_250"
        assert historic not in d26


def test_2024_2025_atp_250_intervals_are_backed_by_official_atp_archives() -> None:
    source = _source("series")
    provenance = source["provenance"]["calendar_validation_2024_2025"]
    assert provenance["singles_main_tour_250_count_by_year"] == {
        "2024": 38, "2025": 30
    }
    assert "atptour.com" in provenance["source_2024"]
    assert "atptour.com" in provenance["source_2025"]
    for year in (2024, 2025):
        active = [
            e for e in source["entities"]
            if any(p["from"] <= year <= p["to"] and p["category_id"] == "atp_250"
                   for p in e["payload"]["history_periods"])
        ]
        assert len(active) == (38 if year == 2024 else 30)
        for entity in active:
            intervals = entity["payload"]["history_periods"]
            record = next(p for p in intervals
                          if p["from"] <= year <= p["to"] and p["category_id"] == "atp_250")
            assert record["source_url"].startswith("https://")



def test_2023_played_tour_250_and_500_roster_matches_official_archive() -> None:
    yearly = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    assert Counter(yearly[2023]["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 13,
        "atp_250": 38,
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert len(yearly[2023]["series_category_ids"]) == 62
    evidence = _source("series")["provenance"]["calendar_validation_2023"]
    assert evidence["singles_main_tour_250_count"] == 38
    assert evidence["atp_500_count"] == 13
    assert evidence["masters_count"] == 9
    assert "atptour.com" in evidence["source_2023"]


def test_2023_two_adelaide_events_and_2024_venue_moves_keep_stable_identity() -> None:
    yearly = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    d23, d24 = yearly[2023]["series_category_ids"], yearly[2024]["series_category_ids"]
    for id in ("adelaide", "adelaide_2", "hong_kong", "banja_luka", "sofia"):
        assert d23[id] == "atp_250"
    assert "adelaide_2" not in d24
    assert d24["hong_kong"] == "atp_250"  # Pune licence moved to Hong Kong
    assert "banja_luka" not in d24
    assert "sofia" not in d24

    # ATP approved explicit relocations: these should NOT mint new
    # Series IDs or fabricate two simultaneous tournaments.
    for id in ("hangzhou", "almaty"):
        assert d23[id] == "atp_250"
        assert d24[id] == "atp_250"
    doc = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in doc["entities"]}
    assert [row["city"] for row in by_id["hangzhou"]["historical_host_change"]] == ["Zhuhai", "Hangzhou"]
    assert [row["city"] for row in by_id["almaty"]["historical_host_change"]] == ["Nur-Sultan", "Nur-Sultan", "Astana", "Astana", "Almaty"]
    assert d23["lyon_old"] == "atp_250"  # Original Lyon clay event
    assert d23["lyon"] == "atp_250"  # Marseille event (later moved to Lyon)


def test_2022_one_year_250_licences_and_cancelled_china_tour() -> None:
    by_year = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    d22 = by_year[2022]["series_category_ids"]
    six_temporary = {
        "san_diego_2022", "seoul_2022", "tel_aviv_2022",
        "florence_2022", "gijon_2022", "naples_2022",
    }
    assert all(d22[x] == "atp_250" for x in six_temporary)
    assert all(x not in by_year[2023]["series_category_ids"] for x in six_temporary)
    assert d22["almaty"] == "atp_500"  # Nur-Sultan / Astana, one-year upgrade
    assert by_year[2023]["series_category_ids"]["almaty"] == "atp_250"
    assert d22["shanghai"] == "atp_masters_1000"
    assert d22["beijing"] == "atp_500"
    assert d22["chengdu"] == "atp_250"
    assert d22["hangzhou"] == "atp_250"  # At that time Zhuhai licence
    assert {"shanghai", "beijing", "chengdu", "hangzhou"} <= set(
        by_year[2022]["known_not_held_series_ids"]
    )
    # A suspended ATP 500 is not an additional played 500 title.
    candidates = {id for id, category in d22.items() if category == "atp_500"}
    assert len(candidates) == 14  # 13 played plus cancelled Beijing
    assert candidates & set(by_year[2022]["known_not_held_series_ids"]) == {"beijing"}


def test_2022_st_petersburg_to_astana_licence_transfer_is_explicitly_linked() -> None:
    series = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in series["entities"]}
    previous = by_id["st_petersburg"]["licence_lineage"]
    current = by_id["almaty"]["licence_lineage"]
    assert previous["successor_source_entity_id"] == "almaty"
    assert current["predecessor_source_entity_id"] == "st_petersburg"
    assert previous["effective_from"] == current["effective_from"] == 2022
    assert previous["source_url"] == current["source_url"]
    assert "st_petersburg" not in {
        e["source_entity_id"] for e in series["entities"]
        if any(p["from"] <= 2022 <= p["to"] for p in e["payload"]["history_periods"])
    }
    assert len(series["provenance"]["historical_exceptions_2022"]["one_year_250_licences"]) == 6


def test_2022_all_played_atp_250_and_cancelled_scheduled_entries_are_distinct() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    row = years[2022]
    current = row["series_category_ids"]
    assert Counter(current.values()) == {
        "atp_250": 44, # 42 actually played plus cancelled Zhuhai/Chengdu
        "atp_500": 14, # 13 played plus cancelled Beijing
        "atp_masters_1000": 9, # 8 played plus cancelled Shanghai
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert len(current) == 69
    assert set(row["known_not_held_series_ids"]) == {
        "beijing", "chengdu", "hangzhou", "shanghai"
    }
    evidence = _source("series")["provenance"]["calendar_validation_2022"]
    assert evidence["played_atp_250_count"] == 42
    assert evidence["scheduled_250_identity_count"] == 44
    assert evidence["played_atp_500_count"] == 13
    assert evidence["played_masters_count"] == 8
    assert "atptour.com" in evidence["archive_source_url"]
    assert (
        sum(cat == "atp_250" and id not in row["known_not_held_series_ids"]
            for id, cat in current.items())
        == 42
    )


def test_2022_melbourne_sydney_adelaide_and_belgrade_do_not_conflate_licences() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    d22, d23, d24 = (years[year]["series_category_ids"] for year in (2022, 2023, 2024))
    for id in ("adelaide", "adelaide_2", "melbourne_2022", "sydney_2022",
               "banja_luka"):
        assert d22[id] == "atp_250"
    assert d23["adelaide"] == d23["adelaide_2"] == "atp_250"
    for id in ("melbourne_2022", "sydney_2022"):
        assert id not in d23
        assert id not in d24
    assert d24["belgrade"] == "atp_250"
    assert d22["lyon_old"] == d22["lyon"] == "atp_250"
    assert d22["brussels"] == "atp_250"
    assert d22["sofia"] == "atp_250"


def test_2021_played_tour_categories_and_cancelled_2021_differ() -> None:
    years = {s["year"]: s for s in build(_source("category"), _source("series"))["seasons"]}
    row = years[2021]
    categories = Counter(row["series_category_ids"].values())
    assert categories == {
        "atp_250": 42,  # 39 played + cancelled Houston, Chengdu, Zhuhai
        "atp_500": 12,  # 9 played + cancelled Rio, Beijing, Basel
        "atp_masters_1000": 9,  # 8 played + cancelled Shanghai
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert set(row["known_not_held_series_ids"]) == {
        "basel", "beijing", "chengdu", "hangzhou", "houston", "rio", "shanghai",
    }
    source = _source("series")["provenance"]["calendar_validation_2021"]
    assert source["played_atp_250_count"] == 39
    assert source["played_atp_500_count"] == 9
    assert source["played_masters_count"] == 8
    for category_id, count in (
        ("atp_250", 39), ("atp_500", 9), ("atp_masters_1000", 8)
    ):
        assert sum(
            category == category_id and id not in row["known_not_held_series_ids"]
            for id, category in row["series_category_ids"].items()
        ) == count


def test_2021_two_belgrade_and_two_melbourne_events_remain_distinct() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    d21, d22 = (years[y]["series_category_ids"] for y in (2021, 2022))
    assert all(d21[name] == "atp_250" for name in (
        "melbourne_1_2021", "melbourne_2_2021",
        "belgrade_clay_2021", "belgrade_2_2021",
        "singapore_2021", "marbella_2021", "almaty",
    ))
    assert d22["melbourne_2022"] == "atp_250"
    assert d22["banja_luka"] == "atp_250"
    for name in ("melbourne_1_2021", "melbourne_2_2021",
                 "belgrade_clay_2021", "belgrade_2_2021",
                 "singapore_2021", "marbella_2021"):
        assert name not in d22
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert [row["city"] for row in by_id["almaty"]["historical_host_change"]] == [
        "Nur-Sultan", "Nur-Sultan", "Astana", "Astana", "Almaty"
    ]


def test_pune_to_hong_kong_retains_one_series_id_from_2022_to_2026() -> None:
    years = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    for year in range(2022, 2027):
        assert years[year]["series_category_ids"]["hong_kong"] == "atp_250"
        assert "pune" not in years[year]["series_category_ids"]
    source = _source("series")
    ids = {e["source_entity_id"] for e in source["entities"]}
    assert "pune" not in ids
    assert "hong_kong" in ids
    hong_kong = next(e for e in source["entities"]
                     if e["source_entity_id"] == "hong_kong")["payload"]
    assert [row["city"] for row in hong_kong["historical_host_change"]] == [
        "Chennai", "Chennai", "Chennai", "Pune", "Pune", "Pune", "Pune", "Pune", "Hong Kong"
    ]
    assert "atptour.com" in hong_kong["historical_licence_source_url"]


def test_belgrade_2022_to_banja_luka_2023_is_one_series() -> None:
    by_year = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    assert by_year[2022]["series_category_ids"]["banja_luka"] == "atp_250"
    assert by_year[2023]["series_category_ids"]["banja_luka"] == "atp_250"
    assert "belgrade_clay_2022" not in {
        e["source_entity_id"] for e in _source("series")["entities"]
    }
    assert by_year[2024]["series_category_ids"]["belgrade"] == "atp_250"
    source = next(e for e in _source("series")["entities"]
                  if e["source_entity_id"] == "banja_luka")
    assert [x["city"] for x in source["payload"]["historical_host_change"]] == [
        "Belgrade", "Banja Luka"
    ]
    assert "atptour.com" in source["payload"]["historical_licence_source_url"]


def test_2020_played_tour_tier_roster_from_official_atp_archive() -> None:
    by_year = {s["year"]: s for s in build(_source("category"), _source("series"))["seasons"]}
    y2020 = by_year[2020]
    actual = Counter({
        tier: sum(
            category == tier and series_id not in y2020["known_not_held_series_ids"]
            for series_id, category in y2020["series_category_ids"].items()
        )
        for tier in ("atp_250", "atp_500", "atp_masters_1000")
    })
    assert actual == {"atp_250": 18, "atp_500": 7, "atp_masters_1000": 3}
    assert y2020["played_tier_roster_validation"]["played_counts"] == {
        "atp_250": 18, "atp_500": 7, "atp_masters_1000": 3
    }
    assert y2020["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    source = _source("series")["provenance"]["calendar_validation_2020"]
    assert source["played_atp_250_count"] == 18
    assert source["played_atp_500_count"] == 7
    assert source["played_masters_count"] == 3
    assert "atptour.com" in source["results_archive_url"]
    assert y2020["edition_assertion"].startswith("none;")


def test_2020_cologne_sardinia_nur_sultan_one_year_events_and_nyc_venue() -> None:
    by_year = {s["year"]: s for s in build(_source("category"), _source("series"))["seasons"]}
    y2019, y2020, y2021 = (by_year[y]["series_category_ids"] for y in (2019, 2020, 2021))
    for identity in ("cologne_1_2020", "cologne_2_2020", "sardinia_2020"):
        assert y2020[identity] == "atp_250"
        assert identity not in y2019
        assert identity not in y2021
    assert y2020["almaty"] == "atp_250"  # Played in Nur-Sultan, not Almaty
    assert y2020["dallas"] == "atp_250"  # New York licence, moved to Dallas 2022
    assert y2020["hong_kong"] == "atp_250"  # Pune licence, moved to Hong Kong 2024
    assert y2020["st_petersburg"] == "atp_500"  # Temporary pandemic promotion
    assert y2020["cincinnati"] == "atp_masters_1000"
    series = _source("series")
    by_id = {x["source_entity_id"]: x["payload"] for x in series["entities"]}
    assert [host["city"] for host in by_id["dallas"]["historical_host_change"]] == ["Memphis", "Memphis", "Memphis", "New York", "New York", "New York", "Dallas"]
    assert [host["city"] for host in by_id["cincinnati"]["historical_host_change"]] == ["New York", "Cincinnati"]
    assert [host["city"] for host in by_id["almaty"]["historical_host_change"]] == [
        "Nur-Sultan", "Nur-Sultan", "Astana", "Astana", "Almaty"
    ]


def test_coverage_gates_reject_false_historical_completeness() -> None:
    import copy
    categories, source = _source("category"), _source("series")
    rows = {s["year"]: s for s in build(categories, source)["seasons"]}
    for year in range(1990, 2015):
        assert rows[year]["played_tier_roster_validation"]["status"] == "unverified_incomplete"
        assert rows[year]["played_tier_roster_validation"]["played_counts"] is None
    assert rows[2026]["played_tier_roster_validation"]["status"] == "provisional_calendar_not_final_results"
    for year in range(2015, 2026):
        assert rows[year]["played_tier_roster_validation"]["status"] == (
            "played_tour_tiers_reconciled_to_atp_results_archive"
        )
        assert rows[year]["played_tier_roster_validation"]["not_an_edition_calendar"] is True

    corrupted = copy.deepcopy(source)
    unheld = next(e for e in corrupted["entities"] if e["source_entity_id"] == "cologne_2_2020")
    unheld["payload"]["not_held_years_known"] = [2020]
    with pytest.raises(ValueError, match="played-tier roster mismatch"):
        build(categories, corrupted)


def test_2019_atp_tour_9_13_39_full_event_census() -> None:
    year = next(s for s in build(_source("category"), _source("series"))["seasons"]
                if s["year"] == 2019)
    assert Counter(year["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 13,
        "atp_250": 39,
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert year["known_not_held_series_ids"] == []
    assert len(year["series_category_ids"]) == 63
    assert year["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 13, "atp_250": 39,
    }
    assert year["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    evidence = _source("series")["provenance"]["calendar_validation_2019"]
    assert evidence["played_atp_masters_1000_count"] == 9
    assert evidence["played_atp_500_count"] == 13
    assert evidence["played_atp_250_count"] == 39


def test_2019_venue_licence_boundary_for_budapest_new_york_and_antalya() -> None:
    yearly = {s["year"]: s["series_category_ids"]
              for s in build(_source("category"), _source("series"))["seasons"]}
    a19, a20, a21 = yearly[2019], yearly[2020], yearly[2021]
    assert a19["belgrade_clay_2021"] == "atp_250"  # Budapest 2019
    assert a21["belgrade_clay_2021"] == "atp_250"  # Belgrade 2021
    assert "belgrade_clay_2021" not in a20  # No fabricated played edition
    assert a19["dallas"] == a20["dallas"] == "atp_250"  # New York licences
    assert a19["hong_kong"] == a20["hong_kong"] == "atp_250"  # Pune licences
    assert a19["antalya_2019"] == "atp_250"
    assert "antalya_2019" not in a21
    assert a21["antalya_2021"] == "atp_250"  # Different one-year 2021 event
    assert a19["sydney_2019"] == "atp_250"
    assert "sydney_2019" not in yearly[2022]
    assert yearly[2022]["sydney_2022"] == "atp_250"
    assert a19["moscow"] == a21["moscow"] == "atp_250"
    assert "moscow" not in a20
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert [r["city"] for r in by_id["belgrade_clay_2021"]["historical_host_change"]] == [
        "Bucharest", "Bucharest", "Budapest", "Budapest", "Budapest", "Belgrade"
    ]
    assert [r["city"] for r in by_id["dallas"]["historical_host_change"]] == [
        "Memphis", "Memphis", "Memphis", "New York", "New York", "New York", "Dallas"
    ]


def test_explicit_played_roster_gate_rejects_fabricated_2019_cancellation() -> None:
    import copy
    categories = _source("category")
    source = copy.deepcopy(_source("series"))
    entity = next(e for e in source["entities"] if e["source_entity_id"] == "sao_paulo")
    entity["payload"]["not_held_years_known"] = [2019]
    with pytest.raises(ValueError, match="played-tier roster mismatch"):
        build(categories, source)


def test_2018_atp_official_calendar_reconciles_all_64_atp_series() -> None:
    seasons = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    y2018 = seasons[2018]
    assert Counter(y2018["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 13,
        "atp_250": 40,
        "atp_finals": 1,
        "next_gen_finals": 1,
    }
    assert len(y2018["series_category_ids"]) == 64
    assert y2018["known_not_held_series_ids"] == []
    assert y2018["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 13, "atp_250": 40,
    }
    assert y2018["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    source = _source("series")["provenance"]["calendar_validation_2018"]
    assert "atptour.com" in source["official_calendar_url"]
    assert source["played_atp_250_count"] == 40
    assert source["played_atp_500_count"] == 13


def test_2018_quito_to_2019_cordoba_and_distinct_southern_venues() -> None:
    years = {r["year"]: r["series_category_ids"]
             for r in build(_source("category"), _source("series"))["seasons"]}
    d18, d19 = years[2018], years[2019]
    assert d18["cordoba"] == "atp_250"  # Quito 2018
    assert d19["cordoba"] == "atp_250"  # Cordoba 2019
    assert d18["shenzhen_2018"] == "atp_250"
    assert "shenzhen_2018" not in d19
    assert d19["hangzhou"] == "atp_250"  # Zhuhai 2019
    assert d18["istanbul_2018"] == "atp_250"
    assert "istanbul_2018" not in d19
    assert d18["sydney_2019"] == d19["sydney_2019"] == "atp_250"
    assert d18["antalya_2019"] == d19["antalya_2019"] == "atp_250"
    assert d18["belgrade_clay_2021"] == d19["belgrade_clay_2021"] == "atp_250"
    doc = _source("series")
    by = {e["source_entity_id"]: e["payload"] for e in doc["entities"]}
    assert [p["city"] for p in by["cordoba"]["historical_host_change"]] == [
        "Quito", "Quito", "Quito", "Quito", "Córdoba"
    ]
    assert [p["city"] for p in by["dallas"]["historical_host_change"]] == [
        "Memphis", "Memphis", "Memphis", "New York", "New York", "New York", "Dallas"
    ]


def test_2018_census_rejects_false_cancellation() -> None:
    import copy
    categories, source = _source("category"), copy.deepcopy(_source("series"))
    entity = next(e for e in source["entities"] if e["source_entity_id"] == "shenzhen_2018")
    entity["payload"]["not_held_years_known"] = [2018]
    with pytest.raises(ValueError, match="played-tier roster mismatch"):
        build(categories, source)


@pytest.mark.parametrize("year,atp250,finals_count", [
    (2016, 39, 1),
    (2017, 40, 2),
])
def test_2016_2017_atp_tour_archive_complete_rosters(
    year: int, atp250: int, finals_count: int
) -> None:
    by_year = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    annual = by_year[year]
    assert Counter(annual["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 13,
        "atp_250": atp250,
        "atp_finals": 1,
        **({"next_gen_finals": 1} if year == 2017 else {}),
    }
    assert len(annual["series_category_ids"]) == 9 + 13 + atp250 + finals_count
    assert annual["known_not_held_series_ids"] == []
    assert annual["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 13, "atp_250": atp250
    }
    assert annual["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    provenance = _source("series")["provenance"][f"calendar_validation_{year}"]
    assert provenance["played_atp_250_count"] == atp250
    assert provenance["played_atp_500_count"] == 13
    assert "atptour.com" in provenance["archive_source_url"]


def test_2016_2017_licence_moves_are_explicit_not_fabricated_separate_events() -> None:
    annual = {r["year"]: r["series_category_ids"] for r in
              build(_source("category"), _source("series"))["seasons"]}
    old, new = annual[2016], annual[2017]
    assert "next_gen_atp_finals" not in old
    assert new["next_gen_atp_finals"] == "next_gen_finals"
    for id in ("hong_kong", "dallas", "cordoba", "lyon_old",
               "eastbourne", "belgrade_clay_2021"):
        assert old[id] == new[id] == "atp_250"

    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    expected_hosts = {
        "hong_kong": ("Chennai", "Chennai"),
        "dallas": ("Memphis", "Memphis"),
        "cordoba": ("Quito", "Quito"),
        "belgrade_clay_2021": ("Bucharest", "Budapest"),
        "lyon_old": ("Nice", "Lyon"),
        "eastbourne": ("Nottingham", "Eastbourne"),
    }
    for identity, (old_city, next_city) in expected_hosts.items():
        host_map = {
            record["year"]: record["city"]
            for record in by_id[identity]["historical_host_change"]
        }
        assert host_map[2016] == old_city, identity
        assert host_map[2017] == next_city, identity
    assert "bucharest" not in old
    assert "bucharest" not in new
    assert annual[2024]["bucharest"] == "atp_250"
    assert "nottingham_2016" not in old  # Correct stable ID: Eastbourne


def test_2016_2017_scope_excludes_olympic_and_non_atp_events() -> None:
    annual = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    source = _source("series")
    for year in (2016, 2017):
        ids = set(annual[year]["series_category_ids"])
        for forbidden in ("rio_olympics", "davis_cup", "hopman_cup",
                          "laver_cup", "grand_slam", "australian_open"):
            assert forbidden not in ids
    assert source["provenance"]["calendar_validation_2016"]["next_gen_finals_did_not_exist"]


def test_2015_atp_tour_full_9_13_39_census() -> None:
    seasons = {row["year"]: row for row in
               build(_source("category"), _source("series"))["seasons"]}
    row = seasons[2015]
    assert Counter(row["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 13,
        "atp_250": 39,
        "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 62
    assert row["known_not_held_series_ids"] == []
    assert "next_gen_atp_finals" not in row["series_category_ids"]
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 13, "atp_250": 39,
    }
    p = _source("series")["provenance"]["calendar_validation_2015"]
    assert p["played_atp_masters_1000_count"] == 9
    assert p["played_atp_500_count"] == 13
    assert p["played_atp_250_count"] == 39


def test_2015_five_verified_2016_tour_250_licence_transfers_are_single_series() -> None:
    season = {year["year"]: year["series_category_ids"] for year in
              build(_source("category"), _source("series"))["seasons"]}
    by_id = {e["source_entity_id"]: e["payload"] for e in _source("series")["entities"]}
    changes = {
        "sofia": ("Zagreb", "Sofia"),
        "marrakech": ("Casablanca", "Marrakech"),
        "los_cabos": ("Bogotá", "Los Cabos"),
        "chengdu": ("Kuala Lumpur", "Chengdu"),
        "brussels": ("Valencia", "Antwerp"),
    }
    for series_id, (old_city, new_city) in changes.items():
        assert season[2015][series_id] == season[2016][series_id] == "atp_250"
        hosts = {h["year"]: h["city"] for h in by_id[series_id]["historical_host_change"]}
        assert hosts[2015] == old_city, series_id
        assert hosts[2016] == new_city, series_id
    assert all(id not in season[2015] for id in ("valencia_2015", "casablanca_2015",
                                              "bogota_2015", "kuala_lumpur_2015", "zagreb_2015"))


def test_2015_2016_cancelled_or_unverified_sport_event_not_fabricated() -> None:
    annual = {year["year"]: year for year in
              build(_source("category"), _source("series"))["seasons"]}
    assert annual[2015]["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    for year in (2015, 2016):
        assert "rio_olympics" not in annual[year]["series_category_ids"]
        assert "davis_cup" not in annual[year]["series_category_ids"]
        assert "australian_open" not in annual[year]["series_category_ids"]
    assert "next_gen_atp_finals" not in annual[2015]["series_category_ids"]
