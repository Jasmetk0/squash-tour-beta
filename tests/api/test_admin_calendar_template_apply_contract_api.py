from __future__ import annotations

import json
from pathlib import Path

from test_admin_calendar_templates_api import CalendarTemplateServer, call_raw, payload

CONFIRMATION = "I understand this will apply reviewed template events to the canonical season calendar."


def readiness_payload(**overrides) -> dict:
    data = {"target_season_label": "2000/01", "source_template_id": "template-a", "policy": "replace_unlocked_only"}
    data.update(overrides)
    return data


def create_template(server: CalendarTemplateServer) -> dict:
    status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
    assert status == 201
    return body['template']


def test_missing_source_template_returns_404(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(source_template_id='missing'))

    assert status == 404
    assert 'Calendar template not found' in body['detail']


def test_valid_source_template_returns_disabled_read_only_contract(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        before_calendar = server.calendar_templates_path.read_text(encoding='utf-8') if server.calendar_templates_path.exists() else None
        create_template(server)
        before_templates = server.calendar_templates_path.read_text(encoding='utf-8')
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())

    assert status == 200
    assert body['command'] == 'calendar_template_apply_contract_readiness'
    assert body['enabled'] is False
    assert body['can_execute'] is False
    assert body['can_mutate'] is False
    assert body['mutation_performed'] is False
    assert body['safety']['read_only'] is True
    assert body['safety']['canonical_season_calendar_modified'] is False
    assert body['safety']['audit_written'] is False
    assert body['readiness_summary']['mutation_allowed'] is False
    assert server.calendar_templates_path.read_text(encoding='utf-8') == before_templates
    assert before_calendar is None


def test_replace_all_is_blocked_deferred(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(policy='replace_all'))

    assert status == 200
    assert body['readiness_summary']['policy_supported_for_future_apply'] is False
    assert body['apply_gate_summary']['replace_all_blocked'] is True
    assert any('replace_all' in warning for warning in body['validation_warnings'])
    assert body['can_mutate'] is False


def test_duplicate_selected_source_event_ids_rejected(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(selected_source_event_ids=['event-a', 'event-a']))

    assert status == 422
    assert 'selected_source_event_ids' in json.dumps(body)


def test_unknown_selected_source_event_id_rejected(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(selected_source_event_ids=['missing']))

    assert status == 400
    assert 'Unknown selected_source_event_id' in body['detail']


def test_source_template_fingerprint_mismatch_reported(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(source_template_fingerprint='tpl_wrong'))

    assert status == 200
    assert body['readiness_summary']['source_template_fingerprint_matched'] is False
    assert any('source_template_fingerprint mismatch' in warning for warning in body['validation_warnings'])
    assert body['can_mutate'] is False


def test_missing_target_calendar_reported_without_creating_one(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        season_calendar_path = server.calendar_templates_path.with_name('calendars.json')
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())

    assert status == 200
    assert body['target_calendar_exists'] is False
    assert body['target_fingerprint'] is None
    assert not season_calendar_path.exists()


def test_existing_target_calendar_produces_deterministic_target_fingerprint(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        build_payload = {"seed": 5, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        build_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/2000%2F2001/calendar/build', build_payload)
        first_status, first = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())
        second_status, second = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())

    assert build_status == 200
    assert first_status == 200
    assert second_status == 200
    assert first['target_calendar_exists'] is True
    assert first['target_fingerprint'].startswith('target_')
    assert first['target_fingerprint'] == second['target_fingerprint']


def test_target_fingerprint_mismatch_reported(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        build_payload = {"seed": 5, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        call_raw('POST', f'{server.base_url}/admin/seasons/2000%2F2001/calendar/build', build_payload)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(target_fingerprint='target_wrong'))

    assert status == 200
    assert body['readiness_summary']['target_fingerprint_matched'] is False
    assert any('target_fingerprint mismatch' in warning for warning in body['validation_warnings'])
    assert body['can_mutate'] is False


def test_missing_audit_fields_and_confirmation_are_reported_in_gates(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())

    assert status == 200
    assert body['readiness_summary']['requested_by_present'] is False
    assert body['readiness_summary']['audit_reason_present'] is False
    assert body['readiness_summary']['explicit_confirmation_present'] is False
    assert body['readiness_summary']['explicit_confirmation_valid'] is False


def test_valid_confirmation_recognized_but_still_no_mutation(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(explicit_confirmation=CONFIRMATION, requested_by='tester', audit_reason='readiness check'))

    assert status == 200
    assert body['readiness_summary']['explicit_confirmation_present'] is True
    assert body['readiness_summary']['explicit_confirmation_valid'] is True
    assert body['can_mutate'] is False
    assert body['readiness_summary']['mutation_allowed'] is False


def test_adapter_gaps_reported(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload())

    assert status == 200
    assert body['adapter_gap_summary']['weeks_adapter']['ready'] is False
    assert body['adapter_gap_summary']['qualification_weeks_adapter']['ready'] is False
    assert body['adapter_gap_summary']['locked_events_adapter']['ready'] is False


def test_template_and_calendar_files_unchanged_and_no_audit_created(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        build_payload = {"seed": 5, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        call_raw('POST', f'{server.base_url}/admin/seasons/2000%2F2001/calendar/build', build_payload)
        season_calendar_path = server.calendar_templates_path.with_name('calendars.json')
        before_templates = server.calendar_templates_path.read_text(encoding='utf-8')
        before_calendar = season_calendar_path.read_text(encoding='utf-8')
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(explicit_confirmation=CONFIRMATION))
        audit_path = season_calendar_path.with_name('calendar_template_apply_audit.jsonl')

    assert status == 200
    assert body['mutation_performed'] is False
    assert server.calendar_templates_path.read_text(encoding='utf-8') == before_templates
    assert season_calendar_path.read_text(encoding='utf-8') == before_calendar
    assert not audit_path.exists()


def test_no_real_calendar_template_apply_endpoint_with_can_mutate_true_exists(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_template(server)
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply-contract-readiness', readiness_payload(explicit_confirmation=CONFIRMATION))
        apply_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/apply', readiness_payload())
        template_apply_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/template-a/apply', readiness_payload())

    assert status == 200
    assert body['can_mutate'] is False
    assert body['mutation_performed'] is False
    assert apply_status in {404, 405}
    assert template_apply_status in {404, 405}
