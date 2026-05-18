from __future__ import annotations

import json

import test_admin_lifecycle_api as lifecycle_api
from test_admin_lifecycle_api import Server, call
from test_admin_weeks_run_api import write_complete_templates


def test_post_week_recovery_no_calendar(tmp_path):
    with Server(tmp_path) as server:
        status, body = call('POST', f'{server.base_url}/admin/weeks/recovery', {'season': '2000/2001', 'season_week': 1})
    assert status == 200
    assert body['events'] == []
    assert body['summary']['next_safe_action'] == 'build_calendar'
    assert body['metadata']['read_only'] is True
    assert body['validation_errors']


def test_post_week_recovery_after_one_week_run(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
        status, body = call('POST', f'{server.base_url}/admin/weeks/recovery', {'season': '2000/2001', 'season_week': 2})
    assert status == 200
    assert body['events'][0]['event_id'] == event_id
    assert body['events'][0]['point_awards_exists'] is True
    assert body['events'][0]['points_applied'] is False
    assert body['summary']['ready_for_point_application'] is True


def test_post_week_recovery_completed_with_snapshot(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 6, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
        status, body = call('POST', f'{server.base_url}/admin/weeks/recovery', {'season': '2000/2001', 'season_week': 2})
    assert status == 200
    assert body['summary']['week_complete'] is True
    assert body['summary']['snapshot_exists'] is True
    assert body['summary']['next_safe_action'] == 'review_completed_week'


def test_post_week_recovery_blocked_event(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        call('POST', f'{server.base_url}/admin/entries/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False, 'max_alternates': 16, 'include_not_entered': False})
        entries_path = tmp_path / 'entries.json'
        registry = json.loads(entries_path.read_text(encoding='utf-8'))
        registry['entry_lists_by_event_id'][event_id]['validation_errors'].append({'severity': 'error', 'code': 'forced_error', 'message': 'forced error', 'event_id': event_id, 'player_id': None, 'field': None})
        entries_path.write_text(json.dumps(registry), encoding='utf-8')
        status, body = call('POST', f'{server.base_url}/admin/weeks/recovery', {'season': '2000/2001', 'season_week': 2})
    assert status == 200
    assert body['summary']['week_blocked'] is True
    assert body['summary']['manual_attention_count'] > 0
    assert body['summary']['next_safe_action'] == 'resolve_blockers'
