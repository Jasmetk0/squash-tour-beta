from __future__ import annotations

import json
from pathlib import Path

import pytest

from beta_engine.application.calendar_template_compare_service import CalendarTemplateCompareDryRunRequest, CalendarTemplateCompareService
from beta_engine.application.calendar_template_service import CalendarTemplate, CalendarTemplateEvent, CalendarTemplateService


def event(**overrides) -> dict:
    payload = {"id": "event-a", "name": "Event A", "category_code": "DIAMOND", "weeks": [6], "qualification_weeks": [5], "locked": False}
    payload.update(overrides)
    return payload


def template(**overrides) -> dict:
    payload = {"id": "template-a", "name": "Template A", "description": "", "status": "draft", "events": [event()]}
    payload.update(overrides)
    return payload


def service_with_template(tmp_path: Path, payload: dict | None = None) -> tuple[CalendarTemplateCompareService, Path]:
    path = tmp_path / "calendar_templates.json"
    template_service = CalendarTemplateService(registry_path=path)
    template_service.create_template(template=CalendarTemplate.model_validate(payload or template()))
    return CalendarTemplateCompareService(template_service=template_service), path


def request(**overrides) -> CalendarTemplateCompareDryRunRequest:
    payload = {"target_season_label": "2000/01", "source_template_id": "template-a", "target_events": []}
    payload.update(overrides)
    return CalendarTemplateCompareDryRunRequest.model_validate(payload)


def test_empty_target_reports_source_events_missing_from_target(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request())

    assert response.summary.missing_from_target_count == 1
    assert response.items[0].status == "missing_from_target"
    assert response.dry_run is True
    assert response.mutation_performed is False


def test_empty_source_template_returns_empty_source_counts(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path, template(events=[]))

    response = service.compare_dry_run(request())

    assert response.summary.source_event_count == 0
    assert response.summary.selected_source_event_count == 0
    assert response.items == []


def test_same_event_reports_same(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request(target_events=[event(id="target-a")]))

    assert response.summary.same_count == 1
    assert response.items[0].status == "same"


def test_same_identity_different_weeks_reports_conflict(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request(target_events=[event(id="target-a", weeks=[7])]))

    assert response.summary.conflict_count == 1
    assert response.items[0].status == "conflict"


def test_same_identity_different_qualification_weeks_reports_conflict(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request(target_events=[event(id="target-a", qualification_weeks=[4])]))

    assert response.summary.conflict_count == 1
    assert response.items[0].status == "conflict"


def test_target_only_event_reports_only_in_target(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request(target_events=[event(id="target-b", name="Event B")]))

    assert response.summary.only_in_target_count == 1
    assert any(item.status == "only_in_target" for item in response.items)


def test_locked_target_conflict_is_preserved_under_replace_unlocked_only(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    response = service.compare_dry_run(request(target_events=[event(id="target-a", weeks=[7], locked=True)]))

    assert response.summary.locked_target_preserved_count == 1
    assert response.summary.conflict_count == 0
    assert response.items[0].status == "locked_target_preserved"
    assert response.items[0].locked_target is True


def test_selected_source_event_ids_restrict_source_events(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path, template(events=[event(id="event-a"), event(id="event-b", name="Event B")]))

    response = service.compare_dry_run(request(selected_source_event_ids=["event-b"]))

    assert response.summary.source_event_count == 2
    assert response.summary.selected_source_event_count == 1
    assert [item.source_event_id for item in response.items] == ["event-b"]


def test_unknown_selected_source_event_id_rejected(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)

    with pytest.raises(ValueError, match="Unknown selected_source_event_id"):
        service.compare_dry_run(request(selected_source_event_ids=["missing"]))


def test_dry_run_does_not_write_or_modify_calendar_templates_json(tmp_path: Path) -> None:
    service, path = service_with_template(tmp_path)
    before = path.read_text(encoding="utf-8")

    service.compare_dry_run(request(target_events=[event(id="target-a", weeks=[7])]))

    assert path.read_text(encoding="utf-8") == before
    json.loads(before)


def test_repeated_same_request_returns_same_diff_fingerprint(tmp_path: Path) -> None:
    service, _ = service_with_template(tmp_path)
    payload = request(target_events=[event(id="target-a", weeks=[7])])

    first = service.compare_dry_run(payload)
    second = service.compare_dry_run(payload)

    assert first.diff_fingerprint == second.diff_fingerprint
    assert first.target_fingerprint == second.target_fingerprint
