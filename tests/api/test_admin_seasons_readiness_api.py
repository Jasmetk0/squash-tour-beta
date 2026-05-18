from __future__ import annotations

import test_admin_lifecycle_api as lifecycle_api
from test_admin_lifecycle_api import Server, call
from test_admin_weeks_run_api import write_complete_templates


def test_post_season_readiness_no_calendar(tmp_path):
    with Server(tmp_path) as server:
        status, body = call('POST', f'{server.base_url}/admin/seasons/readiness', {'season': '2000/2001'})
    assert status == 200
    assert body['summary']['total_weeks'] == 61
    assert body['summary']['next_safe_action'] == 'build_calendar'
    assert body['metadata']['read_only'] is True
    assert body['validation_errors']


def test_post_season_readiness_planned_week(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/seasons/readiness', {'season': '2000/2001'})
    assert status == 200
    assert body['summary']['next_safe_action'] == 'run_week'
    assert body['summary']['next_week_to_run'] == 2
    row = next(row for row in body['weeks'] if row['season_week'] == 2)
    assert row['status'] == 'planned'
    assert row['representative_event_ids'] == [event_id]


def test_post_season_readiness_after_week_run(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
        status, body = call('POST', f'{server.base_url}/admin/seasons/readiness', {'season': '2000/2001'})
    assert status == 200
    assert body['summary']['next_safe_action'] == 'apply_points'
    row = next(row for row in body['weeks'] if row['season_week'] == 2)
    assert row['status'] == 'ready_for_point_application'
    assert row['ready_for_point_application'] is True


def test_post_season_readiness_filters(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 6, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
        status, body = call('POST', f'{server.base_url}/admin/seasons/readiness', {'season': '2000/2001', 'include_empty_weeks': False, 'include_completed_weeks': False})
    assert status == 200
    assert body['weeks'] == []
    assert body['summary']['total_weeks'] == 61
    assert body['summary']['empty_weeks'] == 60
    assert body['summary']['complete_weeks'] == 1
