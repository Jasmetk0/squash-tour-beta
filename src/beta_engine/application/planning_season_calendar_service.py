"""File-backed Admin planning season calendars.

Planning calendars are template-native Admin planning artifacts. They intentionally
stay separate from canonical simulation season calendars and do not adapt to
SeasonCalendarEvent in this phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StrictInt, field_validator, model_validator

from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label

PLANNING_SEASON_CALENDAR_SCHEMA_VERSION = "planning_season_calendars.v1"
PlanningCalendarStatus = Literal["draft", "active", "archived"]
PlanningSeasonWeek = Annotated[StrictInt, Field(ge=1, le=61)]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prefix: str, payload: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:24]}"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalized_long_season_label(label: str) -> str:
    return to_long_season_label(normalize_season_label(label))


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class PlanningCalendarEventApplyMetadata(BaseModel):
    """Deterministic provenance metadata for future planning apply commands."""

    last_applied_at: str | None = None
    last_applied_by: str | None = None
    last_apply_command_id: str | None = None
    last_apply_audit_record_id: str | None = None
    last_apply_policy: str | None = None
    last_source_template_fingerprint: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def fingerprint_payload(self) -> dict[str, Any]:
        return self.model_dump(
            mode="json",
            exclude={"last_applied_at", "last_applied_by"},
        )


class PlanningCalendarEvent(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category_code: str = Field(min_length=1)
    weeks: list[PlanningSeasonWeek] = Field(default_factory=list)
    qualification_weeks: list[PlanningSeasonWeek] = Field(default_factory=list)
    locked: bool = False
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    city: str | None = None
    venue: str | None = None
    notes: str | None = None
    source_template_id: str | None = None
    source_template_fingerprint: str | None = None
    source_template_event_id: str | None = None
    source_template_event_fingerprint: str | None = None
    event_fingerprint: str | None = None
    apply_metadata: PlanningCalendarEventApplyMetadata | None = None

    @field_validator("id", "name", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("category_code", mode="before")
    @classmethod
    def _normalize_category_code(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("country_code", mode="before")
    @classmethod
    def _normalize_country_code(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip().upper()
            return cleaned or None
        return value

    @field_validator(
        "city",
        "venue",
        "notes",
        "source_template_id",
        "source_template_fingerprint",
        "source_template_event_id",
        "source_template_event_fingerprint",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _clean_optional_text(value)
        return value

    @model_validator(mode="after")
    def validate_and_fingerprint(self) -> "PlanningCalendarEvent":
        _ensure_unique_weeks(self.weeks, field_name="weeks")
        _ensure_unique_weeks(self.qualification_weeks, field_name="qualification_weeks")
        self.weeks = sorted(self.weeks)
        self.qualification_weeks = sorted(self.qualification_weeks)
        self.event_fingerprint = _digest("pl_evt", self.fingerprint_payload())
        return self

    def fingerprint_payload(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"event_fingerprint"})
        apply_metadata = self.apply_metadata.fingerprint_payload() if self.apply_metadata is not None else None
        payload["apply_metadata"] = apply_metadata
        return payload


class PlanningSeasonCalendar(BaseModel):
    season_label: str = Field(min_length=1)
    normalized_season_label: str = Field(min_length=1)
    status: PlanningCalendarStatus = "draft"
    events: list[PlanningCalendarEvent] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    calendar_fingerprint: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @field_validator("season_label", mode="before")
    @classmethod
    def _strip_season_label(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("normalized_season_label", mode="before")
    @classmethod
    def _normalize_calendar_season_label(cls, value: Any) -> Any:
        if isinstance(value, str):
            return _normalized_long_season_label(value)
        return value

    @model_validator(mode="after")
    def validate_calendar(self) -> "PlanningSeasonCalendar":
        self.normalized_season_label = _normalized_long_season_label(self.normalized_season_label)
        self.season_label = self.season_label.strip()
        seen_event_ids: set[str] = set()
        for event in self.events:
            if event.id in seen_event_ids:
                raise ValueError(f"Duplicate planning event id in calendar: {event.id}")
            seen_event_ids.add(event.id)
            if self.status == "active" and not event.weeks:
                raise ValueError("Active planning calendar events must include at least one week.")
        self.events = [event for event in self.events]
        self.calendar_fingerprint = _digest("pl_cal", self.fingerprint_payload())
        return self

    def fingerprint_payload(self) -> dict[str, Any]:
        payload = self.model_dump(
            mode="json",
            exclude={"created_at", "updated_at", "calendar_fingerprint"},
        )
        payload["events"] = [
            event.fingerprint_payload()
            for event in sorted(
                self.events,
                key=lambda event: (
                    event.weeks[0] if event.weeks else 999,
                    event.category_code,
                    event.name.casefold(),
                    event.id,
                ),
            )
        ]
        return payload


class PlanningSeasonCalendarRegistry(BaseModel):
    schema_version: Literal["planning_season_calendars.v1"] = PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
    calendars_by_season: dict[str, PlanningSeasonCalendar] = Field(default_factory=dict)
    registry_fingerprint: str | None = None

    @model_validator(mode="after")
    def validate_registry(self) -> "PlanningSeasonCalendarRegistry":
        normalized_calendars: dict[str, PlanningSeasonCalendar] = {}
        for season_key, calendar in self.calendars_by_season.items():
            normalized_key = _normalized_long_season_label(season_key)
            if calendar.normalized_season_label != normalized_key:
                raise ValueError("Planning calendar registry keys must match normalized season labels.")
            if normalized_key in normalized_calendars:
                raise ValueError(f"Duplicate normalized planning season label: {normalized_key}")
            normalized_calendars[normalized_key] = calendar
        self.calendars_by_season = normalized_calendars
        self.registry_fingerprint = _digest("pl_reg", self.fingerprint_payload())
        return self

    def fingerprint_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "calendars_by_season": {
                season: calendar.fingerprint_payload()
                for season, calendar in sorted(self.calendars_by_season.items())
            },
        }


@dataclass(slots=True)
class PlanningSeasonCalendarService:
    """Read and write separate Admin planning season calendars."""

    registry_path: Path = Path("config/simulation/planning_season_calendars.json")

    def __post_init__(self) -> None:
        if not isinstance(self.registry_path, Path):
            self.registry_path = Path(self.registry_path)

    def load_registry(self) -> PlanningSeasonCalendarRegistry:
        if not self.registry_path.exists():
            return PlanningSeasonCalendarRegistry()
        return PlanningSeasonCalendarRegistry.model_validate(json.loads(self.registry_path.read_text(encoding="utf-8")))

    def list_calendars(self) -> list[PlanningSeasonCalendar]:
        registry = self.load_registry()
        return [registry.calendars_by_season[key] for key in sorted(registry.calendars_by_season)]

    def get_calendar(self, season_label: str) -> PlanningSeasonCalendar | None:
        registry = self.load_registry()
        normalized = _normalized_long_season_label(season_label)
        return registry.calendars_by_season.get(normalized)

    def save_calendar(self, calendar: PlanningSeasonCalendar) -> PlanningSeasonCalendar:
        registry = self.load_registry()
        normalized = _normalized_long_season_label(calendar.normalized_season_label)
        existing = registry.calendars_by_season.get(normalized)
        now = _utc_now_iso()
        persisted = PlanningSeasonCalendar.model_validate(
            calendar.model_dump(mode="json")
            | {
                "normalized_season_label": normalized,
                "created_at": calendar.created_at or (existing.created_at if existing is not None else now),
                "updated_at": now,
            }
        )
        next_calendars = dict(registry.calendars_by_season)
        next_calendars[normalized] = persisted
        self._save_registry(PlanningSeasonCalendarRegistry(calendars_by_season=next_calendars))
        return persisted

    def update_calendar(self, calendar: PlanningSeasonCalendar) -> PlanningSeasonCalendar:
        return self.save_calendar(calendar)

    def _save_registry(self, registry: PlanningSeasonCalendarRegistry) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.registry_path.with_suffix(f"{self.registry_path.suffix}.tmp")
        tmp_path.write_text(json.dumps(registry.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
        tmp_path.replace(self.registry_path)


def _ensure_unique_weeks(weeks: list[int], *, field_name: str) -> None:
    if len(weeks) != len(set(weeks)):
        raise ValueError(f"{field_name} must contain unique season weeks.")
