from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_post_week_preflight_no_calendar(tmp_path):
    with Server(tmp_path) as server:
        status, body = call('POST', f'{server.base_url}/admin/weeks/preflight', {'season': '2000/2001', 'season_week': 1})
    assert status == 200
    assert body['events'] == []
    assert body['summary']['can_run_week'] is False
    assert body['validation_errors']
    assert body['metadata']['read_only'] is True


def test_post_week_preflight_with_one_event(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/preflight', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
    assert status == 200
    assert body['summary']['event_count'] == 1
    assert body['events'][0]['event_id'] == event_id
    assert body['events'][0]['one_event_report']['dry_run'] is True
    assert body['events'][0]['one_event_report']['artifact_state_before'] == body['events'][0]['one_event_report']['artifact_state_after']


def test_week_preflight_publish_snapshot_apply_points_validation(tmp_path):
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/preflight', {'season': '2000/2001', 'season_week': 2, 'publish_snapshot': True, 'apply_points': False})
    assert status == 200
    assert body['summary']['can_run_week'] is False
    assert 'publish_snapshot=true requires apply_points=true for week preflight.' in body['validation_errors']


def test_week_preflight_event_filter_behavior(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/preflight', {'season': '2000/2001', 'season_week': 2, 'event_id_filter': [event_id, 'missing']})
    assert status == 200
    assert [event['event_id'] for event in body['events']] == [event_id]
    assert any('Unknown event_id_filter' in warning for warning in body['validation_warnings'])
