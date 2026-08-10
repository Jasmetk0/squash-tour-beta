"""File-backed countries dataset management over canonical world config."""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.infrastructure.world_config import COUNTRY_EXPORT_TABULAR_FIELDS, COUNTRY_TABULAR_FIELDS, load_countries_config
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


@dataclass(frozen=True)
class CountriesDatasetMetadata:
    dataset_status: str | None
    country_count: int
    source_path: str


@dataclass(frozen=True)
class CountriesImportError:
    row_number: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class CountriesImportSummary:
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


@dataclass(frozen=True)
class CountriesImportResult:
    ok: bool
    dry_run: bool
    summary: CountriesImportSummary
    errors: list[CountriesImportError]


@dataclass(slots=True)
class CountriesConfigService:
    """CRUD management for countries backed by canonical JSON/package config."""

    package_root: Path = Path("config/world_packages/official_fax_world")
    config_path: Path | None = None  # Explicit aggregate fixture compatibility; never a production default.

    def __post_init__(self) -> None:
        self.package_root = Path(self.package_root)
        if self.config_path is not None and not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)

    def list_countries(self) -> list[Country]:
        return self._load().countries

    def get_config(self) -> CountriesConfig:
        return self._load()

    def get_country(self, code: str) -> Country | None:
        normalized = code.upper()
        return next((country for country in self._load().countries if country.code == normalized), None)

    def get_metadata(self) -> CountriesDatasetMetadata:
        config = self._load()
        return CountriesDatasetMetadata(
            dataset_status=config.dataset_status,
            country_count=len(config.countries),
            source_path=str(self.config_path or (self.package_root / "countries/index.json")),
        )

    def export_countries_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=COUNTRY_EXPORT_TABULAR_FIELDS)
        writer.writeheader()
        for country in sorted(self._load().countries, key=lambda item: item.code):
            writer.writerow(
                {
                    "code": country.code,
                    "name": country.name,
                    "flag_asset": country.flag_asset or "",
                    "region": country.region,
                    "population": country.population,
                    "squash_popularity": country.squash_popularity,
                    "squash_access": country.squash_access,
                    "development_quality": country.development_quality,
                    "competition_quality": country.competition_quality,
                    "elite_support": country.elite_support,
                    "squash_tradition": country.squash_tradition,
                    "court_count": country.court_count if country.court_count is not None else "",
                    "travel_region": country.travel_region or "",
                    "notes": country.notes or "",
                }
            )
        return output.getvalue()

    def import_countries_csv(self, *, csv_text: str, dry_run: bool) -> CountriesImportResult:
        errors: list[CountriesImportError] = []
        current = self._load()
        current_by_code = {country.code: country for country in current.countries}

        try:
            reader = csv.DictReader(io.StringIO(csv_text))
        except csv.Error as exc:
            return CountriesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=CountriesImportSummary(total_records=0, new_records=0, updated_records=0, unchanged_records=0),
                errors=[CountriesImportError(row_number=None, field=None, message=f"dataset is not parseable CSV: {exc}")],
            )

        fields = reader.fieldnames or []
        missing = [field for field in COUNTRY_TABULAR_FIELDS if field not in fields]
        if missing:
            return CountriesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=CountriesImportSummary(total_records=0, new_records=0, updated_records=0, unchanged_records=0),
                errors=[CountriesImportError(row_number=None, field=None, message=f"countries csv is missing required columns: {', '.join(missing)}")],
            )

        parsed_countries: list[Country] = []
        seen_codes: set[str] = set()
        for index, row in enumerate(reader, start=2):
            code = (row.get("code") or "").strip().upper()
            if not code:
                errors.append(CountriesImportError(row_number=index, field="code", message="code is required"))
                continue
            if not re.fullmatch(r"[A-Z]{3}", code):
                errors.append(CountriesImportError(row_number=index, field="code", message="code must be exactly 3 uppercase letters"))
            if code in seen_codes:
                errors.append(CountriesImportError(row_number=index, field="code", message=f"duplicate code '{code}' in import"))
                continue
            seen_codes.add(code)

            payload: dict[str, object] = {
                "code": code,
                "name": (row.get("name") or "").strip(),
                "flag_asset": ((row.get("flag_asset") or "").strip() or None),
                "region": (row.get("region") or "").strip(),
            }
            for int_field in (
                "population",
                "squash_popularity",
                "squash_access",
                "development_quality",
                "competition_quality",
                "elite_support",
                "squash_tradition",
            ):
                raw = (row.get(int_field) or "").strip()
                if not raw:
                    errors.append(CountriesImportError(row_number=index, field=int_field, message=f"{int_field} is required"))
                    continue
                try:
                    payload[int_field] = int(raw)
                except ValueError:
                    errors.append(CountriesImportError(row_number=index, field=int_field, message=f"{int_field} must be an integer"))

            raw_court_count = (row.get("court_count") or "").strip()
            if raw_court_count:
                try:
                    payload["court_count"] = int(raw_court_count)
                except ValueError:
                    errors.append(CountriesImportError(row_number=index, field="court_count", message="court_count must be an integer"))

            travel_region = (row.get("travel_region") or "").strip()
            if travel_region:
                payload["travel_region"] = travel_region
            notes = (row.get("notes") or "").strip()
            if notes:
                payload["notes"] = notes

            if any(err.row_number == index for err in errors):
                continue

            try:
                parsed_countries.append(Country.model_validate(payload))
            except ValidationError as exc:
                for issue in exc.errors():
                    field = str(issue.get("loc", [""])[0]) if issue.get("loc") else None
                    errors.append(CountriesImportError(row_number=index, field=field, message=str(issue.get("msg", "invalid value"))))

        if not parsed_countries and not errors:
            errors.append(CountriesImportError(row_number=None, field=None, message="dataset contains no records"))

        if errors:
            return CountriesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=CountriesImportSummary(total_records=len(parsed_countries), new_records=0, updated_records=0, unchanged_records=0),
                errors=errors,
            )

        new_records = 0
        updated_records = 0
        unchanged_records = 0
        for country in parsed_countries:
            existing = current_by_code.get(country.code)
            if existing is None:
                new_records += 1
            elif existing.model_dump(mode="json") == country.model_dump(mode="json"):
                unchanged_records += 1
            else:
                updated_records += 1

        summary = CountriesImportSummary(
            total_records=len(parsed_countries),
            new_records=new_records,
            updated_records=updated_records,
            unchanged_records=unchanged_records,
        )
        if dry_run:
            return CountriesImportResult(ok=True, dry_run=True, summary=summary, errors=[])

        replacement = CountriesConfig(dataset_status=current.dataset_status, countries=parsed_countries)
        self._save(replacement)
        return CountriesImportResult(ok=True, dry_run=False, summary=summary, errors=[])

    def create_country(self, payload: Country) -> Country:
        config = self._load()
        if any(country.code == payload.code for country in config.countries):
            raise ValueError(f"country with code '{payload.code}' already exists")
        updated = CountriesConfig(dataset_status=config.dataset_status, countries=[*config.countries, payload])
        self._save(updated)
        return payload

    def update_country(self, code: str, payload: Country) -> Country:
        normalized = code.upper()
        config = self._load()
        if payload.code != normalized and any(country.code == payload.code for country in config.countries):
            raise ValueError(f"country with code '{payload.code}' already exists")
        replaced = False
        updated_countries: list[Country] = []
        for country in config.countries:
            if country.code == normalized:
                updated_countries.append(payload)
                replaced = True
            else:
                updated_countries.append(country)
        if not replaced:
            raise LookupError(f"country '{normalized}' was not found")
        updated = CountriesConfig(dataset_status=config.dataset_status, countries=updated_countries)
        self._save(updated)
        return payload

    def delete_country(self, code: str) -> None:
        normalized = code.upper()
        config = self._load()
        remaining = [country for country in config.countries if country.code != normalized]
        if len(remaining) == len(config.countries):
            raise LookupError(f"country '{normalized}' was not found")
        updated = CountriesConfig(dataset_status=config.dataset_status, countries=remaining)
        self._save(updated)

    def replace_dataset(self, payload: CountriesConfig) -> CountriesConfig:
        seen: set[str] = set()
        for country in payload.countries:
            if country.code in seen:
                raise ValueError(f"duplicate country code '{country.code}' in dataset")
            seen.add(country.code)
        self._save(payload)
        return payload

    def _load(self) -> CountriesConfig:
        if self.config_path is not None:
            return load_countries_config(self.config_path)
        return WorldPackageCountryStore(self.package_root).load_config()

    def _save(self, payload: CountriesConfig) -> None:
        if self.config_path is None:
            manifest_path = self.package_root / "world.json"
            try:
                editable = bool(json.loads(manifest_path.read_text(encoding="utf-8")).get("editable"))
            except (OSError, json.JSONDecodeError, AttributeError):
                editable = False
            if not editable:
                raise PermissionError(f"World Package at {self.package_root} is built-in or not editable")
            WorldPackageCountryStore(self.package_root).replace_dataset(payload)
            return
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.config_path
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload.model_dump(mode="json"), fh, indent=2)
            fh.write("\n")
        tmp_path.replace(target)
