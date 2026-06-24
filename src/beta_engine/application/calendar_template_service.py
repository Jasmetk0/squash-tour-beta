"""Admin-authored calendar template persistence service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StrictInt, model_validator

CALENDAR_TEMPLATE_SCHEMA_VERSION = "calendar_templates.v1"
CalendarTemplateStatus = Literal["draft", "active", "archived"]
SeasonWeek = Annotated[StrictInt, Field(ge=1, le=61)]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class CalendarTemplateEvent(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category_code: str = Field(min_length=1)
    weeks: list[SeasonWeek] = Field(default_factory=list)
    qualification_weeks: list[SeasonWeek] = Field(default_factory=list)
    locked: bool = False
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    city: str | None = None
    venue: str | None = None
    notes: str | None = None
    source_template_id: str | None = None
    event_fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_week_uniqueness(self) -> "CalendarTemplateEvent":
        _ensure_unique_weeks(self.weeks, field_name="weeks")
        _ensure_unique_weeks(self.qualification_weeks, field_name="qualification_weeks")
        return self.with_fingerprint()

    def fingerprint_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"event_fingerprint"})

    def with_fingerprint(self) -> "CalendarTemplateEvent":
        return self.model_copy(update={"event_fingerprint": f"evt_{_digest(self.fingerprint_payload())[:24]}"})


class CalendarTemplate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    status: CalendarTemplateStatus = "draft"
    created_at: str | None = None
    updated_at: str | None = None
    events: list[CalendarTemplateEvent] = Field(default_factory=list)
    template_fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_template(self) -> "CalendarTemplate":
        seen_event_ids: set[str] = set()
        for event in self.events:
            if event.id in seen_event_ids:
                raise ValueError(f"Duplicate event id in calendar template: {event.id}")
            seen_event_ids.add(event.id)
            if self.status == "active" and not event.weeks:
                raise ValueError("Active calendar template events must include at least one week.")
        normalized_events = [event.with_fingerprint() for event in self.events]
        return self.model_copy(update={"events": normalized_events}).with_fingerprint()

    def fingerprint_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"created_at", "updated_at", "template_fingerprint"})
        for event in payload.get("events", []):
            event.pop("event_fingerprint", None)
        return payload

    def with_fingerprint(self) -> "CalendarTemplate":
        return self.model_copy(update={"template_fingerprint": f"tpl_{_digest(self.fingerprint_payload())[:24]}"})


class CalendarTemplateRegistry(BaseModel):
    schema_version: Literal["calendar_templates.v1"] = CALENDAR_TEMPLATE_SCHEMA_VERSION
    templates_by_id: dict[str, CalendarTemplate] = Field(default_factory=dict)


class CalendarTemplateListResponse(BaseModel):
    templates: list[CalendarTemplate] = Field(default_factory=list)
    source_path: str | None = None
    status: str = "ok"
    schema_version: str = CALENDAR_TEMPLATE_SCHEMA_VERSION


class CalendarTemplateDetailResponse(BaseModel):
    template: CalendarTemplate | None = None
    source_path: str | None = None
    status: str = "ok"
    schema_version: str = CALENDAR_TEMPLATE_SCHEMA_VERSION


@dataclass(slots=True)
class CalendarTemplateService:
    registry_path: Path = Path("config/world/calendar_templates.json")

    def __post_init__(self) -> None:
        if not isinstance(self.registry_path, Path):
            self.registry_path = Path(self.registry_path)

    def list_templates(self) -> CalendarTemplateListResponse:
        registry = self._load_registry()
        templates = sorted(registry.templates_by_id.values(), key=lambda item: item.id)
        return CalendarTemplateListResponse(templates=templates, source_path=str(self.registry_path), status="ok")

    def get_template(self, *, template_id: str) -> CalendarTemplateDetailResponse:
        registry = self._load_registry()
        return CalendarTemplateDetailResponse(template=registry.templates_by_id.get(template_id), source_path=str(self.registry_path), status="ok")

    def create_template(self, *, template: CalendarTemplate) -> CalendarTemplate:
        registry = self._load_registry()
        if template.id in registry.templates_by_id:
            raise ValueError(f"Calendar template already exists: {template.id}")
        now = _utc_now_iso()
        persisted = template.model_copy(update={"created_at": template.created_at or now, "updated_at": template.updated_at or now}).with_fingerprint()
        next_templates = dict(registry.templates_by_id)
        next_templates[persisted.id] = persisted
        self._save_registry(CalendarTemplateRegistry(templates_by_id=next_templates))
        return persisted

    def update_template(self, *, template_id: str, template: CalendarTemplate) -> CalendarTemplate:
        if template.id != template_id:
            raise ValueError("Calendar template id in path and payload must match.")
        registry = self._load_registry()
        existing = registry.templates_by_id.get(template_id)
        if existing is None:
            raise KeyError(template_id)
        now = _utc_now_iso()
        persisted = template.model_copy(update={"created_at": template.created_at or existing.created_at, "updated_at": now}).with_fingerprint()
        next_templates = dict(registry.templates_by_id)
        next_templates[template_id] = persisted
        self._save_registry(CalendarTemplateRegistry(templates_by_id=next_templates))
        return persisted

    def archive_template(self, *, template_id: str) -> CalendarTemplate:
        registry = self._load_registry()
        existing = registry.templates_by_id.get(template_id)
        if existing is None:
            raise KeyError(template_id)
        archived = existing.model_copy(update={"status": "archived", "updated_at": _utc_now_iso()}).with_fingerprint()
        next_templates = dict(registry.templates_by_id)
        next_templates[template_id] = archived
        self._save_registry(CalendarTemplateRegistry(templates_by_id=next_templates))
        return archived

    def _load_registry(self) -> CalendarTemplateRegistry:
        if not self.registry_path.exists():
            return CalendarTemplateRegistry()
        return CalendarTemplateRegistry.model_validate(json.loads(self.registry_path.read_text(encoding="utf-8")))

    def _save_registry(self, registry: CalendarTemplateRegistry) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.registry_path.with_suffix(f"{self.registry_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.registry_path)


def _ensure_unique_weeks(weeks: list[int], *, field_name: str) -> None:
    if len(weeks) != len(set(weeks)):
        raise ValueError(f"{field_name} must contain unique season weeks.")
