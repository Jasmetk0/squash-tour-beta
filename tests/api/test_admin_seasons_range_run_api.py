from __future__ import annotations

import test_admin_lifecycle_api as lifecycle_api
from test_admin_lifecycle_api import Server, call
from test_admin_weeks_run_api import write_complete_templates


def test_post_range_run_unsafe_preflight(tmp_path):
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-run', {'season': '2000/2001', 'start_week': 2, 'end_week': 2, 'apply_points': False, 'publish_snapshot': True})
    assert status == 200
    assert body['summary']['run_started'] is False
    assert body['summary']['stop_reason'] == 'range_preflight_not_safe'
    assert body['weeks'] == []


def test_post_range_run_planned_week_execution(tmp_path):
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-run', {'season': '2000/2001', 'start_week': 2, 'end_week': 2, 'seed': 5, 'apply_points': False, 'publish_snapshot': False})
    assert status == 200
    assert body['summary']['executed_week_count'] == 1
    assert body['weeks'][0]['week_run_result'] is not None


def test_post_range_run_ready_for_points(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-run', {'season': '2000/2001', 'start_week': 2, 'end_week': 2, 'seed': 5, 'apply_points': True, 'publish_snapshot': False})
    assert status == 200
    assert body['summary']['point_application_week_count'] == 1


def test_post_range_run_ready_for_snapshot(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 6, 'apply_points': True})
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-run', {'season': '2000/2001', 'start_week': 2, 'end_week': 2, 'seed': 6, 'apply_points': True, 'publish_snapshot': True})
    assert status == 200
    assert body['summary']['snapshot_publication_week_count'] == 1


def test_post_range_run_skips_completed_week(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 7, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
        status, body = call('POST', f'{server.base_url}/admin/seasons/range-run', {'season': '2000/2001', 'start_week': 2, 'end_week': 2})
    assert status == 200
    assert body['summary']['skipped_complete_week_count'] == 1
    assert body['summary']['executed_week_count'] == 0
