"""Read-only calendar template compare dry-run service."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from beta_engine.application.calendar_template_service import CalendarTemplateEvent, CalendarTemplateService
from beta_engine.application.planning_season_calendar_service import PlanningCalendarEvent, PlanningSeasonCalendarService

CalendarTemplateComparePolicy = Literal["replace_unlocked_only", "copy_missing_only"]
CalendarTemplateCompareTargetSource = Literal["payload", "planning_calendar"]
CalendarTemplateCompareStatus = Literal[
    "same",
    "missing_from_target",
    "only_in_target",
    "conflict",
    "locked_target_preserved",
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _digest(prefix: str, payload: Any) -> str:
    return f"{prefix}_{hashlib.sha256(_canonical_json(payload).encode('utf-8')).hexdigest()[:24]}"


def _identity_key(event: CalendarTemplateEvent) -> str:
    normalized_name = re.sub(r"\s+", " ", event.name.strip().casefold())
    return f"{normalized_name}|{event.category_code.strip().casefold()}"


def _event_fingerprint_payload(event: CalendarTemplateEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "name": event.name,
        "category_code": event.category_code,
        "weeks": event.weeks,
        "qualification_weeks": event.qualification_weeks,
        "locked": event.locked,
        "country_code": event.country_code,
        "city": event.city,
        "venue": event.venue,
        "notes": event.notes,
        "source_template_id": event.source_template_id,
    }


class PlanningCalendarTargetNotFoundError(KeyError):
    pass


class CalendarTemplateCompareDryRunRequest(BaseModel):
    target_season_label: str = Field(min_length=1)
    source_template_id: str = Field(min_length=1)
    target_events: list[CalendarTemplateEvent] = Field(default_factory=list)
    target_source: CalendarTemplateCompareTargetSource = "payload"
    selected_source_event_ids: list[str] | None = None
    policy: CalendarTemplateComparePolicy = "replace_unlocked_only"

    @model_validator(mode="after")
    def validate_selected_ids_are_unique(self) -> "CalendarTemplateCompareDryRunRequest":
        if self.selected_source_event_ids is not None and len(self.selected_source_event_ids) != len(set(self.selected_source_event_ids)):
            raise ValueError("selected_source_event_ids must contain unique event ids.")
        if self.target_source == "planning_calendar" and self.target_events:
            raise ValueError("target_events must be omitted when target_source is planning_calendar.")
        return self


class CalendarTemplateCompareSummary(BaseModel):
    same_count: int = 0
    missing_from_target_count: int = 0
    only_in_target_count: int = 0
    conflict_count: int = 0
    locked_target_preserved_count: int = 0
    selected_source_event_count: int = 0
    source_event_count: int = 0
    target_event_count: int = 0


class CalendarTemplateCompareItem(BaseModel):
    status: CalendarTemplateCompareStatus
    source_event_id: str | None = None
    target_event_id: str | None = None
    event_name: str
    category_code: str
    source_weeks: list[int] | None = None
    target_weeks: list[int] | None = None
    source_qualification_weeks: list[int] | None = None
    target_qualification_weeks: list[int] | None = None
    locked_target: bool = False
    reason: str


class CalendarTemplateCompareSafety(BaseModel):
    read_only: bool = True
    mutation_performed: bool = False
    apply_endpoint_enabled: bool = False
    message: str = "Compare dry-run only; no canonical season calendar was modified."


class CalendarTemplateCompareDryRunResponse(BaseModel):
    dry_run: bool = True
    mutation_performed: bool = False
    target_season_label: str
    source_template_id: str
    policy: CalendarTemplateComparePolicy
    target_source: CalendarTemplateCompareTargetSource = "payload"
    source_template_fingerprint: str | None = None
    target_fingerprint: str
    target_calendar_fingerprint: str | None = None
    target_calendar_exists: bool = False
    diff_fingerprint: str
    summary: CalendarTemplateCompareSummary
    items: list[CalendarTemplateCompareItem] = Field(default_factory=list)
    safety: CalendarTemplateCompareSafety = Field(default_factory=CalendarTemplateCompareSafety)
    status: str = "ok"


@dataclass(slots=True)
class CalendarTemplateCompareService:
    template_service: CalendarTemplateService
    planning_calendar_service: PlanningSeasonCalendarService | None = None

    def compare_dry_run(self, request: CalendarTemplateCompareDryRunRequest) -> CalendarTemplateCompareDryRunResponse:
        source_template = self.template_service.get_template(template_id=request.source_template_id).template
        if source_template is None:
            raise KeyError(request.source_template_id)

        source_events = list(source_template.events)
        if request.selected_source_event_ids is not None:
            by_id = {event.id: event for event in source_events}
            missing_ids = [event_id for event_id in request.selected_source_event_ids if event_id not in by_id]
            if missing_ids:
                raise ValueError(f"Unknown selected_source_event_id: {missing_ids[0]}")
            selected_set = set(request.selected_source_event_ids)
            source_events = [event for event in source_events if event.id in selected_set]

        target_events, target_fingerprint, target_calendar_fingerprint, target_calendar_exists = self._resolve_target(request)

        source_by_key = {_identity_key(event): event for event in source_events}
        target_by_key = {_identity_key(event): event for event in target_events}
        all_keys = sorted(set(source_by_key) | set(target_by_key))
        items = [self._compare_key(key, source_by_key.get(key), target_by_key.get(key), request.policy) for key in all_keys]
        summary = self._build_summary(
            items=items,
            selected_source_event_count=len(source_events),
            source_event_count=len(source_template.events),
            target_event_count=len(target_events),
        )
        diff_payload = {
            "target_season_label": request.target_season_label,
            "source_template_id": request.source_template_id,
            "policy": request.policy,
            "target_source": request.target_source,
            "source_template_fingerprint": source_template.template_fingerprint,
            "target_fingerprint": target_fingerprint,
            "summary": summary.model_dump(mode="json"),
            "items": [item.model_dump(mode="json") for item in items],
        }
        return CalendarTemplateCompareDryRunResponse(
            target_season_label=request.target_season_label,
            source_template_id=request.source_template_id,
            policy=request.policy,
            target_source=request.target_source,
            source_template_fingerprint=source_template.template_fingerprint,
            target_fingerprint=target_fingerprint,
            target_calendar_fingerprint=target_calendar_fingerprint,
            target_calendar_exists=target_calendar_exists,
            diff_fingerprint=_digest("diff", diff_payload),
            summary=summary,
            items=items,
        )


    def _resolve_target(
        self,
        request: CalendarTemplateCompareDryRunRequest,
    ) -> tuple[list[CalendarTemplateEvent], str, str | None, bool]:
        if request.target_source == "payload":
            target_events = list(request.target_events)
            target_fingerprint = _digest(
                "target",
                [_event_fingerprint_payload(event) for event in sorted(target_events, key=lambda event: (_identity_key(event), event.id))],
            )
            return target_events, target_fingerprint, None, bool(target_events)

        if self.planning_calendar_service is None:
            raise PlanningCalendarTargetNotFoundError(request.target_season_label)

        calendar = self.planning_calendar_service.get_calendar(request.target_season_label)
        if calendar is None:
            raise PlanningCalendarTargetNotFoundError(request.target_season_label)

        target_events = [self._planning_event_to_template_event(event) for event in calendar.events]
        target_fingerprint = calendar.calendar_fingerprint or _digest(
            "target",
            [_event_fingerprint_payload(event) for event in sorted(target_events, key=lambda event: (_identity_key(event), event.id))],
        )
        return target_events, target_fingerprint, calendar.calendar_fingerprint, True

    def _planning_event_to_template_event(self, event: PlanningCalendarEvent) -> CalendarTemplateEvent:
        return CalendarTemplateEvent.model_validate(
            {
                "id": event.id,
                "name": event.name,
                "category_code": event.category_code,
                "weeks": event.weeks,
                "qualification_weeks": event.qualification_weeks,
                "locked": event.locked,
                "country_code": event.country_code,
                "city": event.city,
                "venue": event.venue,
                "notes": event.notes,
                "source_template_id": event.source_template_id,
                "event_fingerprint": event.event_fingerprint,
            }
        )

    def _compare_key(
        self,
        key: str,
        source: CalendarTemplateEvent | None,
        target: CalendarTemplateEvent | None,
        policy: CalendarTemplateComparePolicy,
    ) -> CalendarTemplateCompareItem:
        if source is None and target is not None:
            return CalendarTemplateCompareItem(status="only_in_target", target_event_id=target.id, event_name=target.name, category_code=target.category_code, target_weeks=target.weeks, target_qualification_weeks=target.qualification_weeks, locked_target=target.locked, reason="Target event has no matching source template event.")
        if source is not None and target is None:
            return CalendarTemplateCompareItem(status="missing_from_target", source_event_id=source.id, event_name=source.name, category_code=source.category_code, source_weeks=source.weeks, source_qualification_weeks=source.qualification_weeks, reason="Source template event has no matching target event.")
        if source is None or target is None:
            raise AssertionError(f"Unexpected empty compare pair for {key}")
        if source.weeks == target.weeks and source.qualification_weeks == target.qualification_weeks:
            return CalendarTemplateCompareItem(status="same", source_event_id=source.id, target_event_id=target.id, event_name=source.name, category_code=source.category_code, source_weeks=source.weeks, target_weeks=target.weeks, source_qualification_weeks=source.qualification_weeks, target_qualification_weeks=target.qualification_weeks, locked_target=target.locked, reason="Source and target event weeks match.")
        if policy == "replace_unlocked_only" and target.locked:
            return CalendarTemplateCompareItem(status="locked_target_preserved", source_event_id=source.id, target_event_id=target.id, event_name=source.name, category_code=source.category_code, source_weeks=source.weeks, target_weeks=target.weeks, source_qualification_weeks=source.qualification_weeks, target_qualification_weeks=target.qualification_weeks, locked_target=True, reason="Target event is locked and would be preserved by replace_unlocked_only policy.")
        return CalendarTemplateCompareItem(status="conflict", source_event_id=source.id, target_event_id=target.id, event_name=source.name, category_code=source.category_code, source_weeks=source.weeks, target_weeks=target.weeks, source_qualification_weeks=source.qualification_weeks, target_qualification_weeks=target.qualification_weeks, locked_target=target.locked, reason="Source and target event weeks or qualification weeks differ.")

    def _build_summary(self, *, items: list[CalendarTemplateCompareItem], selected_source_event_count: int, source_event_count: int, target_event_count: int) -> CalendarTemplateCompareSummary:
        counts = {status: sum(1 for item in items if item.status == status) for status in ("same", "missing_from_target", "only_in_target", "conflict", "locked_target_preserved")}
        return CalendarTemplateCompareSummary(
            same_count=counts["same"],
            missing_from_target_count=counts["missing_from_target"],
            only_in_target_count=counts["only_in_target"],
            conflict_count=counts["conflict"],
            locked_target_preserved_count=counts["locked_target_preserved"],
            selected_source_event_count=selected_source_event_count,
            source_event_count=source_event_count,
            target_event_count=target_event_count,
        )
