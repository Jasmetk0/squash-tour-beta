from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

import uvicorn

from beta_engine.main import create_app

COUNTRIES = {
    "countries": [
        {"code": "AAA", "name": "Alpha", "region": "EUROPE", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5},
        {"code": "BBB", "name": "Beta", "region": "ASIA", "population": 60_000_000, "wealth_support": 2, "squash_popularity": 2, "squash_tradition": 2, "system_quality": 2},
    ]
}


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    with request.urlopen(req, timeout=60) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        countries_path = tmp_path / "countries.json"
        countries_path.write_text(json.dumps(COUNTRIES), encoding="utf-8")
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            countries_config_path=str(countries_path),
            initial_player_pool_config_path=str(tmp_path / "pool.json"),
            season_active_players_config_path=str(tmp_path / "season_active_players.json"),
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                call("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def test_get_season_players_empty_state(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/players")
        assert status == 200
        assert body["players"] == []
        assert body["summary"]["total_active_players"] == 0


def test_post_bootstrap_dry_run_and_persist(tmp_path) -> None:
    with Server(tmp_path) as server:
        call("POST", f"{server.base_url}/admin/players/initial-pool/generate", {"season": "2000/2001", "seed": 7, "target_pool_size": 6, "dry_run": False})

        status, preview = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", {"source_season": "2000/2001", "seed": 12345, "dry_run": True, "overwrite_existing": False})
        assert status == 200
        assert preview["summary"]["total_active_players"] == 6
        _, empty = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/players")
        assert empty["players"] == []

        status, persisted = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", {"source_season": "2000/2001", "seed": 12345, "dry_run": False, "overwrite_existing": False})
        assert status == 200
        assert persisted["players"][0]["ranking_points"] == 0
        _, players = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/players")
        assert players["summary"]["total_active_players"] == 6


def test_overwrite_safety_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        call("POST", f"{server.base_url}/admin/players/initial-pool/generate", {"season": "2000/2001", "seed": 7, "target_pool_size": 2, "dry_run": False})
        payload = {"source_season": "2000/2001", "seed": 1, "dry_run": False, "overwrite_existing": False}
        call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", payload)
        try:
            call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exist" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing active players")


def test_empty_initial_pool_error(tmp_path) -> None:
    with Server(tmp_path) as server:
        try:
            call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/bootstrap-from-initial-pool", {"source_season": "2000/2001", "seed": 1, "dry_run": False, "overwrite_existing": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "initial pool is empty" in exc.read().decode()
        else:
            raise AssertionError("empty initial pool should fail")
