from __future__ import annotations

import test_admin_lifecycle_api as lifecycle_api
from test_admin_lifecycle_api import Server, call


def write_complete_templates(path):
    path.write_text(
        '{"templates":[{"template_id":"wt_complete","tour_level":"WORLD_TOUR","category":"PLATINUM","event_name":"World Complete","region":"EUROPE","host_country":"AAA","main_draw_size":4,"qualification_draw_size":0,"seeds_count":2,"qualifier_spots":0,"wild_cards":0,"byes":0,"lucky_loser_rules":{"enabled":false,"max_spots":0,"replacement_window":"pre_main_draw_round_1"},"point_distribution_ref":"world","prize_money":100000,"prestige":9,"event_duration_days":4,"qualification_duration_days":0,"duration_in_season_weeks":1,"active":true}]}',
        encoding='utf-8',
    )


def test_post_week_run_preflight_unsafe_no_run(tmp_path):
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'publish_snapshot': True, 'apply_points': False})
    assert status == 200
    assert body['summary']['run_started'] is False
    assert body['summary']['stop_reason'] == 'preflight_not_safe'
    assert body['events'] == []


def test_post_week_run_one_event(tmp_path):
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 5})
    assert status == 200
    assert body['summary']['run_started'] is True
    assert body['summary']['attempted_event_count'] == 1
    assert body['events'][0]['event_id'] == event_id
    assert body['events'][0]['event_report']['requested_publish_snapshot'] is False
    assert body['summary']['snapshot_published'] is False


def test_post_week_run_apply_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        status, body = call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 6, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
    assert status == 200
    assert body['summary']['points_applied_event_count'] == 1
    assert body['summary']['snapshot_published'] is True
    assert body['metadata']['read_only'] is False


def test_post_week_run_rerun_skips_existing_snapshot(tmp_path, monkeypatch):
    monkeypatch.setitem(lifecycle_api.Server.__init__.__globals__, 'write_templates', write_complete_templates)
    with Server(tmp_path) as server:
        server.persist_calendar()
        call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 7, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
        status, body = call('POST', f'{server.base_url}/admin/weeks/run', {'season': '2000/2001', 'season_week': 2, 'seed': 7, 'apply_points': True, 'publish_snapshot': True, 'allow_blocked': True, 'allow_incomplete_results': True})
    assert status == 200
    assert body['summary']['snapshot_published'] is False
    assert body['summary']['snapshot_skipped'] is True
    assert body['summary']['snapshot_already_existed'] is True
