from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import pytest
import uvicorn
from pydantic import ValidationError

from beta_engine.api.country_v1_schemas import CountryV1UpsertRequest
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
            "squash_popularity": 4,
            "squash_access": 3,
            "development_quality": 5,
            "competition_quality": 4,
            "elite_support": 3,
            "squash_tradition": 2,
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


def _base_country_upsert_payload() -> dict[str, object]:
    return {
        "code": "BBB",
        "name": "Beta",
        "flag_asset": None,
        "region": "ASIA",
        "population": 2_000_000,
        "squash_popularity": 2,
        "squash_access": 2,
        "development_quality": 2,
        "competition_quality": 2,
        "elite_support": 2,
        "squash_tradition": 2,
    }


def test_country_upsert_request_accepts_default_population_year_2020() -> None:
    payload = CountryV1UpsertRequest.model_validate(
        {**_base_country_upsert_payload(), "default_population_year": 2020}
    )

    assert payload.default_population_year == 2020


def test_country_upsert_request_rejects_non_2020_default_population_year() -> None:
    with pytest.raises(ValidationError, match="default_population_year must be 2020 when provided"):
        CountryV1UpsertRequest.model_validate(
            {**_base_country_upsert_payload(), "default_population_year": 2019}
        )


def test_country_upsert_request_accepts_population_by_year_2050() -> None:
    payload = CountryV1UpsertRequest.model_validate(
        {**_base_country_upsert_payload(), "population_by_year": {"2050": 123_456_789}}
    )

    assert payload.population_by_year == {2050: 123_456_789}


def test_country_upsert_request_rejects_population_by_year_2051() -> None:
    with pytest.raises(ValidationError, match="population_by_year years must be between 1955 and 2050"):
        CountryV1UpsertRequest.model_validate(
            {**_base_country_upsert_payload(), "population_by_year": {"2051": 123_456_789}}
        )


def test_country_upsert_request_rejects_default_population_year_2050() -> None:
    with pytest.raises(ValidationError, match="default_population_year must be 2020 when provided"):
        CountryV1UpsertRequest.model_validate(
            {**_base_country_upsert_payload(), "default_population_year": 2050}
        )


def test_list_countries_endpoint(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-list.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request("GET", f"{server.base_url}/world/countries")
        assert status == 200
        country = payload["countries"][0]
        assert country["code"] == "AAA"
        assert country["squash_access"] == 3
        assert country["development_quality"] == 5
        assert country["competition_quality"] == 4
        assert country["elite_support"] == 3
        assert country["court_count"] is None
        assert "wealth_support" not in country
        assert "style_dna" not in country
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
                **_base_country_upsert_payload(),
                "competition_quality": 5,
                "elite_support": 4,
                "court_count": 80,
            },
        )
        assert status == 201
        assert created["code"] == "BBB"
        assert created["competition_quality"] == 5
        assert created["elite_support"] == 4
        assert created["court_count"] == 80
        assert "style_dna" not in created

    persisted = json.loads(countries_path.read_text(encoding="utf-8"))
    beta = next(country for country in persisted["countries"] if country["code"] == "BBB")
    assert beta["competition_quality"] == 5
    assert beta["elite_support"] == 4
    assert beta["court_count"] == 80
    assert "wealth_support" not in beta
    assert "style_dna" not in beta


def test_reject_duplicate_country_code(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-duplicate.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries",
            {**_base_country_upsert_payload(), "code": "AAA", "name": "Again Alpha"},
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
            {**_base_country_upsert_payload(), "code": "BAD", "name": "Bad", "squash_access": 9},
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
                **COUNTRIES_FIXTURE["countries"][0],
                "name": "Alpha Updated",
                "flag_asset": "flags/aaa.svg",
                "population": 1_500_000,
                "elite_support": 4,
            },
        )
        assert status == 200
        assert payload["name"] == "Alpha Updated"
        assert payload["elite_support"] == 4


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
        assert "code,name,flag_asset,region,population,squash_popularity,squash_access,development_quality,competition_quality,elite_support,squash_tradition" in body
        assert "court_count,travel_region,notes" in body
        assert "wealth_support" not in body
        assert "style_dna" not in body
        assert "AAA,Alpha" in body


def test_import_countries_csv_replaces_dataset(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    csv_text = (
        "code,name,flag_asset,region,population,squash_popularity,squash_access,development_quality,competition_quality,elite_support,squash_tradition,court_count,travel_region,notes\n"
        "BBB,Beta,,ASIA,2000000,3,4,4,5,4,2,200,,Imported\n"
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
    assert persisted["countries"][0]["competition_quality"] == 5
    assert persisted["countries"][0]["elite_support"] == 4
    assert persisted["countries"][0]["court_count"] == 200
    assert "wealth_support" not in persisted["countries"][0]


def test_import_rejects_duplicate_code_and_does_not_partially_write(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    _write_fixture(countries_path)
    before = countries_path.read_text(encoding="utf-8")
    csv_text = (
        "code,name,flag_asset,region,population,squash_popularity,squash_access,development_quality,competition_quality,elite_support,squash_tradition,court_count,travel_region,notes\n"
        "BBB,Beta,,ASIA,2000000,3,4,4,5,4,2,200,,First\n"
        "BBB,Beta Again,,ASIA,2100000,3,4,4,5,4,2,201,,Duplicate\n"
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
        "code,name,flag_asset,region,population,squash_popularity,squash_access,development_quality,competition_quality,elite_support,squash_tradition\n"
        "BBB,Beta,,ASIA,2000000,3,9,4,4,4,2\n"
    )

    with ApiServer(database_url=f"sqlite:///{tmp_path / 'countries-import-factors.db'}", countries_config_path=str(countries_path)) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/countries/import",
            {"csv_text": csv_text, "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is False
        assert payload["errors"][0]["field"] == "squash_access"


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
