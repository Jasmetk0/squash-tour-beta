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

from beta_engine.application.planning_calendar_apply_audit_service import PlanningCalendarApplyAuditService
from beta_engine.application.planning_calendar_apply_template_service import (
    PlanningCalendarApplyBackupService,
    PlanningCalendarApplyTemplateCommandRequest,
    PlanningCalendarApplyTemplateCommandService,
)


def valid_command_request(template_service: CalendarTemplateService, planning_service: PlanningSeasonCalendarService, **overrides) -> PlanningCalendarApplyTemplateCommandRequest:
    plan_request = valid_request(template_service, planning_service, **{k: v for k, v in overrides.items() if k in {"policy", "selected_source_event_ids"}})
    payload = {
        "source_template_id": plan_request.source_template_id,
        "policy": plan_request.policy,
        "selected_source_event_ids": plan_request.selected_source_event_ids,
        "expected_planning_calendar_fingerprint": plan_request.expected_planning_calendar_fingerprint,
        "source_template_fingerprint": plan_request.source_template_fingerprint,
        "reviewed_diff_fingerprint": plan_request.reviewed_diff_fingerprint,
        "requested_by": plan_request.requested_by,
        "audit_reason": plan_request.audit_reason,
        "explicit_confirmation": plan_request.explicit_confirmation,
    }
    payload.update(overrides)
    return PlanningCalendarApplyTemplateCommandRequest.model_validate(payload)


def command_service(tmp_path: Path, *, template_events: list[dict] | None = None, planning_events: list[dict] | None = None):
    service, template_service, planning_service, template_path, planning_path, season_calendar_path = build_services(
        tmp_path,
        template_events=template_events,
        planning_events=planning_events,
    )
    audit_path = tmp_path / "planning_calendar_apply_audit.jsonl"
    backup_dir = tmp_path / "planning_calendar_apply_backups"
    command = PlanningCalendarApplyTemplateCommandService(
        template_service=template_service,
        planning_calendar_service=planning_service,
        audit_service=PlanningCalendarApplyAuditService(audit_log_path=audit_path),
        backup_service=PlanningCalendarApplyBackupService(backup_dir=backup_dir),
    )
    return command, template_service, planning_service, planning_path, season_calendar_path, audit_path, backup_dir


def read_audit(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_successful_copy_missing_only_creates_missing_events_in_planning_calendar(tmp_path: Path) -> None:
    command, template_service, planning_service, planning_path, season_calendar_path, audit_path, backup_dir = command_service(tmp_path, planning_events=[])
    before = planning_path.read_text(encoding="utf-8")

    response = command.apply_template(target_season_label="2000/01", request=valid_command_request(template_service, planning_service))

    assert response.mutation_performed is True
    assert response.created_event_count == 1
    assert planning_path.read_text(encoding="utf-8") != before
    saved = planning_service.get_calendar("2000/01")
    assert saved is not None
    assert len(saved.events) == 1
    created = saved.events[0]
    assert created.id == stable_planning_event_id(source_template_id="template-a", source_template_event_id="event-a")
    assert created.source_template_id == "template-a"
    assert created.source_template_event_id == "event-a"
    assert created.apply_metadata is not None
    assert created.apply_metadata.last_apply_policy == "copy_missing_only"
    assert read_audit(audit_path)[0]["audit_stage"] == "pre_mutation_reserved"
    assert read_audit(audit_path)[1]["audit_stage"] == "succeeded"
    assert list(backup_dir.rglob("*.before.json"))
    assert not season_calendar_path.exists()


def test_copy_missing_only_apply_does_not_update_existing_locked_or_target_only_events(tmp_path: Path) -> None:
    generated_id = stable_planning_event_id(source_template_id="template-a", source_template_event_id="event-a")
    command, template_service, planning_service, _, _, _, _ = command_service(
        tmp_path,
        planning_events=[
            planning_event(generated_id, weeks=[9], locked=True),
            planning_event("target-only", name="Target Only", source_template_id=None, source_template_event_id=None),
        ],
    )
    before_calendar = planning_service.get_calendar("2000/01")
    assert before_calendar is not None
    before_by_id = {event.id: event.event_fingerprint for event in before_calendar.events}

    response = command.apply_template(target_season_label="2000/01", request=valid_command_request(template_service, planning_service))

    assert response.mutation_performed is False or response.created_event_count == 0
    after_calendar = planning_service.get_calendar("2000/01")
    assert after_calendar is not None
    assert {event.id: event.event_fingerprint for event in after_calendar.events} == before_by_id


def test_selected_source_event_ids_restrict_real_created_events(tmp_path: Path) -> None:
    command, template_service, planning_service, *_ = command_service(
        tmp_path,
        template_events=[template_event("event-a"), template_event("event-b", name="Event B")],
        planning_events=[],
    )

    response = command.apply_template(target_season_label="2000/01", request=valid_command_request(template_service, planning_service, selected_source_event_ids=["event-b"]))

    assert response.created_event_count == 1
    saved = planning_service.get_calendar("2000/01")
    assert saved is not None
    assert [event.source_template_event_id for event in saved.events] == ["event-b"]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("selected_source_event_ids", ["missing"], "Unknown selected_source_event_id"),
        ("source_template_fingerprint", "tpl_stale", "source_template_fingerprint"),
        ("expected_planning_calendar_fingerprint", "pl_cal_stale", "expected_planning_calendar_fingerprint"),
        ("reviewed_diff_fingerprint", "diff_stale", "reviewed_diff_fingerprint"),
        ("explicit_confirmation", None, "explicit_confirmation is required"),
        ("explicit_confirmation", "wrong", "explicit_confirmation does not match"),
        ("requested_by", " ", "requested_by is required"),
        ("audit_reason", " ", "audit_reason is required"),
        ("policy", "replace_unlocked_only", "not supported"),
        ("policy", "replace_all", "not supported"),
    ],
)
def test_real_apply_rejections_are_audited_with_no_mutation(tmp_path: Path, field: str, value, expected: str) -> None:
    command, template_service, planning_service, planning_path, season_calendar_path, audit_path, _ = command_service(tmp_path, planning_events=[])
    before = planning_path.read_text(encoding="utf-8")
    request = valid_command_request(template_service, planning_service).model_copy(update={field: value})

    response = command.apply_template(target_season_label="2000/01", request=request)

    assert response.mutation_performed is False
    assert any(expected in error for error in response.validation_errors)
    assert planning_path.read_text(encoding="utf-8") == before
    assert not season_calendar_path.exists()
    records = read_audit(audit_path)
    assert records
    assert records[-1]["audit_stage"] == "rejected"


class FailingAuditService:
    def append_record(self, record):
        raise OSError("audit unavailable")


class FailingBackupService(PlanningCalendarApplyBackupService):
    def write_before_backup(self, **kwargs):
        raise OSError("backup unavailable")


def test_audit_prewrite_failure_fails_closed_with_no_mutation(tmp_path: Path) -> None:
    _, template_service, planning_service, _, planning_path, _ = build_services(tmp_path, planning_events=[])
    command = PlanningCalendarApplyTemplateCommandService(
        template_service=template_service,
        planning_calendar_service=planning_service,
        audit_service=FailingAuditService(),
        backup_service=PlanningCalendarApplyBackupService(backup_dir=tmp_path / "backups"),
    )
    before = planning_path.read_text(encoding="utf-8")

    response = command.apply_template(target_season_label="2000/01", request=valid_command_request(template_service, planning_service))

    assert response.mutation_performed is False
    assert "audit pre-write failed" in response.validation_errors[0]
    assert planning_path.read_text(encoding="utf-8") == before


def test_backup_failure_fails_closed_with_no_mutation(tmp_path: Path) -> None:
    _, template_service, planning_service, _, planning_path, _ = build_services(tmp_path, planning_events=[])
    command = PlanningCalendarApplyTemplateCommandService(
        template_service=template_service,
        planning_calendar_service=planning_service,
        audit_service=PlanningCalendarApplyAuditService(audit_log_path=tmp_path / "audit.jsonl"),
        backup_service=FailingBackupService(backup_dir=tmp_path / "backups"),
    )
    before = planning_path.read_text(encoding="utf-8")

    response = command.apply_template(target_season_label="2000/01", request=valid_command_request(template_service, planning_service))

    assert response.mutation_performed is False
    assert "before-state backup failed" in response.validation_errors[0]
    assert planning_path.read_text(encoding="utf-8") == before
