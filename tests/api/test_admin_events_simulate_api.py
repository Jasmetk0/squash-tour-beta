from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_post_dry_run_simulate_planned_event(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/events/{event_id}/simulate', {'seed': 5, 'dry_run': True})
    assert status == 200
    assert body['report']['event_id'] == event_id
    assert body['report']['dry_run'] is True
    assert any(step['step'] == 'generate_entries' and step['status'] == 'planned' for step in body['report']['steps'])


def test_post_execute_one_event_generates_artifacts_or_reports_blocker(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/events/{event_id}/simulate', {'seed': 5, 'dry_run': False, 'allow_blocked': True, 'allow_incomplete_results': True})
    assert status == 200
    assert body['report']['event_id'] == event_id
    assert any(step['step'] == 'generate_entries' and step['status'] == 'succeeded' for step in body['report']['steps'])
    assert any(step['step'] == 'generate_draw' and step['status'] == 'succeeded' for step in body['report']['steps'])
    assert any(step['step'] == 'generate_matches' and step['status'] == 'succeeded' for step in body['report']['steps'])


def test_post_with_apply_points_publish_snapshot_validation(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/events/{event_id}/simulate', {'seed': 5, 'dry_run': False, 'apply_points': False, 'publish_snapshot': True})
    assert status == 200
    assert body['validation_errors']
    assert 'requires apply_points=true' in body['validation_errors'][0]


def test_unknown_event_error(tmp_path):
    with Server(tmp_path) as server:
        status, body = call('POST', f'{server.base_url}/admin/events/EVT-missing/simulate', {'dry_run': True})
    assert status == 200
    assert body['report'] is None
    assert body['validation_errors']


def test_blocked_event_behavior(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        call('POST', f'{server.base_url}/admin/entries/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False, 'max_alternates': 16, 'include_not_entered': False})
        call('POST', f'{server.base_url}/admin/draws/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False})
        call('POST', f'{server.base_url}/admin/matches/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False})
        status, body = call('POST', f'{server.base_url}/admin/events/{event_id}/simulate', {'seed': 5, 'dry_run': False})
    assert status == 200
    assert body['report']['blocked'] is True
    assert body['validation_errors']
