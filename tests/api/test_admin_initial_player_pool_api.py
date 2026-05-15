from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import request

import uvicorn

from beta_engine.main import create_app

COUNTRIES = {
    "countries": [
        {"code": "AAA", "name": "Alpha", "region": "EUROPE", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5},
        {"code": "BBB", "name": "Beta", "region": "ASIA", "population": 60_000_000, "wealth_support": 2, "squash_popularity": 2, "squash_tradition": 2, "system_quality": 2},
    ]
}


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    with request.urlopen(req, timeout=60) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


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


def test_generate_preview_dry_run_and_lock_workflow(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, preview = call("POST", f"{server.base_url}/admin/players/initial-pool/generate", {"season": "2000/2001", "seed": 7, "target_pool_size": 24, "dry_run": True})
        assert status == 200
        assert preview["summary"]["total_players"] == 24
        assert preview["players"][0]["birth_year_week"] >= 1

        _, empty = call("GET", f"{server.base_url}/admin/players/initial-pool?season=2000/2001")
        assert empty["summary"]["total_players"] == 0

        _, persisted = call("POST", f"{server.base_url}/admin/players/initial-pool/generate", {"season": "2000/2001", "seed": 7, "target_pool_size": 24, "dry_run": False})
        player_id = persisted["players"][0]["player_id"]
        _, locked = call("POST", f"{server.base_url}/admin/players/{player_id}/lock")
        assert locked["locked"] is True

        _, regenerated = call("POST", f"{server.base_url}/admin/players/initial-pool/regenerate-unlocked", {"season": "2000/2001", "seed": 8, "country_code": locked["country_code"], "dry_run": False})
        assert next(player for player in regenerated["players"] if player["player_id"] == player_id) == locked


def custom_api_payload(player_id="CUST-2000-AAA-API") -> dict:
    return {
        "player_id": player_id,
        "name": "API Player",
        "country_code": "AAA",
        "birth_year": 1977,
        "birth_year_week": 8,
        "current_ability": 77,
        "potential_ability": 86,
        "potential_tier": "A",
        "career_stage": "prime",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {"technique": 77, "movement": 76, "physical": 75, "mental": 78, "consistency": 77, "clutch": 76, "recovery": 75},
        "hidden_career_traits": {"potential_ceiling": 86, "growth_curve": "steady", "professionalism": 0.8, "ambition": 0.7, "travel_tolerance": 0.6, "schedule_aggression": 0.5, "injury_proneness": 0.2, "resilience": 0.7},
        "reason": "api test",
    }


def test_custom_update_and_audit_api_workflow(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, created = call("POST", f"{server.base_url}/admin/players/custom", custom_api_payload())
        assert status == 200
        assert created["locked"] is True
        assert created["manual_override"] is True
        assert created["generation_source"] == "manual"

        status, updated = call("PATCH", f"{server.base_url}/admin/players/{created['player_id']}", {"name": "Edited API Player", "current_ability": 79, "reason": "safe edit"})
        assert status == 200
        assert updated["name"] == "Edited API Player"
        assert updated["locked"] is True
        assert updated["manual_override"] is True

        _, audit = call("GET", f"{server.base_url}/admin/players/audit?player_id={created['player_id']}")
        assert [event["action"] for event in audit["audit_events"]] == ["create_custom_player", "update_player"]
        assert "current_ability" in audit["audit_events"][-1]["changed_fields"]

        _, regenerated = call("POST", f"{server.base_url}/admin/players/initial-pool/regenerate-unlocked", {"season": "2000/2001", "seed": 17, "target_pool_size": 6, "dry_run": False})
        assert next(player for player in regenerated["players"] if player["player_id"] == created["player_id"])["name"] == "Edited API Player"

        try:
            call("POST", f"{server.base_url}/admin/players/custom", custom_api_payload())
        except Exception as exc:  # urllib raises HTTPError for non-2xx responses.
            assert getattr(exc, "code", None) == 400
        else:
            raise AssertionError("duplicate custom player_id should fail")
