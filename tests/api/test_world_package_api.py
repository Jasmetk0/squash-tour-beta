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
from beta_engine.domain.countries import CountriesConfig
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.application.world_package_registry_service import REQUIRED_WORLD_PACKAGE_FILES
from tests.support.world_packages import load_fax_reference_countries, materialize_test_world_package
from tests.support.fax_reference import compute_source_tree_hash

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
            world_packages_root=worlds_root,
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
    worlds_root = tmp_path / "world_packages"
    shutil.copytree(Path("config/world_packages/official_fax_world"), worlds_root / "official_fax_world")
    return worlds_root


def _write_custom_world(root: Path, world_id: str = "my_custom_world", *, malformed: bool = False) -> Path:
    package_dir = root / "custom" / world_id
    package_dir.mkdir(parents=True, exist_ok=True)
    if malformed:
        (package_dir / "world.json").write_text("{not-json", encoding="utf-8")
        return package_dir
    package_dir = materialize_test_world_package(root / "custom", CountriesConfig.model_validate({
        "dataset_status": "temporary_test_custom_world",
        "countries": [
            {"code": "AAA", "name": "Alpha", "flag_asset": None, "region": "EUROPE", "travel_region": "WEST", "population": 1_000_000, "wealth_support": 3, "squash_popularity": 4, "squash_tradition": 2, "system_quality": 5},
            {"code": "BBB", "name": "Beta", "flag_asset": None, "region": "EUROPE", "travel_region": "WEST", "population": 2_000_000, "wealth_support": 4, "squash_popularity": 3, "squash_tradition": 3, "system_quality": 4},
        ],
    }), world_id=world_id, editable=True)
    metadata = json.loads((package_dir / "world.json").read_text(encoding="utf-8"))
    metadata.update({"name": "My Custom World", "description": "Custom world package.", "version": "v1"})
    _write_fixture(package_dir / "world.json", metadata)
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


def _country_update_payload(detail: dict[str, object]) -> dict[str, object]:
    country = detail["country"]
    assert isinstance(country, dict)
    return {key: country[key] for key in (
        "name", "notes", "area_km2", "region", "travel_region", "wealth_support",
        "squash_popularity", "squash_tradition", "system_quality",
        "competition_density", "federation_quality", "court_count", "style_dna",
    )}


def _country_create_payload(fingerprint: str) -> dict[str, object]:
    return {
        "code": "ABC", "name": "Alphabetia", "notes": "New country", "area_km2": 12_345,
        "region": "EUROPE", "travel_region": "EUROPE", "wealth_support": 3,
        "squash_popularity": 2, "squash_tradition": 1, "system_quality": 4,
        "competition_density": 2.5, "federation_quality": 3.5, "court_count": 12,
        "style_dna": {"pace": 1.25}, "population_by_year": {"1995": 900_000, "2020": 1_200_000},
        "expected_package_fingerprint": fingerprint,
    }


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

    official_config = load_fax_reference_countries()
    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["world_name"] == "Official FAX World"
    assert payload["type"] == "official"
    assert payload["source"] == "built_in"
    assert payload["read_only"] is True
    assert payload["country_count"] == 4
    assert payload["country_count"] == len(official_config.countries)
    assert payload["source_path"] == "config/world_packages/official_fax_world/countries/index.json"
    assert [country["code"] for country in payload["countries"]] == ["BOG", "GER", "HUN", "POL"]
    assert [country["name"] for country in payload["countries"]] == ["Bogemia", "Germanica", "Hungarica", "Polandia"]
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
    assert payload["read_only"] is False
    assert payload["country_count"] == 2
    assert payload["source_path"].endswith("world_packages/custom/my_custom_world/countries/index.json")
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
    custom_store = WorldPackageCountryStore(custom_dir)
    country = custom_store.load_country("AAA").model_copy(update={
        "population": 1_000_000,
        "default_population": 1_500_000,
        "default_population_year": 2020,
        "population_by_year": {1980: 900_000, 2000: 1_200_000, 2020: 1_500_000},
    })
    custom_store.write_country(country)

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
    assert payload["legacy_population"] == 1_500_000
    assert payload["default_population"] == 1_500_000
    assert payload["population_by_year_count"] == 3
    assert payload["usable_population_by_year_count"] == 3

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
        assert len(payload["packages"]) == 2
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
        assert package["continent_count"] == 6
        assert package["region_count"] == 5
        assert package["travel_region_count"] == 5
        assert package["used_by_run_count"] is None
        assert package["validation_status"] == "valid"
        assert package["storage"] == {
            "package_root_path": "config/world_packages/official_fax_world",
            "world_metadata_path": "config/world_packages/official_fax_world/world.json",
            "countries_root_path": "config/world_packages/official_fax_world/countries",
            "countries_index_path": "config/world_packages/official_fax_world/countries/index.json",
            "geography_root_path": "config/world_packages/official_fax_world/geography",
            "continents_path": "config/world_packages/official_fax_world/geography/continents.json",
            "regions_path": "config/world_packages/official_fax_world/geography/regions.json",
            "travel_regions_path": "config/world_packages/official_fax_world/geography/travel_regions.json",
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
    assert custom["continent_count"] == 1
    assert custom["region_count"] == 1
    assert custom["travel_region_count"] == 1
    assert custom["used_by_run_count"] is None
    assert custom["storage"]["world_metadata_path"] == str(custom_dir / "world.json")
    assert custom["storage"]["countries_index_path"] == str(custom_dir / "countries/index.json")
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
    assert {check["code"] for check in payload["checks"]} >= {"world_metadata_valid", "countries_index_valid", "country_orphans_valid"}


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
        assert detail["storage"]["world_metadata_path"] == "config/world_packages/official_fax_world/world.json"

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

    package_root = Path("config/world_packages/official_fax_world")
    before = compute_source_tree_hash(package_root)

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
        "countries_index_valid",
        "country_orphans_valid",
    }
    assert compute_source_tree_hash(package_root) == before


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
    assert payload["created_files"] == list(REQUIRED_WORLD_PACKAGE_FILES)
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
    assert payload["validation"]["error_count"] == 0
    assert target_dir.is_dir()
    for filename in REQUIRED_WORLD_PACKAGE_FILES:
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
        "package_format_version": "world_package_directory.v1",
        "cloned_from_world_id": "official_fax_world",
    }
    cloned_countries = WorldPackageCountryStore(target_dir).load_config().countries
    assert [country.code for country in cloned_countries] == ["BOG", "GER", "HUN", "POL"]
    germanica = next(country for country in cloned_countries if country.code == "GER")
    assert germanica.area_km2 == 870516
    assert germanica.population_by_year == {2020: 169702055}
    assert WorldPackageCountryStore(target_dir).semantic_payload() == WorldPackageCountryStore(worlds_root / "official_fax_world").semantic_payload()
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


def test_real_world_clone_is_not_supported(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'real-world-clone-rejected.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "POST",
            f"{server.base_url}/world/packages/real_world/clone",
            {"new_world_id": "real_copy", "name": "Real Copy", "dry_run": False},
        )

    assert status == 404
    assert "clone is not supported" in payload["detail"]


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
        world_packages_root=worlds_root,
    )
    service = WorldPackageCloneService(registry_service=registry, validation_service=WorldPackageValidationService(registry_service=registry))

    def fail_copy(*args, **kwargs):
        raise OSError("forced copy failure")

    monkeypatch.setattr(WorldPackageCloneService, "_write_clone_files", fail_copy)
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
    package_path = Path("config/world_packages/official_fax_world/countries/index.json")
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


def test_world_package_weekly_intake_season_schedule_preview_success(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    package_path = Path("config/world_packages/official_fax_world/countries/index.json")
    before = package_path.read_text(encoding="utf-8")

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-season-schedule.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001",
        )
        final_status, final_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2049/2050",
        )
        max_growth_status, max_growth_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001&season_growth_rate=0.10",
        )

    assert status == 200
    assert payload["world_id"] == "official_fax_world"
    assert payload["world_name"] == "Official FAX World"
    assert payload["season"] == "2000/2001"
    assert payload["season_start_year"] == 2000
    assert payload["season_index"] == 0
    assert payload["annual_target"] > 0
    assert payload["total_weekly_target"] == payload["annual_target"]
    assert len(payload["weeks"]) == 61
    assert payload["weeks"][0]["season_week"] == 1
    assert payload["weeks"][0]["year_week"] == 37
    assert payload["weeks"][0]["birth_year"] == 1985
    assert payload["weeks"][25]["season_week"] == 26
    assert payload["weeks"][25]["year_week"] == 1
    assert payload["weeks"][25]["birth_year"] == 1986
    assert all(week["target_intake_count"] >= 0 for week in payload["weeks"])
    assert final_status == 200
    assert final_payload["season"] == "2049/2050"
    assert final_payload["season_start_year"] == 2049
    assert final_payload["season_index"] == 49
    assert len(final_payload["weeks"]) == 61
    assert final_payload["total_weekly_target"] == final_payload["annual_target"]
    assert max_growth_status == 200
    assert max_growth_payload["season_growth_rate"] == 0.10
    assert len(max_growth_payload["weeks"]) == 61
    assert max_growth_payload["total_weekly_target"] == max_growth_payload["annual_target"]
    assert package_path.read_text(encoding="utf-8") == before


def test_world_package_weekly_intake_season_schedule_preview_errors_and_custom_targets(tmp_path) -> None:
    countries_path = tmp_path / "canonical-countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'weekly-intake-season-schedule-custom.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        missing_status, missing_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/unknown/weekly-intake/season-schedule/preview?season=2000/2001",
        )
        custom_status, custom_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001&base_annual_intake_target=200",
        )
        zero_status, zero_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001&base_annual_intake_target=0",
        )
        before_registry_status, before_registry_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=1999/2000",
        )
        after_registry_status, after_registry_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2050/2051",
        )
        high_growth_status, high_growth_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001&season_growth_rate=0.11",
        )
        negative_growth_status, negative_growth_payload = _request(
            "GET",
            f"{server.base_url}/world/packages/official_fax_world/weekly-intake/season-schedule/preview?season=2000/2001&season_growth_rate=-0.01",
        )

    assert missing_status == 404
    assert "world package 'unknown' not found" in missing_payload["detail"]
    assert custom_status == 200
    assert custom_payload["base_annual_intake_target"] == 200
    assert custom_payload["annual_target"] > 0
    assert zero_status == 200
    assert zero_payload["annual_target"] == 0
    assert zero_payload["total_weekly_target"] == 0
    assert all(week["target_intake_count"] == 0 for week in zero_payload["weeks"])
    assert before_registry_status == 422
    assert "outside the supported season registry" in before_registry_payload["detail"]
    assert after_registry_status == 422
    assert "outside the supported season registry" in after_registry_payload["detail"]
    assert high_growth_status == 422
    assert high_growth_payload["detail"]
    assert negative_growth_status == 422
    assert negative_growth_payload["detail"]


def test_canonical_world_package_countries_api_reports_source_editability(tmp_path) -> None:
    from beta_engine.application.world_package_clone_service import WorldPackageCloneService
    from beta_engine.application.world_package_registry_service import WorldPackageRegistryService
    from beta_engine.application.world_package_validation_service import WorldPackageValidationService

    packages_root = tmp_path / "world_packages"
    shutil.copytree("config/world_packages/official_fax_world", packages_root / "official_fax_world")
    shutil.copytree("config/world_packages/real_world", packages_root / "real_world")
    registry = WorldPackageRegistryService(world_packages_root=packages_root)
    clone = WorldPackageCloneService(registry, WorldPackageValidationService(registry)).clone_official_world(
        new_world_id="editable_world", name="Editable World", description=None, dry_run=False
    )
    assert clone.ok

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'canonical-world-package-api.db'}",
        countries_config_path=str(tmp_path / "unused-countries.json"),
        manual_overrides_config_path=str(tmp_path / "unused-overrides.json"),
        worlds_root=str(packages_root),
    ) as server:
        official_status, official = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries")
        custom_status, custom = _request("GET", f"{server.base_url}/world/packages/editable_world/countries")
        custom_detail_status, custom_detail = _request(
            "GET", f"{server.base_url}/world/packages/editable_world/countries/GER"
        )

    assert official_status == 200
    assert official["read_only"] is True
    assert official["source_path"].endswith("countries/index.json")
    assert custom_status == 200
    assert custom["read_only"] is False
    assert custom["country_count"] == official["country_count"]
    assert custom_detail_status == 200
    assert custom_detail["package"]["world_id"] == "editable_world"
    assert custom_detail["package"]["editable"] is True
    assert custom_detail["country"]["name"] == "Germanica"


def test_world_package_country_detail_and_geography_are_typed_and_package_scoped(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'explorer.db'}", countries_config_path=str(countries_path), manual_overrides_config_path=str(overrides_path)) as server:
        status, detail = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/GER")
        geography_status, geography = _request("GET", f"{server.base_url}/world/packages/official_fax_world/geography")
        missing_country_status, _ = _request("GET", f"{server.base_url}/world/packages/official_fax_world/countries/ZZZ")
        missing_world_status, _ = _request("GET", f"{server.base_url}/world/packages/unknown/countries/GER")
    assert status == 200
    assert detail["package"]["name"] == "Official FAX World"
    assert detail["country"]["name"] == "Germanica"
    assert detail["country"]["population"] == 169702055
    assert detail["country"]["population_by_year"] == {"2020": 169702055}
    assert detail["region"] == {"code": "EUROPE", "name": "Europe", "continent_code": "EUR"}
    assert detail["continent"] == {"code": "EUR", "name": "Europe"}
    assert geography_status == 200
    assert any(item == {"code": "EUR", "name": "Europe"} for item in geography["continents"])
    assert missing_country_status == 404
    assert missing_world_status == 404


def test_real_world_country_detail_preserves_authored_population_timeline(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, OVERRIDES_FIXTURE)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'real-explorer.db'}", countries_config_path=str(countries_path), manual_overrides_config_path=str(overrides_path)) as server:
        status, detail = _request("GET", f"{server.base_url}/world/packages/real_world/countries/DEU")
    assert status == 200
    timeline = detail["country"]["population_by_year"]
    assert len(timeline) == 96
    assert "1955" in timeline and "2050" in timeline


def test_put_custom_country_persists_edit_and_preserves_population_and_index(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE)
    worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'edit.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        clone_status,_=_request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        assert clone_status==200
        _,before=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
        payload=_country_update_payload(before); payload.update({'name':'Germanica Prime','squash_popularity':4,'style_dna':{'pace':1.25},'expected_package_fingerprint':before['package']['fingerprint']})
        package_root=worlds_root/'custom/editable'; population=(package_root/'countries/GER/attributes/population.json').read_bytes(); index=(package_root/'countries/index.json').read_bytes()
        status,response=_request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',payload)
        get_status,after=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert status==200 and get_status==200
    assert response['package']['fingerprint']!=before['package']['fingerprint']
    assert response['validation']['status']!='errors' and response['validation']['error_count']==0
    assert (after['country']['code'],after['country']['name'],after['country']['squash_popularity'],after['country']['style_dna'])==('GER','Germanica Prime',4,{'pace':1.25})
    assert after['country']['population_by_year']==before['country']['population_by_year']
    assert (package_root/'countries/GER/attributes/population.json').read_bytes()==population
    assert (package_root/'countries/index.json').read_bytes()==index


def test_put_builtin_countries_is_forbidden_without_filesystem_changes(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE)
    worlds_root=tmp_path/'world_packages'
    for world_id in ('official_fax_world','real_world'): shutil.copytree(Path('config/world_packages')/world_id,worlds_root/world_id)
    before={world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in ('official_fax_world','real_world')}
    with ApiServer(database_url=f"sqlite:///{tmp_path/'builtins.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        for world_id,code in (('official_fax_world','GER'),('real_world','DEU')):
            _,detail=_request('GET',f'{server.base_url}/world/packages/{world_id}/countries/{code}')
            status,_=_request('PUT',f'{server.base_url}/world/packages/{world_id}/countries/{code}',_country_update_payload(detail))
            assert status==403
    assert {world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in before}==before


def test_put_country_rejects_unknown_invalid_and_protected_state_without_mutation(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'invalid.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        _,detail=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); valid=_country_update_payload(detail)
        package_root=worlds_root/'custom/editable'; original=compute_source_tree_hash(package_root)
        assert _request('PUT',f'{server.base_url}/world/packages/unknown/countries/GER',valid)[0]==404
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/ZZZ',valid)[0]==404
        invalid_cases=(('squash_popularity',6),('competition_density',0.9),('court_count',-1),('area_km2',0),('region','UNKNOWN'),('travel_region','UNKNOWN'))
        for field,value in invalid_cases:
            assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',{**valid,field:value})[0]==422
        for field,value in (('code','ZZZ'),('population',1),('population_by_year',{'2020':1}),('default_population',1),('default_population_year',2020)):
            assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',{**valid,field:value})[0]==422
        _,unchanged=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert unchanged['country']==detail['country'] and compute_source_tree_hash(package_root)==original


def test_put_country_rejects_stale_package_fingerprint(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'stale.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        _,detail=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); old=detail['package']['fingerprint']; first={**_country_update_payload(detail),'name':'First','expected_package_fingerprint':old}
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',first)[0]==200
        stale={**first,'name':'Stale overwrite'}
        status,_=_request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',stale)
        _,after=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert status==409 and after['country']['name']=='First'


def test_put_custom_population_adds_edits_removes_and_materializes_2020(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'population.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        assert _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})[0]==200
        _,before=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); old_2020=before['country']['population_by_year']['2020']; new_2020=old_2020+123
        status,response=_request('PUT',f'{server.base_url}/world/packages/editable/countries/GER/population',{'values_by_year':{'1995':120_000_000,'2020':new_2020},'expected_package_fingerprint':before['package']['fingerprint']})
        _,after=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
        assert status==200 and response['validation']['error_count']==0
        assert after['country']['population_by_year']=={'1995':120_000_000,'2020':new_2020}
        assert after['country']['population']==after['country']['default_population']==new_2020 and after['country']['default_population_year']==2020
        assert after['package']['fingerprint']!=before['package']['fingerprint']
        fingerprint=after['package']['fingerprint']
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER/population',{'values_by_year':{'1995':121_000_000,'2020':new_2020},'expected_package_fingerprint':fingerprint})[0]==200
        _,non_default=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
        assert non_default['country']['population_by_year']['1995']==121_000_000
        assert non_default['country']['population_by_year']['2020']==new_2020 and non_default['country']['population']==non_default['country']['default_population']==new_2020
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER/population',{'values_by_year':{'2020':new_2020},'expected_package_fingerprint':non_default['package']['fingerprint']})[0]==200
        _,removed=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert '1995' not in removed['country']['population_by_year']


def test_put_population_rejects_invalid_protected_unknown_builtin_and_stale(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    shutil.copytree(Path('config/world_packages/real_world'),worlds_root/'real_world')
    builtins={world_id:{path.relative_to(worlds_root/world_id):path.read_bytes() for path in (worlds_root/world_id).rglob('*') if path.is_file()} for world_id in ('official_fax_world','real_world')}
    with ApiServer(database_url=f"sqlite:///{tmp_path/'population-invalid.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        assert _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})[0]==200
        _,detail=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); original=detail['country']['population_by_year']; fingerprint=detail['package']['fingerprint']; url=f'{server.base_url}/world/packages/editable/countries/GER/population'
        invalid=({'1995':1},{'1954':1,'2020':2},{'2020':2,'2051':1},{'2020':0},{'2020':-1},{'2020':1.5},{'2020':True},{'2020':'text'},{'2020':'123'})
        for timeline in invalid: assert _request('PUT',url,{'values_by_year':timeline,'expected_package_fingerprint':fingerprint})[0]==422
        for field in ('code','name','region','squash_popularity','default_year'):
            assert _request('PUT',url,{'values_by_year':original,field:'forbidden'})[0]==422
        assert _request('PUT',f'{server.base_url}/world/packages/unknown/countries/GER/population',{'values_by_year':original})[0]==404
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/ZZZ/population',{'values_by_year':original})[0]==404
        for world_id,code in (('official_fax_world','GER'),('real_world','DEU')):
            assert _request('PUT',f'{server.base_url}/world/packages/{world_id}/countries/{code}/population',{'values_by_year':{'2020':1}})[0]==403
        country_payload=_country_update_payload(detail); country_payload.update(name='Newer source',expected_package_fingerprint=fingerprint)
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',country_payload)[0]==200
        assert _request('PUT',url,{'values_by_year':{'2020':999},'expected_package_fingerprint':fingerprint})[0]==409
        _,unchanged=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert unchanged['country']['population_by_year']==original
    assert {world_id:{path.relative_to(worlds_root/world_id):path.read_bytes() for path in (worlds_root/world_id).rglob('*') if path.is_file()} for world_id in builtins}==builtins


def test_put_population_semantic_noop_preserves_fingerprint_and_all_bytes(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'population-noop.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        _,before=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); root=worlds_root/'custom/editable'; tree=compute_source_tree_hash(root); population=(root/'countries/GER/attributes/population.json').read_bytes()
        status,response=_request('PUT',f'{server.base_url}/world/packages/editable/countries/GER/population',{'values_by_year':before['country']['population_by_year'],'expected_package_fingerprint':before['package']['fingerprint']})
    assert status==200 and response['package']['fingerprint']==before['package']['fingerprint']
    assert compute_source_tree_hash(root)==tree and (root/'countries/GER/attributes/population.json').read_bytes()==population


def test_country_create_http_roundtrips_authored_state_and_rejects_duplicate(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'create-country.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        assert _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})[0]==200
        _,package=_request('GET',f'{server.base_url}/world/packages/editable'); before=package['fingerprint']; payload=_country_create_payload(before)
        status,response=_request('POST',f'{server.base_url}/world/packages/editable/countries',payload)
        get_status,detail=_request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')
        _,countries=_request('GET',f'{server.base_url}/world/packages/editable/countries')
        duplicate_status,_=_request('POST',f'{server.base_url}/world/packages/editable/countries',{**payload,'expected_package_fingerprint':response['package']['fingerprint']})
        _,unchanged=_request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')
    assert status==201 and get_status==200 and response['country_detail']['country']['code']=='ABC'
    country=detail['country']; assert country['name']=='Alphabetia' and country['notes']=='New country' and country['style_dna']=={'pace':1.25}
    assert country['population_by_year']=={'1995':900_000,'2020':1_200_000} and len(country['population_by_year'])==2
    assert country['population']==country['default_population']==1_200_000 and country['default_population_year']==2020
    assert [item['code'] for item in countries['countries']].count('ABC')==1
    assert response['package']['fingerprint']!=before and response['validation']['error_count']==0
    assert duplicate_status==409 and unchanged['country']==country


def test_country_create_http_rejects_invalid_contract_without_mutation(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path)
    with ApiServer(database_url=f"sqlite:///{tmp_path/'invalid-create.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        _,package=_request('GET',f'{server.base_url}/world/packages/editable'); valid=_country_create_payload(package['fingerprint']); root=worlds_root/'custom/editable'; original=compute_source_tree_hash(root)
        for code in ('AB','ABCD','A1C','A-C','abc',' ABC','ABC '): assert _request('POST',f'{server.base_url}/world/packages/editable/countries',{**valid,'code':code})[0]==422
        for field,value in (('area_km2',0),('wealth_support',6),('competition_density',0.9),('court_count',-1),('region','UNKNOWN'),('travel_region','UNKNOWN')):
            assert _request('POST',f'{server.base_url}/world/packages/editable/countries',{**valid,field:value})[0]==422
        invalid_timelines=({'1995':1},{'1954':1,'2020':2},{'2020':2,'2051':1},{'2020':0},{'2020':-1},{'2020':1.5},{'2020':True},{'2020':'123'})
        for timeline in invalid_timelines: assert _request('POST',f'{server.base_url}/world/packages/editable/countries',{**valid,'population_by_year':timeline})[0]==422
        for field in ('population','default_population','default_population_year','flag_asset'):
            assert _request('POST',f'{server.base_url}/world/packages/editable/countries',{**valid,field:1})[0]==422
        assert _request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')[0]==404
    assert compute_source_tree_hash(root)==original


def test_country_create_http_forbids_builtins_and_stale_fingerprint(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path); shutil.copytree('config/world_packages/real_world',worlds_root/'real_world')
    before={world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in ('official_fax_world','real_world')}
    with ApiServer(database_url=f"sqlite:///{tmp_path/'guard-create.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        for world_id in before:
            _,package=_request('GET',f'{server.base_url}/world/packages/{world_id}'); assert _request('POST',f'{server.base_url}/world/packages/{world_id}/countries',_country_create_payload(package['fingerprint']))[0]==403
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False})
        _,detail=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER'); old=detail['package']['fingerprint']; update={**_country_update_payload(detail),'name':'Changed','expected_package_fingerprint':old}
        assert _request('PUT',f'{server.base_url}/world/packages/editable/countries/GER',update)[0]==200
        assert _request('POST',f'{server.base_url}/world/packages/editable/countries',_country_create_payload(old))[0]==409
        assert _request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')[0]==404
    assert {world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in before}==before


def test_country_delete_http_success_unknown_builtin_and_stale(tmp_path) -> None:
    countries_path=tmp_path/'countries.json'; overrides_path=tmp_path/'overrides.json'; _write_fixture(countries_path,COUNTRIES_FIXTURE); _write_fixture(overrides_path,OVERRIDES_FIXTURE); worlds_root=_copy_worlds_root(tmp_path); shutil.copytree('config/world_packages/real_world',worlds_root/'real_world')
    builtins={world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in ('official_fax_world','real_world')}
    with ApiServer(database_url=f"sqlite:///{tmp_path/'delete-country.db'}",countries_config_path=str(countries_path),manual_overrides_config_path=str(overrides_path),worlds_root=str(worlds_root)) as server:
        _request('POST',f'{server.base_url}/world/packages/official_fax_world/clone',{'new_world_id':'editable','name':'Editable','dry_run':False}); _,package=_request('GET',f'{server.base_url}/world/packages/editable')
        _,created=_request('POST',f'{server.base_url}/world/packages/editable/countries',_country_create_payload(package['fingerprint'])); fingerprint=created['package']['fingerprint']; _,ger_before=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
        assert _request('DELETE',f'{server.base_url}/world/packages/editable/countries/ABC?expected_package_fingerprint=stale')[0]==409
        _,abc_before=_request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')
        assert _request('DELETE',f'{server.base_url}/world/packages/editable/countries/ZZZ?expected_package_fingerprint={fingerprint}')[0]==404
        assert _request('DELETE',f'{server.base_url}/world/packages/unknown/countries/ABC?expected_package_fingerprint={fingerprint}')[0]==404
        for world_id,code in (('official_fax_world','GER'),('real_world','DEU')):
            _,builtin=_request('GET',f'{server.base_url}/world/packages/{world_id}'); assert _request('DELETE',f"{server.base_url}/world/packages/{world_id}/countries/{code}?expected_package_fingerprint={builtin['fingerprint']}")[0]==403
        status,response=_request('DELETE',f'{server.base_url}/world/packages/editable/countries/ABC?expected_package_fingerprint={fingerprint}')
        assert _request('GET',f'{server.base_url}/world/packages/editable/countries/ABC')[0]==404
        _,countries=_request('GET',f'{server.base_url}/world/packages/editable/countries'); _,ger_after=_request('GET',f'{server.base_url}/world/packages/editable/countries/GER')
    assert abc_before['country']['code']=='ABC' and status==200 and response['deleted_country_code']=='ABC'
    assert response['package']['fingerprint']!=fingerprint and response['validation']['error_count']==0
    assert 'ABC' not in [item['code'] for item in countries['countries']] and ger_after['country']==ger_before['country']
    assert {world_id:compute_source_tree_hash(worlds_root/world_id) for world_id in builtins}==builtins
