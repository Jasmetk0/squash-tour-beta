from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from beta_engine.application.calendar_template_service import (
    CALENDAR_TEMPLATE_SCHEMA_VERSION,
    CalendarTemplate,
    CalendarTemplateEvent,
    CalendarTemplateService,
)


def event_payload(**overrides):
    payload = {
        "id": "event-a",
        "name": "Event A",
        "category_code": "DIAMOND",
        "weeks": [6, 7],
        "qualification_weeks": [5],
        "locked": True,
    }
    payload.update(overrides)
    return payload


def template_payload(**overrides):
    payload = {
        "id": "template-a",
        "name": "Template A",
        "description": "A persisted calendar template.",
        "status": "draft",
        "events": [event_payload()],
    }
    payload.update(overrides)
    return payload


def test_missing_registry_file_returns_empty_list(tmp_path: Path) -> None:
    service = CalendarTemplateService(registry_path=tmp_path / "calendar_templates.json")

    response = service.list_templates()

    assert response.templates == []
    assert response.schema_version == CALENDAR_TEMPLATE_SCHEMA_VERSION


def test_create_persists_calendar_templates_json_and_list_get(tmp_path: Path) -> None:
    path = tmp_path / "calendar_templates.json"
    service = CalendarTemplateService(registry_path=path)

    created = service.create_template(template=CalendarTemplate.model_validate(template_payload()))

    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == CALENDAR_TEMPLATE_SCHEMA_VERSION
    assert "template-a" in raw["templates_by_id"]
    assert service.list_templates().templates == [created]
    assert service.get_template(template_id="template-a").template == created


def test_update_changes_persisted_content(tmp_path: Path) -> None:
    service = CalendarTemplateService(registry_path=tmp_path / "calendar_templates.json")
    service.create_template(template=CalendarTemplate.model_validate(template_payload()))

    updated = service.update_template(
        template_id="template-a",
        template=CalendarTemplate.model_validate(template_payload(name="Template A Updated", description="Updated")),
    )

    assert updated.name == "Template A Updated"
    assert service.get_template(template_id="template-a").template.description == "Updated"


def test_duplicate_template_id_is_rejected(tmp_path: Path) -> None:
    service = CalendarTemplateService(registry_path=tmp_path / "calendar_templates.json")
    template = CalendarTemplate.model_validate(template_payload())
    service.create_template(template=template)

    with pytest.raises(ValueError, match="already exists"):
        service.create_template(template=template)


@pytest.mark.parametrize("weeks", [[0], [62]])
def test_invalid_weeks_are_rejected(weeks: list[int]) -> None:
    with pytest.raises(ValidationError):
        CalendarTemplate.model_validate(template_payload(events=[event_payload(weeks=weeks)]))


def test_non_integer_weeks_are_rejected() -> None:
    with pytest.raises(ValidationError):
        CalendarTemplate.model_validate(template_payload(events=[event_payload(weeks=["6"])]))


def test_duplicate_weeks_are_rejected() -> None:
    with pytest.raises(ValidationError, match="weeks must contain unique season weeks"):
        CalendarTemplate.model_validate(template_payload(events=[event_payload(weeks=[6, 6])]))


def test_duplicate_qualification_weeks_are_rejected() -> None:
    with pytest.raises(ValidationError, match="qualification_weeks must contain unique season weeks"):
        CalendarTemplate.model_validate(template_payload(events=[event_payload(qualification_weeks=[5, 5])]))


def test_duplicate_event_ids_inside_template_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Duplicate event id"):
        CalendarTemplate.model_validate(template_payload(events=[event_payload(id="event-a"), event_payload(id="event-a", name="Event B")]))


def test_empty_weeks_allowed_for_draft_templates() -> None:
    template = CalendarTemplate.model_validate(template_payload(status="draft", events=[event_payload(weeks=[])]))

    assert template.events[0].weeks == []


def test_empty_weeks_rejected_for_active_templates() -> None:
    with pytest.raises(ValidationError, match="Active calendar template events"):
        CalendarTemplate.model_validate(template_payload(status="active", events=[event_payload(weeks=[])]))


def test_same_stable_payload_produces_same_fingerprints_without_timestamps() -> None:
    first = CalendarTemplate.model_validate(template_payload(created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z"))
    second = CalendarTemplate.model_validate(template_payload(created_at="2026-06-24T00:00:00Z", updated_at="2026-06-24T00:00:00Z"))

    assert first.template_fingerprint == second.template_fingerprint
    assert first.events[0].event_fingerprint == second.events[0].event_fingerprint
    assert first.template_fingerprint
    assert first.events[0].event_fingerprint


def test_archive_template_marks_archived(tmp_path: Path) -> None:
    service = CalendarTemplateService(registry_path=tmp_path / "calendar_templates.json")
    service.create_template(template=CalendarTemplate.model_validate(template_payload()))

    archived = service.archive_template(template_id="template-a")

    assert archived.status == "archived"
