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
            "population": 10_000_000,
            "wealth_support": 5,
            "squash_popularity": 5,
            "squash_tradition": 4,
            "system_quality": 5,
        },
        {
            "code": "BBB",
            "name": "Beta",
            "flag_asset": None,
            "region": "ASIA",
            "population": 80_000_000,
            "wealth_support": 2,
            "squash_popularity": 2,
            "squash_tradition": 2,
            "system_quality": 2,
        },
    ],
}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str, countries_config_path: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=database_url, countries_config_path=countries_config_path)
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


def _write_fixture(path: Path, payload: dict[str, object] = COUNTRIES_FIXTURE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_single_year_preview_is_deterministic_for_same_seed_and_year(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'preview.db'}", countries_config_path=str(countries_path)) as server:
        status_left, left = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")
        status_right, right = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")

    assert status_left == 200
    assert status_right == 200
    assert left == right
    assert left["total_talents"] == sum(item["planned_count"] for item in left["countries"])
    assert "dampener" in left["countries"][0]
    assert left["countries"][0]["dampener"]["active"] is False


def test_multi_year_summary_aggregates_counts_and_rates(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'summary.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request("GET", f"{server.base_url}/world/talent-class/summary?year_start=2030&years=5&seed=77")

    assert status == 200
    assert payload["years"] == 5
    assert payload["total_talents_across_span"] > 0
    assert payload["average_total_talents_per_year"] > 0
    assert payload["total_talents_across_span"] == sum(item["total_planned_talents"] for item in payload["countries"])
    assert sum(payload["global_band_totals"].values()) == payload["total_talents_across_span"]


def test_preview_reflects_current_countries_config(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'reflect.db'}", countries_config_path=str(countries_path)) as server:
        _, before = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")
        updated = dict(COUNTRIES_FIXTURE)
        updated["countries"] = [
            *COUNTRIES_FIXTURE["countries"],
            {
                "code": "CCC",
                "name": "Gamma",
                "flag_asset": None,
                "region": "AFRICA",
                "population": 30_000_000,
                "wealth_support": 3,
                "squash_popularity": 3,
                "squash_tradition": 3,
                "system_quality": 3,
            },
        ]
        _write_fixture(countries_path, updated)
        _, after = _request("GET", f"{server.base_url}/world/talent-class/preview?year=2030&seed=123")

    assert before["country_count"] == 2
    assert after["country_count"] == 3
    assert len(after["countries"]) == 3
    assert any(country["country_code"] == "CCC" for country in after["countries"])


def test_preview_rejects_invalid_query_params(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'invalid.db'}", countries_config_path=str(countries_path)) as server:
        status_preview, payload_preview = _request("GET", f"{server.base_url}/world/talent-class/preview?year=bad&seed=1")
        status_summary, payload_summary = _request("GET", f"{server.base_url}/world/talent-class/summary?year_start=2030&years=0")

    assert status_preview == 422
    assert payload_preview["detail"]
    assert status_summary == 422
    assert payload_summary["detail"]
