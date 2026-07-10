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

OVERRIDES_FIXTURE = {
    "overrides": [
        {
            "override_id": "aaa-manual-2027",
            "season": 2027,
            "country_code": "AAA",
            "player_name": "Manual Talent",
            "age": 18,
            "profile_tier": "elite",
            "enabled": True,
            "is_exceptional": False,
        }
    ]
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


def _request_raw(method: str, url: str) -> tuple[int, str]:
    req = request.Request(url, method=method)
    with request.urlopen(req, timeout=60) as response:
        return response.status, response.read().decode("utf-8")


def _write_fixture(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_export_returns_world_package(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-export.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, body = _request_raw("GET", f"{server.base_url}/world/package/export")
        assert status == 200
        package = json.loads(body)
        assert package["package_version"] == "1"
        assert package["countries_dataset"]["countries"][0]["code"] == "AAA"
        assert package["manual_player_overrides_dataset"]["overrides"][0]["override_id"] == "aaa-manual-2027"


def test_valid_package_dry_run_succeeds(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    package = {
        "package_version": "1",
        "countries_dataset": {
            "dataset_status": "temporary_seed_demo",
            "countries": [{**COUNTRIES_FIXTURE["countries"][0], "name": "Alpha Updated"}],
        },
        "manual_player_overrides_dataset": OVERRIDES_FIXTURE,
    }

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-dry-run.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": json.dumps(package), "dry_run": True},
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["dry_run"] is True
        assert payload["countries_summary"]["updated_records"] == 1


def test_apply_replaces_both_datasets(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    package = {
        "package_version": "1",
        "countries_dataset": {
            "dataset_status": "variant_a",
            "countries": [
                {
                    "code": "BBB",
                    "name": "Beta",
                    "flag_asset": None,
                    "region": "ASIA",
                    "population": 2_000_000,
                    "wealth_support": 4,
                    "squash_popularity": 3,
                    "squash_tradition": 2,
                    "system_quality": 4,
                }
            ],
        },
        "manual_player_overrides_dataset": {
            "overrides": [
                {
                    "override_id": "bbb-manual-2027",
                    "season": 2027,
                    "country_code": "BBB",
                    "player_name": "Beta Talent",
                    "age": 19,
                    "profile_tier": "strong",
                    "enabled": True,
                    "is_exceptional": False,
                }
            ]
        },
    }

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-apply.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": json.dumps(package), "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["dry_run"] is False

    persisted_countries = json.loads(countries_path.read_text(encoding="utf-8"))
    persisted_overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    assert [item["code"] for item in persisted_countries["countries"]] == ["BBB"]
    assert [item["override_id"] for item in persisted_overrides["overrides"]] == ["bbb-manual-2027"]


def test_invalid_package_version_rejected(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    package = {
        "package_version": "999",
        "countries_dataset": COUNTRIES_FIXTURE,
        "manual_player_overrides_dataset": OVERRIDES_FIXTURE,
    }

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-invalid-version.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": json.dumps(package), "dry_run": True},
        )
        assert status == 200
        assert payload["ok"] is False
        assert "unsupported package_version" in payload["errors"][0]["message"]


def test_malformed_json_rejected(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-malformed.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": "{bad json", "dry_run": True},
        )
        assert status == 200
        assert payload["ok"] is False
        assert "not parseable JSON" in payload["errors"][0]["message"]


def test_override_country_must_exist_in_imported_countries(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    package = {
        "package_version": "1",
        "countries_dataset": COUNTRIES_FIXTURE,
        "manual_player_overrides_dataset": {
            "overrides": [
                {
                    "override_id": "bad-country",
                    "season": 2027,
                    "country_code": "ZZZ",
                    "player_name": "Ghost",
                    "age": 18,
                    "profile_tier": "elite",
                    "enabled": True,
                    "is_exceptional": False,
                }
            ]
        },
    }

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-country-ref.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": json.dumps(package), "dry_run": True},
        )
        assert status == 200
        assert payload["ok"] is False
        assert "does not exist in imported countries_dataset" in payload["errors"][0]["message"]


def test_invalid_package_does_not_partially_write(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    countries_before = countries_path.read_text(encoding="utf-8")
    overrides_before = overrides_path.read_text(encoding="utf-8")

    package = {
        "package_version": "1",
        "countries_dataset": {
            "dataset_status": "broken",
            "countries": [{**COUNTRIES_FIXTURE["countries"][0], "wealth_support": 9}],
        },
        "manual_player_overrides_dataset": OVERRIDES_FIXTURE,
    }

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-no-partial.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/package/import",
            {"package_text": json.dumps(package), "dry_run": False},
        )
        assert status == 200
        assert payload["ok"] is False

    assert countries_path.read_text(encoding="utf-8") == countries_before
    assert overrides_path.read_text(encoding="utf-8") == overrides_before


def test_world_packages_registry_lists_built_in_official_package(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-list.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages")
        assert status == 200
        assert len(payload["packages"]) == 1
        package = payload["packages"][0]
        assert package["world_id"] == "official_fax_world"
        assert package["name"] == "Official FAX World"
        assert package["description"] == "Built-in official FAX squash world package."
        assert package["type"] == "official"
        assert package["status"] == "active"
        assert package["source"] == "built_in"
        assert package["editable"] is False
        assert package["deletable"] is False
        assert package["archivable"] is False
        assert package["version"] == "v1"
        assert package["country_count"] == 5
        assert package["manual_override_count"] == 1
        assert package["continent_count"] == 6
        assert package["region_count"] == 5
        assert package["travel_region_count"] == 5
        assert package["used_by_run_count"] is None
        assert package["validation_status"] == "valid"
        assert package["storage"] == {
            "countries_path": "config/worlds/official_fax_world/countries.json",
            "manual_player_overrides_path": str(overrides_path),
            "world_metadata_path": "config/worlds/official_fax_world/world.json",
            "continents_path": "config/worlds/official_fax_world/continents.json",
            "regions_path": "config/worlds/official_fax_world/regions.json",
            "travel_regions_path": "config/worlds/official_fax_world/travel_regions.json",
        }
        assert isinstance(package["fingerprint"], str)
        assert len(package["fingerprint"]) == 64


def test_world_packages_registry_detail_and_deterministic_fingerprint(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-detail.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, list_payload = _request("GET", f"{server.base_url}/world/packages")
        assert status == 200
        list_fingerprint = list_payload["packages"][0]["fingerprint"]

        status, detail = _request("GET", f"{server.base_url}/world/packages/official_fax_world")
        assert status == 200
        assert detail["world_id"] == "official_fax_world"
        assert detail["fingerprint"] == list_fingerprint
        assert detail["source"] == "built_in"
        assert detail["storage"]["world_metadata_path"] == "config/worlds/official_fax_world/world.json"

        status, detail_again = _request("GET", f"{server.base_url}/world/packages/official_fax_world")
        assert status == 200
        assert detail_again["fingerprint"] == list_fingerprint


def test_world_packages_registry_unknown_world_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-unknown.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/unknown")
        assert status == 404
        assert "not found" in payload["detail"]


def test_world_packages_registry_does_not_change_existing_world_package_export(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-export-compat.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        registry_status, registry_payload = _request("GET", f"{server.base_url}/world/packages")
        assert registry_status == 200
        assert registry_payload["packages"][0]["world_id"] == "official_fax_world"

        status, body = _request_raw("GET", f"{server.base_url}/world/package/export")
        assert status == 200
        package = json.loads(body)
        assert package["package_version"] == "1"
        assert "exported_at" in package
        assert package["countries_dataset"]["countries"][0]["code"] == "AAA"
        assert package["manual_player_overrides_dataset"]["overrides"][0]["override_id"] == "aaa-manual-2027"
