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


def _request_raw(method: str, url: str) -> tuple[int, str]:
    req = request.Request(url, method=method)
    try:
        with request.urlopen(req, timeout=60) as response:
            return response.status, response.read().decode("utf-8")
    except error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8")


def _write_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(COUNTRIES_FIXTURE, indent=2) + "\n", encoding="utf-8")


def test_list_countries_endpoint(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-list.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request("GET", f"{server.base_url}/world/countries")
        assert status == 200
        assert payload["countries"][0]["code"] == "AAA"
        assert payload["countries"][0]["competition_density"] == 3.0
        assert payload["countries"][0]["federation_quality"] == 5.0
        assert payload["countries"][0]["court_count"] is None
        assert payload["countries"][0]["style_dna"] == {}
        status, meta = _request("GET", f"{server.base_url}/world/countries/metadata")
        assert status == 200
        assert meta["dataset_status"] == "temporary_seed_demo"
        assert meta["country_count"] == 1


def test_create_country_and_persist_write_back(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-create.db'}", countries_config_path=str(countries_path)) as server:
        status, created = _request(
            "POST",
            f"{server.base_url}/world/countries",
            {
                "code": "BBB",
                "name": "Beta",
                "flag_asset": None,
                "region": "ASIA",
                "population": 2_000_000,
                "wealth_support": 2,
                "squash_popularity": 2,
                "squash_tradition": 2,
                "system_quality": 2,
                "competition_density": 4.5,
                "federation_quality": 4.0,
                "court_count": 80,
                "style_dna": {"attrition": 0.25},
            },
        )
        assert status == 201
        assert created["code"] == "BBB"
        assert created["competition_density"] == 4.5
        assert created["federation_quality"] == 4.0
        assert created["court_count"] == 80
        assert created["style_dna"] == {"attrition": 0.25}

    persisted = json.loads(countries_path.read_text(encoding="utf-8"))
    beta = next(country for country in persisted["countries"] if country["code"] == "BBB")
    assert beta["competition_density"] == 4.5
    assert beta["federation_quality"] == 4.0
    assert beta["court_count"] == 80
    assert beta["style_dna"] == {"attrition": 0.25}


def test_reject_duplicate_country_code(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-duplicate.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries",
            {
                "code": "AAA",
                "name": "Again Alpha",
                "flag_asset": None,
                "region": "EUROPE",
                "population": 1_100_000,
                "wealth_support": 3,
                "squash_popularity": 3,
                "squash_tradition": 3,
                "system_quality": 3,
            },
        )
        assert status == 409
        assert "already exists" in payload["detail"]


def test_reject_invalid_factor_range(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-invalid.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries",
            {
                "code": "BAD",
                "name": "Bad",
                "flag_asset": None,
                "region": "EUROPE",
                "population": 1_000_000,
                "wealth_support": 9,
                "squash_popularity": 3,
                "squash_tradition": 3,
                "system_quality": 3,
            },
        )
        assert status == 422
        assert payload["detail"]


def test_update_country(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-update.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "PUT",
            f"{server.base_url}/world/countries/AAA",
            {
                "code": "AAA",
                "name": "Alpha Updated",
                "flag_asset": "flags/aaa.svg",
                "region": "EUROPE",
                "population": 1_500_000,
                "wealth_support": 4,
                "squash_popularity": 4,
                "squash_tradition": 3,
                "system_quality": 4,
            },
        )
        assert status == 200
        assert payload["name"] == "Alpha Updated"


def test_delete_country(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-delete.db'}", countries_config_path=str(countries_path)) as server:
        status, _ = _request("DELETE", f"{server.base_url}/world/countries/AAA")
        assert status == 204

        status, payload = _request("GET", f"{server.base_url}/world/countries")
        assert status == 200
        assert payload["countries"] == []


def test_export_countries_csv(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-export.db'}", countries_config_path=str(countries_path)) as server:
        status, body = _request_raw("GET", f"{server.base_url}/world/countries/export")
        assert status == 200
        assert "code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality" in body
        assert "competition_density,federation_quality,court_count" in body
        assert "AAA,Alpha" in body


def test_import_countries_csv_replaces_dataset(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    csv_text = (
        "code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality,competition_density,federation_quality,court_count\n"
        "BBB,Beta,,ASIA,2000000,4,3,2,4,4.5,4,200\n"
    )

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-import.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries/import",
            {"csv_text": csv_text, "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["summary"]["total_records"] == 1

    persisted = json.loads(countries_path.read_text(encoding="utf-8"))
    assert [country["code"] for country in persisted["countries"]] == ["BBB"]
    assert persisted["countries"][0]["competition_density"] == 4.5
    assert persisted["countries"][0]["federation_quality"] == 4.0
    assert persisted["countries"][0]["court_count"] == 200


def test_import_rejects_duplicate_code_and_does_not_partially_write(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    before = countries_path.read_text(encoding="utf-8")
    csv_text = (
        "code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality,competition_density,federation_quality,court_count\n"
        "BBB,Beta,,ASIA,2000000,4,3,2,4,4.5,4,200\n"
        "BBB,Beta Again,,ASIA,2100000,4,3,2,4\n"
    )

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-import-dup.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries/import",
            {"csv_text": csv_text, "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is False
        assert "duplicate code 'BBB'" in payload["errors"][0]["message"]

    assert countries_path.read_text(encoding="utf-8") == before


def test_import_rejects_invalid_factor_range(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    csv_text = (
        "code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality\n"
        "BBB,Beta,,ASIA,2000000,9,3,2,4\n"
    )

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-import-factors.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries/import",
            {"csv_text": csv_text, "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is False
        assert payload["errors"][0]["field"] == "wealth_support"


def test_import_rejects_malformed_payload(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    malformed = "code,name\nAAA,Alpha\n"

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-import-malformed.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries/import",
            {"csv_text": malformed, "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is False
        assert "missing required columns" in payload["errors"][0]["message"]
