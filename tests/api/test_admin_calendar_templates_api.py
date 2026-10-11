from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib import request

import uvicorn
import threading
import time

from beta_engine.main import create_app
from test_admin_entries_api import write_active, write_countries, write_templates
from test_admin_lifecycle_api import call, free_port


def call_raw(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header('content-type', 'application/json')
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, json.loads(raw) if raw else {}


class CalendarTemplateServer:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f'http://127.0.0.1:{self.port}'
        countries_path = tmp_path / 'countries.json'; write_countries(countries_path)
        templates_path = tmp_path / 'templates.json'; write_templates(templates_path)
        active_path = tmp_path / 'active.json'; write_active(active_path)
        self.calendar_templates_path = tmp_path / 'calendar_templates.json'
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            countries_config_path=str(countries_path),
            tournament_templates_config_path=str(templates_path),
            calendar_config_dir=str(tmp_path / 'legacy'),
            season_active_players_config_path=str(active_path),
            season_calendar_registry_path=str(tmp_path / 'calendars.json'),
            calendar_templates_registry_path=str(self.calendar_templates_path),
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


def payload(**overrides) -> dict:
    data = {
        "id": "template-a",
        "name": "Template A",
        "description": "API template",
        "status": "draft",
        "events": [
            {
                "id": "event-a",
                "name": "Event A",
                "category_code": "DIAMOND",
                "weeks": [6, 7],
                "qualification_weeks": [5],
                "locked": True,
            }
        ],
    }
    data.update(overrides)
    return data


def test_calendar_template_crud_api_and_persistence(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        status_empty, empty = call('GET', f'{server.base_url}/admin/seasons/calendar-templates')
        create_status, created = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        list_status, listed = call('GET', f'{server.base_url}/admin/seasons/calendar-templates')
        get_status, fetched = call('GET', f'{server.base_url}/admin/seasons/calendar-templates/template-a')
        update_status, updated = call_raw('PUT', f'{server.base_url}/admin/seasons/calendar-templates/template-a', payload(name='Template A Updated'))
        archive_status, archived = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates/template-a/archive')

    assert status_empty == 200
    assert empty['templates'] == []
    assert create_status == 201
    assert server.calendar_templates_path.exists()
    assert created['template']['template_fingerprint']
    assert created['template']['events'][0]['event_fingerprint']
    assert list_status == 200
    assert listed['templates'][0]['id'] == 'template-a'
    assert get_status == 200
    assert fetched['template']['id'] == 'template-a'
    assert update_status == 200
    assert updated['template']['name'] == 'Template A Updated'
    assert archive_status == 200
    assert archived['template']['status'] == 'archived'


def test_duplicate_template_id_api_rejected(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        first_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())
        second_status, second = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload())

    assert first_status == 201
    assert second_status == 400
    assert 'already exists' in second['detail']


def test_invalid_calendar_template_payloads_api_rejected(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        bad_week_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload(events=[{**payload()['events'][0], 'weeks': [0]}]))
        duplicate_event_status, duplicate_event = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload(events=[payload()['events'][0], payload()['events'][0]]))
        active_empty_status, _ = call_raw('POST', f'{server.base_url}/admin/seasons/calendar-templates', payload(status='active', events=[{**payload()['events'][0], 'weeks': []}]))

    assert bad_week_status == 422
    assert duplicate_event_status == 422
    assert 'Duplicate event id' in json.dumps(duplicate_event)
    assert active_empty_status == 422


def test_existing_season_templates_endpoint_still_works(tmp_path: Path) -> None:
    with CalendarTemplateServer(tmp_path) as server:
        status, body = call('GET', f'{server.base_url}/admin/seasons/templates')

    assert status == 200
    assert body['status'] == 'read_only_foundation'
    assert body['templates']
