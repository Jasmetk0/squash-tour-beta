"""Read-only validation for World Package storage."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
from beta_engine.infrastructure.world_config import load_countries_config

ValidationSeverity = Literal["info", "warning", "error"]
ValidationCheckStatus = Literal["passed", "warning", "failed"]
ValidationStatus = Literal["valid", "warnings", "errors"]


@dataclass(frozen=True)
class WorldPackageValidationCheck:
    code: str
    severity: ValidationSeverity
    status: ValidationCheckStatus
    message: str
    path: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class WorldPackageValidationResult:
    world_id: str
    status: ValidationStatus
    error_count: int
    warning_count: int
    info_count: int
    checks: list[WorldPackageValidationCheck]


@dataclass(slots=True)
class WorldPackageValidationService:
    """Validate built-in World Package files without mutating repository data."""

    registry_service: WorldPackageRegistryService

    def validate_package(self, world_id: str) -> WorldPackageValidationResult | None:
        normalized = world_id.strip().lower()
        record = self.registry_service.get_package(normalized)
        if record is None:
            return None

        checks: list[WorldPackageValidationCheck] = []
        paths = self.registry_service.package_paths(record.world_id)
        if paths is None:
            return None

        world_payload = self._read_json(paths["world"], checks, code="world_metadata_json_valid")
        continents_payload = self._read_json(paths["continents"], checks, code="continents_json_valid")
        regions_payload = self._read_json(paths["regions"], checks, code="regions_json_valid")
        travel_regions_payload = self._read_json(paths["travel_regions"], checks, code="travel_regions_json_valid")
        countries_payload = self._read_json(paths["countries"], checks, code="countries_json_valid")

        self._validate_world_metadata(world_payload, paths["world"], checks, expected_world_id=record.world_id, expected_type=record.type, expected_status=record.status, expected_source=record.source, expected_editable=record.editable, expected_deletable=record.deletable, expected_archivable=record.archivable)
        continent_codes, continent_count = self._validate_code_name_collection(
            continents_payload, "continents", paths["continents"], checks, "continents_valid", required_non_empty=False
        )
        region_codes, region_count = self._validate_regions(regions_payload, continent_codes, paths["regions"], checks)
        travel_region_codes, travel_region_count = self._validate_code_name_collection(
            travel_regions_payload,
            "travel_regions",
            paths["travel_regions"],
            checks,
            "travel_regions_valid",
            required_non_empty=False,
        )
        country_count = self._validate_countries(countries_payload, region_codes, travel_region_codes, paths["countries"], checks)
        self._validate_population_coverage(world_payload, countries_payload, paths["countries"], checks)
        self._validate_registry_consistency(record.world_id, checks, country_count, continent_count, region_count, travel_region_count)

        error_count = sum(1 for check in checks if check.severity == "error" and check.status == "failed")
        warning_count = sum(1 for check in checks if check.severity == "warning")
        info_count = sum(1 for check in checks if check.severity == "info")
        status: ValidationStatus = "errors" if error_count else "warnings" if warning_count else "valid"
        return WorldPackageValidationResult(
            world_id=record.world_id,
            status=status,
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            checks=checks,
        )

    def _read_json(self, path: Path, checks: list[WorldPackageValidationCheck], *, code: str) -> dict[str, Any] | None:
        path_text = str(path)
        if not path.exists():
            checks.append(WorldPackageValidationCheck(code=code, severity="error", status="failed", message=f"{path.name} is missing.", path=path_text))
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append(WorldPackageValidationCheck(code=code, severity="error", status="failed", message=f"{path.name} is not valid JSON: {exc.msg}.", path=path_text))
            return None
        if not isinstance(payload, dict):
            checks.append(WorldPackageValidationCheck(code=code, severity="error", status="failed", message=f"{path.name} must contain a JSON object.", path=path_text))
            return None
        checks.append(WorldPackageValidationCheck(code=code, severity="info", status="passed", message=f"{path.name} is present and valid JSON.", path=path_text))
        return payload

    def _validate_world_metadata(
        self,
        payload: dict[str, Any] | None,
        path: Path,
        checks: list[WorldPackageValidationCheck],
        *,
        expected_world_id: str,
        expected_type: str,
        expected_status: str,
        expected_source: str,
        expected_editable: bool,
        expected_deletable: bool,
        expected_archivable: bool,
    ) -> None:
        expected = {"world_id": expected_world_id, "type": expected_type, "status": expected_status, "source": expected_source, "editable": expected_editable, "deletable": expected_deletable, "archivable": expected_archivable}
        if payload is None:
            return
        missing = [field for field in ("world_id", "name", "version", "content_schema_version", *expected.keys()) if field not in payload]
        mismatches = [field for field, value in expected.items() if payload.get(field) != value]
        empty = [field for field in ("world_id", "name", "version", "content_schema_version") if not isinstance(payload.get(field), str) or not payload.get(field).strip()]
        if missing or mismatches or empty:
            checks.append(WorldPackageValidationCheck("world_metadata_valid", "error", "failed", f"world.json metadata is invalid (missing={sorted(set(missing))}, mismatches={mismatches}, empty={empty}).", str(path)))
        else:
            checks.append(WorldPackageValidationCheck("world_metadata_valid", "info", "passed", f"world.json is present and declares {expected_world_id}.", str(path), "world_id"))

    def _validate_code_name_collection(self, payload: dict[str, Any] | None, key: str, path: Path, checks: list[WorldPackageValidationCheck], code: str, *, required_non_empty: bool) -> tuple[set[str], int]:
        if payload is None:
            return set(), 0
        items = payload.get(key)
        if not isinstance(items, list) or (required_non_empty and not items):
            checks.append(WorldPackageValidationCheck(code, "error", "failed", f"{key} must be an array" + (" with at least one item." if required_non_empty else "."), str(path), key))
            return set(), 0
        codes: list[str] = []
        errors: list[str] = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{key}[{idx}] must be an object")
                continue
            item_code = item.get("code")
            name = item.get("name")
            if not isinstance(item_code, str) or not item_code.strip():
                errors.append(f"{key}[{idx}].code must be a non-empty string")
            else:
                codes.append(item_code)
            if not isinstance(name, str) or not name.strip():
                errors.append(f"{key}[{idx}].name must be a non-empty string")
        duplicates = sorted({value for value in codes if codes.count(value) > 1})
        if duplicates:
            errors.append(f"duplicate codes: {duplicates}")
        if errors:
            checks.append(WorldPackageValidationCheck(code, "error", "failed", f"{key} validation failed: {'; '.join(errors)}.", str(path), key))
        else:
            checks.append(WorldPackageValidationCheck(code, "info", "passed", f"{key} array is present with unique non-empty codes and names.", str(path), key))
        return set(codes), len(items)

    def _validate_regions(self, payload: dict[str, Any] | None, continent_codes: set[str], path: Path, checks: list[WorldPackageValidationCheck]) -> tuple[set[str], int]:
        region_codes, count = self._validate_code_name_collection(payload, "regions", path, checks, "regions_valid", required_non_empty=False)
        if payload is None or not isinstance(payload.get("regions"), list):
            return region_codes, count
        missing_continents: list[str] = []
        null_continents: list[str] = []
        for item in payload["regions"]:
            if isinstance(item, dict):
                region_code = str(item.get("code", ""))
                continent_code = item.get("continent_code")
                if continent_code is None:
                    null_continents.append(region_code)
                elif continent_code not in continent_codes:
                    missing_continents.append(region_code)
        if missing_continents:
            checks.append(WorldPackageValidationCheck("regions_continent_references_valid", "error", "failed", f"Regions reference unknown continent codes: {missing_continents}.", str(path), "continent_code"))
        else:
            checks.append(WorldPackageValidationCheck("regions_continent_references_valid", "info", "passed", "All non-null region continent_code values reference continents.json.", str(path), "continent_code"))
        if null_continents:
            checks.append(WorldPackageValidationCheck("regions_null_continent_codes_allowed", "warning", "warning", f"Regions with intentionally unresolved continent_code values: {null_continents}.", str(path), "continent_code"))
        return region_codes, count

    def _validate_countries(self, payload: dict[str, Any] | None, region_codes: set[str], travel_region_codes: set[str], path: Path, checks: list[WorldPackageValidationCheck]) -> int:
        if payload is None:
            return 0
        try:
            load_countries_config(path)
            checks.append(WorldPackageValidationCheck("countries_loader_valid", "info", "passed", "countries.json loads through the existing country config loader.", str(path)))
        except ValidationError as exc:
            checks.append(WorldPackageValidationCheck("countries_loader_valid", "error", "failed", f"countries.json failed existing country config loader validation: {exc.errors()[0]['msg']}.", str(path)))
        countries = payload.get("countries")
        if not isinstance(countries, list) or not countries:
            checks.append(WorldPackageValidationCheck("countries_valid", "error", "failed", "countries must be a non-empty array.", str(path), "countries"))
            return 0
        codes: list[str] = []
        errors: list[str] = []
        for idx, country in enumerate(countries):
            if not isinstance(country, dict):
                errors.append(f"countries[{idx}] must be an object")
                continue
            code = country.get("code")
            name = country.get("name")
            region = country.get("region")
            travel_region = country.get("travel_region")
            if not isinstance(code, str) or not code.strip():
                errors.append(f"countries[{idx}].code must be a non-empty string")
            else:
                codes.append(code)
            if not isinstance(name, str) or not name.strip():
                errors.append(f"countries[{idx}].name must be a non-empty string")
            if not isinstance(region, str) or not region.strip():
                errors.append(f"countries[{idx}].region must be a non-empty string")
            elif region not in region_codes:
                errors.append(f"countries[{idx}].region references unknown region {region}")
            if travel_region is not None and travel_region not in travel_region_codes:
                errors.append(f"countries[{idx}].travel_region references unknown travel region {travel_region}")
        duplicates = sorted({value for value in codes if codes.count(value) > 1})
        if duplicates:
            errors.append(f"duplicate country codes: {duplicates}")
        if errors:
            checks.append(WorldPackageValidationCheck("countries_valid", "error", "failed", f"countries validation failed: {'; '.join(errors)}.", str(path), "countries"))
        else:
            checks.append(WorldPackageValidationCheck("countries_valid", "info", "passed", "countries array is present with unique country codes, names, and valid region references.", str(path), "countries"))
        return len(countries)

    def _validate_population_coverage(
        self,
        world_payload: dict[str, Any] | None,
        countries_payload: dict[str, Any] | None,
        path: Path,
        checks: list[WorldPackageValidationCheck],
    ) -> None:
        coverage = world_payload.get("population_years") if world_payload is not None else None
        if coverage is None:
            return
        if not isinstance(coverage, dict) or not isinstance(coverage.get("from"), int) or not isinstance(coverage.get("to"), int):
            checks.append(WorldPackageValidationCheck("population_coverage_valid", "error", "failed", "world.json population_years must contain integer from/to values.", str(path), "population_by_year"))
            return
        start, end = coverage["from"], coverage["to"]
        if start > end or start < 1955 or end > 2050:
            checks.append(WorldPackageValidationCheck("population_coverage_valid", "error", "failed", f"Declared population coverage {start}–{end} is outside the supported 1955–2050 range.", str(path), "population_by_year"))
            return
        countries = countries_payload.get("countries") if countries_payload is not None else None
        if not isinstance(countries, list):
            return
        required_years = {str(year) for year in range(start, end + 1)}
        incomplete: list[str] = []
        for country in countries:
            if not isinstance(country, dict):
                continue
            timeline = country.get("population_by_year")
            available = {
                str(year)
                for year, population in timeline.items()
                if isinstance(timeline, dict) and isinstance(population, int) and population > 0
            } if isinstance(timeline, dict) else set()
            if not required_years.issubset(available):
                incomplete.append(str(country.get("code", "?")))
        if incomplete:
            checks.append(WorldPackageValidationCheck("population_coverage_valid", "error", "failed", f"Countries missing positive annual population values for {start}–{end}: {incomplete}.", str(path), "population_by_year"))
        else:
            checks.append(WorldPackageValidationCheck("population_coverage_valid", "info", "passed", f"All countries have positive annual population values for {start}–{end}.", str(path), "population_by_year"))

    def _validate_registry_consistency(self, world_id: str, checks: list[WorldPackageValidationCheck], country_count: int, continent_count: int, region_count: int, travel_region_count: int) -> None:
        try:
            record = self.registry_service.get_package(world_id)
        except Exception as exc:  # noqa: BLE001 - validation reports registry build failures as data health checks.
            checks.append(WorldPackageValidationCheck("registry_consistency_valid", "error", "failed", f"Registry record could not be built: {exc}."))
            return
        if record is None:
            checks.append(WorldPackageValidationCheck("registry_consistency_valid", "error", "failed", f"Registry did not return {world_id}."))
            return
        errors: list[str] = []
        expected = {"country_count": country_count, "continent_count": continent_count, "region_count": region_count, "travel_region_count": travel_region_count}
        for field, value in expected.items():
            if getattr(record, field) != value:
                errors.append(f"{field}={getattr(record, field)!r} expected {value!r}")
        if not re.fullmatch(r"[0-9a-f]{64}", record.fingerprint):
            errors.append("fingerprint must be 64 lowercase hex characters")
        if errors:
            checks.append(WorldPackageValidationCheck("registry_consistency_valid", "error", "failed", f"Registry consistency failed: {'; '.join(errors)}."))
        else:
            checks.append(WorldPackageValidationCheck("registry_consistency_valid", "info", "passed", f"Registry record is consistent with {world_id} package storage."))
