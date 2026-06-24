from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.application.calendar_template_compare_service import CalendarTemplateCompareDryRunRequest, CalendarTemplateCompareService
from beta_engine.application.calendar_template_service import CalendarTemplate, CalendarTemplateService
from beta_engine.application.planning_calendar_apply_template_service import (
    REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
    PlanningCalendarApplyTemplatePlanRequest,
    PlanningCalendarApplyTemplatePlanService,
    stable_planning_event_id,
)
from beta_engine.application.planning_season_calendar_service import (
    PlanningSeasonCalendar,
    PlanningSeasonCalendarRegistry,
    PlanningSeasonCalendarService,
)


def template_event(event_id: str = "event-a", **overrides) -> dict:
    payload = {
        "id": event_id,
        "name": "Event A" if event_id == "event-a" else "Event B",
        "category_code": "DIAMOND",
        "weeks": [6],
        "qualification_weeks": [5],
        "locked": False,
        "country_code": "EGY",
        "city": "Cairo",
    }
    payload.update(overrides)
    return payload


def planning_event(event_id: str = "planning-a", **overrides) -> dict:
    payload = {
        "id": event_id,
        "name": "Event A",
        "category_code": "DIAMOND",
        "weeks": [6],
        "qualification_weeks": [5],
        "locked": False,
        "country_code": "EGY",
        "city": "Cairo",
        "source_template_id": "template-a",
        "source_template_event_id": "event-a",
        "source_template_fingerprint": "tpl_placeholder",
        "source_template_event_fingerprint": "evt_placeholder",
    }
    payload.update(overrides)
    return payload


def build_services(
    tmp_path: Path,
    *,
    template_events: list[dict] | None = None,
    planning_events: list[dict] | None = None,
) -> tuple[PlanningCalendarApplyTemplatePlanService, CalendarTemplateService, PlanningSeasonCalendarService, Path, Path, Path]:
    template_path = tmp_path / "calendar_templates.json"
    planning_path = tmp_path / "planning_season_calendars.json"
    season_calendar_path = tmp_path / "season_calendars.json"
    template_service = CalendarTemplateService(registry_path=template_path)
    template = template_service.create_template(
        template=CalendarTemplate.model_validate(
            {
                "id": "template-a",
                "name": "Template A",
                "status": "draft",
                "events": template_events if template_events is not None else [template_event()],
            }
        )
    )
    normalized_planning_events = []
    for payload in planning_events or []:
        if payload.get("source_template_id") == "template-a":
            payload = dict(payload)
            payload.setdefault("source_template_fingerprint", template.template_fingerprint)
            source_id = payload.get("source_template_event_id")
            if source_id:
                source = next((event for event in template.events if event.id == source_id), None)
                if source is not None:
                    payload.setdefault("source_template_event_fingerprint", source.event_fingerprint)
        normalized_planning_events.append(payload)
    calendar = PlanningSeasonCalendar.model_validate(
        {
            "season_label": "2000/01",
            "normalized_season_label": "2000/01",
            "status": "draft",
            "events": normalized_planning_events,
            "metadata": {"source": "test"},
        }
    )
    planning_path.write_text(
        json.dumps(PlanningSeasonCalendarRegistry(calendars_by_season={calendar.normalized_season_label: calendar}).model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    planning_service = PlanningSeasonCalendarService(registry_path=planning_path)
    return (
        PlanningCalendarApplyTemplatePlanService(template_service=template_service, planning_calendar_service=planning_service),
        template_service,
        planning_service,
        template_path,
        planning_path,
        season_calendar_path,
    )


def valid_request(template_service: CalendarTemplateService, planning_service: PlanningSeasonCalendarService, **overrides) -> PlanningCalendarApplyTemplatePlanRequest:
    template = template_service.get_template(template_id="template-a").template
    assert template is not None
    calendar = planning_service.get_calendar("2000/01")
    assert calendar is not None
    diff = CalendarTemplateCompareService(template_service=template_service, planning_calendar_service=planning_service).compare_dry_run(
        CalendarTemplateCompareDryRunRequest(
            target_season_label="2000/01",
            source_template_id="template-a",
            target_source="planning_calendar",
            selected_source_event_ids=overrides.get("selected_source_event_ids"),
            policy=overrides.get("policy", "copy_missing_only"),
        )
    )
    payload = {
        "target_season_label": "2000/01",
        "source_template_id": "template-a",
        "policy": "copy_missing_only",
        "selected_source_event_ids": None,
        "expected_planning_calendar_fingerprint": calendar.calendar_fingerprint,
        "source_template_fingerprint": template.template_fingerprint,
        "reviewed_diff_fingerprint": diff.diff_fingerprint,
        "requested_by": "qa",
        "audit_reason": "reviewed planning calendar diff",
        "explicit_confirmation": REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
    }
    payload.update(overrides)
    return PlanningCalendarApplyTemplatePlanRequest.model_validate(payload)


def test_copy_missing_only_plan_creates_missing_events_but_does_not_persist(tmp_path: Path) -> None:
    service, template_service, planning_service, _, planning_path, _ = build_services(tmp_path, planning_events=[])
    before = planning_path.read_text(encoding="utf-8")

    response = service.build_plan(valid_request(template_service, planning_service))

    assert response.status == "ok"
    assert response.mutation_performed is False
    assert response.counts.planned_create_count == 1
    assert response.planned_items[0].action == "create"
    assert planning_path.read_text(encoding="utf-8") == before


def test_copy_missing_only_does_not_plan_updates_for_existing_events(tmp_path: Path) -> None:
    generated_id = stable_planning_event_id(source_template_id="template-a", source_template_event_id="event-a")
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[planning_event(generated_id, weeks=[9])])

    response = service.build_plan(valid_request(template_service, planning_service))

    assert response.counts.planned_update_count == 0
    assert response.counts.skipped_event_count == 1
    assert response.skipped_items[0].action == "skip"


def test_replace_unlocked_only_plans_updates_for_unlocked_strong_identity_matches(tmp_path: Path) -> None:
    generated_id = stable_planning_event_id(source_template_id="template-a", source_template_event_id="event-a")
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[planning_event(generated_id, weeks=[9])])

    response = service.build_plan(valid_request(template_service, planning_service, policy="replace_unlocked_only"))

    assert response.status == "ok"
    assert response.counts.planned_update_count == 1
    assert response.planned_items[0].action == "update"


def test_replace_unlocked_only_preserves_locked_strong_identity_matches(tmp_path: Path) -> None:
    generated_id = stable_planning_event_id(source_template_id="template-a", source_template_event_id="event-a")
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[planning_event(generated_id, weeks=[9], locked=True)])

    response = service.build_plan(valid_request(template_service, planning_service, policy="replace_unlocked_only"))

    assert response.status == "ok"
    assert response.counts.planned_update_count == 0
    assert response.counts.preserved_locked_event_count == 1
    assert response.skipped_items[0].action == "preserve_locked"


def test_target_only_events_are_preserved(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(
        tmp_path,
        planning_events=[planning_event("target-only", name="Target Only", source_template_id=None, source_template_event_id=None)],
    )

    response = service.build_plan(valid_request(template_service, planning_service))

    assert response.counts.target_only_event_count == 1
    assert all(item.action != "reject" for item in response.planned_items + response.skipped_items)


def test_selected_source_event_ids_restrict_source_events(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(
        tmp_path,
        template_events=[template_event("event-a"), template_event("event-b", name="Event B")],
        planning_events=[],
    )

    response = service.build_plan(valid_request(template_service, planning_service, selected_source_event_ids=["event-b"]))

    assert response.counts.selected_source_event_count == 1
    assert [item.source_event_id for item in response.planned_items] == ["event-b"]


def test_unknown_selected_source_event_id_rejected(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[])
    request = valid_request(template_service, planning_service)
    request = request.model_copy(update={"selected_source_event_ids": ["missing"]})

    response = service.build_plan(request)

    assert response.status == "rejected"
    assert any("Unknown selected_source_event_id" in error for error in response.validation_errors)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("source_template_fingerprint", "tpl_stale", "source_template_fingerprint"),
        ("expected_planning_calendar_fingerprint", "pl_cal_stale", "expected_planning_calendar_fingerprint"),
        ("reviewed_diff_fingerprint", "diff_stale", "reviewed_diff_fingerprint"),
        ("explicit_confirmation", None, "explicit_confirmation is required"),
        ("explicit_confirmation", "wrong", "explicit_confirmation does not match"),
        ("requested_by", " ", "requested_by is required"),
        ("audit_reason", " ", "audit_reason is required"),
    ],
)
def test_fail_closed_validation_errors(tmp_path: Path, field: str, value: str | None, expected: str) -> None:
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[])
    request = valid_request(template_service, planning_service).model_copy(update={field: value})

    response = service.build_plan(request)

    assert response.status == "rejected"
    assert any(expected in error for error in response.validation_errors)
    assert response.mutation_performed is False


def test_ambiguous_identity_rejected(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(
        tmp_path,
        planning_events=[
            planning_event("weak-a", source_template_id=None, source_template_event_id=None),
            planning_event("weak-b", source_template_id=None, source_template_event_id=None),
        ],
    )

    response = service.build_plan(valid_request(template_service, planning_service))

    assert response.status == "rejected"
    assert any("Ambiguous target identity" in error for error in response.validation_errors)


def test_apply_plan_fingerprint_is_deterministic(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[])
    request = valid_request(template_service, planning_service)

    first = service.build_plan(request)
    second = service.build_plan(request)

    assert first.apply_plan_fingerprint == second.apply_plan_fingerprint


def test_plan_builder_does_not_modify_planning_or_season_calendar_files(tmp_path: Path) -> None:
    service, template_service, planning_service, _, planning_path, season_calendar_path = build_services(tmp_path, planning_events=[])
    season_calendar_path.write_text('{"sentinel": true}\n', encoding="utf-8")
    planning_before = planning_path.read_text(encoding="utf-8")
    season_before = season_calendar_path.read_text(encoding="utf-8")

    service.build_plan(valid_request(template_service, planning_service))

    assert planning_path.read_text(encoding="utf-8") == planning_before
    assert season_calendar_path.read_text(encoding="utf-8") == season_before


def test_no_simulation_adapter_invoked_or_added(tmp_path: Path) -> None:
    service, template_service, planning_service, *_ = build_services(tmp_path, planning_events=[])

    response = service.build_plan(valid_request(template_service, planning_service))

    assert response.safety_summary["simulation_invoked"] is False
    assert response.safety_summary["planning_to_simulation_adapter"] is False
    assert not hasattr(service, "to_season_calendar")
    assert not hasattr(planning_service, "to_season_calendar")
    assert not hasattr(planning_service, "to_season_calendar_event")
