from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request

import uvicorn

from beta_engine.main import create_app
from test_admin_entries_api import write_active, write_countries, write_templates


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header('content-type', 'application/json')
    with request.urlopen(req, timeout=60) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f'http://127.0.0.1:{self.port}'
        countries_path = tmp_path / 'countries.json'; write_countries(countries_path)
        templates_path = tmp_path / 'templates.json'; write_templates(templates_path)
        active_path = tmp_path / 'active.json'; write_active(active_path)
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            countries_config_path=str(countries_path),
            tournament_templates_config_path=str(templates_path),
            calendar_config_dir=str(tmp_path / 'legacy'),
            season_active_players_config_path=str(active_path),
            season_calendar_registry_path=str(tmp_path / 'calendars.json'),
            season_entry_lists_registry_path=str(tmp_path / 'entries.json'),
            season_draws_registry_path=str(tmp_path / 'draws.json'),
            season_matches_registry_path=str(tmp_path / 'matches.json'),
            season_event_results_registry_path=str(tmp_path / 'results.json'),
            season_point_awards_registry_path=str(tmp_path / 'points.json'),
            season_ranking_snapshots_registry_path=str(tmp_path / 'snapshots.json'),
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

    def persist_calendar(self) -> str:
        _, body = call('POST', f'{self.base_url}/admin/seasons/2000%2F2001/calendar/build', {'seed': 1, 'dry_run': False, 'overwrite_existing': False, 'season_start_calendar_year': 2000, 'season_start_year_week': 37, 'include_inactive_templates': False, 'max_events': 1})
        return body['calendar']['events'][0]['event_id']


def test_get_season_lifecycle_no_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call('GET', f'{server.base_url}/admin/lifecycle/2000%2F2001')
    assert status == 200
    assert body['events'] == []
    assert body['summary']['event_count'] == 0
    assert body['metadata']['read_only'] is True
    assert body['validation_errors']


def test_get_season_lifecycle_with_staged_artifact(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        call('POST', f'{server.base_url}/admin/entries/{event_id}/generate', {'seed': 1, 'dry_run': False, 'overwrite_existing': False, 'max_alternates': 16, 'include_not_entered': False})
        status, body = call('GET', f'{server.base_url}/admin/lifecycle/2000%2F2001')
    assert status == 200
    assert body['events'][0]['current_stage'] == 'entries_generated'
    assert body['events'][0]['next_recommended_action'] == 'generate_draw'
    assert body['summary']['entries_generated_count'] == 1


def test_get_event_lifecycle_and_unknown_event(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        status, body = call('GET', f'{server.base_url}/admin/lifecycle/event/{event_id}')
        unknown_status, unknown = call('GET', f'{server.base_url}/admin/lifecycle/event/EVT-missing')
    assert status == 200
    assert body['event']['event_id'] == event_id
    assert body['event']['current_stage'] == 'planned'
    assert unknown_status == 200
    assert unknown['event'] is None
    assert unknown['validation_errors']
