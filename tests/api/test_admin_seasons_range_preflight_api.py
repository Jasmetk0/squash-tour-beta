from __future__ import annotations

import json

import test_admin_lifecycle_api as lifecycle_api
from test_admin_lifecycle_api import Server, call
from test_admin_weeks_run_api import write_complete_templates


def test_post_range_preflight_invalid_range(tmp_path):
    with Server(tmp_path) as server:
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-preflight', {'season': '2000/2001', 'start_week': 10, 'end_week': 1})
    assert status == 200
    assert body['summary']['next_safe_action'] == 'adjust_range'
    assert body['summary']['range_safe_to_run'] is False
    assert body['validation_errors']


def test_post_range_preflight_planned_week(tmp_path):
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-preflight', {'season': '2000/2001', 'start_week': 2, 'end_week': 2})
    assert status == 200
    assert body['summary']['range_safe_to_run'] is True
    assert body['summary']['runnable_weeks'] == 1
    assert body['weeks'][0]['range_action'] == 'run_week'
    assert body['metadata']['read_only'] is True


def test_post_range_preflight_after_week_run_ready_for_points(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-preflight', {'season': '2000/2001', 'start_week': 2, 'end_week': 2})
    assert status == 200
    assert body['weeks'][0]['range_action'] == 'apply_points'
    assert body['summary']['point_application_weeks'] == 1
    assert body['summary']['recommended_run_flags']['apply_points'] is True


def test_post_range_preflight_completed_week(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 6, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-preflight', {'season': '2000/2001', 'start_week': 2, 'end_week': 2})
    assert status == 200
    assert body['weeks'][0]['range_action'] == 'skip_complete'
    assert body['summary']['skipped_weeks'] == 1
    assert body['summary']['range_safe_to_run'] is False


def test_post_range_preflight_blocked_week(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        call('POST', f'{server.base_url}/admin/entries/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False, 'max_alternates': 16, 'include_not_entered': False})
        entries_path = tmp_path / 'entries.json'
        registry = json.loads(entries_path.read_text(encoding='utf-8'))
        entry_list = registry['entry_lists_by_event_id'][event_id]
        entry_list['validation_errors'].append({'severity': 'error', 'code': 'forced_error', 'message': 'forced error', 'event_id': event_id, 'player_id': None, 'field': None})
        entries_path.write_text(json.dumps(registry), encoding='utf-8')
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-preflight', {'season': '2000/2001', 'start_week': 2, 'end_week': 2})
    assert status == 200
    assert body['weeks'][0]['range_action'] == 'blocked'
    assert body['summary']['range_safe_to_run'] is False
    assert body['summary']['next_safe_action'] == 'resolve_blockers'
