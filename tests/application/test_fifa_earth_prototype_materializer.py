from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.materialize_fifa_earth_prototype import audit_anchor_transitions, materialise

pytestmark = pytest.mark.pr_critical

ANCHORS = Path("config/earth_research/fifa_earth_prototype_anchors_v2.json")
COUNTRY_INDEX = Path("config/world_packages/real_world/countries/index.json")


def _load() -> dict:
    return json.loads(ANCHORS.read_text(encoding="utf-8"))


def _earth_codes() -> set[str]:
    return set(json.loads(COUNTRY_INDEX.read_text(encoding="utf-8"))["country_codes"])


def _materialise() -> dict:
    return materialise(_load(), earth_country_codes=_earth_codes())


def test_prototype_materialises_complete_histories_for_review_set() -> None:
    result = _materialise()

    assert set(result["countries"]) == {"CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"}
    assert sum(len(history["years"]) for history in result["countries"].values()) == 9 * 72
    assert sum(
        len(year["ratings"])
        for history in result["countries"].values()
        for year in history["years"].values()
    ) == 3888

    assert result["countries"]["USA"]["years"][1984]["ratings"]["competition_quality"]["method"] == "sourced_estimate"
    assert result["countries"]["USA"]["years"][1985]["ratings"]["competition_quality"]["method"] == "interpolated"


def test_prototype_keeps_attributes_independent_across_known_breaks() -> None:
    result = _materialise()

    usa_1968 = result["countries"]["USA"]["years"][1968]["ratings"]
    usa_1984 = result["countries"]["USA"]["years"][1984]["ratings"]
    assert usa_1984["squash_access"]["value"] > usa_1968["squash_access"]["value"]
    assert usa_1984["competition_quality"]["value"] < usa_1968["competition_quality"]["value"]
    assert usa_1984["elite_support"]["value"] < usa_1968["elite_support"]["value"]

    zaf_1955 = result["countries"]["ZAF"]["years"][1955]["ratings"]
    zaf_1961 = result["countries"]["ZAF"]["years"][1961]["ratings"]
    assert zaf_1961["squash_popularity"]["value"] == zaf_1955["squash_popularity"]["value"]
    assert zaf_1961["competition_quality"]["value"] < zaf_1955["competition_quality"]["value"]
    assert zaf_1961["elite_support"]["value"] < zaf_1955["elite_support"]["value"]

    fro_1979 = result["countries"]["FRO"]["years"][1979]["ratings"]
    fro_1986 = result["countries"]["FRO"]["years"][1986]["ratings"]
    assert fro_1986["squash_access"]["value"] - fro_1979["squash_access"]["value"] >= 2.0
    assert round(fro_1986["squash_popularity"]["value"] - fro_1979["squash_popularity"]["value"], 1) <= 0.2


def test_review_flags_are_clean_after_reviewed_anchor_expansion() -> None:
    flags = audit_anchor_transitions(_load())

    assert flags == []


def test_successor_states_use_local_historical_context_without_duplicate_predecessor_state() -> None:
    result = _materialise()

    cze_1992 = result["countries"]["CZE"]["years"][1992]
    svk_1992 = result["countries"]["SVK"]["years"][1992]
    cze_1993 = result["countries"]["CZE"]["years"][1993]
    svk_1993 = result["countries"]["SVK"]["years"][1993]

    assert cze_1992["historical_entity"] == "Czechoslovakia — Czech lands"
    assert svk_1992["historical_entity"] == "Czechoslovakia — Slovak lands"
    assert cze_1993["historical_entity"] == "Czech Republic / Czechia"
    assert svk_1993["historical_entity"] == "Slovakia"

    cze_values = {name: evidence["value"] for name, evidence in cze_1992["ratings"].items()}
    svk_values = {name: evidence["value"] for name, evidence in svk_1992["ratings"].items()}
    assert cze_values != svk_values
    assert "not duplicated" in cze_1992["territory_mapping_note"]
    assert "not copied" in svk_1992["territory_mapping_note"]


def test_senegal_long_gap_is_split_by_historical_anchors() -> None:
    raw = _load()
    years = sorted(int(year) for year in raw["countries"]["SEN"]["anchors"])

    for year in (1968, 1986, 1990, 1992, 2000, 2002, 2003, 2006, 2009):
        assert year in years

    result = _materialise()
    sen = result["countries"]["SEN"]["years"]

    assert sen[2002]["ratings"]["competition_quality"]["value"] > sen[2000]["ratings"]["competition_quality"]["value"]
    assert sen[2002]["ratings"]["development_quality"]["value"] - sen[2000]["ratings"]["development_quality"]["value"] <= 0.3
    assert sen[2003]["ratings"]["development_quality"]["value"] > sen[2002]["ratings"]["development_quality"]["value"]
    assert sen[2009]["ratings"]["elite_support"]["value"] > sen[2006]["ratings"]["elite_support"]["value"]


def test_big_count_2006_cross_country_access_calibration() -> None:
    raw = _load()
    result = _materialise()

    for code in {"CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"}:
        assert "fifa-big-count-2006" in raw["countries"][code]["anchors"]["2006"]["source_ids"]

    access = {
        code: result["countries"][code]["years"][2006]["ratings"]["squash_access"]["value"]
        for code in result["countries"]
    }
    assert access["FRO"] > access["SVK"] > access["CZE"] > access["USA"] > access["ZAF"] > access["SEN"] > access["JPN"] > access["IND"]
    assert access["MAR"] < access["SEN"]
    assert access["MAR"] > access["IND"]

    popularity = {
        code: result["countries"][code]["years"][2006]["ratings"]["squash_popularity"]["value"]
        for code in result["countries"]
    }
    assert popularity["ZAF"] > popularity["USA"]
    assert popularity["SEN"] > popularity["USA"]
    assert popularity["CZE"] > popularity["USA"]
