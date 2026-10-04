"""Build an Earth-normalised benchmark from FIFA Professional Football Report 2023.

The report is association-level and records men's professional players/clubs.
Identity reconciliation is mandatory before any population normalisation.
Missing values stay null and are never converted to zero.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.reconcile_fifa_professional_2023_identities import (
    DEFAULT_EARTH_ROOT,
    DEFAULT_SOURCE,
    build_report,
    load_source,
)

POPULATION_REFERENCE_YEAR = 2023
NUMERIC_FIELDS = ("professional_players", "professional_clubs")


def _population(earth_root: Path, code: str, year: int = POPULATION_REFERENCE_YEAR) -> int:
    payload = json.loads(
        (earth_root / code / "attributes" / "population.json").read_text(encoding="utf-8")
    )
    values = payload.get("values_by_year")
    key = str(year)
    if not isinstance(values, dict) or key not in values:
        raise ValueError(f"{code}: missing Earth population for {year}")
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{code}: invalid Earth population for {year}")
    return int(value)


def _metric_per_million(value: int | None, population: int) -> float | None:
    if value is None:
        return None
    return round(value / population * 1_000_000, 3)


def _players_per_club(players: int | None, clubs: int | None) -> float | None:
    if players is None or clubs is None or clubs <= 0:
        return None
    return round(players / clubs, 3)


def build_benchmark(
    *,
    source_path: Path = DEFAULT_SOURCE,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    identity = build_report(source_path=source_path, earth_root=earth_root)
    if identity["unresolved_count"]:
        raise ValueError(f"identity reconciliation has unresolved rows: {identity['unresolved']}")
    if identity["duplicate_direct_targets"]:
        raise ValueError(
            "identity reconciliation has duplicate direct targets: "
            f"{identity['duplicate_direct_targets']}"
        )

    source = load_source(source_path)
    by_page = {int(item["pdf_page"]): item for item in source["observations"]}
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = set(earth_index["country_codes"])

    entities: dict[str, dict[str, Any]] = {}
    manual_review_pages: list[int] = []

    for mapping in identity["mappings"]:
        status = mapping["status"]
        page = int(mapping["pdf_page"])
        association = mapping["association"]

        if status == "manual_review":
            manual_review_pages.append(page)
            continue
        if status == "aggregate_member":
            continue
        if status not in {"explicit_map", "exact_normalized_name"}:
            raise ValueError(f"unexpected reconciliation status on page {page}: {status}")

        code = mapping["earth_code"]
        if code in entities:
            raise ValueError(f"{code}: duplicate safely reconciled Earth entity")

        observation = by_page[page]
        players = observation.get("professional_players")
        clubs = observation.get("professional_clubs")
        population = _population(earth_root, code)

        entities[code] = {
            "earth_code": code,
            "source_associations": [association],
            "source_pages": [page],
            "identity_status": status,
            "population_reference_year": POPULATION_REFERENCE_YEAR,
            "population": population,
            "values": {
                "professional_players": players,
                "professional_clubs": clubs,
            },
            "metrics": {
                "professional_players_per_million": _metric_per_million(players, population),
                "professional_clubs_per_million": _metric_per_million(clubs, population),
                "professional_players_per_club": _players_per_club(players, clubs),
            },
        }

    for code, aggregate in identity["aggregates"].items():
        if code in entities:
            raise ValueError(f"{code}: aggregate collides with direct mapping")

        population = _population(earth_root, code)
        players_field = aggregate["fields"]["professional_players"]
        clubs_field = aggregate["fields"]["professional_clubs"]
        players = players_field["value"]
        clubs = clubs_field["value"]

        entities[code] = {
            "earth_code": code,
            "source_associations": list(aggregate["source_associations"]),
            "source_pages": sorted(
                int(item["pdf_page"])
                for item in identity["mappings"]
                if item["status"] == "aggregate_member" and item["earth_code"] == code
            ),
            "identity_status": "aggregate",
            "population_reference_year": POPULATION_REFERENCE_YEAR,
            "population": population,
            "values": {
                "professional_players": players,
                "professional_clubs": clubs,
            },
            "known_partial_sums": {
                "professional_players": players_field["known_partial_sum"],
                "professional_clubs": clubs_field["known_partial_sum"],
            },
            "missing_associations": {
                "professional_players": list(players_field["missing_associations"]),
                "professional_clubs": list(clubs_field["missing_associations"]),
            },
            "metrics": {
                "professional_players_per_million": _metric_per_million(players, population),
                "professional_clubs_per_million": _metric_per_million(clubs, population),
                "professional_players_per_club": _players_per_club(players, clubs),
            },
        }

    unknown_targets = set(entities) - earth_codes
    if unknown_targets:
        raise ValueError(f"benchmark produced unknown Earth codes: {sorted(unknown_targets)}")

    entities = dict(sorted(entities.items()))
    complete_players = sum(
        entity["values"]["professional_players"] is not None
        for entity in entities.values()
    )
    complete_clubs = sum(
        entity["values"]["professional_clubs"] is not None
        for entity in entities.values()
    )
    complete_both = sum(
        entity["values"]["professional_players"] is not None
        and entity["values"]["professional_clubs"] is not None
        for entity in entities.values()
    )

    return {
        "schema_version": "fifa_professional_earth_benchmark.v1",
        "source_id": "fifa-professional-2023",
        "source_edition": source.get("edition"),
        "source_scope": source.get("scope"),
        "population_reference_year": POPULATION_REFERENCE_YEAR,
        "source_row_count": identity["row_count"],
        "safe_earth_entity_count": len(entities),
        "entities_with_professional_players": complete_players,
        "entities_with_professional_clubs": complete_clubs,
        "entities_with_both": complete_both,
        "manual_review_pages": sorted(manual_review_pages),
        "unobserved_earth_codes": sorted(earth_codes - set(entities)),
        "published_global_totals": source.get("published_global_totals"),
        "extracted_national_sums": source.get("extracted_national_sums"),
        "entities": entities,
        "limitations": [
            "The report covers men's professional football, not total participation.",
            "The 2023 Earth population is a normalising denominator, not a claim that every association count shares one exact observation date.",
            "Missing professional counts remain null and are never interpreted as zero.",
            "Professional-player/club density is evidence for professional ecosystem depth and elite support, not a direct game-rating formula.",
            "Published global totals and extracted national-page sums disagree and are preserved separately.",
            "The page-38 Kuwait/Kyrgyzstan identity conflict is excluded from automatic benchmarking.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    benchmark = build_benchmark(source_path=args.source, earth_root=args.earth_root)
    summary = {
        "source_row_count": benchmark["source_row_count"],
        "safe_earth_entity_count": benchmark["safe_earth_entity_count"],
        "entities_with_professional_players": benchmark["entities_with_professional_players"],
        "entities_with_professional_clubs": benchmark["entities_with_professional_clubs"],
        "entities_with_both": benchmark["entities_with_both"],
        "manual_review_pages": benchmark["manual_review_pages"],
        "unobserved_earth_count": len(benchmark["unobserved_earth_codes"]),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(benchmark, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
