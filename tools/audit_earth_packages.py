import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class AuditResult:
    package_id: str
    total_countries: int
    missing_histories: List[str] = field(default_factory=list)
    invalid_ids: List[str] = field(default_factory=list)
    missing_attributes: List[str] = field(default_factory=list)
    invalid_ranges: List[str] = field(default_factory=list)
    missing_population: List[str] = field(default_factory=list)
    missing_years: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    load_errors: List[str] = field(default_factory=list)
    deterministic_load_errors: List[str] = field(default_factory=list)

def audit_package(package_dir: Path) -> AuditResult:
    package_id = package_dir.name
    countries_dir = package_dir / "countries"
    histories_dir = package_dir / "generation" / "country_histories"

    if not countries_dir.exists():
        return AuditResult(package_id, 0)

    index_file = countries_dir / "index.json"
    if not index_file.exists():
        logging.error(f"Missing index.json in {package_id}")
        return AuditResult(package_id, 0)

    try:
        with open(index_file) as f:
            index_data = json.load(f)
    except Exception as e:
        res = AuditResult(package_id, 0)
        res.deterministic_load_errors.append(f"Failed to load index.json: {str(e)}")
        return res

    country_codes = index_data.get("country_codes", [])

    result = AuditResult(package_id, len(country_codes))

    required_attributes = [
        "squash_popularity", "squash_access", "development_quality",
        "competition_quality", "elite_support", "squash_tradition"
    ]

    seen_codes = set()
    for code in country_codes:
        if code in seen_codes:
            result.duplicates.append(code)
        seen_codes.add(code)

        country_dir = countries_dir / code
        if not country_dir.exists():
            result.invalid_ids.append(code)
            continue

        history_file = histories_dir / f"{code}.json"
        has_history = history_file.exists()
        if not has_history:
            result.missing_histories.append(code)

        if has_history:
            try:
                # Test deterministic loading
                with open(history_file, 'r') as f:
                    content = f.read()
                    history_data = json.loads(content)

                    # Dump and load back to ensure json serialization determinism roughly
                    json.dumps(history_data)
            except Exception as e:
                result.deterministic_load_errors.append(f"{code}: {str(e)}")
                continue

            try:
                years = []

                # 'years' key holds the actual history records
                items_to_check = history_data.get("years", {})

                for key in items_to_check.keys():
                    try:
                        year = int(key)
                        if 1955 <= year <= 2026:
                            years.append(year)

                            year_data = items_to_check[key]
                            ratings = year_data.get("ratings", {})
                            for attr in required_attributes:
                                if attr not in ratings:
                                    result.missing_attributes.append(f"{code} ({key}: {attr})")
                                else:
                                    attr_val = ratings[attr].get("value")
                                    if attr_val is None or not (isinstance(attr_val, (int, float))) or not (1 <= attr_val <= 10):
                                        result.invalid_ranges.append(f"{code} ({key}: {attr}={attr_val})")
                    except ValueError:
                        pass

                if not years:
                    result.missing_years.append(f"{code} (No valid years 1955-2026)")
                else:
                     required_years = set(range(1955, 2027))
                     if not required_years.issubset(set(years)):
                         missing = required_years - set(years)
                         result.missing_years.append(f"{code} (Missing {len(missing)} years, e.g. {sorted(list(missing))[:3]})")
            except Exception as e:
                result.load_errors.append(f"{code}: {str(e)}")

        pop_file = country_dir / "attributes" / "population.json"
        if not pop_file.exists():
            result.missing_population.append(code)
        else:
            try:
                with open(pop_file, 'r') as f:
                    pop_data = json.load(f)

                    if "values_by_year" in pop_data:
                         pop_years = []
                         for y_str in pop_data["values_by_year"].keys():
                             try:
                                 y = int(y_str)
                                 if 1955 <= y <= 2026:
                                     pop_years.append(y)
                             except ValueError:
                                 pass
                         required_years = set(range(1955, 2027))
                         if not required_years.issubset(set(pop_years)):
                             if pop_years:
                                  missing = required_years - set(pop_years)
                                  result.missing_population.append(f"{code} (Missing {len(missing)} population years, e.g. {sorted(list(missing))[:3]})")
                             else:
                                  result.missing_population.append(f"{code} (No valid population years 1955-2026)")

            except Exception as e:
                result.deterministic_load_errors.append(f"{code} pop: {str(e)}")

    return result

def main():
    config_dir = Path("config/world_packages")
    packages = ["fifa_earth", "atp_earth"]

    for package in packages:
        result = audit_package(config_dir / package)
        print(f"=== Audit {package} ===")
        print(f"Total countries in manifest: {result.total_countries}")

        # Jasně oddělit úplná, chybějící a neověřená data
        print("\n--- Chybějící data (Missing Data) ---")
        if result.missing_histories:
            print(f"Missing history files: {len(result.missing_histories)} (e.g., {result.missing_histories[:5]})")
        else:
            print("Missing history files: 0")

        if result.missing_population:
            print(f"Missing population files/data for 1955-2026: {len(result.missing_population)} (e.g., {result.missing_population[:5]})")
        else:
            print("Missing population files/data for 1955-2026: 0")

        if result.missing_attributes:
            print(f"Missing attributes in history: {len(result.missing_attributes)} (e.g., {result.missing_attributes[:5]})")
        else:
            print("Missing attributes in history: 0")

        if result.missing_years:
            print(f"Missing years 1955-2026 coverage issues: {len(result.missing_years)} (e.g., {result.missing_years[:5]})")
        else:
            print("Missing years 1955-2026 coverage issues: 0")

        print("\n--- Neověřená / Neplatná data (Invalid/Unverified Data) ---")
        if result.invalid_ids:
            print(f"Invalid country IDs (missing dir): {len(result.invalid_ids)} (e.g., {result.invalid_ids[:5]})")
        else:
            print("Invalid country IDs: 0")

        if result.invalid_ranges:
            print(f"Invalid attribute ranges (not 1-10): {len(result.invalid_ranges)} (e.g., {result.invalid_ranges[:5]})")
        else:
            print("Invalid attribute ranges: 0")

        if result.duplicates:
            print(f"Duplicate IDs in index: {len(result.duplicates)} (e.g., {result.duplicates[:5]})")
        else:
            print("Duplicate IDs in index: 0")

        if result.load_errors or result.deterministic_load_errors:
            print(f"Load Errors: {len(result.load_errors) + len(result.deterministic_load_errors)}")
        else:
            print("Load Errors: 0")

        print("\n--- Úplná data (Complete Data) ---")
        complete_count = result.total_countries - len(set(
            result.missing_histories + result.invalid_ids +
            [x.split(" ")[0] for x in result.missing_attributes] +
            [x.split(" ")[0] for x in result.invalid_ranges] +
            [x.split(" ")[0] for x in result.missing_population] +
            [x.split(" ")[0] for x in result.missing_years] +
            result.duplicates +
            [x.split(":")[0] for x in result.load_errors] +
            [x.split(":")[0] for x in result.deterministic_load_errors]
        ))
        print(f"Fully valid countries: {complete_count} / {result.total_countries}")
        print("\n")

if __name__ == "__main__":
    main()
