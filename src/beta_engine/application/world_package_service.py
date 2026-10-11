"""Import/export service for full authored world package payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from beta_engine.application.countries_service import CountriesConfigService
from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
from beta_engine.domain.countries import CountriesConfig
from beta_engine.domain.players import ManualPlayerOverridesRegistry

WORLD_PACKAGE_VERSION = "1"


@dataclass(frozen=True)
class WorldPackageSummary:
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


@dataclass(frozen=True)
class WorldPackageImportError:
    field: str | None
    message: str


@dataclass(frozen=True)
class WorldPackageImportResult:
    ok: bool
    dry_run: bool
    countries_summary: WorldPackageSummary
    manual_overrides_summary: WorldPackageSummary
    errors: list[WorldPackageImportError]


@dataclass(slots=True)
class WorldPackageService:
    countries_service: CountriesConfigService
    manual_overrides_service: ManualPlayerOverridesService

    def export_package_text(self) -> str:
        countries = sorted(self.countries_service.get_config().countries, key=lambda item: item.code)
        overrides = sorted(
            self.manual_overrides_service.list_overrides(),
            key=lambda item: (item.season, item.country_code, item.override_id),
        )
        package = {
            "package_version": WORLD_PACKAGE_VERSION,
            "exported_at": datetime.now(tz=timezone.utc).isoformat(),
            "countries_dataset": CountriesConfig(
                dataset_status=self.countries_service.get_config().dataset_status,
                countries=countries,
            ).model_dump(mode="json"),
            "manual_player_overrides_dataset": ManualPlayerOverridesRegistry(overrides=overrides).model_dump(mode="json"),
        }
        return json.dumps(package, indent=2) + "\n"

    def import_package_text(self, *, package_text: str, dry_run: bool) -> WorldPackageImportResult:
        countries_empty = WorldPackageSummary(total_records=0, new_records=0, updated_records=0, unchanged_records=0)
        overrides_empty = WorldPackageSummary(total_records=0, new_records=0, updated_records=0, unchanged_records=0)

        try:
            parsed = json.loads(package_text)
        except json.JSONDecodeError as exc:
            return WorldPackageImportResult(
                ok=False,
                dry_run=dry_run,
                countries_summary=countries_empty,
                manual_overrides_summary=overrides_empty,
                errors=[WorldPackageImportError(field="package_text", message=f"package_text is not parseable JSON: {exc.msg}")],
            )

        if not isinstance(parsed, dict):
            return WorldPackageImportResult(
                ok=False,
                dry_run=dry_run,
                countries_summary=countries_empty,
                manual_overrides_summary=overrides_empty,
                errors=[WorldPackageImportError(field="package", message="package root must be a JSON object")],
            )

        errors: list[WorldPackageImportError] = []
        package_version = str(parsed.get("package_version", "")).strip()
        if package_version != WORLD_PACKAGE_VERSION:
            errors.append(
                WorldPackageImportError(
                    field="package_version",
                    message=f"unsupported package_version '{package_version}'. Supported: {WORLD_PACKAGE_VERSION}",
                )
            )

        countries_payload = parsed.get("countries_dataset")
        overrides_payload = parsed.get("manual_player_overrides_dataset")

        imported_countries: CountriesConfig | None = None
        imported_overrides: ManualPlayerOverridesRegistry | None = None

        try:
            imported_countries = CountriesConfig.model_validate(countries_payload)
        except ValidationError as exc:
            for issue in exc.errors():
                loc = ".".join(str(part) for part in issue.get("loc", []))
                errors.append(
                    WorldPackageImportError(
                        field=f"countries_dataset.{loc}" if loc else "countries_dataset",
                        message=str(issue.get("msg", "invalid value")),
                    )
                )

        try:
            imported_overrides = ManualPlayerOverridesRegistry.model_validate(overrides_payload)
        except ValidationError as exc:
            for issue in exc.errors():
                loc = ".".join(str(part) for part in issue.get("loc", []))
                errors.append(
                    WorldPackageImportError(
                        field=f"manual_player_overrides_dataset.{loc}" if loc else "manual_player_overrides_dataset",
                        message=str(issue.get("msg", "invalid value")),
                    )
                )

        if imported_countries is not None:
            seen_codes: set[str] = set()
            for country in imported_countries.countries:
                if country.code in seen_codes:
                    errors.append(
                        WorldPackageImportError(
                            field="countries_dataset.countries",
                            message=f"duplicate country code '{country.code}' in countries dataset",
                        )
                    )
                seen_codes.add(country.code)

        imported_country_codes = {country.code for country in imported_countries.countries} if imported_countries else set()
        if imported_overrides is not None:
            seen_override_ids: set[str] = set()
            for override in imported_overrides.overrides:
                if override.override_id in seen_override_ids:
                    errors.append(
                        WorldPackageImportError(
                            field="manual_player_overrides_dataset.overrides",
                            message=f"duplicate override_id '{override.override_id}' in manual overrides dataset",
                        )
                    )
                seen_override_ids.add(override.override_id)
                if override.country_code not in imported_country_codes:
                    errors.append(
                        WorldPackageImportError(
                            field="manual_player_overrides_dataset.overrides.country_code",
                            message=(
                                f"override '{override.override_id}' country_code '{override.country_code}' does not exist "
                                "in imported countries_dataset"
                            ),
                        )
                    )

        if errors or imported_countries is None or imported_overrides is None:
            return WorldPackageImportResult(
                ok=False,
                dry_run=dry_run,
                countries_summary=countries_empty,
                manual_overrides_summary=overrides_empty,
                errors=errors,
            )

        countries_summary = self._countries_summary(imported_countries)
        overrides_summary = self._overrides_summary(imported_overrides)

        if dry_run:
            return WorldPackageImportResult(
                ok=True,
                dry_run=True,
                countries_summary=countries_summary,
                manual_overrides_summary=overrides_summary,
                errors=[],
            )

        self._apply_atomic(countries=imported_countries, overrides=imported_overrides)
        return WorldPackageImportResult(
            ok=True,
            dry_run=False,
            countries_summary=countries_summary,
            manual_overrides_summary=overrides_summary,
            errors=[],
        )

    def _countries_summary(self, imported: CountriesConfig) -> WorldPackageSummary:
        current_by_code = {item.code: item for item in self.countries_service.get_config().countries}
        new_records = 0
        updated_records = 0
        unchanged_records = 0
        for country in imported.countries:
            existing = current_by_code.get(country.code)
            if existing is None:
                new_records += 1
            elif existing.model_dump(mode="json") == country.model_dump(mode="json"):
                unchanged_records += 1
            else:
                updated_records += 1
        return WorldPackageSummary(
            total_records=len(imported.countries),
            new_records=new_records,
            updated_records=updated_records,
            unchanged_records=unchanged_records,
        )

    def _overrides_summary(self, imported: ManualPlayerOverridesRegistry) -> WorldPackageSummary:
        current_by_id = {item.override_id: item for item in self.manual_overrides_service.list_overrides()}
        new_records = 0
        updated_records = 0
        unchanged_records = 0
        for item in imported.overrides:
            existing = current_by_id.get(item.override_id)
            if existing is None:
                new_records += 1
            elif existing.model_dump(mode="json") == item.model_dump(mode="json"):
                unchanged_records += 1
            else:
                updated_records += 1
        return WorldPackageSummary(
            total_records=len(imported.overrides),
            new_records=new_records,
            updated_records=updated_records,
            unchanged_records=unchanged_records,
        )

    def _apply_atomic(self, *, countries: CountriesConfig, overrides: ManualPlayerOverridesRegistry) -> None:
        countries_path = self.countries_service.config_path
        if countries_path is None:
            raise PermissionError("Built-in World Package countries are read-only; use an editable custom package")
        overrides_path = self.manual_overrides_service.config_path
        countries_before = countries_path.read_text(encoding="utf-8") if countries_path.exists() else None
        overrides_before = overrides_path.read_text(encoding="utf-8") if overrides_path.exists() else None

        try:
            self._write_json_atomic(countries_path, countries.model_dump(mode="json"))
            self._write_json_atomic(overrides_path, overrides.model_dump(mode="json"))
        except Exception:
            self._restore_file(countries_path, countries_before)
            self._restore_file(overrides_path, overrides_before)
            raise

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        tmp_path.replace(path)

    @staticmethod
    def _restore_file(path: Path, previous_text: str | None) -> None:
        if previous_text is None:
            if path.exists():
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(previous_text, encoding="utf-8")
