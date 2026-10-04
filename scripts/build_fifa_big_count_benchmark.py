"""Build a population-normalised FIFA Big Count 2006 Earth benchmark.

Only identity-reconciled source rows are included. Manual-review historical
geographies are excluded rather than coerced into modern Earth entities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.reconcile_fifa_big_count_identities import (
    DEFAULT_EARTH_ROOT,
    DEFAULT_SOURCE,
    build_report,
    load_rows,
)

NUMERIC_FIELDS = (
    "All Players",
    "Registered players",
    "Unregistered Players",
    "Clubs",
    "Officials",
)


def _number(value: str | float | int | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def _clean_number(value: float | None) -> int | float | None:
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


def _population_2006(earth_root: Path, code: str) -> int:
    payload = json.loads(
        (earth_root / code / "attributes" / "population.json").read_text(encoding="utf-8")
    )
    values = payload.get("values_by_year")
    if not isinstance(values, dict) or "2006" not in values:
        raise ValueError(f"{code}: missing Earth population for 2006")
    population = values["2006"]
    if isinstance(population, bool) or not isinstance(population, (int, float)) or population <= 0:
        raise ValueError(f"{code}: invalid Earth population for 2006")
    return int(population)


def _metrics(values: dict[str, int | float | None], population: int) -> dict[str, float | None]:
    all_players = values["All Players"]
    registered = values["Registered players"]
    clubs = values["Clubs"]
    officials = values["Officials"]
    return {
        "all_players_per_1000": None
        if all_players is None
        else round(float(all_players) / population * 1000, 2),
        "registered_players_per_1000": None
        if registered is None
        else round(float(registered) / population * 1000, 2),
        "clubs_per_million": None
        if clubs is None
        else round(float(clubs) / population * 1_000_000, 2),
        "officials_per_1000": None
        if officials is None
        else round(float(officials) / population * 1000, 2),
    }


def build_benchmark(
    *,
    source: Path = DEFAULT_SOURCE,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    identity = build_report(source=source, earth_root=earth_root)
    if identity["unresolved_count"]:
        raise ValueError(f"identity reconciliation still has unresolved rows: {identity['unresolved']}")
    if identity["duplicate_direct_targets"]:
        raise ValueError(
            f"identity reconciliation has duplicate targets: {identity['duplicate_direct_targets']}"
        )

    rows = load_rows(source)
    rows_by_association = {row["Association"]: row for row in rows}
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = set(earth_index["country_codes"])

    entities: dict[str, dict[str, Any]] = {}
    manual_review_associations: list[str] = []

    for mapping in identity["mappings"]:
        status = mapping["status"]
        association = mapping["association"]

        if status == "manual_review":
            manual_review_associations.append(association)
            continue
        if status == "aggregate_member":
            continue
        if status not in {"explicit_map", "exact_normalized_name"}:
            raise ValueError(f"unexpected reconciliation status for {association!r}: {status}")

        code = mapping["earth_code"]
        if code in entities:
            raise ValueError(f"{code}: duplicate safely mapped Earth entity")
        row = rows_by_association[association]
        values = {
            field: _clean_number(_number(row.get(field)))
            for field in NUMERIC_FIELDS
        }
        population = _population_2006(earth_root, code)
        entities[code] = {
            "earth_code": code,
            "source_associations": [association],
            "identity_status": status,
            "population_2006": population,
            "values": values,
            "metrics": _metrics(values, population),
        }

    for code, aggregate in identity["aggregates"].items():
        if code in entities:
            raise ValueError(f"{code}: aggregate collides with a direct mapping")
        values = {
            field: _clean_number(_number(aggregate["values"].get(field)))
            for field in NUMERIC_FIELDS
        }
        population = _population_2006(earth_root, code)
        entities[code] = {
            "earth_code": code,
            "source_associations": list(aggregate["source_associations"]),
            "identity_status": "aggregate",
            "population_2006": population,
            "values": values,
            "metrics": _metrics(values, population),
        }

    unknown_targets = set(entities) - earth_codes
    if unknown_targets:
        raise ValueError(f"benchmark produced unknown Earth codes: {sorted(unknown_targets)}")

    entities = dict(sorted(entities.items()))
    return {
        "schema_version": "fifa_big_count_earth_benchmark.v1",
        "source_id": "fifa-big-count-2006",
        "observation_year": 2006,
        "source_row_count": identity["row_count"],
        "safe_earth_entity_count": len(entities),
        "manual_review_associations": sorted(manual_review_associations),
        "unobserved_earth_codes": sorted(earth_codes - set(entities)),
        "entities": entities,
        "limitations": [
            "Big Count is all-player rather than men-only.",
            "A single 2006 participation survey does not determine annual historical ratings.",
            "Population-normalised metrics primarily inform popularity/access and do not directly measure development, competition quality or elite support.",
            "Manual-review historical geographies are excluded rather than divided by modern successor populations.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    benchmark = build_benchmark(source=args.source, earth_root=args.earth_root)
    summary = {
        "source_row_count": benchmark["source_row_count"],
        "safe_earth_entity_count": benchmark["safe_earth_entity_count"],
        "manual_review_count": len(benchmark["manual_review_associations"]),
        "unobserved_earth_count": len(benchmark["unobserved_earth_codes"]),
    }
    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
