"""File-backed tournament template dataset management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from beta_engine.domain.tournaments import SeasonCalendar, TournamentTemplate, TournamentTemplatesConfig
from beta_engine.infrastructure.tournament_config import load_tournament_templates_config


@dataclass(frozen=True)
class TournamentTemplatesDatasetMetadata:
    template_count: int
    source_path: str
    referenced_by_calendar: bool
    referenced_template_ids: list[str]


@dataclass(frozen=True)
class TournamentTemplatesValidationIssue:
    field: str | None
    message: str


@dataclass(frozen=True)
class TournamentTemplatesImportResult:
    ok: bool
    dry_run: bool
    template_count: int
    errors: list[TournamentTemplatesValidationIssue]


@dataclass(slots=True)
class TournamentTemplatesConfigService:
    """CRUD management for tournament templates backed by canonical JSON config."""

    config_path: Path = Path("config/tournament_templates/mvp_templates.json")
    calendar_dir: Path = Path("config/calendar")

    def __post_init__(self) -> None:
        if not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)
        if not isinstance(self.calendar_dir, Path):
            self.calendar_dir = Path(self.calendar_dir)

    def list_templates(self) -> list[TournamentTemplate]:
        return self._load().templates

    def get_config(self) -> TournamentTemplatesConfig:
        return self._load()

    def get_template(self, template_id: str) -> TournamentTemplate | None:
        return next((template for template in self._load().templates if template.template_id == template_id), None)

    def get_metadata(self) -> TournamentTemplatesDatasetMetadata:
        config = self._load()
        referenced_ids = self._referenced_template_ids()
        return TournamentTemplatesDatasetMetadata(
            template_count=len(config.templates),
            source_path=str(self.config_path),
            referenced_by_calendar=bool(referenced_ids),
            referenced_template_ids=referenced_ids,
        )

    def create_template(self, payload: TournamentTemplate) -> TournamentTemplate:
        config = self._load()
        if any(template.template_id == payload.template_id for template in config.templates):
            raise ValueError(f"tournament template with template_id '{payload.template_id}' already exists")
        updated = TournamentTemplatesConfig(templates=[*config.templates, payload])
        self._save(updated)
        return payload

    def update_template(self, template_id: str, payload: TournamentTemplate) -> TournamentTemplate:
        config = self._load()
        if payload.template_id != template_id and any(template.template_id == payload.template_id for template in config.templates):
            raise ValueError(f"tournament template with template_id '{payload.template_id}' already exists")

        replaced = False
        templates: list[TournamentTemplate] = []
        for template in config.templates:
            if template.template_id == template_id:
                templates.append(payload)
                replaced = True
            else:
                templates.append(template)
        if not replaced:
            raise LookupError(f"tournament template '{template_id}' was not found")

        updated = TournamentTemplatesConfig(templates=templates)
        self._save(updated)
        return payload

    def delete_template(self, template_id: str) -> None:
        references = self._template_references(template_id)
        if references:
            refs = ", ".join(references[:5])
            suffix = "" if len(references) <= 5 else f" (+{len(references) - 5} more)"
            raise ValueError(f"tournament template '{template_id}' is referenced by loaded season calendar events: {refs}{suffix}")

        config = self._load()
        remaining = [template for template in config.templates if template.template_id != template_id]
        if len(remaining) == len(config.templates):
            raise LookupError(f"tournament template '{template_id}' was not found")
        self._save(TournamentTemplatesConfig(templates=remaining))

    def export_dataset(self) -> TournamentTemplatesConfig:
        return self._load()

    def import_dataset(self, payload: dict[str, Any], *, dry_run: bool) -> TournamentTemplatesImportResult:
        config, errors = self.validate_dataset(payload)
        if errors:
            return TournamentTemplatesImportResult(ok=False, dry_run=dry_run, template_count=0, errors=errors)
        assert config is not None
        if not dry_run:
            self._save(config)
        return TournamentTemplatesImportResult(ok=True, dry_run=dry_run, template_count=len(config.templates), errors=[])

    def replace_dataset(self, payload: TournamentTemplatesConfig) -> TournamentTemplatesConfig:
        self._ensure_unique_template_ids(payload.templates)
        self._save(payload)
        return payload

    def validate_dataset(
        self, payload: dict[str, Any]
    ) -> tuple[TournamentTemplatesConfig | None, list[TournamentTemplatesValidationIssue]]:
        try:
            config = TournamentTemplatesConfig.model_validate(payload)
            self._ensure_unique_template_ids(config.templates)
        except ValidationError as exc:
            return None, [
                TournamentTemplatesValidationIssue(
                    field=".".join(str(part) for part in error.get("loc", [])) or None,
                    message=str(error.get("msg", "validation error")),
                )
                for error in exc.errors()
            ]
        except ValueError as exc:
            return None, [TournamentTemplatesValidationIssue(field="template_id", message=str(exc))]
        return config, []

    def validate_current_dataset(self) -> TournamentTemplatesImportResult:
        payload = self._read_raw()
        config, errors = self.validate_dataset(payload)
        return TournamentTemplatesImportResult(
            ok=not errors,
            dry_run=True,
            template_count=0 if config is None else len(config.templates),
            errors=errors,
        )

    def _load(self) -> TournamentTemplatesConfig:
        config = load_tournament_templates_config(self.config_path)
        self._ensure_unique_template_ids(config.templates)
        return config

    def _read_raw(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("tournament templates config must be a JSON object")
        return data

    def _save(self, payload: TournamentTemplatesConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.config_path
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload.model_dump(mode="json"), fh, indent=2)
            fh.write("\n")
        tmp_path.replace(target)

    def _ensure_unique_template_ids(self, templates: list[TournamentTemplate]) -> None:
        seen: set[str] = set()
        for template in templates:
            if template.template_id in seen:
                raise ValueError(f"duplicate template_id '{template.template_id}' in dataset")
            seen.add(template.template_id)

    def _calendar_paths(self) -> list[Path]:
        if not self.calendar_dir.exists():
            return []
        return sorted(self.calendar_dir.glob("*.json"))

    def _referenced_template_ids(self) -> list[str]:
        referenced: set[str] = set()
        for path in self._calendar_paths():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    calendar = SeasonCalendar.model_validate(json.load(fh))
            except (OSError, json.JSONDecodeError, ValidationError, ValueError):
                continue
            referenced.update(event.template_id for event in calendar.events)
        return sorted(referenced)

    def _template_references(self, template_id: str) -> list[str]:
        references: list[str] = []
        for path in self._calendar_paths():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    calendar = SeasonCalendar.model_validate(json.load(fh))
            except (OSError, json.JSONDecodeError, ValidationError, ValueError):
                continue
            for event in calendar.events:
                if event.template_id == template_id:
                    references.append(f"{path}:{event.event_id}")
        return references
