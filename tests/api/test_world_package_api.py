from __future__ import annotations

import json
import shutil
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
    def __init__(self, *, database_url: str, countries_config_path: str, manual_overrides_config_path: str, worlds_root: str | None = None) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(
            database_url=database_url,
            countries_config_path=countries_config_path,
            manual_player_overrides_config_path=manual_overrides_config_path,
            worlds_root=worlds_root,
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



def _copy_worlds_root(tmp_path: Path) -> Path:
    worlds_root = tmp_path / "worlds"
    shutil.copytree(Path("config/worlds/official_fax_world"), worlds_root / "official_fax_world")
    return worlds_root


def _write_custom_world(root: Path, world_id: str = "my_custom_world", *, malformed: bool = False) -> Path:
    package_dir = root / "custom" / world_id
    package_dir.mkdir(parents=True, exist_ok=True)
    if malformed:
        (package_dir / "world.json").write_text("{not-json", encoding="utf-8")
        return package_dir
    _write_fixture(package_dir / "world.json", {
        "world_id": world_id,
        "name": "My Custom World",
        "description": "Custom world package.",
        "type": "custom",
        "status": "active",
        "source": "custom_config",
        "editable": True,
        "deletable": True,
        "archivable": True,
        "version": "v1",
        "content_schema_version": "1",
    })
    _write_fixture(package_dir / "continents.json", {"continents": [{"code": "EU", "name": "Europe"}]})
    _write_fixture(package_dir / "regions.json", {"regions": [{"code": "EUROPE", "name": "Europe", "continent_code": "EU"}]})
    _write_fixture(package_dir / "travel_regions.json", {"travel_regions": [{"code": "WEST", "name": "West"}]})
    _write_fixture(package_dir / "countries.json", {
        "dataset_status": "temporary_test_custom_world",
        "countries": [
            {"code": "AAA", "name": "Alpha", "flag_asset": None, "region": "EUROPE", "travel_region": "WEST", "population": 1_000_000, "wealth_support": 3, "squash_popularity": 4, "squash_tradition": 2, "system_quality": 5},
            {"code": "BBB", "name": "Beta", "flag_asset": None, "region": "EUROPE", "travel_region": "WEST", "population": 2_000_000, "wealth_support": 4, "squash_popularity": 3, "squash_tradition": 3, "system_quality": 4},
        ],
    })
    return package_dir

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



def test_world_package_countries_returns_official_package_countries_without_canonical_fallback(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-countries-official.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries")

    official_config = json.loads(Path("config/worlds/official_fax_world/countries.json").read_text(encoding="utf-8"))
    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["world_name"] == "Official FAX World"
    assert payload["type"] == "official"
    assert payload["source"] == "built_in"
    assert payload["read_only"] is True
    assert payload["country_count"] == 4
    assert payload["country_count"] == len(official_config["countries"])
    assert payload["source_path"] == "config/worlds/official_fax_world/countries.json"
    assert [country["code"] for country in payload["countries"]] == ["GER", "BOG", "HUN", "POL"]
    assert [country["name"] for country in payload["countries"]] == ["Germanica", "Bogemia", "Hungarica", "Polandia"]
    assert all(country["code"] != "AAA" for country in payload["countries"])
    for country in payload["countries"]:
        assert country["area_km2"] is not None
        assert country["default_population_year"] == 2020
        assert country["default_population"] == country["population"]
        assert country["population_by_year"] == {"2020": country["population"]}


def test_world_package_countries_returns_custom_package_countries(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    _write_custom_world(worlds_root)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-countries-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/my_custom_world/countries")

    assert status == 200
    assert payload["world_id"] == "my_custom_world"
    assert payload["world_name"] == "My Custom World"
    assert payload["type"] == "custom"
    assert payload["source"] == "custom_config"
    assert payload["read_only"] is True
    assert payload["country_count"] == 2
    assert payload["source_path"].endswith("worlds/custom/my_custom_world/countries.json")
    assert [country["code"] for country in payload["countries"]] == ["AAA", "BBB"]


def test_world_package_countries_unknown_world_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-countries-unknown.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/unknown/countries")

    assert status == 404
    assert "not found" in payload["detail"]


def test_world_package_effective_population_official_ger_1987_uses_nearest_2020(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-1987.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER/effective-population?year=1987")

    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["world_name"] == "Official FAX World"
    assert payload["type"] == "official"
    assert payload["source"] == "built_in"
    assert payload["read_only"] is True
    assert payload["country_code"] == "GER"
    assert payload["country_name"] == "Germanica"
    assert payload["requested_year"] == 1987
    assert payload["effective_population"] == 169702055
    assert payload["source_type"] == "nearest_population_year"
    assert payload["source_year"] == 2020
    assert payload["is_estimated"] is True
    assert payload["default_population_year"] == 2020
    assert payload["default_population"] == 169702055
    assert payload["legacy_population"] == 169702055
    assert payload["population_by_year_count"] == 1
    assert payload["usable_population_by_year_count"] == 1


def test_world_package_effective_population_official_ger_2020_uses_exact_population_year(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-2020.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER/effective-population?year=2020")

    assert status == 200
    assert payload["country_code"] == "GER"
    assert payload["requested_year"] == 2020
    assert payload["effective_population"] == 169702055
    assert payload["source_type"] == "exact_population_year"
    assert payload["source_year"] == 2020
    assert payload["is_estimated"] is False


def test_world_package_effective_population_normalizes_lowercase_country_code(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-lowercase.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/ger/effective-population?year=2020")

    assert status == 200
    assert payload["country_code"] == "GER"


def test_world_package_effective_population_unknown_country_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-unknown-country.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/ZZZ/effective-population?year=2020")

    assert status == 404
    assert "country 'ZZZ' not found" in payload["detail"]


def test_world_package_effective_population_unknown_world_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-unknown-world.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/unknown/countries/GER/effective-population?year=2020")

    assert status == 404
    assert "world package 'unknown' not found" in payload["detail"]


def test_world_package_effective_population_accepts_2050_as_nearest_2020_for_official_ger(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-2050.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER/effective-population?year=2050")

    assert status == 200
    assert payload["requested_year"] == 2050
    assert payload["effective_population"] == 169_702_055
    assert payload["source_type"] == "nearest_population_year"
    assert payload["source_year"] == 2020
    assert payload["is_estimated"] is True


def test_world_package_effective_population_rejects_year_below_range(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-year-low.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER/effective-population?year=1954")

    assert status == 422
    assert payload["detail"]


def test_world_package_effective_population_rejects_year_above_range(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-year-high.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER/effective-population?year=2051")

    assert status == 422
    assert payload["detail"]


def test_world_package_effective_population_uses_custom_package_country_data(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    custom_dir = _write_custom_world(worlds_root)
    custom_countries = json.loads((custom_dir / "countries.json").read_text(encoding="utf-8"))
    custom_countries["countries"][0]["population"] = 1_000_000
    custom_countries["countries"][0]["default_population"] = 1_500_000
    custom_countries["countries"][0]["default_population_year"] = 2020
    custom_countries["countries"][0]["population_by_year"] = {"1980": 900_000, "2000": 1_200_000}
    _write_fixture(custom_dir / "countries.json", custom_countries)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-package-effective-population-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/my_custom_world/countries/AAA/effective-population?year=1987")

    assert status == 200
    assert payload["world_id"] == "my_custom_world"
    assert payload["country_code"] == "AAA"
    assert payload["effective_population"] == 900_000
    assert payload["source_type"] == "nearest_population_year"
    assert payload["source_year"] == 1980
    assert payload["legacy_population"] == 1_000_000
    assert payload["default_population"] == 1_500_000
    assert payload["population_by_year_count"] == 2
    assert payload["usable_population_by_year_count"] == 2

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
        assert package["country_count"] == 4
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

def test_world_packages_registry_lists_official_when_custom_root_missing(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-no-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages")

    assert status == 200
    assert [package["world_id"] for package in payload["packages"]] == ["official_fax_world"]


def test_world_packages_registry_discovers_custom_world_read_only(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    custom_dir = _write_custom_world(worlds_root)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages")
        detail_status, detail = _request("GET", f"{server.base_url}/world/packages/my_custom_world")

    assert status == 200
    assert [package["world_id"] for package in payload["packages"]] == ["official_fax_world", "my_custom_world"]
    custom = payload["packages"][1]
    assert detail_status == 200
    assert detail == custom
    assert custom["type"] == "custom"
    assert custom["status"] == "active"
    assert custom["source"] == "custom_config"
    assert custom["editable"] is True
    assert custom["deletable"] is True
    assert custom["archivable"] is True
    assert custom["country_count"] == 2
    assert custom["manual_override_count"] == 0
    assert custom["continent_count"] == 1
    assert custom["region_count"] == 1
    assert custom["travel_region_count"] == 1
    assert custom["used_by_run_count"] is None
    assert custom["storage"]["world_metadata_path"] == str(custom_dir / "world.json")
    assert custom["storage"]["countries_path"] == str(custom_dir / "countries.json")
    assert isinstance(custom["fingerprint"], str)
    assert __import__("re").fullmatch(r"[0-9a-f]{64}", custom["fingerprint"])


def test_world_packages_registry_malformed_custom_world_does_not_break_official(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    _write_custom_world(worlds_root, "broken_custom", malformed=True)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-malformed-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages")

    assert status == 200
    assert [package["world_id"] for package in payload["packages"]] == ["official_fax_world"]


def test_world_package_validation_supports_custom_world(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    _write_custom_world(worlds_root)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-custom-validation.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/my_custom_world/validation")

    assert status == 200
    assert payload["world_id"] == "my_custom_world"
    assert payload["status"] == "valid"
    assert payload["error_count"] == 0
    assert {check["code"] for check in payload["checks"]} >= {"world_metadata_valid", "countries_valid", "registry_consistency_valid"}


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


def test_world_package_validation_for_official_fax_world_returns_health(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    package_paths = [
        "config/worlds/official_fax_world/world.json",
        "config/worlds/official_fax_world/countries.json",
        "config/worlds/official_fax_world/continents.json",
        "config/worlds/official_fax_world/regions.json",
        "config/worlds/official_fax_world/travel_regions.json",
    ]
    before = {path: Path(path).read_bytes() for path in package_paths}

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-validation.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/validation")

    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["status"] in {"valid", "warnings"}
    assert payload["error_count"] == 0
    assert payload["warning_count"] >= 0
    assert payload["info_count"] > 0
    assert {check["code"] for check in payload["checks"]} >= {
        "world_metadata_valid",
        "countries_valid",
        "continents_valid",
        "regions_valid",
        "travel_regions_valid",
        "registry_consistency_valid",
    }
    assert all(Path(path).read_bytes() == contents for path, contents in before.items())


def test_world_package_validation_unknown_world_returns_404(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-validation-unknown.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/unknown/validation")
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


def test_clone_official_world_dry_run_does_not_write_target(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-clone-dry-run.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/packages/official_fax_world/clone",
            {"new_world_id": "dry_run_world", "name": "Dry Run World", "description": "Preview clone.", "dry_run": True},
        )

    assert status == 200
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["source_world_id"] == "official_fax_world"
    assert payload["new_world_id"] == "dry_run_world"
    assert payload["created_files"] == ["world.json", "countries.json", "continents.json", "regions.json", "travel_regions.json"]
    assert payload["package"] is None
    assert payload["validation"] is None
    assert payload["errors"] == []
    assert not (worlds_root / "custom" / "dry_run_world").exists()


def test_clone_official_world_actual_creates_discoverable_custom_world(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    target_dir = worlds_root / "custom" / "actual_world"

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-clone-actual.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/packages/official_fax_world/clone",
            {"new_world_id": "actual_world", "name": "Actual World", "description": "Cloned world.", "dry_run": False},
        )
        list_status, list_payload = _request("GET", f"{server.base_url}/world/packages")
        detail_status, detail = _request("GET", f"{server.base_url}/world/packages/actual_world")
        validation_status, validation = _request("GET", f"{server.base_url}/world/packages/actual_world/validation")

    assert status == 200
    assert payload["ok"] is True
    assert payload["dry_run"] is False
    assert payload["package"]["world_id"] == "actual_world"
    assert payload["package"]["manual_override_count"] == 0
    assert payload["validation"]["error_count"] == 0
    assert target_dir.is_dir()
    for filename in ["world.json", "countries.json", "continents.json", "regions.json", "travel_regions.json"]:
        assert (target_dir / filename).is_file()
    metadata = json.loads((target_dir / "world.json").read_text(encoding="utf-8"))
    assert metadata == {
        "world_id": "actual_world",
        "name": "Actual World",
        "description": "Cloned world.",
        "type": "custom",
        "status": "active",
        "source": "custom_config",
        "editable": True,
        "deletable": True,
        "archivable": True,
        "version": "v1",
        "content_schema_version": "1",
        "cloned_from_world_id": "official_fax_world",
    }
    for filename in ["countries.json", "continents.json", "regions.json", "travel_regions.json"]:
        assert (target_dir / filename).read_text(encoding="utf-8") == (worlds_root / "official_fax_world" / filename).read_text(encoding="utf-8")
    cloned_countries = json.loads((target_dir / "countries.json").read_text(encoding="utf-8"))["countries"]
    assert [country["code"] for country in cloned_countries] == ["GER", "BOG", "HUN", "POL"]
    assert cloned_countries[0]["area_km2"] == 870516
    assert cloned_countries[0]["population_by_year"] == {"2020": 169702055}
    assert list_status == 200
    assert [package["world_id"] for package in list_payload["packages"]] == ["official_fax_world", "actual_world"]
    assert detail_status == 200
    assert detail["world_id"] == "actual_world"
    assert detail["type"] == "custom"
    assert validation_status == 200
    assert validation["error_count"] == 0


def test_clone_official_world_duplicate_invalid_official_id_and_missing_name_rejected(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    existing_dir = _write_custom_world(worlds_root, "existing_world")
    before = (existing_dir / "world.json").read_text(encoding="utf-8")

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'world-packages-clone-rejected.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        duplicate_status, duplicate = _request("POST", f"{server.base_url}/world/packages/official_fax_world/clone", {"new_world_id": "existing_world", "name": "Duplicate", "dry_run": False})
        invalid_status, invalid = _request("POST", f"{server.base_url}/world/packages/official_fax_world/clone", {"new_world_id": "Bad/World", "name": "Invalid", "dry_run": False})
        official_status, official = _request("POST", f"{server.base_url}/world/packages/official_fax_world/clone", {"new_world_id": "official_fax_world", "name": "Official", "dry_run": False})
        missing_name_status, missing_name = _request("POST", f"{server.base_url}/world/packages/official_fax_world/clone", {"new_world_id": "missing_name_world", "name": "", "dry_run": False})

    assert duplicate_status == 200
    assert duplicate["ok"] is False
    assert (existing_dir / "world.json").read_text(encoding="utf-8") == before
    assert invalid_status == 200
    assert invalid["ok"] is False
    assert not (worlds_root / "custom" / "Bad/World").exists()
    assert official_status == 200
    assert official["ok"] is False
    assert missing_name_status == 422 or missing_name["ok"] is False
    assert not (worlds_root / "custom" / "missing_name_world").exists()


def test_clone_official_world_filesystem_failure_cleans_temporary_package(tmp_path, monkeypatch) -> None:
    from beta_engine.application.countries_service import CountriesConfigService
    from beta_engine.application.manual_player_overrides_service import ManualPlayerOverridesService
    from beta_engine.application.world_package_clone_service import WorldPackageCloneService
    from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
    from beta_engine.application.world_package_validation_service import WorldPackageValidationService

    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    worlds_root = _copy_worlds_root(tmp_path)
    registry = WorldPackageRegistryService(
        countries_service=CountriesConfigService(config_path=countries_path),
        manual_overrides_service=ManualPlayerOverridesService(config_path=overrides_path),
        worlds_root=worlds_root,
    )
    service = WorldPackageCloneService(registry_service=registry, validation_service=WorldPackageValidationService(registry_service=registry))

    def fail_copy(*args, **kwargs):
        raise OSError("forced copy failure")

    monkeypatch.setattr("beta_engine.application.world_package_clone_service.shutil.copy2", fail_copy)
    result = service.clone_official_world(new_world_id="failed_world", name="Failed World", description=None, dry_run=False)

    assert result.ok is False
    assert "forced copy failure" in result.errors[0].message
    assert not (worlds_root / "custom" / "failed_world").exists()
    assert not list((worlds_root / "custom").glob(".failed_world.tmp-*"))


def test_world_package_weekly_intake_preview_success_for_official_world(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-preview.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?season=2000/2001&season_week=1&target_intake_count=10")

    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["world_name"] == "Official FAX World"
    assert payload["season"] == "2000/2001"
    assert payload["season_start_year"] == 2000
    assert payload["season_week"] == 1
    assert payload["calendar_year"] == 2000
    assert payload["year_week"] == 37
    assert payload["birth_year"] == 1985
    assert payload["birth_year_week"] == 37
    assert payload["intake_age"] == 15
    assert payload["target_intake_count"] == 10
    assert payload["total_allocated"] == 10
    assert payload["allocations"]
    assert sum(row["allocated_count"] for row in payload["allocations"]) == 10
    assert {"population_source_type", "population_source_year", "is_population_estimated"} <= set(payload["allocations"][0])


def test_world_package_weekly_intake_preview_calendar_boundaries(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    expected = {1: (37, 1985), 25: (61, 1985), 26: (1, 1986), 61: (36, 1986)}

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-boundaries.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        for season_week, (year_week, birth_year) in expected.items():
            status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?season=2000/2001&season_week={season_week}&target_intake_count=1")
            assert status == 200
            assert payload["year_week"] == year_week
            assert payload["birth_year"] == birth_year
            assert payload["birth_year_week"] == year_week


def test_world_package_weekly_intake_preview_validation_and_errors(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-errors.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        for query in [
            "season=2000/2001&season_week=0&target_intake_count=1",
            "season=2000/2001&season_week=62&target_intake_count=1",
            "season=2000/2001&season_week=1&target_intake_count=-1",
        ]:
            status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?{query}")
            assert status == 422
            assert payload["detail"]

        status, payload = _request("GET", f"{server.base_url}/world/packages/unknown/weekly-intake/preview?season=2000/2001&season_week=1&target_intake_count=1")
        assert status == 404
        assert "world package 'unknown' not found" in payload["detail"]

        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?season=2000/2001&season_week=1&target_intake_count=1&country_code=ZZZ")
        assert status == 404
        assert "no matching countries" in payload["detail"]


def test_world_package_weekly_intake_preview_filters_and_is_read_only(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    package_path = Path("config/worlds/official_fax_world/countries.json")
    before = package_path.read_text(encoding="utf-8")

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-filters.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?season=2000/2001&season_week=1&target_intake_count=10&country_code=ger")
        region_status, region_payload = _request("GET", f"{server.base_url}/world/packages/official_fax_world/weekly-intake/preview?season=2000/2001&season_week=1&target_intake_count=10&region=EUROPE")

    assert status == 200
    assert [row["country_code"] for row in payload["allocations"]] == ["GER"]
    assert payload["total_allocated"] == 10
    assert region_status == 200
    assert {row["country_code"] for row in region_payload["allocations"]} == {"BOG", "GER", "HUN", "POL"}
    assert package_path.read_text(encoding="utf-8") == before
