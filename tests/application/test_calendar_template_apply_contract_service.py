from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from beta_engine.application.calendar_template_apply_contract_service import (
    REQUIRED_CALENDAR_TEMPLATE_APPLY_CONFIRMATION,
    CalendarTemplateApplyContractReadinessRequest,
    CalendarTemplateApplyContractService,
)
from beta_engine.application.calendar_template_service import CalendarTemplate, CalendarTemplateService
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments import SeasonCalendar, SeasonCalendarEvent


def event(**overrides) -> dict:
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


def template(**overrides) -> dict:
    payload = {"id": "template-a", "name": "Template A", "description": "", "status": "draft", "events": [event()]}
    payload.update(overrides)
    return payload


def write_tournament_templates(path: Path) -> None:
    path.write_text(json.dumps({"templates": [{
        "template_id": "wt_a",
        "tour_level": "WORLD_TOUR",
        "category": "PLATINUM",
        "event_name": "World A",
        "region": "EUROPE",
        "host_country": "ENG",
        "main_draw_size": 32,
        "qualification_draw_size": 16,
        "seeds_count": 8,
        "qualifier_spots": 4,
        "wild_cards": 2,
        "byes": 0,
        "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"},
        "point_distribution_ref": "world",
        "prize_money": 100000,
        "prestige": 9,
        "event_duration_days": 6,
        "qualification_duration_days": 2,
        "duration_in_season_weeks": 1,
        "active": True,
    }]}), encoding="utf-8")


def service(tmp_path: Path) -> tuple[CalendarTemplateApplyContractService, Path, Path]:
    template_path = tmp_path / "calendar_templates.json"
    calendar_path = tmp_path / "season_calendars.json"
    tournament_template_path = tmp_path / "tournament_templates.json"
    write_tournament_templates(tournament_template_path)
    template_service = CalendarTemplateService(registry_path=template_path)
    template_service.create_template(template=CalendarTemplate.model_validate(template()))
    calendar_service = SeasonCalendarService(
        template_service=TournamentTemplatesConfigService(config_path=tournament_template_path, calendar_dir=tmp_path / "legacy"),
        calendar_registry_path=calendar_path,
    )
    return CalendarTemplateApplyContractService(template_service=template_service, calendar_service=calendar_service), template_path, calendar_path


def request(**overrides) -> CalendarTemplateApplyContractReadinessRequest:
    payload = {"target_season_label": "2000/01", "source_template_id": "template-a"}
    payload.update(overrides)
    return CalendarTemplateApplyContractReadinessRequest.model_validate(payload)


def test_valid_source_template_returns_read_only_disabled_response(tmp_path: Path) -> None:
    svc, template_path, calendar_path = service(tmp_path)
    before_template = template_path.read_text(encoding="utf-8")

    response = svc.build_readiness(request())

    assert response.enabled is False
    assert response.can_execute is False
    assert response.can_mutate is False
    assert response.mutation_performed is False
    assert response.safety["read_only"] is True
    assert response.safety["audit_written"] is False
    assert response.readiness_summary["mutation_allowed"] is False
    assert response.source_template_fingerprint
    assert template_path.read_text(encoding="utf-8") == before_template
    assert not calendar_path.exists()


def test_replace_all_is_blocked_deferred(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    response = svc.build_readiness(request(policy="replace_all"))

    assert response.readiness_summary["policy_supported_for_future_apply"] is False
    assert response.apply_gate_summary["replace_all_blocked"] is True
    assert any("replace_all" in warning for warning in response.validation_warnings)
    assert response.can_mutate is False


def test_duplicate_selected_source_event_ids_rejected_by_request_model() -> None:
    with pytest.raises(ValidationError, match="selected_source_event_ids"):
        request(selected_source_event_ids=["event-a", "event-a"])


def test_unknown_selected_source_event_id_rejected(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    with pytest.raises(ValueError, match="Unknown selected_source_event_id"):
        svc.build_readiness(request(selected_source_event_ids=["missing"]))


def test_source_template_fingerprint_mismatch_reported(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    response = svc.build_readiness(request(source_template_fingerprint="tpl_wrong"))

    assert response.readiness_summary["source_template_fingerprint_matched"] is False
    assert any("source_template_fingerprint mismatch" in warning for warning in response.validation_warnings)
    assert response.can_mutate is False


def test_missing_target_calendar_reported_without_creating_one(tmp_path: Path) -> None:
    svc, _, calendar_path = service(tmp_path)

    response = svc.build_readiness(request())

    assert response.target_calendar_exists is False
    assert response.target_fingerprint is None
    assert not calendar_path.exists()


def test_existing_target_calendar_produces_deterministic_fingerprint(tmp_path: Path) -> None:
    svc, _, calendar_path = service(tmp_path)
    event_model = SeasonCalendarEvent(
        event_id="EVT-2000-W06-001",
        season="2000/2001",
        season_week=6,
        calendar_year=2000,
        year_week=42,
        template_id="wt_a",
        event_name="Event A",
        category="DIAMOND",
        tour_level="WORLD_TOUR",
        host_country="ENG",
        region="EUROPE",
    )
    svc.calendar_service.create_calendar_if_absent(season="2000/2001", calendar=SeasonCalendar(season="2000/2001", events=[event_model]))
    before_calendar = calendar_path.read_text(encoding="utf-8")

    first = svc.build_readiness(request())
    second = svc.build_readiness(request())

    assert first.target_calendar_exists is True
    assert first.target_fingerprint
    assert first.target_fingerprint == second.target_fingerprint
    assert calendar_path.read_text(encoding="utf-8") == before_calendar


def test_target_fingerprint_mismatch_reported(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)
    event_model = SeasonCalendarEvent(event_id="EVT-2000-W06-001", season="2000/2001", season_week=6, template_id="wt_a", event_name="Event A", category="DIAMOND", tour_level="WORLD_TOUR", host_country="ENG", region="EUROPE")
    svc.calendar_service.create_calendar_if_absent(season="2000/2001", calendar=SeasonCalendar(season="2000/2001", events=[event_model]))

    response = svc.build_readiness(request(target_fingerprint="target_wrong"))

    assert response.readiness_summary["target_fingerprint_matched"] is False
    assert any("target_fingerprint mismatch" in warning for warning in response.validation_warnings)
    assert response.can_mutate is False


def test_missing_audit_metadata_and_confirmation_reported_in_gates(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    response = svc.build_readiness(request())

    assert response.readiness_summary["requested_by_present"] is False
    assert response.readiness_summary["audit_reason_present"] is False
    assert response.readiness_summary["explicit_confirmation_present"] is False
    assert response.readiness_summary["explicit_confirmation_valid"] is False


def test_valid_explicit_confirmation_recognized_but_still_no_mutation(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    response = svc.build_readiness(request(explicit_confirmation=REQUIRED_CALENDAR_TEMPLATE_APPLY_CONFIRMATION))

    assert response.readiness_summary["explicit_confirmation_present"] is True
    assert response.readiness_summary["explicit_confirmation_valid"] is True
    assert response.can_mutate is False
    assert response.readiness_summary["mutation_allowed"] is False


def test_adapter_gaps_report_weeks_qualification_weeks_and_locked_events(tmp_path: Path) -> None:
    svc, _, _ = service(tmp_path)

    response = svc.build_readiness(request())

    assert response.adapter_gap_summary["weeks_adapter"]["ready"] is False
    assert response.adapter_gap_summary["qualification_weeks_adapter"]["ready"] is False
    assert response.adapter_gap_summary["locked_events_adapter"]["ready"] is False
    assert any("weeks list" in item for item in response.adapter_gap_summary["blocked_until_resolved"])
    assert any("qualification_weeks" in item for item in response.adapter_gap_summary["blocked_until_resolved"])
    assert any("locked target event" in item for item in response.adapter_gap_summary["blocked_until_resolved"])
