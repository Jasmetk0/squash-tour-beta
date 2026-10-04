"""Materialise a reviewable FIFA Earth anchor prototype into CountryRatingHistory years.

This is research tooling. It does not modify canonical fifa_earth.json or build an
official World Package.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import EarthSportResearch
from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES

FIRST_YEAR = 1955
LAST_YEAR = 2026
DEFAULT_COUNTRY_INDEX = Path("config/world_packages/real_world/countries/index.json")
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
RANK_CONFIDENCE = {1: "low", 2: "medium", 3: "high"}


def _rating(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("prototype rating must be numeric")
    number = float(value)
    if not 1 <= number <= 10 or round(number, 1) != number:
        raise ValueError("prototype rating must be 1..10 with at most one decimal")
    return number


def _load_earth_country_codes(path: Path) -> set[str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    codes = raw.get("country_codes")
    if not isinstance(codes, list) or not codes or any(not isinstance(code, str) for code in codes):
        raise ValueError("Earth country index must contain a non-empty country_codes list")
    return set(codes)


def _validate_anchor_file(raw: dict[str, Any], *, earth_country_codes: set[str]) -> None:
    if raw.get("schema_version") != "fifa_earth_anchor_prototype.v2":
        raise ValueError("unsupported prototype schema")
    if raw.get("world_id") != "fifa_earth":
        raise ValueError("prototype must target fifa_earth")
    sources = raw.get("sources")
    countries = raw.get("countries")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("prototype sources are required")
    if not isinstance(countries, dict) or not countries:
        raise ValueError("prototype countries are required")
    for code, country in countries.items():
        if len(code) != 3 or not code.isupper():
            raise ValueError(f"invalid country code {code!r}")
        if code not in earth_country_codes:
            raise ValueError(f"{code}: country code is not present in the Earth catalogue")
        _validate_historical_context(country, code)
        anchors = country.get("anchors")
        if not isinstance(anchors, dict):
            raise ValueError(f"{code}: anchors are required")
        years = sorted(int(year) for year in anchors)
        if years[0] != FIRST_YEAR or years[-1] != LAST_YEAR:
            raise ValueError(f"{code}: prototype must anchor both {FIRST_YEAR} and {LAST_YEAR}")
        for year_text, anchor in anchors.items():
            year = int(year_text)
            if not FIRST_YEAR <= year <= LAST_YEAR:
                raise ValueError(f"{code}: anchor year outside supported range: {year}")
            if anchor.get("confidence") not in CONFIDENCE_RANK:
                raise ValueError(f"{code} {year}: invalid confidence")
            source_ids = anchor.get("source_ids")
            if not source_ids or any(source_id not in sources for source_id in source_ids):
                raise ValueError(f"{code} {year}: missing/unknown source id")
            ratings = anchor.get("ratings")
            if set(ratings or {}) != set(GAME_ATTRIBUTE_NAMES):
                raise ValueError(f"{code} {year}: exactly six ratings are required")
            for value in ratings.values():
                _rating(value)


def _validate_historical_context(country: dict[str, Any], code: str) -> None:
    periods = country.get("historical_periods")
    if periods is None:
        if not str(country.get("historical_entity", "")).strip():
            raise ValueError(f"{code}: historical_entity is required")
        if not str(country.get("territory_mapping_note", "")).strip():
            raise ValueError(f"{code}: territory_mapping_note is required")
        return
    if not isinstance(periods, list) or not periods:
        raise ValueError(f"{code}: historical_periods must be a non-empty list")
    expected = FIRST_YEAR
    for period in sorted(periods, key=lambda item: int(item["from"])):
        start, end = int(period["from"]), int(period["to"])
        if start != expected or end < start or end > LAST_YEAR:
            raise ValueError(f"{code}: historical_periods must cover 1955–2026 exactly without gaps/overlap")
        if not str(period.get("historical_entity", "")).strip():
            raise ValueError(f"{code}: historical period entity is required")
        if not str(period.get("territory_mapping_note", "")).strip():
            raise ValueError(f"{code}: historical period territory note is required")
        expected = end + 1
    if expected != LAST_YEAR + 1:
        raise ValueError(f"{code}: historical_periods must cover 1955–2026 exactly without gaps/overlap")


def _historical_context(country: dict[str, Any], year: int) -> tuple[str, str]:
    periods = country.get("historical_periods")
    if periods is not None:
        for period in periods:
            if int(period["from"]) <= year <= int(period["to"]):
                return str(period["historical_entity"]), str(period["territory_mapping_note"])
        raise ValueError(f"no historical context for year {year}")
    return str(country["historical_entity"]), str(country["territory_mapping_note"])


def _weaker_confidence(left: str, right: str) -> str:
    return RANK_CONFIDENCE[min(CONFIDENCE_RANK[left], CONFIDENCE_RANK[right])]


def _round_tenth(value: float) -> float:
    return round(value + 1e-12, 1)


def audit_anchor_transitions(raw: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for code, country in raw["countries"].items():
        anchors = {int(year): payload for year, payload in country["anchors"].items()}
        years = sorted(anchors)
        for left, right in zip(years, years[1:]):
            a = anchors[left]["ratings"]
            b = anchors[right]["ratings"]
            deltas = {name: _round_tenth(float(b[name]) - float(a[name])) for name in GAME_ATTRIBUTE_NAMES}
            strong_positive = [name for name, delta in deltas.items() if delta >= 0.4]
            strong_negative = [name for name, delta in deltas.items() if delta <= -0.4]
            if right - left > 20:
                flags.append({"country": code, "from": left, "to": right, "kind": "long_gap",
                              "years": right - left})
            coupled = strong_positive if len(strong_positive) >= 5 else strong_negative
            if len(coupled) >= 5:
                flags.append({"country": code, "from": left, "to": right, "kind": "coupled_transition",
                              "direction": "up" if coupled is strong_positive else "down",
                              "attributes": coupled, "deltas": deltas})
            if abs(deltas["squash_tradition"]) >= 0.8:
                flags.append({"country": code, "from": left, "to": right, "kind": "tradition_jump",
                              "delta": deltas["squash_tradition"]})
    return flags


def materialise(raw: dict[str, Any], *, earth_country_codes: set[str]) -> dict[str, Any]:
    _validate_anchor_file(raw, earth_country_codes=earth_country_codes)
    countries: dict[str, Any] = {}
    for code, country in raw["countries"].items():
        anchors = {int(year): payload for year, payload in country["anchors"].items()}
        anchor_years = sorted(anchors)
        years: dict[int, Any] = {}
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            if year in anchors:
                anchor = anchors[year]
                ratings = {
                    name: {
                        "value": _rating(anchor["ratings"][name]),
                        "method": "sourced_estimate",
                        "confidence": anchor["confidence"],
                        "source_ids": list(anchor["source_ids"]),
                        "rationale": (
                            "Prototype anchor. " + anchor["rationale"].strip()
                            + " The numeric rating is a project-authored game estimate, not a direct source measurement."
                        ),
                        "anchor_years": [year],
                    }
                    for name in GAME_ATTRIBUTE_NAMES
                }
            else:
                left = max(item for item in anchor_years if item < year)
                right = min(item for item in anchor_years if item > year)
                left_anchor = anchors[left]
                right_anchor = anchors[right]
                fraction = (year - left) / (right - left)
                source_ids = list(dict.fromkeys(left_anchor["source_ids"] + right_anchor["source_ids"]))
                confidence = _weaker_confidence(left_anchor["confidence"], right_anchor["confidence"])
                ratings = {}
                for name in GAME_ATTRIBUTE_NAMES:
                    start = float(left_anchor["ratings"][name])
                    end = float(right_anchor["ratings"][name])
                    ratings[name] = {
                        "value": _round_tenth(start + (end - start) * fraction),
                        "method": "interpolated",
                        "confidence": confidence,
                        "source_ids": source_ids,
                        "rationale": (
                            f"Prototype linear interpolation between reviewed {left} and {right} anchors. "
                            "No additional structural break is represented for this attribute in this prototype interval; "
                            "the value is a model estimate, not an observed measurement."
                        ),
                        "anchor_years": [left, right],
                    }
            historical_entity, territory_mapping_note = _historical_context(country, year)
            years[year] = {
                "historical_entity": historical_entity,
                "territory_mapping_note": territory_mapping_note,
                "ratings": ratings,
            }
        countries[code] = {
            "schema_version": "country_rating_history.v1",
            "rating_scale": "country_ratings_1_10.v2",
            "reference_year": int(country.get("reference_year", LAST_YEAR)),
            "data_cutoff": raw["data_cutoff"],
            "years": years,
        }
    output = {
        "schema_version": "earth_sport_research.v1",
        "world_id": "fifa_earth",
        "data_cutoff": raw["data_cutoff"],
        "sources": raw["sources"],
        "countries": countries,
    }
    EarthSportResearch.model_validate(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "anchors",
        nargs="?",
        type=Path,
        default=Path("config/earth_research/fifa_earth_prototype_anchors_v2.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--country-index", type=Path, default=DEFAULT_COUNTRY_INDEX)
    parser.add_argument("--strict", action="store_true", help="fail if review flags remain")
    args = parser.parse_args()

    raw = json.loads(args.anchors.read_text(encoding="utf-8"))
    earth_country_codes = _load_earth_country_codes(args.country_index)
    materialised = materialise(raw, earth_country_codes=earth_country_codes)
    flags = audit_anchor_transitions(raw)
    summary = {
        "country_count": len(materialised["countries"]),
        "years_per_country": LAST_YEAR - FIRST_YEAR + 1,
        "rating_count": len(materialised["countries"]) * (LAST_YEAR - FIRST_YEAR + 1) * len(GAME_ATTRIBUTE_NAMES),
        "review_flag_count": len(flags),
        "review_flags": flags,
        "canonical_ready": False,
    }
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.write_text(json.dumps(materialised, indent=2) + "\n", encoding="utf-8")
    if args.strict and flags:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
