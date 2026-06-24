from __future__ import annotations

from pathlib import Path

from beta_engine.main import create_app

from test_admin_calendar_templates_api import CalendarTemplateServer, call_raw, payload


def compare_payload(**overrides) -> dict:
    payload_data = {"target_season_label": "2000/01", "source_template_id": "template-a", "target_events": []}
    payload_data.update(overrides)
    return payload_data


def test_missing_source_template_returns_404(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run', compare_payload(source_template_id='missing'))

    assert status == 404
    assert 'Calendar template not found' in body['detail']


def test_compare_dry_run_api_returns_read_only_response(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        create_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run', compare_payload())

    assert create_status == 201
    assert status == 200
    assert body['dry_run'] is True
    assert body['mutation_performed'] is False
    assert body['safety']['read_only'] is True
    assert body['safety']['apply_endpoint_enabled'] is False
    assert body['summary']['missing_from_target_count'] == 1
    assert body['diff_fingerprint'].startswith('diff_')


def test_unknown_selected_source_event_id_returns_400(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        status, body = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run', compare_payload(selected_source_event_ids=['missing']))

    assert status == 400
    assert 'Unknown selected_source_event_id' in body['detail']


def test_no_apply_endpoint_added() -> None:
    app = create_app()
    post_paths = {route.path for route in app.routes if 'POST' in getattr(route, 'methods', set())}

    assert '/admin/seasons/calendar-templates/apply' not in post_paths
    assert '/admin/seasons/calendar-templates/{template_id}/apply' not in post_paths
