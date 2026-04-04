from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app


COUNTRIES_FIXTURE = {
    "dataset_status": "temporary_seed_demo",
    "countries": [
        {
            "code": "AAA",
            "name": "Alpha",
            "flag_asset": None,
            "region": "EUROPE",
            "population": 1_000_000,
            "wealth_support": 3,
            "squash_popularity": 4,
            "squash_tradition": 2,
            "system_quality": 5,
        }
    ],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str, countries_config_path: str, manual_overrides_config_path: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(
            database_url=database_url,
            countries_config_path=countries_config_path,
            manual_player_overrides_config_path=manual_overrides_config_path,
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "ApiServer":
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                _ = _request("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _request(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return int(exc.code), parsed


def _write_fixture(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_manual_overrides_crud_and_filters(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        payload = {
            "override_id": "aaa-manual-2027",
            "season": 2027,
            "country_code": "AAA",
            "player_name": "Manual Talent",
            "age": 18,
            "profile_tier": "elite",
            "is_exceptional": True,
            "enabled": True,
            "notes": "test",
        }
        status, created = _request("POST", f"{server.base_url}/world/manual-player-overrides", payload)
        assert status == 201
        assert created["override_id"] == payload["override_id"]
        assert created["is_exceptional"] is True

        status, listing = _request("GET", f"{server.base_url}/world/manual-player-overrides?season=2027&enabled=true")
        assert status == 200
        assert len(listing["overrides"]) == 1

        updated = {**payload, "enabled": False}
        status, updated_payload = _request(
            "PUT",
            f"{server.base_url}/world/manual-player-overrides/{payload['override_id']}",
            updated,
        )
        assert status == 200
        assert updated_payload["enabled"] is False

        status, single = _request(
            "GET",
            f"{server.base_url}/world/manual-player-overrides/{payload['override_id']}",
        )
        assert status == 200
        assert single["enabled"] is False

        status, _ = _request("DELETE", f"{server.base_url}/world/manual-player-overrides/{payload['override_id']}")
        assert status == 204


def test_create_override_with_unknown_country_is_rejected(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-create-invalid-country.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/manual-player-overrides",
            {
                "override_id": "bad-country",
                "season": 2027,
                "country_code": "ZZZ",
                "player_name": "Ghost Player",
                "age": 18,
                "profile_tier": "elite",
                "enabled": True,
            },
        )
        assert status == 422
        assert "country_code 'ZZZ' does not exist in countries dataset" in payload["detail"]


def test_update_override_with_unknown_country_is_rejected(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-update-invalid-country.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        valid_payload = {
            "override_id": "valid-country",
            "season": 2027,
            "country_code": "AAA",
            "player_name": "Valid Country",
            "age": 18,
            "profile_tier": "elite",
            "enabled": True,
        }
        status, _ = _request("POST", f"{server.base_url}/world/manual-player-overrides", valid_payload)
        assert status == 201

        status, payload = _request(
            "PUT",
            f"{server.base_url}/world/manual-player-overrides/valid-country",
            {**valid_payload, "country_code": "ZZZ"},
        )
        assert status == 422
        assert "country_code 'ZZZ' does not exist in countries dataset" in payload["detail"]


def test_run_generation_provenance_exposes_manual_override_source(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(
        overrides_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2027",
                    "season": 2027,
                    "country_code": "AAA",
                    "player_name": "Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "enabled": True,
                    "is_exceptional": True,
                }
            ]
        },
    )

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-provenance.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "manual-prov", "seed": 99, "season": 2027},
        )
        assert status == 201

        status, players_payload = _request("GET", f"{server.base_url}/runs/manual-prov/world/generated-players")
        assert status == 200
        assert players_payload["players"]
        assert any(player["source_type"] == "planner_generated" for player in players_payload["players"])
        manual_rows = [player for player in players_payload["players"] if player["source_type"] == "manual_override"]
        assert len(manual_rows) == 1
        assert manual_rows[0]["override_id"] == "aaa-legend-2027"
