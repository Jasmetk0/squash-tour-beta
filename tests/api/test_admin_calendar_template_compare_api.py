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

import json
import threading
import time
from urllib import request

import uvicorn

from beta_engine.application.planning_season_calendar_service import PlanningSeasonCalendar, PlanningSeasonCalendarRegistry
from test_admin_lifecycle_api import free_port, call


class PlanningCompareServer:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f'http://127.0.0.1:{self.port}'
        self.calendar_templates_path = tmp_path / 'calendar_templates.json'
        self.planning_path = tmp_path / 'planning_season_calendars.json'
        self.season_calendar_path = tmp_path / 'season_calendars.json'
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            calendar_templates_registry_path=str(self.calendar_templates_path),
            planning_season_calendar_registry_path=str(self.planning_path),
            season_calendar_registry_path=str(self.season_calendar_path),
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host='127.0.0.1', port=self.port, log_level='error'))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                call('GET', f'{self.base_url}/health')
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError('server did not start')

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def write_planning_registry(path: Path, *, weeks: list[int] | None = None) -> str:
    calendar = PlanningSeasonCalendar.model_validate(
        {
            'season_label': '2000/01',
            'normalized_season_label': '2000/01',
            'status': 'draft',
            'events': [
                {
                    'id': 'target-a',
                    'name': 'Event A',
                    'category_code': 'DIAMOND',
                    'weeks': weeks or [6, 7],
                    'qualification_weeks': [5],
                    'locked': True,
                    'country_code': 'egy',
                    'city': 'Cairo',
                    'venue': 'Venue A',
                    'notes': 'Planning note',
                    'source_template_id': 'template-a',
                }
            ],
        }
    )
    registry = PlanningSeasonCalendarRegistry(calendars_by_season={calendar.normalized_season_label: calendar})
    path.write_text(json.dumps(registry.model_dump(mode='json'), indent=2) + '\n', encoding='utf-8')
    return path.read_text(encoding='utf-8')


def test_compare_dry_run_api_with_planning_calendar_target_returns_200(tmp_path: Path) -> None:
    with PlanningCompareServer(tmp_path) as server:
        call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        before = write_planning_registry(server.planning_path)
        status, body = call_raw(
            'POST',
            f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run',
            compare_payload(target_source='planning_calendar'),
        )

    assert status == 200
    assert body['target_source'] == 'planning_calendar'
    assert body['target_fingerprint'].startswith('pl_cal_')
    assert body['target_calendar_fingerprint'] == body['target_fingerprint']
    assert body['target_calendar_exists'] is True
    assert body['summary']['same_count'] == 1
    assert server.planning_path.read_text(encoding='utf-8') == before


def test_compare_dry_run_api_missing_planning_calendar_returns_404(tmp_path: Path) -> None:
    with PlanningCompareServer(tmp_path) as server:
        call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        status, body = call_raw(
            'POST',
            f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run',
            compare_payload(target_source='planning_calendar'),
        )

    assert status == 404
    assert 'Planning season calendar not found' in body['detail']
    assert not server.planning_path.exists()
    assert not server.season_calendar_path.exists()


def test_compare_dry_run_api_with_planning_target_does_not_modify_files(tmp_path: Path) -> None:
    with PlanningCompareServer(tmp_path) as server:
        call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        planning_before = write_planning_registry(server.planning_path, weeks=[8])
        server.season_calendar_path.write_text('{"sentinel": true}\n', encoding='utf-8')
        season_before = server.season_calendar_path.read_text(encoding='utf-8')
        status, body = call_raw(
            'POST',
            f'{server.base_url}/admin/seasons/calendar-templates/compare-dry-run',
            compare_payload(target_source='planning_calendar'),
        )

    assert status == 200
    assert body['target_source'] == 'planning_calendar'
    assert body['summary']['locked_target_preserved_count'] == 1
    assert server.planning_path.read_text(encoding='utf-8') == planning_before
    assert server.season_calendar_path.read_text(encoding='utf-8') == season_before
