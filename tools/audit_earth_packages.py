"""Read-only structural inventory, not scientific approval of Earth ratings."""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

YEARS = set(range(1955, 2027))
ATTRIBUTES = (
    'squash_popularity', 'squash_access', 'development_quality',
    'competition_quality', 'elite_support', 'squash_tradition',
)


@dataclass
class AuditResult:
    package_id: str
    total_countries: int = 0
    missing_histories: list[str] = field(default_factory=list)
    invalid_ids: list[str] = field(default_factory=list)
    missing_attributes: list[str] = field(default_factory=list)
    invalid_ranges: list[str] = field(default_factory=list)
    missing_population: list[str] = field(default_factory=list)
    missing_years: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    load_errors: list[str] = field(default_factory=list)
    deterministic_load_errors: list[str] = field(default_factory=list)
    structurally_complete_codes: list[str] = field(default_factory=list)

    def issues(self):
        return {name: getattr(self, name) for name in (
            'missing_histories', 'invalid_ids', 'missing_attributes', 'invalid_ranges',
            'missing_population', 'missing_years', 'duplicates', 'load_errors',
            'deterministic_load_errors',
        )}


def _read(path: Path) -> dict:
    def reject_constant(value):
        raise ValueError('Non-finite JSON number: ' + value)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    with path.open(encoding='utf-8') as stream:
        value = json.load(stream, parse_constant=reject_constant, object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise TypeError('Expected a JSON object')
    return value


def _years(value, label):
    if not isinstance(value, dict):
        raise TypeError(label + ' must be a year-indexed object')
    if any(not isinstance(k, str) or len(k) != 4 or not k.isascii() or not k.isdecimal() for k in value):
        raise ValueError(label + ' contains an invalid year key')
    return {int(k) for k in value}


def _rating(value):
    return (type(value) in (int, float) and math.isfinite(value) and 1 <= value <= 10
            and Decimal(str(value)) * 10 == (Decimal(str(value)) * 10).to_integral_value())


def audit_package(package_dir: Path) -> AuditResult:
    result = AuditResult(package_dir.name)
    try:
        index = _read(package_dir / 'countries/index.json')
        codes = index.get('country_codes')
        if index.get('schema_version') != 'world_package_countries_index.v1' or not isinstance(codes, list):
            raise ValueError('Invalid country index schema or country_codes list')
    except (OSError, ValueError, TypeError) as error:
        result.load_errors.append('index: ' + str(error))
        return result
    result.total_countries = len(codes)
    valid_codes = [c for c in codes if isinstance(c, str) and len(c) == 3
                   and c.isascii() and c.isalpha() and c.isupper()]
    result.invalid_ids.extend(repr(c) for c in codes if c not in valid_codes)
    counts = Counter(valid_codes)
    result.duplicates.extend(sorted(c for c, count in counts.items() if count > 1))
    for code in sorted(counts):
        issue_count = sum(len(v) for v in result.issues().values())
        directory = package_dir / 'countries' / code
        if not directory.is_dir():
            result.invalid_ids.append(code)
            continue
        history_file = package_dir / 'generation/country_histories' / (code + '.json')
        if not history_file.is_file():
            result.missing_histories.append(code)
        else:
            try:
                history = _read(history_file)
                if history.get('schema_version') != 'country_rating_history.v2':
                    raise ValueError('Unsupported rating history schema')
                years = _years(history.get('years'), 'history.years')
                missing = sorted(YEARS - years)
                if missing:
                    result.missing_years.append(f'{code} (missing {len(missing)} years, e.g. {missing[:3]})')
                for year in sorted(YEARS & years):
                    row = history['years'][str(year)]
                    ratings = row.get('ratings') if isinstance(row, dict) else None
                    if not isinstance(ratings, dict):
                        raise TypeError(f'Invalid ratings object at {year}')
                    for attribute in ATTRIBUTES:
                        if attribute not in ratings:
                            result.missing_attributes.append(f'{code} ({year}: {attribute})')
                        else:
                            item = ratings[attribute]
                            value = item.get('value') if isinstance(item, dict) else None
                            if not _rating(value):
                                result.invalid_ranges.append(f'{code} ({year}: {attribute}={value!r})')
            except (OSError, ValueError, TypeError, OverflowError) as error:
                result.load_errors.append(f'{code} history: {error}')
        try:
            population = _read(directory / 'attributes/population.json')
            if population.get('schema_version') != 'country_population.v1':
                raise ValueError('Unsupported population schema')
            values = population.get('values_by_year')
            years = _years(values, 'population.values_by_year')
            missing = sorted(YEARS - years)
            if missing:
                result.missing_population.append(f'{code} (missing {len(missing)} years, e.g. {missing[:3]})')
            for year in sorted(YEARS & years):
                value = values[str(year)]
                if type(value) is not int or value < 0:
                    raise ValueError(f'Invalid population at {year}: {value!r}')
        except (OSError, ValueError, TypeError) as error:
            result.missing_population.append(f'{code}: {error}')
        if counts[code] == 1 and sum(len(v) for v in result.issues().values()) == issue_count:
            result.structurally_complete_codes.append(code)
    return result


def main():
    for package in ('fifa_earth', 'atp_earth'):
        result = audit_package(Path('config/world_packages') / package)
        print(f'=== Audit {package} ===')
        print(f'Total country index entries: {result.total_countries}')
        for name, values in result.issues().items():
            print(f'{name}: {len(values)}' + (f' (examples: {values[:3]})' if values else ''))
        print(f'Structurally complete countries: {len(result.structurally_complete_codes)} / {result.total_countries}')
        print('Scope: required years, six rating ranges/precision and population types only; '
              'NOT scientific validity, production-loader replay, or Package acceptance.\n')


if __name__ == '__main__':
    main()
