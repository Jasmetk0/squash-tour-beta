"""File-backed CRUD + bulk tabular workflow service for world manual player overrides."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from beta_engine.domain.players import (
    ManualPlayerAttributeOverrides,
    ManualPlayerHiddenTraitOverrides,
    ManualPlayerOverride,
    ManualPlayerOverridesRegistry,
)
from beta_engine.infrastructure.world_config import (
    MANUAL_PLAYER_OVERRIDE_TABULAR_FIELDS,
    load_manual_player_overrides_config,
)


@dataclass(frozen=True)
class ManualPlayerOverridesImportError:
    row_number: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class ManualPlayerOverridesImportSummary:
    total_records: int
    new_records: int
    updated_records: int
    unchanged_records: int


@dataclass(frozen=True)
class ManualPlayerOverridesImportResult:
    ok: bool
    dry_run: bool
    summary: ManualPlayerOverridesImportSummary
    errors: list[ManualPlayerOverridesImportError]


@dataclass(slots=True)
class ManualPlayerOverridesService:
    config_path: Path = Path("config/world/manual_player_overrides.json")

    def __post_init__(self) -> None:
        if not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)

    def list_overrides(
        self,
        *,
        season: int | None = None,
        country_code: str | None = None,
        enabled: bool | None = None,
    ) -> list[ManualPlayerOverride]:
        items = self._load().overrides
        if season is not None:
            items = [item for item in items if item.season == season]
        if country_code is not None:
            normalized_country = country_code.upper()
            items = [item for item in items if item.country_code == normalized_country]
        if enabled is not None:
            items = [item for item in items if item.enabled is enabled]
        return sorted(items, key=lambda item: (item.season, item.country_code, item.override_id))

    def get_override(self, override_id: str) -> ManualPlayerOverride | None:
        normalized_id = override_id.strip()
        return next((item for item in self._load().overrides if item.override_id == normalized_id), None)

    def export_overrides_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=MANUAL_PLAYER_OVERRIDE_TABULAR_FIELDS)
        writer.writeheader()
        for item in sorted(self._load().overrides, key=lambda row: row.override_id):
            writer.writerow(self._to_tabular_row(item))
        return output.getvalue()

    def import_overrides_csv(
        self,
        *,
        csv_text: str,
        dry_run: bool,
        countries: set[str],
    ) -> ManualPlayerOverridesImportResult:
        current = self._load()
        current_by_id = {item.override_id: item for item in current.overrides}
        errors: list[ManualPlayerOverridesImportError] = []

        try:
            reader = csv.DictReader(io.StringIO(csv_text), strict=True)
            rows = list(reader)
        except csv.Error as exc:
            return ManualPlayerOverridesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=ManualPlayerOverridesImportSummary(0, 0, 0, 0),
                errors=[ManualPlayerOverridesImportError(None, None, f"dataset is not parseable CSV: {exc}")],
            )

        fields = reader.fieldnames or []
        missing = [field for field in MANUAL_PLAYER_OVERRIDE_TABULAR_FIELDS if field not in fields]
        if missing:
            return ManualPlayerOverridesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=ManualPlayerOverridesImportSummary(0, 0, 0, 0),
                errors=[
                    ManualPlayerOverridesImportError(
                        None,
                        None,
                        f"manual overrides csv is missing required columns: {', '.join(missing)}",
                    )
                ],
            )

        parsed: list[ManualPlayerOverride] = []
        seen_ids: set[str] = set()
        known_countries = {code.upper() for code in countries}

        for index, row in enumerate(rows, start=2):
            override_id = (row.get("override_id") or "").strip()
            if not override_id:
                errors.append(ManualPlayerOverridesImportError(index, "override_id", "override_id is required"))
                continue
            if override_id in seen_ids:
                errors.append(
                    ManualPlayerOverridesImportError(index, "override_id", f"duplicate override_id '{override_id}' in import")
                )
                continue
            seen_ids.add(override_id)

            country_code = (row.get("country_code") or "").strip().upper()
            if country_code not in known_countries:
                errors.append(
                    ManualPlayerOverridesImportError(
                        index,
                        "country_code",
                        f"country_code '{country_code}' does not exist in countries dataset",
                    )
                )

            payload: dict[str, object] = {
                "override_id": override_id,
                "season": self._parse_int_required(row=row, field="season", index=index, errors=errors),
                "country_code": country_code,
                "player_name": (row.get("player_name") or "").strip(),
                "player_slug": self._null_if_blank(row.get("player_slug")),
                "player_id": self._null_if_blank(row.get("player_id")),
                "age": self._parse_int_required(row=row, field="age", index=index, errors=errors),
                "profile_tier": self._null_if_blank(row.get("profile_tier")),
                "quality_band_override": self._null_if_blank(row.get("quality_band_override")),
                "is_exceptional": self._parse_bool(row=row, field="is_exceptional", index=index, errors=errors),
                "enabled": self._parse_bool(row=row, field="enabled", index=index, errors=errors),
                "notes": self._null_if_blank(row.get("notes")),
            }

            attr_payload = self._parse_overrides(
                index=index,
                row=row,
                errors=errors,
                fields=(
                    "attribute_technique",
                    "attribute_movement",
                    "attribute_physical",
                    "attribute_mental",
                    "attribute_consistency",
                    "attribute_clutch",
                    "attribute_recovery",
                ),
                parser=self._parse_int_optional,
                normalize=lambda key: key.removeprefix("attribute_"),
            )
            if attr_payload:
                try:
                    payload["attribute_overrides"] = ManualPlayerAttributeOverrides.model_validate(attr_payload).model_dump(mode="json")
                except ValidationError as exc:
                    for issue in exc.errors():
                        field = str(issue.get("loc", [""])[0]) if issue.get("loc") else None
                        errors.append(
                            ManualPlayerOverridesImportError(
                                row_number=index,
                                field=f"attribute_{field}" if field else "attribute_overrides",
                                message=str(issue.get("msg", "invalid value")),
                            )
                        )

            trait_payload = self._parse_overrides(
                index=index,
                row=row,
                errors=errors,
                fields=(
                    "trait_potential_ceiling",
                    "trait_growth_curve",
                    "trait_professionalism",
                    "trait_ambition",
                    "trait_travel_tolerance",
                    "trait_schedule_aggression",
                    "trait_injury_proneness",
                    "trait_resilience",
                ),
                parser=self._parse_trait_value,
                normalize=lambda key: key.removeprefix("trait_"),
            )
            if trait_payload:
                try:
                    payload["hidden_trait_overrides"] = ManualPlayerHiddenTraitOverrides.model_validate(trait_payload).model_dump(mode="json")
                except ValidationError as exc:
                    for issue in exc.errors():
                        field = str(issue.get("loc", [""])[0]) if issue.get("loc") else None
                        errors.append(
                            ManualPlayerOverridesImportError(
                                row_number=index,
                                field=f"trait_{field}" if field else "hidden_trait_overrides",
                                message=str(issue.get("msg", "invalid value")),
                            )
                        )

            if any(err.row_number == index for err in errors):
                continue

            try:
                parsed.append(ManualPlayerOverride.model_validate(payload))
            except ValidationError as exc:
                for issue in exc.errors():
                    field = str(issue.get("loc", [""])[0]) if issue.get("loc") else None
                    errors.append(
                        ManualPlayerOverridesImportError(
                            row_number=index,
                            field=field,
                            message=str(issue.get("msg", "invalid value")),
                        )
                    )

        if not parsed and not errors:
            errors.append(ManualPlayerOverridesImportError(None, None, "dataset contains no records"))

        if errors:
            return ManualPlayerOverridesImportResult(
                ok=False,
                dry_run=dry_run,
                summary=ManualPlayerOverridesImportSummary(len(parsed), 0, 0, 0),
                errors=errors,
            )

        new_records = 0
        updated_records = 0
        unchanged_records = 0
        for item in parsed:
            existing = current_by_id.get(item.override_id)
            if existing is None:
                new_records += 1
            elif existing.model_dump(mode="json") == item.model_dump(mode="json"):
                unchanged_records += 1
            else:
                updated_records += 1

        summary = ManualPlayerOverridesImportSummary(len(parsed), new_records, updated_records, unchanged_records)
        if dry_run:
            return ManualPlayerOverridesImportResult(ok=True, dry_run=True, summary=summary, errors=[])

        self._save(ManualPlayerOverridesRegistry(overrides=parsed))
        return ManualPlayerOverridesImportResult(ok=True, dry_run=False, summary=summary, errors=[])

    def create_override(self, payload: ManualPlayerOverride) -> ManualPlayerOverride:
        registry = self._load()
        if any(item.override_id == payload.override_id for item in registry.overrides):
            raise ValueError(f"override with id '{payload.override_id}' already exists")
        self._save(ManualPlayerOverridesRegistry(overrides=[*registry.overrides, payload]))
        return payload

    def update_override(self, override_id: str, payload: ManualPlayerOverride) -> ManualPlayerOverride:
        normalized_id = override_id.strip()
        registry = self._load()

        if payload.override_id != normalized_id and any(item.override_id == payload.override_id for item in registry.overrides):
            raise ValueError(f"override with id '{payload.override_id}' already exists")

        updated_items: list[ManualPlayerOverride] = []
        replaced = False
        for item in registry.overrides:
            if item.override_id == normalized_id:
                updated_items.append(payload)
                replaced = True
            else:
                updated_items.append(item)

        if not replaced:
            raise LookupError(f"override '{normalized_id}' was not found")

        self._save(ManualPlayerOverridesRegistry(overrides=updated_items))
        return payload

    def delete_override(self, override_id: str) -> None:
        normalized_id = override_id.strip()
        registry = self._load()
        remaining = [item for item in registry.overrides if item.override_id != normalized_id]
        if len(remaining) == len(registry.overrides):
            raise LookupError(f"override '{normalized_id}' was not found")
        self._save(ManualPlayerOverridesRegistry(overrides=remaining))

    def _load(self) -> ManualPlayerOverridesRegistry:
        if not self.config_path.exists():
            return ManualPlayerOverridesRegistry(overrides=[])
        return load_manual_player_overrides_config(self.config_path)

    def _save(self, payload: ManualPlayerOverridesRegistry) -> None:
        seen: set[str] = set()
        for item in payload.overrides:
            if item.override_id in seen:
                raise ValueError(f"duplicate override id '{item.override_id}' in dataset")
            seen.add(item.override_id)

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.config_path
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload.model_dump(mode="json"), fh, indent=2)
            fh.write("\n")
        tmp_path.replace(target)

    def _to_tabular_row(self, item: ManualPlayerOverride) -> dict[str, object]:
        attributes = item.attribute_overrides.model_dump(mode="json") if item.attribute_overrides else {}
        traits = item.hidden_trait_overrides.model_dump(mode="json") if item.hidden_trait_overrides else {}
        return {
            "override_id": item.override_id,
            "season": item.season,
            "country_code": item.country_code,
            "player_name": item.player_name,
            "player_slug": item.player_slug or "",
            "player_id": item.player_id or "",
            "age": item.age,
            "profile_tier": item.profile_tier.value,
            "quality_band_override": item.quality_band_override.value if item.quality_band_override else "",
            "is_exceptional": str(item.is_exceptional).lower(),
            "enabled": str(item.enabled).lower(),
            "notes": item.notes or "",
            "attribute_technique": attributes.get("technique") if attributes.get("technique") is not None else "",
            "attribute_movement": attributes.get("movement") if attributes.get("movement") is not None else "",
            "attribute_physical": attributes.get("physical") if attributes.get("physical") is not None else "",
            "attribute_mental": attributes.get("mental") if attributes.get("mental") is not None else "",
            "attribute_consistency": attributes.get("consistency") if attributes.get("consistency") is not None else "",
            "attribute_clutch": attributes.get("clutch") if attributes.get("clutch") is not None else "",
            "attribute_recovery": attributes.get("recovery") if attributes.get("recovery") is not None else "",
            "trait_potential_ceiling": traits.get("potential_ceiling") if traits.get("potential_ceiling") is not None else "",
            "trait_growth_curve": traits.get("growth_curve") if traits.get("growth_curve") is not None else "",
            "trait_professionalism": traits.get("professionalism") if traits.get("professionalism") is not None else "",
            "trait_ambition": traits.get("ambition") if traits.get("ambition") is not None else "",
            "trait_travel_tolerance": traits.get("travel_tolerance") if traits.get("travel_tolerance") is not None else "",
            "trait_schedule_aggression": traits.get("schedule_aggression") if traits.get("schedule_aggression") is not None else "",
            "trait_injury_proneness": traits.get("injury_proneness") if traits.get("injury_proneness") is not None else "",
            "trait_resilience": traits.get("resilience") if traits.get("resilience") is not None else "",
        }

    @staticmethod
    def _null_if_blank(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _parse_int_required(*, row: dict[str, str | None], field: str, index: int, errors: list[ManualPlayerOverridesImportError]) -> int | None:
        raw = (row.get(field) or "").strip()
        if not raw:
            errors.append(ManualPlayerOverridesImportError(index, field, f"{field} is required"))
            return None
        try:
            return int(raw)
        except ValueError:
            errors.append(ManualPlayerOverridesImportError(index, field, f"{field} must be an integer"))
            return None

    @staticmethod
    def _parse_int_optional(*, row: dict[str, str | None], field: str, index: int, errors: list[ManualPlayerOverridesImportError]) -> int | None:
        raw = (row.get(field) or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            errors.append(ManualPlayerOverridesImportError(index, field, f"{field} must be an integer"))
            return None

    @staticmethod
    def _parse_bool(*, row: dict[str, str | None], field: str, index: int, errors: list[ManualPlayerOverridesImportError]) -> bool | None:
        raw = (row.get(field) or "").strip().lower()
        if raw in {"true", "1", "yes"}:
            return True
        if raw in {"false", "0", "no"}:
            return False
        errors.append(ManualPlayerOverridesImportError(index, field, f"{field} must be true/false"))
        return None

    def _parse_trait_value(
        self,
        *,
        row: dict[str, str | None],
        field: str,
        index: int,
        errors: list[ManualPlayerOverridesImportError],
    ) -> str | float | int | None:
        if field == "trait_growth_curve":
            return self._null_if_blank(row.get(field))
        if field == "trait_potential_ceiling":
            return self._parse_int_optional(row=row, field=field, index=index, errors=errors)

        raw = (row.get(field) or "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            errors.append(ManualPlayerOverridesImportError(index, field, f"{field} must be a number"))
            return None

    @staticmethod
    def _parse_overrides(
        *,
        index: int,
        row: dict[str, str | None],
        errors: list[ManualPlayerOverridesImportError],
        fields: tuple[str, ...],
        parser,
        normalize,
    ) -> dict[str, object]:
        payload: dict[str, object] = {}
        for field in fields:
            parsed = parser(row=row, field=field, index=index, errors=errors)
            if parsed is not None:
                payload[normalize(field)] = parsed
        return payload
