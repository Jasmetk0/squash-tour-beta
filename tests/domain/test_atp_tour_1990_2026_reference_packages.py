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


def _host_by_year(payload: dict) -> dict[int, str]:
    """Date-keyed host assertions tolerate adding still older verified years."""
    return {entry["year"]: entry["city"]
            for entry in payload["historical_host_change"]}



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
    assert len(series["entities"]) == 125
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
    hosts = _host_by_year(hong_kong)
    assert hosts[2017] == "Chennai"
    assert hosts[2018] == hosts[2020] == hosts[2023] == "Pune"
    assert hosts[2024] == "Hong Kong"
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
    hosts = _host_by_year(by_id["dallas"])
    assert hosts[2008] == hosts[2017] == "Memphis"
    assert hosts[2018] == hosts[2020] == "New York"
    assert hosts[2022] == "Dallas"
    assert [host["city"] for host in by_id["cincinnati"]["historical_host_change"]
            if 2020 <= host["year"] <= 2021] == ["New York", "Cincinnati"]
    assert [host["city"] for host in by_id["almaty"]["historical_host_change"]] == [
        "Nur-Sultan", "Nur-Sultan", "Astana", "Astana", "Almaty"
    ]


def test_coverage_gates_reject_false_historical_completeness() -> None:
    import copy
    categories, source = _source("category"), _source("series")
    rows = {s["year"]: s for s in build(categories, source)["seasons"]}
    for year in range(1990, 1997):
        assert rows[year]["played_tier_roster_validation"]["status"] == "unverified_incomplete"
        assert rows[year]["played_tier_roster_validation"]["played_counts"] is None
    assert rows[2026]["played_tier_roster_validation"]["status"] == "provisional_calendar_not_final_results"
    for year in range(2008, 2026):
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
    bucharest_hosts = _host_by_year(by_id["belgrade_clay_2021"])
    assert bucharest_hosts[2015] == bucharest_hosts[2016] == "Bucharest"
    assert bucharest_hosts[2017] == bucharest_hosts[2019] == "Budapest"
    assert bucharest_hosts[2021] == "Belgrade"
    dallas_hosts = _host_by_year(by_id["dallas"])
    assert dallas_hosts[2017] == "Memphis"
    assert dallas_hosts[2018] == dallas_hosts[2019] == "New York"
    assert dallas_hosts[2022] == "Dallas"


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
    cordoba_hosts = _host_by_year(by["cordoba"])
    assert cordoba_hosts[2009] == "Viña del Mar"
    assert cordoba_hosts[2010] == cordoba_hosts[2011] == "Santiago"
    assert cordoba_hosts[2012] == cordoba_hosts[2014] == "Viña del Mar"
    assert cordoba_hosts[2015] == cordoba_hosts[2018] == "Quito"
    assert cordoba_hosts[2019] == "Córdoba"
    dallas_hosts = _host_by_year(by["dallas"])
    assert dallas_hosts[2008] == dallas_hosts[2017] == "Memphis"
    assert dallas_hosts[2018] == dallas_hosts[2020] == "New York"
    assert dallas_hosts[2022] == "Dallas"


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


def test_2014_atp_tour_official_results_9_masters_11_500_39_250() -> None:
    rows = {row["year"]: row for row in
            build(_source("category"), _source("series"))["seasons"]}
    row = rows[2014]
    assert Counter(row["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 11,
        "atp_250": 39,
        "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 60
    assert "next_gen_atp_finals" not in row["series_category_ids"]
    assert row["known_not_held_series_ids"] == []
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 11, "atp_250": 39,
    }
    evidence = _source("series")["provenance"]["calendar_validation_2014"]
    assert "atptour.com" in evidence["archive_source_url"]
    assert evidence["played_atp_500_count"] == 11
    assert evidence["played_atp_250_count"] == 39


def test_2014_to_2015_500_tier_promotions_and_valencia_demotion() -> None:
    years = {r["year"]: r["series_category_ids"]
             for r in build(_source("category"), _source("series"))["seasons"]}
    old, new = years[2014], years[2015]
    for id in ("halle", "queens_club", "vienna"):
        assert old[id] == "atp_250"
        assert new[id] == "atp_500"
    assert old["brussels"] == "atp_500"  # Valencia 2014
    assert new["brussels"] == "atp_250"  # Valencia 2015
    assert years[2016]["brussels"] == "atp_250"  # Antwerp
    assert old["rio"] == "atp_500"  # ATP 500 debuted 2014
    assert "st_petersburg" not in old
    assert "duesseldorf_2014" in old
    assert "duesseldorf_2014" not in new


def test_2014_vina_del_mar_to_quito_to_cordoba_licence_history() -> None:
    years = {r["year"]: r["series_category_ids"]
             for r in build(_source("category"), _source("series"))["seasons"]}
    assert years[2014]["cordoba"] == "atp_250"
    assert years[2015]["cordoba"] == "atp_250"
    assert years[2018]["cordoba"] == "atp_250"
    assert years[2019]["cordoba"] == "atp_250"
    by = {e["source_entity_id"]: e["payload"] for e in _source("series")["entities"]}
    locations = {
        h["year"]: h["city"]
        for h in by["cordoba"]["historical_host_change"]
    }
    expected_hosts = {
        2014: "Viña del Mar", 2015: "Quito",
        2017: "Quito", 2018: "Quito", 2019: "Córdoba"
    }
    assert all(locations[year] == city for year, city in expected_hosts.items())
    assert by["duesseldorf_2014"]["history_scope"].startswith("2014_verified_")
    estoril_2014 = next(
        record for record in by["estoril"]["historical_host_change"]
        if record["year"] == 2014
    )
    assert estoril_2014["city"] == "Oeiras"
    assert "rtp.pt" in estoril_2014["source_url"]


def test_2013_top_level_atp_tour_61_played_events_and_correct_tiers() -> None:
    source = _source("series")
    y = next(r for r in build(_source("category"), source)["seasons"] if r["year"] == 2013)
    assert Counter(y["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 11,
        "atp_250": 40,
        "atp_finals": 1,
    }
    assert len(y["series_category_ids"]) == 61
    assert y["known_not_held_series_ids"] == []
    assert y["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert y["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 11, "atp_250": 40
    }
    evidence = source["provenance"]["calendar_validation_2013"]
    assert evidence["played_atp_250_count"] == 40
    assert evidence["played_atp_500_count"] == 11
    assert "nos.nl" in evidence["detailed_contemporary_tier_listing_url"]


def test_2013_memphis_was_atp_500_and_2014_memphis_was_atp_250() -> None:
    years = {row["year"]: row["series_category_ids"] for row in
             build(_source("category"), _source("series"))["seasons"]}
    assert years[2013]["dallas"] == "atp_500"  # Memphis
    assert years[2014]["dallas"] == "atp_250"  # Memphis
    assert years[2019]["dallas"] == "atp_250"  # New York
    assert years[2025]["dallas"] == "atp_500"  # Dallas
    assert years[2013]["brussels"] == "atp_500"  # Valencia
    assert years[2014]["brussels"] == "atp_500"
    assert years[2015]["brussels"] == "atp_250"
    for id in ("halle", "queens_club", "vienna"):
        assert years[2013][id] == "atp_250"
        assert years[2014][id] == "atp_250"
        assert years[2015][id] == "atp_500"


def test_2013_san_jose_bangkok_and_los_angeles_are_not_backfilled() -> None:
    years = {row["year"]: row["series_category_ids"] for row in
             build(_source("category"), _source("series"))["seasons"]}
    for id in ("san_jose_2013", "los_angeles_2013", "bangkok_2013"):
        assert years[2013][id] == "atp_250"
        assert id not in years[2014]
    assert years[2013]["duesseldorf_2014"] == "atp_250"
    assert years[2014]["duesseldorf_2014"] == "atp_250"
    assert years[2013]["cordoba"] == "atp_250"  # Viña del Mar
    assert years[2014]["cordoba"] == "atp_250"  # Viña del Mar
    assert years[2015]["cordoba"] == "atp_250"  # Quito
    assert "rio" not in years[2013]  # Rio ATP 500 began 2014


def test_2012_real_atp_tour_roster_9_masters_11_500_40_250() -> None:
    years = {row["year"]: row for row in
             build(_source("category"), _source("series"))["seasons"]}
    annual = years[2012]
    assert Counter(annual["series_category_ids"].values()) == {
        "atp_masters_1000": 9,
        "atp_500": 11,
        "atp_250": 40,
        "atp_finals": 1,
    }
    assert len(annual["series_category_ids"]) == 61
    assert annual["known_not_held_series_ids"] == []
    assert annual["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9,
        "atp_500": 11,
        "atp_250": 40,
    }
    assert annual["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    evidence = _source("series")["provenance"]["calendar_validation_2012"]
    assert "atptour.com" in evidence["archive_source_url"]
    assert evidence["played_atp_250_count"] == 40
    assert evidence["played_atp_500_count"] == 11


def test_2012_belgrade_serbia_open_is_not_automatically_later_belgrade() -> None:
    years = {r["year"]: r["series_category_ids"]
             for r in build(_source("category"), _source("series"))["seasons"]}
    assert years[2012]["belgrade_2012"] == "atp_250"
    assert "belgrade_2012" not in years[2013]
    assert "belgrade_2012" not in years[2021]
    assert years[2012]["belgrade_clay_2021"] == "atp_250"  # Bucharest
    # Bucharest and Serbia Open Belgrade are two distinct Tour events in 2012.
    assert years[2013]["san_jose_2013"] == "atp_250"
    assert years[2012]["san_jose_2013"] == "atp_250"
    for forbidden in ("olympics_2012", "world_team_cup", "davis_cup",
                      "australian_open", "french_open", "wimbledon", "us_open"):
        assert forbidden not in years[2012]
    assert years[2012]["dallas"] == "atp_500"  # Memphis
    assert years[2012]["brussels"] == "atp_500"  # Valencia
    for name in ("halle", "queens_club", "vienna"):
        assert years[2012][name] == "atp_250"


def test_2012_played_tier_gate_rejects_false_cancelled_tournament() -> None:
    import copy
    categories = _source("category")
    source = copy.deepcopy(_source("series"))
    vienna = next(e for e in source["entities"]
                  if e["source_entity_id"] == "vienna")
    vienna["payload"]["not_held_years_known"] = [2012]
    with pytest.raises(ValueError, match="played-tier roster mismatch"):
        build(categories, source)


def test_2011_played_atp_tour_9_masters_11_500_40_250() -> None:
    years = {row["year"]: row for row in
             build(_source("category"), _source("series"))["seasons"]}
    y2011 = years[2011]
    assert Counter(y2011["series_category_ids"].values()) == {
        "atp_masters_1000": 9, "atp_500": 11,
        "atp_250": 40, "atp_finals": 1,
    }
    assert len(y2011["series_category_ids"]) == 61
    assert y2011["known_not_held_series_ids"] == []
    assert y2011["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 11, "atp_250": 40,
    }
    evidence = _source("series")["provenance"]["calendar_validation_2011"]
    assert evidence["played_atp_masters_1000_count"] == 9
    assert evidence["played_atp_500_count"] == 11
    assert evidence["played_atp_250_count"] == 40
    assert "atptour.com" in evidence["archive_source_url"]


def test_2011_event_families_before_2012_relocations_remain_distinct() -> None:
    by_year = {r["year"]: r["series_category_ids"] for r in
               build(_source("category"), _source("series"))["seasons"]}
    assert by_year[2011]["johannesburg_2011"] == "atp_250"
    assert "johannesburg_2011" not in by_year[2012]
    assert by_year[2011]["belgrade_2012"] == "atp_250"
    assert by_year[2012]["belgrade_2012"] == "atp_250"
    assert "belgrade_2012" not in by_year[2013]
    assert by_year[2011]["sao_paulo"] == by_year[2012]["sao_paulo"] == "atp_250"
    assert by_year[2011]["cordoba"] == by_year[2012]["cordoba"] == "atp_250"
    by_id = {e["source_entity_id"]: e["payload"] for e in _source("series")["entities"]}
    brazil_hosts = {p["year"]: p["city"] for p in by_id["sao_paulo"]["historical_host_change"]}
    assert brazil_hosts[2011] == "Costa do Sauípe"
    assert brazil_hosts[2012] == "São Paulo"
    chile_hosts = {p["year"]: p["city"] for p in by_id["cordoba"]["historical_host_change"]}
    assert chile_hosts[2011] == "Santiago"
    assert chile_hosts[2012] == "Viña del Mar"
    belgrade_hosts = _host_by_year(by_id["belgrade_2012"])
    assert belgrade_hosts[2008] == "Amersfoort"
    assert all(belgrade_hosts[year] == "Belgrade" for year in range(2009, 2013))


def test_2011_tour_finals_and_world_team_cup_scope_is_strict() -> None:
    year = next(x for x in build(_source("category"), _source("series"))["seasons"]
                if x["year"] == 2011)
    assert year["series_category_ids"]["atp_finals"] == "atp_finals"
    for excluded in ("world_team_cup", "davis_cup", "australian_open",
                     "roland_garros", "wimbledon", "us_open", "johannesburg_challenger"):
        assert excluded not in year["series_category_ids"]
    assert "next_gen_atp_finals" not in year["series_category_ids"]


def test_2010_atp_tour_61_played_events_and_no_challengers() -> None:
    year = next(r for r in build(_source("category"), _source("series"))["seasons"]
                if r["year"] == 2010)
    assert Counter(year["series_category_ids"].values()) == {
        "atp_masters_1000": 9, "atp_500": 11,
        "atp_250": 40, "atp_finals": 1,
    }
    assert len(year["series_category_ids"]) == 61
    assert year["known_not_held_series_ids"] == []
    assert year["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 11, "atp_250": 40,
    }
    evidence = _source("series")["provenance"]["calendar_validation_2010"]
    assert "atptour.com" in evidence["archive_source_url"]
    assert evidence["played_atp_250_count"] == 40
    assert evidence["played_atp_500_count"] == 11
    assert evidence["played_atp_masters_1000_count"] == 9
    assert "davis_cup" not in year["series_category_ids"]
    assert "world_team_cup" not in year["series_category_ids"]


def test_2010_new_haven_is_same_licence_as_2011_winston_salem() -> None:
    seasons = {r["year"]: r["series_category_ids"] for r in
               build(_source("category"), _source("series"))["seasons"]}
    assert seasons[2010]["winston_salem"] == "atp_250"
    assert seasons[2011]["winston_salem"] == "atp_250"
    assert "new_haven_2010" not in seasons[2010]
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    host_rows = {p["year"]: p["city"] for p in
                 by_id["winston_salem"]["historical_host_change"]}
    assert host_rows[2010] == "New Haven"
    assert "nhregister.com" in by_id["winston_salem"]["historical_licence_source_url"]
    evidence = source["provenance"]["calendar_validation_2010"]
    assert "godeacs.com" in evidence["atp_ustatour_licence_transfer_url"]
    assert evidence["specific_transfer"]["source_id"] == "winston_salem"


def test_2010_brazil_and_chile_tour_rosters_are_historic_not_modern_cities() -> None:
    seasons = {r["year"]: r["series_category_ids"] for r in
               build(_source("category"), _source("series"))["seasons"]}
    assert seasons[2010]["sao_paulo"] == "atp_250"  # Costa do Sauipe
    assert seasons[2010]["cordoba"] == "atp_250"  # Santiago
    assert seasons[2010]["johannesburg_2011"] == "atp_250"
    assert seasons[2010]["belgrade_2012"] == "atp_250"
    assert seasons[2011]["johannesburg_2011"] == "atp_250"
    assert "johannesburg_2011" not in seasons[2012]
    by_id = {e["source_entity_id"]: e["payload"] for e in
             _source("series")["entities"]}
    chile = {x["year"]: x["city"] for x in by_id["cordoba"]["historical_host_change"]}
    brazil = {x["year"]: x["city"] for x in by_id["sao_paulo"]["historical_host_change"]}
    assert chile[2010] == chile[2011] == "Santiago"
    assert brazil[2010] == brazil[2011] == "Costa do Sauípe"
    assert brazil[2012] == "São Paulo"
    assert "new_haven_2010" not in seasons[2010]


def test_2009_inaugural_1000_500_250_roster_matches_atp_archive() -> None:
    year = next(row for row in build(_source("category"), _source("series"))["seasons"]
                if row["year"] == 2009)
    assert Counter(year["series_category_ids"].values()) == {
        "atp_masters_1000": 9, "atp_500": 11,
        "atp_250": 40, "atp_finals": 1,
    }
    assert len(year["series_category_ids"]) == 61
    assert year["known_not_held_series_ids"] == []
    assert year["played_tier_roster_validation"]["played_counts"] == {
        "atp_masters_1000": 9, "atp_500": 11, "atp_250": 40,
    }
    source = _source("series")["provenance"]["calendar_validation_2009"]
    assert "atptour.com" in source["archive_source_url"]
    assert source["played_atp_250_count"] == 40
    assert source["played_atp_500_count"] == 11
    assert source["played_atp_masters_1000_count"] == 9


def test_2009_indianapolis_to_2010_atlanta_is_same_tour_sanction() -> None:
    years = {row["year"]: row["series_category_ids"] for row in
             build(_source("category"), _source("series"))["seasons"]}
    assert years[2009]["atlanta"] == "atp_250"
    assert years[2010]["atlanta"] == "atp_250"
    assert "indianapolis_2009" not in years[2009]
    s = next(e["payload"] for e in _source("series")["entities"]
             if e["source_entity_id"] == "atlanta")
    hosts = {row["year"]: row["city"] for row in s["historical_host_change"]}
    assert hosts[2009] == "Indianapolis"
    assert "ajc.com" in s["historical_licence_source_url"]


def test_2009_lyon_indoor_to_2010_montpellier_not_other_lyons() -> None:
    years = {row["year"]: row["series_category_ids"] for row in
             build(_source("category"), _source("series"))["seasons"]}
    assert years[2009]["montpellier"] == "atp_250"
    assert years[2010]["montpellier"] == "atp_250"
    assert "lyon_old" not in years[2009]  # Nice to Lyon CLAY occurred in 2017
    assert years[2017]["lyon_old"] == "atp_250"
    assert years[2009]["lyon"] == "atp_250"  # Marseille licence, still Marseille
    assert years[2026]["lyon"] == "atp_250"  # Marseille to Lyon 2026
    source = next(e["payload"] for e in _source("series")["entities"]
                  if e["source_entity_id"] == "montpellier")
    locations = {row["year"]: row["city"] for row in
                 source["historical_host_change"]}
    assert locations[2009] == "Lyon"
    assert "lequipe.fr" in source["historical_licence_source_url"]


def test_2009_kitzbuhel_2010_challenger_and_2011_tour_resume() -> None:
    years = {row["year"]: row["series_category_ids"] for row in
             build(_source("category"), _source("series"))["seasons"]}
    assert years[2009]["kitzbuhel"] == "atp_250"
    assert "kitzbuhel" not in years[2010]  # Challenger, not Tour 250
    assert years[2011]["kitzbuhel"] == "atp_250"
    assert years[2009]["winston_salem"] == "atp_250"  # New Haven
    assert years[2010]["winston_salem"] == "atp_250"  # New Haven
    assert years[2011]["winston_salem"] == "atp_250"  # Winston-Salem


def test_2008_international_series_gold_has_nine_historic_tier_members() -> None:
    years = {row["year"]: row for row in
             build(_source("category"), _source("series"))["seasons"]}
    old = years[2008]
    assert old["played_tier_roster_validation"]["status"] == "played_tour_tiers_reconciled_to_atp_results_archive"
    assert old["played_tier_roster_validation"]["played_counts"] == {"tennis_masters_series": 9, "atp_international_series_gold": 9, "atp_international_series": 42}
    gold = {
        series_id for series_id, category in old["series_category_ids"].items()
        if category == "atp_international_series_gold"
    }
    assert gold == {
        "rotterdam", "dallas", "dubai", "acapulco", "barcelona",
        "stuttgart", "kitzbuhel", "tokyo", "vienna",
    }
    assert len(gold) == 9
    assert old["series_category_ids"]["hamburg"] == "tennis_masters_series"
    assert old["series_category_ids"]["madrid"] == "tennis_masters_series"
    assert "shanghai" not in old["series_category_ids"]
    provenance = _source("series")["provenance"]["calendar_validation_2008_partial"]
    assert provenance["documented_played_gold_count"] == 9
    assert provenance["lower_international_series_census_status"] == "COMPLETE_2008_PLAYED"
    assert "atptour.com" in provenance["official_results_archive_url"]


def test_2008_historic_gold_cannot_be_retroactively_called_2009_500() -> None:
    years = {row["year"]: row for row in
             build(_source("category"), _source("series"))["seasons"]}
    for id in ("stuttgart", "kitzbuhel", "vienna"):
        assert years[2008]["series_category_ids"][id] == "atp_international_series_gold"
        assert years[2009]["series_category_ids"][id] == "atp_250"
    for id in ("rotterdam", "dallas", "dubai", "acapulco",
               "barcelona", "tokyo"):
        assert years[2008]["series_category_ids"][id] == "atp_international_series_gold"
        assert years[2009]["series_category_ids"][id] == "atp_500"
    assert years[2008]["era"] == "tennis_masters_and_international_series"
    assert years[2009]["era"] == "atp_masters_1000_500_250"
    assert years[2008]["edition_assertion"].startswith("none;")


def test_2008_original_atp_masters_gold_and_international_played_census() -> None:
    rows = {r["year"]: r for r in
            build(_source("category"), _source("series"))["seasons"]}
    year = rows[2008]
    assert Counter(year["series_category_ids"].values()) == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 43, # Includes CANCELLED Bangalore
        "atp_finals": 1,
    }
    assert len(year["series_category_ids"]) == 62
    assert year["known_not_held_series_ids"] == ["bangalore_2008"]
    assert year["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 42,
    }
    assert sum(
        tier == "atp_international_series" and series_id != "bangalore_2008"
        for series_id, tier in year["series_category_ids"].items()
    ) == 42
    assert year["played_tier_roster_validation"]["not_an_edition_calendar"]
    source = _source("series")["provenance"]["calendar_validation_2008"]
    assert source["played_international_series_count"] == 42
    assert source["scheduled_international_series_identity_count"] == 43
    assert "atptour.com" in source["official_played_results_archive_url"]
    assert ".pdf" in source["official_calendar_snapshot_url"]


def test_2008_warsaw_not_prospective_sopot_and_bangalore_cancelled() -> None:
    source = _source("series")
    rows = {r["year"]: r for r in
            build(_source("category"), source)["seasons"]}
    assert rows[2008]["series_category_ids"]["warsaw_2008"] == "atp_international_series"
    assert "sopot_2008" not in rows[2008]["series_category_ids"]
    assert rows[2008]["series_category_ids"]["bangalore_2008"] == "atp_international_series"
    assert rows[2008]["known_not_held_series_ids"] == ["bangalore_2008"]
    assert "bangalore_2008" not in rows[2009]["series_category_ids"]
    for excluded in ("mumbai_2008_played", "beijing_olympics_2008",
                     "world_team_cup", "davis_cup", "wimbledon"):
        assert excluded not in rows[2008]["series_category_ids"]
    by = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert by["bangalore_2008"]["not_held_years_known"] == [2008]
    assert "skysports.com" in by["bangalore_2008"]["known_nonheld_source"]


def test_2008_amersfoort_to_2009_belgrade_and_adelaide_to_brisbane() -> None:
    source = _source("series")
    rows = {r["year"]: r["series_category_ids"] for r in
            build(_source("category"), source)["seasons"]}
    for id in ("belgrade_2012", "brisbane"):
        assert rows[2008][id] == "atp_international_series"
        assert rows[2009][id] == "atp_250"
    by = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert _host_by_year(by["belgrade_2012"])[2008] == "Amersfoort"
    assert _host_by_year(by["belgrade_2012"])[2009] == "Belgrade"
    assert _host_by_year(by["brisbane"])[2008] == "Adelaide"
    assert _host_by_year(by["brisbane"])[2009] == "Brisbane"


def test_2008_source_gate_refuses_false_played_result() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    warsaw = next(e for e in source["entities"]
                  if e["source_entity_id"] == "warsaw_2008")
    warsaw["payload"]["not_held_years_known"] = [2008]
    with pytest.raises(ValueError, match="played-tier roster mismatch"):
        build(_source("category"), source)


def test_2007_complete_actual_played_historical_tier_roster_and_distinct_finals() -> None:
    """All 61 played 2007 singles ATP Tour main-circuit tier events, plus Finals."""
    categories, series = _source("category"), _source("series")
    row = next(s for s in build(categories, series)["seasons"] if s["year"] == 2007)
    assert row["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 43,
    }
    assert Counter(row["series_category_ids"].values()) == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 43,
        "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 62
    assert "next_gen_atp_finals" not in row["series_category_ids"]
    assert not any(event in row["series_category_ids"] for event in (
        "australian_open", "roland_garros", "wimbledon", "us_open",
        "davis_cup", "hopman_cup", "world_team_cup",
    ))
    gold_ids = {id for id, tier in row["series_category_ids"].items()
                if tier == "atp_international_series_gold"}
    assert gold_ids == {
        "rotterdam", "dallas", "dubai", "acapulco", "barcelona",
        "stuttgart", "kitzbuhel", "tokyo", "vienna",
    }
    provenance = series["provenance"]["calendar_validation_2007"]
    assert provenance["played_international_series_count"] == 43
    assert provenance["historical_category_calendar_url"].startswith("https://")
    assert row["edition_assertion"].startswith("none;")


def test_2007_historical_hosts_and_2008_cancelled_bangalore_not_played() -> None:
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    expected_hosts = {
        "warsaw_2008": ("Sopot", "Warsaw"),
        "bangalore_2008": ("Mumbai", None),
        "brisbane": ("Adelaide", "Adelaide"),
        "hong_kong": ("Chennai", "Chennai"),
        "belgrade_2012": ("Amersfoort", "Amersfoort"),
        "atlanta": ("Indianapolis", "Indianapolis"),
        "winston_salem": ("New Haven", "New Haven"),
        "montpellier": ("Lyon", "Lyon"),
        "brussels": ("Valencia", "Valencia"),
        "belgrade_clay_2021": ("Bucharest", "Bucharest"),
    }
    for id, (city_2007, city_2008) in expected_hosts.items():
        hosts = _host_by_year(by_id[id])
        assert hosts[2007] == city_2007
        if city_2008 is not None:
            assert hosts[2008] == city_2008
    assert by_id["bangalore_2008"]["not_held_years_known"] == [2008]
    years = {s["year"]: s for s in build(_source("category"), source)["seasons"]}
    assert "bangalore_2008" in years[2007]["series_category_ids"]
    assert "bangalore_2008" in years[2008]["known_not_held_series_ids"]


def test_2007_missing_gold_or_misreported_event_is_rejected() -> None:
    import copy
    bad = copy.deepcopy(_source("series"))
    item = next(e for e in bad["entities"] if e["source_entity_id"] == "dallas")
    item["payload"]["not_held_years_known"] = [2007]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2007"):
        build(_source("category"), bad)


def test_2006_original_era_complete_played_atp_tour_tiers() -> None:
    """9 Masters + 9 Gold + 44 International; the separate Finals is not a tier."""
    category, series = _source("category"), _source("series")
    row = next(r for r in build(category, series)["seasons"] if r["year"] == 2006)
    assert row["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 44,
    }
    assert Counter(row["series_category_ids"].values()) == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 44,
        "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 63
    assert "palermo" in row["series_category_ids"]
    assert row["series_category_ids"]["palermo"] == "atp_international_series"
    assert row["edition_assertion"].startswith("none;")
    assert not any(x in row["series_category_ids"] for x in (
        "australian_open", "wimbledon", "roland_garros", "us_open",
        "davis_cup", "world_team_cup", "ho_chi_minh_city", "milan_2006",
    ))


def test_2006_palermo_and_continuous_pre_2007_city_licence_history() -> None:
    source = _source("series")
    by_id = {e["source_entity_id"]: e for e in source["entities"]}
    palermo = by_id["palermo"]
    assert palermo["payload"]["historical_surface"] == "clay"
    played_2006 = [
        p for p in palermo["payload"]["history_periods"]
        if p["from"] <= 2006 <= p["to"]
    ]
    assert len(played_2006) == 1
    assert played_2006[0]["category_id"] == "atp_international_series"
    assert played_2006[0]["source_url"] == (
        "https://www.atptour.com/en/tournaments/palermo/325/overview"
    )
    hosts = {
        "warsaw_2008": "Sopot",
        "bangalore_2008": "Mumbai",
        "belgrade_2012": "Amersfoort",
        "brisbane": "Adelaide",
        "hong_kong": "Chennai",
        "sofia": "Zagreb",
        "winston_salem": "New Haven",
        "montpellier": "Lyon",
        "lyon": "Marseille",
        "brussels": "Valencia",
        "palermo": "Palermo",
    }
    for sid, city in hosts.items():
        history = _host_by_year(by_id[sid]["payload"])
        assert history[2006] == city
    assert by_id["bangalore_2008"]["payload"]["not_held_years_known"] == [2008]
    years = {r["year"]: r for r in build(_source("category"), source)["seasons"]}
    assert "palermo" in years[2006]["series_category_ids"]
    assert "palermo" not in years[2007]["series_category_ids"]
    assert years[2006]["known_not_held_series_ids"] == []
    assert years[2008]["known_not_held_series_ids"] == ["bangalore_2008"]


def test_2006_rejects_a_mutated_played_tier_as_complete() -> None:
    import copy
    broken = copy.deepcopy(_source("series"))
    entity = next(e for e in broken["entities"] if e["source_entity_id"] == "palermo")
    entity["payload"]["not_held_years_known"] = [2006]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2006"):
        build(_source("category"), broken)

def test_2005_historical_played_tiers_and_stable_series() -> None:
    rows = {s["year"]: s for s in build(_source("category"), _source("series"))["seasons"]}
    old, next_year = rows[2005], rows[2006]
    assert old["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44,
    }
    assert old["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert Counter(old["series_category_ids"].values()) == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44, "atp_finals": 1,
    }
    assert len(old["series_category_ids"]) == 63
    assert old["series_category_ids"] == next_year["series_category_ids"]
    assert not old["known_not_held_series_ids"]
    for impossible in ("milan_2005", "vietnam_open_2005", "scottsdale_2005"):
        assert impossible not in old["series_category_ids"]


def test_2005_to_2006_real_licence_moves_keep_single_identity() -> None:
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    moves = {
        "sofia": ("Milan", "Zagreb"),
        "las_vegas_2008": ("Scottsdale", "Las Vegas"),
        "bangalore_2008": ("Ho Chi Minh City", "Mumbai"),
        "poertschach_2008": ("St. Pölten", "Pörtschach"),
    }
    for id, (from_city, to_city) in moves.items():
        hosts = _host_by_year(by_id[id])
        assert hosts[2005] == from_city
        assert hosts[2006] == to_city
    assert [p["from"] for p in by_id["palermo"]["history_periods"]
            if 2005 <= p["from"] <= 2006] == [2005, 2006]
    refs = source["provenance"]["calendar_validation_2005"]["verified_licence_relocations"]
    assert len(refs) == 4
    assert {r["series_id"] for r in refs} == set(moves)


def test_2005_fake_cancellation_breaks_played_tier_gate() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    palermo = next(e for e in source["entities"] if e["source_entity_id"] == "palermo")
    palermo["payload"]["not_held_years_known"] = [2005]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2005"):
        build(_source("category"), source)


def test_2004_source_census_full_original_categories_and_no_external_events() -> None:
    row = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}[2004]
    assert row["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44,
    }
    assert Counter(row["series_category_ids"].values()) == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44, "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 63
    assert row["known_not_held_series_ids"] == []
    for not_tour in ("australian_open", "wimbledon", "us_open", "roland_garros",
                     "world_team_cup", "athens_olympics", "davis_cup"):
        assert not_tour not in row["series_category_ids"]


def test_2004_shanghai_and_long_island_hosted_actual_source_series() -> None:
    entities = {e["source_entity_id"]: e["payload"] for e in _source("series")["entities"]}
    history = _host_by_year(entities["bangalore_2008"])
    assert history[2004] == "Shanghai"
    assert history[2005] == "Ho Chi Minh City"
    assert history[2006] == "Mumbai"
    history = _host_by_year(entities["winston_salem"])
    assert history[2004] == "Long Island"
    assert history[2005] == "New Haven"
    assert history[2010] == "New Haven"
    assert "atp_finals" != "bangalore_2008"
    assert _host_by_year(entities["atp_finals"])[2004] == "Houston"
    for id in ("bangalore_2008", "winston_salem"):
        assert [p for p in entities[id]["history_periods"]
                if p["from"] <= 2004 <= p["to"]][0]["category_id"] == (
                    "atp_international_series"
                )


def test_2004_false_cancelled_tour_event_fails_historical_tier_gate() -> None:
    import copy
    series = copy.deepcopy(_source("series"))
    entity = next(e for e in series["entities"] if e["source_entity_id"] == "palermo")
    entity["payload"]["not_held_years_known"] = [2004]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2004"):
        build(_source("category"), series)


def test_2003_original_atp_tiers_with_copenhagen_not_beijing() -> None:
    rows = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    row = rows[2003]
    assert row["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert row["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44,
    }
    assert Counter(row["series_category_ids"].values()) == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 44, "atp_finals": 1,
    }
    assert len(row["series_category_ids"]) == 63
    assert row["series_category_ids"]["copenhagen_2003"] == "atp_international_series"
    assert "beijing" not in row["series_category_ids"]
    assert "copenhagen_2003" not in rows[2004]["series_category_ids"]
    assert row["known_not_held_series_ids"] == []


def test_2003_master_hosts_and_copenhagen_excludes_false_licence_link() -> None:
    series = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in series["entities"]}
    assert _host_by_year(by_id["canadian_open"])[2003] == "Montreal"
    assert _host_by_year(by_id["canadian_open"])[2004] == "Toronto"
    assert _host_by_year(by_id["atp_finals"])[2003] == "Houston"
    assert _host_by_year(by_id["bangalore_2008"])[2003] == "Shanghai"
    assert _host_by_year(by_id["winston_salem"])[2003] == "Long Island"
    copenhagen = by_id["copenhagen_2003"]
    assert copenhagen["historical_host_city"] == "Copenhagen"
    assert copenhagen["historical_country_code"] == "DNK"
    assert [p["from"] for p in copenhagen["history_periods"]
            if p["from"] == 2003] == [2003]
    assert "NOT linked" in series["provenance"]["calendar_validation_2003"]["legal_continuity"]


def test_2003_fake_copenhagen_cancellation_rejected() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    item = next(e for e in source["entities"] if e["source_entity_id"] == "copenhagen_2003")
    item["payload"]["not_held_years_known"] = [2003]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2003"):
        build(_source("category"), source)


def test_2002_original_played_tier_census_and_hong_kong_identity_isolation() -> None:
    rows = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    r02, r03 = rows[2002], rows[2003]
    assert r02["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert r02["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 43,
    }
    assert Counter(r02["series_category_ids"].values()) == {
        "tennis_masters_series": 9, "atp_international_series_gold": 9,
        "atp_international_series": 43, "atp_finals": 1,
    }
    assert len(r02["series_category_ids"]) == 62
    for source_id in ("hong_kong", "hong_kong_salem_2002"):
        assert r02["series_category_ids"][source_id] == "atp_international_series"
    for only_2003 in ("metz", "bangalore_2008"):
        assert only_2003 not in r02["series_category_ids"]
        assert only_2003 in r03["series_category_ids"]
    assert "hong_kong_salem_2002" not in r03["series_category_ids"]
    assert not r02["known_not_held_series_ids"]


def test_2002_verified_tour_moves_and_actual_host_not_outdated_calendar() -> None:
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    moves = {
        "brussels": ("Mallorca", "Valencia"),
        "bangkok_2013": ("Tashkent", "Bangkok"),
    }
    for sid, (before, after) in moves.items():
        hosts = _host_by_year(by_id[sid])
        assert hosts[2002] == before
        assert hosts[2003] == after
    assert _host_by_year(by_id["canadian_open"])[2002] == "Toronto"
    assert _host_by_year(by_id["canadian_open"])[2003] == "Montreal"
    assert _host_by_year(by_id["atp_finals"])[2002] == "Shanghai"
    assert _host_by_year(by_id["atp_finals"])[2003] == "Houston"
    assert _host_by_year(by_id["hong_kong"])[2002] == "Chennai"
    assert _host_by_year(by_id["hong_kong_salem_2002"])[2002] == "Hong Kong"
    assert "mallorca" not in {
        sid for sid in build(_source("category"), source)["seasons"][12]["series_category_ids"]
    }
    evidence = source["provenance"]["calendar_validation_2002"]
    assert evidence["played_international_series_count"] == 43
    assert len(evidence["verified_licence_moves"]) == 2
    assert {x["source_id"] for x in evidence["verified_licence_moves"]} == set(moves)


def test_2002_fake_salems_cancelled_not_mistaken_for_chennai() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    hong_kong = next(
        e for e in source["entities"]
        if e["source_entity_id"] == "hong_kong_salem_2002"
    )
    hong_kong["payload"]["not_held_years_known"] = [2002]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2002"):
        build(_source("category"), source)


def test_2001_historical_played_original_9_9_46_census() -> None:
    rows = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    r = rows[2001]
    assert r["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 46,
    }
    assert Counter(r["series_category_ids"].values()) == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 9,
        "atp_international_series": 46, "atp_finals": 1,
    }
    assert len(r["series_category_ids"]) == 65
    assert r["series_category_ids"]["stuttgart_indoor_masters"] == "tennis_masters_series"
    assert r["series_category_ids"]["stuttgart"] == "atp_international_series_gold"
    assert "madrid" not in r["series_category_ids"]
    assert r["series_category_ids"]["atlanta"] == "atp_international_series"
    assert r["series_category_ids"]["atlanta_verizon_2001"] == "atp_international_series"
    assert r["series_category_ids"]["bogota_colombia_2001"] == "atp_international_series"
    for id in ("bogota_colombia_2001", "atlanta_verizon_2001", "bangalore_2008"):
        assert id not in rows[2002]["series_category_ids"]


def test_2001_stuttgart_masters_vs_clay_gold_and_sydney_finals() -> None:
    series = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in series["entities"]}
    assert _host_by_year(by_id["stuttgart_indoor_masters"])[2001] == "Stuttgart"
    assert _host_by_year(by_id["madrid"])[2002] == "Madrid"
    assert _host_by_year(by_id["stuttgart"])[2001] == "Stuttgart"
    assert _host_by_year(by_id["atp_finals"])[2001] == "Sydney"
    assert _host_by_year(by_id["atp_finals"])[2002] == "Shanghai"
    assert _host_by_year(by_id["canadian_open"])[2001] == "Montreal"
    assert _host_by_year(by_id["canadian_open"])[2002] == "Toronto"
    assert _host_by_year(by_id["bangalore_2008"])[2001] == "Shanghai"
    assert 2002 not in _host_by_year(by_id["bangalore_2008"])
    source = series["provenance"]["calendar_validation_2001"]["indoor_masters_license_transition"]
    assert source["source_id_2001"] == "stuttgart_indoor_masters"
    assert source["source_id_2002"] == "madrid"
    assert "emol.com" in source["source_url"]


def test_2001_false_bogota_cancellation_rejected() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    entity = next(e for e in source["entities"] if e["source_entity_id"] == "bogota_colombia_2001")
    entity["payload"]["not_held_years_known"] = [2001]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2001"):
        build(_source("category"), source)


def test_2000_original_9_11_44_tour_tiers_and_reclassification() -> None:
    yrs = {r["year"]: r for r in build(_source("category"), _source("series"))["seasons"]}
    r = yrs[2000]
    assert r["played_tier_roster_validation"]["played_counts"] == {
        "tennis_masters_series": 9,
        "atp_international_series_gold": 11,
        "atp_international_series": 44,
    }
    assert Counter(r["series_category_ids"].values()) == {
        "tennis_masters_series": 9, "atp_international_series_gold": 11,
        "atp_international_series": 44, "atp_finals": 1,
    }
    assert len(r["series_category_ids"]) == 65
    for id in ("sofia", "atlanta", "washington"):
        assert r["series_category_ids"][id] == "atp_international_series_gold"
        assert yrs[2001]["series_category_ids"][id] == "atp_international_series"
    assert r["series_category_ids"]["dubai"] == "atp_international_series"
    assert yrs[2001]["series_category_ids"]["dubai"] == "atp_international_series_gold"
    for id in ("san_marino_2000", "toulouse_2000", "brighton_2000"):
        assert r["series_category_ids"][id] == "atp_international_series"
        assert id not in yrs[2001]["series_category_ids"]


def test_2000_original_hosts_and_two_distinct_london_events() -> None:
    src = _source("series")
    by = {e["source_entity_id"]: e["payload"] for e in src["entities"]}
    city = lambda sid, year: _host_by_year(by[sid])[year]
    assert city("atp_finals", 2000) == "Lisbon"
    assert city("atp_finals", 2001) == "Sydney"
    assert city("sofia", 2000) == "London"
    assert city("sofia", 2001) == "Milan"
    assert city("queens_club", 2000) == "London"
    assert city("houston", 2000) == "Orlando"
    assert city("houston", 2001) == "Houston"
    assert city("acapulco", 2000) == "Mexico City"
    assert city("acapulco", 2001) == "Acapulco"
    assert city("cordoba", 2000) == "Santiago"
    assert city("cordoba", 2001) == "Viña del Mar"
    assert city("belgrade_2012", 2000) == "Amsterdam"
    assert city("belgrade_2012", 2001) == "Amersfoort"
    assert city("canadian_open", 2000) == "Toronto"
    assert city("stuttgart_indoor_masters", 2000) == "Stuttgart"
    assert city("stuttgart", 2000) == "Stuttgart"
    assert city("hong_kong_salem_2002", 2000) == "Hong Kong"
    assert city("hong_kong", 2000) == "Chennai"
    p = src["provenance"]["calendar_validation_2000"]
    assert p["played_international_series_gold_count"] == 11
    assert p["doubles_only_world_championship_host"] == "Bengaluru"
    assert "independent.co.uk" in p["verified_london_gold_to_milan_international_url"]


def test_2000_cancelled_brighton_should_fail_category_census() -> None:
    import copy
    data = copy.deepcopy(_source("series"))
    x = next(e for e in data["entities"] if e["source_entity_id"] == "brighton_2000")
    x["payload"]["not_held_years_known"] = [2000]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 2000"):
        build(_source("category"), data)


def test_1999_super9_championship_world_series_original_played_roster() -> None:
    source = _source("series")
    rows = {r["year"]: r for r in build(_source("category"), source)["seasons"]}
    old, modern = rows[1999], rows[2000]
    assert old["played_tier_roster_validation"]["status"] == (
        "played_tour_tiers_reconciled_to_atp_results_archive"
    )
    assert old["played_tier_roster_validation"]["played_counts"] == {
        "atp_championship_single_week": 9,
        "atp_championship_series": 11,
        "atp_world_series": 45,
    }
    assert Counter(old["series_category_ids"].values()) == {
        "atp_championship_single_week": 9, "atp_championship_series": 11,
        "atp_world_series": 45, "atp_finals": 1,
    }
    assert len(old["series_category_ids"]) == 66
    assert "Super 9" in old["played_tier_roster_validation"]["scope"]
    assert old["series_category_ids"]["sofia"] == "atp_championship_series"
    assert modern["series_category_ids"]["sofia"] == "atp_international_series_gold"
    assert old["series_category_ids"]["singapore_1999"] == "atp_championship_series"
    for absent in ("australian_open", "wimbledon", "roland_garros", "us_open",
                   "grand_slam_cup", "davis_cup", "world_team_cup",
                   "atp_world_doubles_championships"):
        assert absent not in old["series_category_ids"]


def test_1999_bournemouth_to_2000_brighton_and_hannover_singles() -> None:
    source = _source("series")
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    bournemouth = by_id["brighton_2000"]
    hosts = _host_by_year(bournemouth)
    assert hosts[1999] == "Bournemouth"
    assert hosts[2000] == "Brighton"
    assert [row["surface"] for row in bournemouth["historical_surface_change"]] == [
        "green_clay_outdoor", "hard_indoor"
    ]
    assert _host_by_year(by_id["atp_finals"])[1999] == "Hannover"
    assert _host_by_year(by_id["atp_finals"])[2000] == "Lisbon"
    assert _host_by_year(by_id["canadian_open"])[1999] == "Montreal"
    assert _host_by_year(by_id["canadian_open"])[2000] == "Toronto"
    assert _host_by_year(by_id["sofia"])[1999] == "London"
    assert _host_by_year(by_id["sofia"])[2000] == "London"
    evidence = source["provenance"]["calendar_validation_1999"]
    assert evidence["atp_singles_finals_host"] == "Hannover"
    assert evidence["atp_doubles_worlds_host"] == "Hartford"
    assert len(evidence["documented_same_licence_1999_to_2000"]) == 1
    assert _host_by_year(by_id["prague_1999"])[1999] == "Prague"
    assert by_id["prague_1999"]["cancelled_following_year"]["year"] == 2000
    assert "prague_1999" not in {
        sid for sid in build(_source("category"), source)["seasons"][10]["series_category_ids"]
    }


def test_1999_source_tier_gate_refuses_cancelled_played_singapore() -> None:
    import copy
    source = copy.deepcopy(_source("series"))
    event = next(e for e in source["entities"] if e["source_entity_id"] == "singapore_1999")
    event["payload"]["not_held_years_known"] = [1999]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 1999"):
        build(_source("category"), source)


def test_1998_original_played_tour_census_and_distinct_historical_events() -> None:
    """1998 stays in ATP Super 9 / Championship Series / World Series vocabulary."""
    categories, source = _source("category"), _source("series")
    rows = {r["year"]: r for r in build(categories, source)["seasons"]}
    y98 = rows[1998]
    assert y98["played_tier_roster_validation"]["played_counts"] == {
        "atp_championship_single_week": 9,
        "atp_championship_series": 12,
        "atp_world_series": 52,
    }
    assert Counter(y98["series_category_ids"].values()) == {
        "atp_championship_single_week": 9,
        "atp_championship_series": 12,
        "atp_world_series": 52,
        "atp_finals": 1,
    }
    assert y98["played_tier_roster_validation"]["status"] == "played_tour_tiers_reconciled_to_atp_results_archive"
    assert y98["played_tier_roster_validation"]["not_an_edition_calendar"]
    assert y98["series_category_ids"]["rotterdam"] == "atp_world_series"
    assert rows[1999]["series_category_ids"]["rotterdam"] == "atp_championship_series"
    assert y98["series_category_ids"]["singapore_1999"] == "atp_championship_series"
    assert y98["series_category_ids"]["new_haven_1998"] == "atp_championship_series"
    assert y98["series_category_ids"]["winston_salem"] == "atp_world_series"
    assert y98["series_category_ids"]["acapulco"] == "atp_world_series"
    assert "acapulco" not in rows[1999]["series_category_ids"]
    assert y98["series_category_ids"]["montpellier"] == "atp_world_series"
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert _host_by_year(by_id["montpellier"])[1998] == "Lyon"
    assert _host_by_year(by_id["split_1998"])[1998] == "Split"
    assert _host_by_year(by_id["singapore_1999"])[1998] == "Singapore"
    assert _host_by_year(by_id["acapulco"])[1998] == "Mexico City"
    assert _host_by_year(by_id["atp_finals"])[1998] == "Hannover"
    assert _host_by_year(by_id["canadian_open"])[1998] == "Toronto"
    assert "grand_slam" not in y98["series_category_ids"]
    assert not set(y98["series_category_ids"]) & {"hopman_cup", "davis_cup"}


def test_1998_original_tier_gate_rejects_reclassification_and_false_cancellation() -> None:
    import copy
    categories, source = _source("category"), _source("series")
    corrupted = copy.deepcopy(source)
    event = next(e for e in corrupted["entities"] if e["source_entity_id"] == "rotterdam")
    period = next(p for p in event["payload"]["history_periods"] if p["from"] == 1998)
    period["category_id"] = "atp_championship_series"
    with pytest.raises(ValueError, match="played-tier roster mismatch in 1998"):
        build(categories, corrupted)
    cancelled = copy.deepcopy(source)
    event = next(e for e in cancelled["entities"] if e["source_entity_id"] == "new_haven_1998")
    event["payload"]["not_held_years_known"] = [1998]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 1998"):
        build(categories, cancelled)


def test_1997_original_played_atp_tour_full_census_and_historical_venues() -> None:
    """1997 counts retain original Super 9, Championship and World category identities."""
    categories, source = _source("category"), _source("series")
    years = {r["year"]: r for r in build(categories, source)["seasons"]}
    y97 = years[1997]
    assert y97["played_tier_roster_validation"]["status"] == "played_tour_tiers_reconciled_to_atp_results_archive"
    assert y97["played_tier_roster_validation"]["played_counts"] == {
        "atp_championship_single_week": 9,
        "atp_championship_series": 12,
        "atp_world_series": 53,
    }
    assert Counter(y97["series_category_ids"].values()) == {
        "atp_championship_single_week": 9,
        "atp_championship_series": 12,
        "atp_world_series": 53,
        "atp_finals": 1,
    }
    assert y97["played_tier_roster_validation"]["not_an_edition_calendar"]
    assert y97["series_category_ids"]["rotterdam"] == "atp_world_series"
    assert y97["series_category_ids"]["singapore_1999"] == "atp_championship_series"
    assert y97["series_category_ids"]["antwerp_1998"] == "atp_championship_series"
    assert y97["series_category_ids"]["philadelphia_1998"] == "atp_championship_series"
    assert y97["series_category_ids"]["sofia"] == "atp_championship_series"
    assert y97["series_category_ids"]["new_haven_1998"] == "atp_championship_series"
    assert y97["series_category_ids"]["winston_salem"] == "atp_world_series"
    assert y97["series_category_ids"]["beijing_1997"] == "atp_world_series"
    assert "beijing" not in y97["series_category_ids"]
    by_id = {e["source_entity_id"]: e["payload"] for e in source["entities"]}
    assert _host_by_year(by_id["sofia"])[1997] == "Milan"
    assert _host_by_year(by_id["montpellier"])[1997] == "Lyon"
    assert _host_by_year(by_id["delray_beach"])[1997] == "Coral Springs"
    assert _host_by_year(by_id["split_1998"])[1997] == "Zagreb"
    assert _host_by_year(by_id["split_1998"])[1998] == "Split"
    assert _host_by_year(by_id["brussels"])[1997] == "Marbella"
    assert _host_by_year(by_id["brussels"])[1998] == "Mallorca"
    assert _host_by_year(by_id["canadian_open"])[1997] == "Montreal"
    assert _host_by_year(by_id["canadian_open"])[1998] == "Toronto"
    assert _host_by_year(by_id["atp_finals"])[1997] == "Hannover"


def test_1997_original_category_census_is_fail_closed() -> None:
    import copy
    categories, source = _source("category"), _source("series")
    wrong = copy.deepcopy(source)
    target = next(e for e in wrong["entities"] if e["source_entity_id"] == "sofia")
    period = next(p for p in target["payload"]["history_periods"] if p["from"] == 1997)
    period["category_id"] = "atp_world_series"
    with pytest.raises(ValueError, match="played-tier roster mismatch in 1997"):
        build(categories, wrong)
    cancelled = copy.deepcopy(source)
    target = next(e for e in cancelled["entities"] if e["source_entity_id"] == "split_1998")
    target["payload"]["not_held_years_known"] = [1997]
    with pytest.raises(ValueError, match="played-tier roster mismatch in 1997"):
        build(categories, cancelled)
