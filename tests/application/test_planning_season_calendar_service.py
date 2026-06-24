from __future__ import annotations

import json
from pathlib import Path
import time

import pytest
from pydantic import ValidationError

from beta_engine.application.planning_season_calendar_service import (
    PLANNING_SEASON_CALENDAR_SCHEMA_VERSION,
    PlanningCalendarEvent,
    PlanningSeasonCalendar,
    PlanningSeasonCalendarService,
)


def event_payload(**overrides):
    payload = {
        "id": "event-a",
        "name": " Event A ",
        "category_code": " diamond ",
        "weeks": [7, 6],
        "qualification_weeks": [5],
        "locked": True,
        "country_code": " egy ",
        "city": "Cairo",
        "venue": "Venue A",
        "notes": "Planning note",
        "source_template_id": "template-a",
        "source_template_fingerprint": "tpl_aaa",
        "source_template_event_id": "template-event-a",
        "source_template_event_fingerprint": "evt_aaa",
    }
    payload.update(overrides)
    return payload


def calendar_payload(**overrides):
    payload = {
        "season_label": "2000/01",
        "normalized_season_label": "2000/01",
        "status": "draft",
        "events": [event_payload()],
        "metadata": {"source": "test"},
    }
    payload.update(overrides)
    return payload


def test_missing_planning_registry_returns_empty_and_does_not_create_file(tmp_path: Path) -> None:
    path = tmp_path / "planning_season_calendars.json"
    service = PlanningSeasonCalendarService(registry_path=path)

    registry = service.load_registry()

    assert registry.schema_version == PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
    assert registry.calendars_by_season == {}
    assert service.list_calendars() == []
    assert not path.exists()


def test_create_and_read_planning_calendar(tmp_path: Path) -> None:
    path = tmp_path / "planning_season_calendars.json"
    service = PlanningSeasonCalendarService(registry_path=path)

    created = service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))

    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == PLANNING_SEASON_CALENDAR_SCHEMA_VERSION
    assert "2000/2001" in raw["calendars_by_season"]
    assert created.normalized_season_label == "2000/2001"
    assert created.events[0].category_code == "DIAMOND"
    assert created.events[0].country_code == "EGY"
    assert service.get_calendar("2000/2001") == created


def test_short_and_long_labels_resolve_same_calendar(tmp_path: Path) -> None:
    service = PlanningSeasonCalendarService(registry_path=tmp_path / "planning_season_calendars.json")
    created = service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))

    assert service.get_calendar("2000/01") == created
    assert service.get_calendar("2000/2001") == created


def test_update_preserves_created_at_and_updates_updated_at(tmp_path: Path) -> None:
    service = PlanningSeasonCalendarService(registry_path=tmp_path / "planning_season_calendars.json")
    created = service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))
    time.sleep(0.001)

    updated_payload = created.model_dump(mode="json")
    updated_payload["metadata"] = {"source": "updated"}
    updated = service.save_calendar(PlanningSeasonCalendar.model_validate(updated_payload))

    assert updated.created_at == created.created_at
    assert updated.updated_at != created.updated_at
    assert updated.metadata == {"source": "updated"}


def test_duplicate_event_ids_rejected() -> None:
    with pytest.raises(ValidationError, match="Duplicate planning event id"):
        PlanningSeasonCalendar.model_validate(
            calendar_payload(events=[event_payload(id="dup"), event_payload(id="dup", name="Other")])
        )


@pytest.mark.parametrize("field", ["weeks", "qualification_weeks"])
@pytest.mark.parametrize("value", [0, 62])
def test_invalid_weeks_rejected(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        PlanningCalendarEvent.model_validate(event_payload(**{field: [value]}))


def test_duplicate_weeks_rejected() -> None:
    with pytest.raises(ValidationError, match="weeks must contain unique season weeks"):
        PlanningCalendarEvent.model_validate(event_payload(weeks=[6, 6]))


def test_duplicate_qualification_weeks_rejected() -> None:
    with pytest.raises(ValidationError, match="qualification_weeks must contain unique season weeks"):
        PlanningCalendarEvent.model_validate(event_payload(qualification_weeks=[5, 5]))


def test_weeks_and_qualification_weeks_round_trip_sorted(tmp_path: Path) -> None:
    service = PlanningSeasonCalendarService(registry_path=tmp_path / "planning_season_calendars.json")
    created = service.save_calendar(
        PlanningSeasonCalendar.model_validate(
            calendar_payload(events=[event_payload(weeks=[9, 6, 7], qualification_weeks=[5, 4])])
        )
    )

    reloaded = service.get_calendar("2000/2001")

    assert reloaded == created
    assert reloaded is not None
    assert reloaded.events[0].weeks == [6, 7, 9]
    assert reloaded.events[0].qualification_weeks == [4, 5]


def test_locked_state_round_trips(tmp_path: Path) -> None:
    service = PlanningSeasonCalendarService(registry_path=tmp_path / "planning_season_calendars.json")
    created = service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload(events=[event_payload(locked=True)])))

    reloaded = service.get_calendar("2000/2001")

    assert reloaded == created
    assert reloaded is not None
    assert reloaded.events[0].locked is True


def test_event_fingerprint_changes_when_locked_changes() -> None:
    locked = PlanningCalendarEvent.model_validate(event_payload(locked=True))
    unlocked = PlanningCalendarEvent.model_validate(event_payload(locked=False))

    assert locked.event_fingerprint != unlocked.event_fingerprint


def test_event_fingerprint_changes_when_weeks_or_qualification_weeks_change() -> None:
    base = PlanningCalendarEvent.model_validate(event_payload(weeks=[6], qualification_weeks=[5]))
    weeks_changed = PlanningCalendarEvent.model_validate(event_payload(weeks=[7], qualification_weeks=[5]))
    qualification_changed = PlanningCalendarEvent.model_validate(event_payload(weeks=[6], qualification_weeks=[4]))

    assert base.event_fingerprint != weeks_changed.event_fingerprint
    assert base.event_fingerprint != qualification_changed.event_fingerprint


def test_calendar_fingerprint_is_deterministic_across_service_instances(tmp_path: Path) -> None:
    path = tmp_path / "planning_season_calendars.json"
    first_service = PlanningSeasonCalendarService(registry_path=path)
    second_service = PlanningSeasonCalendarService(registry_path=path)

    created = first_service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))
    reloaded = second_service.get_calendar("2000/2001")

    assert reloaded is not None
    assert reloaded.calendar_fingerprint == created.calendar_fingerprint


def test_timestamps_do_not_change_calendar_fingerprint() -> None:
    first = PlanningSeasonCalendar.model_validate(
        calendar_payload(created_at="2000-01-01T00:00:00Z", updated_at="2000-01-01T00:00:00Z")
    )
    second = PlanningSeasonCalendar.model_validate(
        calendar_payload(created_at="2001-01-01T00:00:00Z", updated_at="2001-01-01T00:00:00Z")
    )

    assert first.calendar_fingerprint == second.calendar_fingerprint


def test_source_template_identity_and_fingerprints_affect_event_fingerprint() -> None:
    base = PlanningCalendarEvent.model_validate(event_payload())
    source_id_changed = PlanningCalendarEvent.model_validate(event_payload(source_template_id="template-b"))
    source_event_changed = PlanningCalendarEvent.model_validate(event_payload(source_template_event_id="template-event-b"))
    source_fp_changed = PlanningCalendarEvent.model_validate(event_payload(source_template_fingerprint="tpl_bbb"))
    source_event_fp_changed = PlanningCalendarEvent.model_validate(event_payload(source_template_event_fingerprint="evt_bbb"))

    fingerprints = {
        base.event_fingerprint,
        source_id_changed.event_fingerprint,
        source_event_changed.event_fingerprint,
        source_fp_changed.event_fingerprint,
        source_event_fp_changed.event_fingerprint,
    }
    assert len(fingerprints) == 5


def test_active_planning_calendar_rejects_event_with_empty_weeks() -> None:
    with pytest.raises(ValidationError, match="Active planning calendar events"):
        PlanningSeasonCalendar.model_validate(calendar_payload(status="active", events=[event_payload(weeks=[])]))


def test_draft_planning_calendar_allows_event_with_empty_weeks() -> None:
    calendar = PlanningSeasonCalendar.model_validate(calendar_payload(status="draft", events=[event_payload(weeks=[])]))

    assert calendar.events[0].weeks == []


def test_planning_service_writes_only_planning_calendar_file(tmp_path: Path) -> None:
    planning_path = tmp_path / "planning_season_calendars.json"
    season_calendar_path = tmp_path / "season_calendars.json"
    service = PlanningSeasonCalendarService(registry_path=planning_path)

    service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))

    assert planning_path.exists()
    assert not season_calendar_path.exists()


def test_planning_service_does_not_modify_existing_season_calendars_json(tmp_path: Path) -> None:
    planning_path = tmp_path / "planning_season_calendars.json"
    season_calendar_path = tmp_path / "season_calendars.json"
    season_calendar_path.write_text('{"sentinel": true}\n', encoding="utf-8")
    before = season_calendar_path.read_text(encoding="utf-8")
    service = PlanningSeasonCalendarService(registry_path=planning_path)

    service.save_calendar(PlanningSeasonCalendar.model_validate(calendar_payload()))

    assert season_calendar_path.read_text(encoding="utf-8") == before


def test_no_adapter_to_season_calendar_event_is_enabled() -> None:
    service = PlanningSeasonCalendarService(registry_path=Path("unused.json"))

    assert not hasattr(service, "to_season_calendar")
    assert not hasattr(service, "to_season_calendar_event")
    assert not hasattr(PlanningSeasonCalendar, "to_season_calendar")
