"""Build empirical FIFA country calibration signals from canonical country evidence.

Signals are measured/derived evidence, not 1–10 game ratings. They preserve the
underlying observation IDs, population denominator, raw rate and empirical
cross-country rank/percentile. Missing evidence stays missing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_country_evidence_index import build_index
from scripts.reconcile_fifa_big_count_identities import (
    DEFAULT_EARTH_ROOT,
    DEFAULT_OVERRIDES as BIG_COUNT_OVERRIDES,
)
from scripts.reconcile_fifa_professional_2023_identities import (
    DEFAULT_OVERRIDES as PROFESSIONAL_OVERRIDES,
)

SIGNAL_SPECS = {
    "participation_intensity_2006": {
        "source_id": "fifa-big-count-2006",
        "measurement_type": "players_all_registered_and_unregistered",
        "year": 2006,
        "per": 1_000,
        "unit": "players_per_1000_population",
        "primary_dimensions": ["squash_popularity"],
        "interpretation": (
            "Population-normalised all-player participation intensity. Mixed-sex and "
            "inclusive of unregistered/casual participation."
        ),
    },
    "registered_intensity_2006": {
        "source_id": "fifa-big-count-2006",
        "measurement_type": "players_registered_or_association_reported",
        "year": 2006,
        "per": 1_000,
        "unit": "registered_players_per_1000_population",
        "primary_dimensions": ["squash_access"],
        "interpretation": (
            "Population-normalised registered/association-reported player footprint. "
            "Registration definitions vary by association."
        ),
    },
    "club_footprint_2006": {
        "source_id": "fifa-big-count-2006",
        "measurement_type": "clubs_reported",
        "year": 2006,
        "per": 1_000_000,
        "unit": "clubs_per_million_population",
        "primary_dimensions": ["squash_access"],
        "interpretation": (
            "Population-normalised reported club footprint. Club definitions vary by "
            "association; use as access evidence, not a direct rating."
        ),
    },
    "professional_player_density_2023": {
        "source_id": "fifa-professional-2023",
        "measurement_type": "professional_male_players_reported",
        "year": 2023,
        "per": 1_000_000,
        "unit": "professional_male_players_per_million_population",
        "primary_dimensions": ["competition_quality", "elite_support"],
        "interpretation": (
            "Population-normalised men's professional-player employment footprint. "
            "Evidence for professional ecosystem depth, not a direct quality score."
        ),
    },
    "professional_club_density_2023": {
        "source_id": "fifa-professional-2023",
        "measurement_type": "professional_clubs_reported",
        "year": 2023,
        "per": 1_000_000,
        "unit": "professional_clubs_per_million_population",
        "primary_dimensions": ["competition_quality", "elite_support"],
        "interpretation": (
            "Population-normalised professional-club footprint. Evidence for the "
            "professional competition/support ecosystem, not mass access."
        ),
    },
}

SOURCE_AGGREGATE_OVERRIDE_PATHS = {
    "fifa-big-count-2006": BIG_COUNT_OVERRIDES,
    "fifa-professional-2023": PROFESSIONAL_OVERRIDES,
}


def _population(earth_root: Path, code: str, year: int) -> int:
    payload = json.loads(
        (earth_root / code / "attributes" / "population.json").read_text(
            encoding="utf-8"
        )
    )
    values = payload.get("values_by_year")
    key = str(year)
    if not isinstance(values, dict) or key not in values:
        raise ValueError(f"{code}: missing Earth population for {year}")
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{code}: invalid Earth population for {year}")
    return int(value)


def _aggregate_members(source_id: str, code: str) -> set[str] | None:
    path = SOURCE_AGGREGATE_OVERRIDE_PATHS[source_id]
    payload = json.loads(path.read_text(encoding="utf-8"))
    group = (payload.get("aggregate_groups") or {}).get(code)
    if group is None:
        return None
    members = group.get("source_associations")
    if not isinstance(members, list) or not members:
        raise ValueError(f"{source_id}/{code}: invalid aggregate-group members")
    return set(str(member) for member in members)


def _collect_value(
    *,
    facts: list[dict[str, Any]],
    source_id: str,
    measurement_type: str,
    code: str,
) -> dict[str, Any]:
    matching = [
        fact
        for fact in facts
        if fact["source_id"] == source_id
        and fact["measurement_type"] == measurement_type
    ]
    if not matching:
        return {
            "value": None,
            "observation_ids": [],
            "source_entities": [],
            "identity_status": None,
            "completeness": "missing",
        }

    statuses = {fact["identity_status"] for fact in matching}
    if statuses == {"direct"}:
        if len(matching) != 1:
            raise ValueError(
                f"{code}/{source_id}/{measurement_type}: duplicate direct observations"
            )
        fact = matching[0]
        return {
            "value": fact["numeric_value"],
            "observation_ids": [fact["observation_id"]],
            "source_entities": [fact["source_entity"]],
            "identity_status": "direct",
            "completeness": "complete",
        }

    if statuses == {"aggregate_member"}:
        expected = _aggregate_members(source_id, code)
        if expected is None:
            raise ValueError(
                f"{code}/{source_id}/{measurement_type}: aggregate facts lack group definition"
            )
        actual = {str(fact["source_entity"]) for fact in matching}
        observation_ids = sorted(fact["observation_id"] for fact in matching)
        source_entities = sorted(actual)
        if actual != expected:
            return {
                "value": None,
                "observation_ids": observation_ids,
                "source_entities": source_entities,
                "identity_status": "aggregate_member",
                "completeness": "partial_aggregate",
                "missing_source_entities": sorted(expected - actual),
            }
        values = [fact["numeric_value"] for fact in matching]
        if any(value is None for value in values):
            raise ValueError(
                f"{code}/{source_id}/{measurement_type}: safe numeric fact is unexpectedly null"
            )
        return {
            "value": sum(float(value) for value in values),
            "observation_ids": observation_ids,
            "source_entities": source_entities,
            "identity_status": "aggregate_member",
            "completeness": "complete_aggregate",
            "missing_source_entities": [],
        }

    raise ValueError(
        f"{code}/{source_id}/{measurement_type}: mixed identity statuses {sorted(statuses)}"
    )


def _midrank_percentiles(rows: dict[str, dict[str, Any]]) -> None:
    observed = [
        (code, float(payload["rate"]))
        for code, payload in rows.items()
        if payload["rate"] is not None
    ]
    if not observed:
        return

    values = sorted(value for _, value in observed)
    n = len(values)
    for code, value in observed:
        equal_positions = [
            index + 1 for index, candidate in enumerate(values) if candidate == value
        ]
        midrank_asc = sum(equal_positions) / len(equal_positions)
        percentile = 50.0 if n == 1 else (midrank_asc - 1) / (n - 1) * 100

        greater = sum(candidate > value for candidate in values)
        equal = sum(candidate == value for candidate in values)
        rank_desc = greater + (equal + 1) / 2

        rows[code]["percentile"] = round(percentile, 2)
        rows[code]["rank_desc"] = round(rank_desc, 2)
        rows[code]["observed_entity_count"] = n


def build_signals(
    *,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    evidence = build_index()
    countries = evidence["countries"]
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = sorted(earth_index["country_codes"])

    signal_rows: dict[str, dict[str, dict[str, Any]]] = {
        signal_id: {} for signal_id in SIGNAL_SPECS
    }

    for signal_id, spec in SIGNAL_SPECS.items():
        rows = signal_rows[signal_id]
        for code in earth_codes:
            facts = countries.get(code, [])
            collected = _collect_value(
                facts=facts,
                source_id=spec["source_id"],
                measurement_type=spec["measurement_type"],
                code=code,
            )
            population = _population(earth_root, code, spec["year"])
            value = collected.pop("value")
            rate = (
                None
                if value is None
                else round(float(value) / population * spec["per"], 6)
            )
            rows[code] = {
                "earth_country_code": code,
                "observation_year": spec["year"],
                "source_id": spec["source_id"],
                "measurement_type": spec["measurement_type"],
                "source_value": value,
                "population": population,
                "rate": rate,
                "unit": spec["unit"],
                "percentile": None,
                "rank_desc": None,
                "observed_entity_count": None,
                **collected,
            }

        _midrank_percentiles(rows)

    country_view: dict[str, dict[str, Any]] = {}
    for code in earth_codes:
        country_view[code] = {
            signal_id: signal_rows[signal_id][code]
            for signal_id in SIGNAL_SPECS
        }

    return {
        "schema_version": "fifa_country_calibration_signals.v1",
        "world_id": "fifa_earth",
        "rating_ready": False,
        "source_evidence_observation_count": evidence["observation_count"],
        "safe_country_evidence_count": evidence["safe_country_evidence_count"],
        "manual_review_count": evidence["manual_review_count"],
        "unresolved_count": evidence["unresolved_count"],
        "signal_definitions": {
            signal_id: {
                "source_id": spec["source_id"],
                "measurement_type": spec["measurement_type"],
                "observation_year": spec["year"],
                "unit": spec["unit"],
                "primary_dimensions": list(spec["primary_dimensions"]),
                "interpretation": spec["interpretation"],
                "percentile_method": (
                    "Empirical ascending midrank percentile among Earth entities with "
                    "a complete observed rate for this signal; 100 = highest observed."
                ),
            }
            for signal_id, spec in SIGNAL_SPECS.items()
        },
        "signals": signal_rows,
        "countries": country_view,
        "limitations": [
            "Signals are empirical calibration evidence, not authored 1–10 ratings.",
            "Percentiles are relative to observed entities for that source/metric and are not comparable sample sizes by assumption.",
            "Big Count 2006 is mixed-sex and includes source-definition variation.",
            "Professional 2023 covers men's professional football and missing values remain missing.",
            "Professional UK aggregate signals stay missing because Northern Ireland is missing in the source.",
            "No signal directly measures all six country attributes and no composite football-strength score is produced.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_signals(earth_root=args.earth_root)
    summary = {
        signal_id: {
            "observed_entity_count": sum(
                row["rate"] is not None for row in rows.values()
            ),
            "missing_entity_count": sum(
                row["rate"] is None for row in rows.values()
            ),
        }
        for signal_id, rows in result["signals"].items()
    }
    print(json.dumps(summary, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
