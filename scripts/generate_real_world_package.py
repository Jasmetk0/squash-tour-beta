"""Generate the built-in Real World package from published country data.

Usage:
    python scripts/generate_real_world_package.py \
        --population-csv /path/to/population-with-un-projections.csv \
        --countries-json /path/to/world-countries/countries.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from beta_engine.domain.countries import CountriesConfig
from beta_engine.infrastructure.world_package_storage import PACKAGE_FORMAT_VERSION, WorldPackageCountryStore


START_YEAR = 1955
END_YEAR = 2050
DEFAULT_YEAR = 2020

# UN WPP does not publish separate series for these ISO territories.  We retain
# them in the game and scale the population curve of their administering country
# to a documented 2020 gameplay anchor. A value of 1 represents no permanent
# residents while satisfying the simulation's positive-population invariant.
FALLBACKS: dict[str, tuple[str, int, str]] = {
    "ALA": ("FIN", 30_129, "Finland curve; territory anchor"),
    "ATA": ("OWID_WRL", 1, "No permanent population; simulation floor"),
    "ATF": ("FRA", 150, "France curve; research personnel anchor"),
    "BVT": ("NOR", 1, "No permanent population; simulation floor"),
    "CCK": ("AUS", 593, "Australia curve; territory anchor"),
    "CXR": ("AUS", 1_692, "Australia curve; territory anchor"),
    "HMD": ("AUS", 1, "No permanent population; simulation floor"),
    "IOT": ("GBR", 3_000, "United Kingdom curve; personnel anchor"),
    "NFK": ("AUS", 2_188, "Australia curve; territory anchor"),
    "PCN": ("GBR", 40, "United Kingdom curve; territory anchor"),
    "SGS": ("GBR", 30, "United Kingdom curve; research personnel anchor"),
    "SJM": ("NOR", 2_926, "Norway curve; territory anchor"),
    "UMI": ("USA", 300, "United States curve; personnel anchor"),
}

CONTINENTS = {
    "Africa": ("AFR", "Africa"),
    "Americas": ("AME", "Americas"),
    "Asia": ("ASI", "Asia"),
    "Europe": ("EUR", "Europe"),
    "Oceania": ("OCE", "Oceania"),
    "Antarctic": ("ANT", "Antarctica"),
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-csv", type=Path, required=True)
    parser.add_argument("--countries-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("config/world_packages/real_world"))
    return parser.parse_args()


def _population_series(path: Path) -> dict[str, dict[int, int]]:
    series: dict[str, dict[int, int]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            year = int(row["Year"])
            if not START_YEAR <= year <= END_YEAR:
                continue
            code = row["Code"].strip()
            if not code:
                continue
            raw = row.get("Population (Projected)") or row.get("Population") or ""
            if raw:
                series.setdefault(code, {})[year] = max(1, round(float(raw)))
    return series


def _scaled_fallback(source: dict[int, int], anchor: int) -> dict[int, int]:
    source_anchor = source[DEFAULT_YEAR]
    return {year: max(1, round(anchor * value / source_anchor)) for year, value in source.items()}


def main() -> None:
    args = _arguments()
    population = _population_series(args.population_csv)
    raw_countries = json.loads(args.countries_json.read_text(encoding="utf-8"))
    countries: list[dict[str, object]] = []

    for raw in sorted(raw_countries, key=lambda item: item["cca3"]):
        source_code = raw["cca3"]
        code = "XKX" if source_code == "UNK" else source_code
        timeline = population.get("OWID_KOS" if code == "XKX" else code)
        note = "UN WPP 2024 estimates (1955–2023) and medium projection (2024–2050)."
        if timeline is None:
            curve_code, anchor, explanation = FALLBACKS[code]
            timeline = _scaled_fallback(population[curve_code], anchor)
            note = f"Gameplay fallback: {explanation}; not a separate UN WPP series."
        missing_years = sorted(set(range(START_YEAR, END_YEAR + 1)) - set(timeline))
        if missing_years:
            raise ValueError(f"{code} is missing population years: {missing_years}")

        region_name = raw.get("region") or "Antarctic"
        continent_code = CONTINENTS[region_name][0]
        countries.append(
            {
                "code": code,
                "name": raw["name"]["common"],
                "flag_asset": None,
                "region": continent_code,
                "population": timeline[DEFAULT_YEAR],
                "area_km2": max(1, round(float(raw.get("area") or 1))),
                "default_population_year": DEFAULT_YEAR,
                "default_population": timeline[DEFAULT_YEAR],
                "population_by_year": {str(year): timeline[year] for year in range(START_YEAR, END_YEAR + 1)},
                "wealth_support": 3,
                "squash_popularity": 3,
                "squash_tradition": 3,
                "system_quality": 3,
                "competition_density": 3.0,
                "federation_quality": 3.0,
                "court_count": 0,
                "travel_region": continent_code,
                "notes": note,
                "style_dna": {},
            }
        )

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    world_document = {
            "world_id": "real_world",
            "name": "Real World",
            "description": "Built-in real-world geography package for experimental squash simulations.",
            "type": "official",
            "status": "active",
            "source": "built_in",
            "editable": False,
            "deletable": False,
            "archivable": False,
            "version": "v1",
            "content_schema_version": "1",
            "package_format_version": PACKAGE_FORMAT_VERSION,
            "population_years": {"from": START_YEAR, "to": END_YEAR},
            "population_source": "UN World Population Prospects 2024 via Our World in Data; medium projection from 2024",
            "geography_source": "world-countries 5.1.0 (ISO-derived metadata)",
    }
    (output / "world.json").write_text(json.dumps(world_document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    geography = output / "geography"
    geography.mkdir(parents=True, exist_ok=True)
    documents = {
        "continents.json": {"schema_version": "continents.v1", "continents": [{"code": code, "name": name} for code, name in CONTINENTS.values()]},
        "regions.json": {"schema_version": "regions.v1", "regions": [{"code": code, "name": name, "continent_code": code} for code, name in CONTINENTS.values()]},
        "travel_regions.json": {"schema_version": "travel_regions.v1", "travel_regions": [{"code": code, "name": name, "description": "Real-world continent travel group."} for code, name in CONTINENTS.values()]},
    }
    for filename, document in documents.items():
        (geography / filename).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    WorldPackageCountryStore(output).replace_dataset(CountriesConfig.model_validate({"dataset_status": "real_world_v1_un_wpp_2024", "countries": countries}))


if __name__ == "__main__":
    main()
