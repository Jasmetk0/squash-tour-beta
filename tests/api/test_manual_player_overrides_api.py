from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib import error, request

import uvicorn

from beta_engine.main import create_app
from beta_engine.domain.countries import CountriesConfig
from tests.support.world_packages import materialize_test_world_package


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
        countries = CountriesConfig.model_validate(json.loads(Path(countries_config_path).read_text(encoding="utf-8")))
        world_packages_root = Path(countries_config_path).parent / "world_packages"
        materialize_test_world_package(world_packages_root, countries)
        app = create_app(
            database_url=database_url,
            countries_config_path=countries_config_path,
            manual_player_overrides_config_path=manual_overrides_config_path,
            world_packages_root=str(world_packages_root),
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


def test_talent_plan_diagnostics_expose_exceptional_override_dampener_signal(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(
        overrides_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-legend-2026",
                    "season": 2026,
                    "country_code": "AAA",
                    "player_name": "Historic Legend",
                    "age": 19,
                    "profile_tier": "generational",
                    "enabled": True,
                    "is_exceptional": True,
                }
            ]
        },
    )

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-dampener-diag.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "manual-dampener", "seed": 99, "season": 2027},
        )
        assert status == 201

        status, plan = _request("GET", f"{server.base_url}/runs/manual-dampener/world/talent-plan")
        assert status == 200
        assert plan["countries"]
        dampener = plan["countries"][0]["dampener"]
        assert dampener["active"] is True
        assert dampener["recent_greatness_score"] > 0
        assert any(item["reference_id"] == "aaa-legend-2026" for item in dampener["contributions"])


def test_manual_overrides_export_import_and_dry_run_flow(tmp_path) -> None:
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
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-import-export.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        req = request.Request(f"{server.base_url}/world/manual-player-overrides/export", method="GET")
        with request.urlopen(req, timeout=60) as response:
            assert response.status == 200
            csv_payload = response.read().decode("utf-8")
        assert "override_id,season,country_code,player_name" in csv_payload
        assert "aaa-legend-2027" in csv_payload

        import_payload = {
            "csv_text": csv_payload.replace("Legend", "Legend Updated").replace("true,true", "false,true"),
            "dry_run": True,
        }
        status, preview = _request("POST", f"{server.base_url}/world/manual-player-overrides/import", import_payload)
        assert status == 200
        assert preview["ok"] is True
        assert preview["dry_run"] is True
        assert preview["summary"]["updated_records"] == 1

        status, listing = _request("GET", f"{server.base_url}/world/manual-player-overrides")
        assert status == 200
        assert listing["overrides"][0]["player_name"] == "Legend"

        import_payload["dry_run"] = False
        status, applied = _request("POST", f"{server.base_url}/world/manual-player-overrides/import", import_payload)
        assert status == 200
        assert applied["ok"] is True
        assert applied["dry_run"] is False

        status, listing = _request("GET", f"{server.base_url}/world/manual-player-overrides")
        assert status == 200
        assert listing["overrides"][0]["player_name"] == "Legend Updated"
        assert listing["overrides"][0]["is_exceptional"] is False


def test_manual_overrides_import_validation_and_no_partial_writes(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(
        overrides_path,
        {
            "overrides": [
                {
                    "override_id": "aaa-manual-keep",
                    "season": 2027,
                    "country_code": "AAA",
                    "player_name": "Keep",
                    "age": 18,
                    "profile_tier": "elite",
                    "enabled": True,
                    "is_exceptional": False,
                }
            ]
        },
    )

    bad_csv = """override_id,season,country_code,player_name,player_slug,player_id,age,profile_tier,quality_band_override,is_exceptional,enabled,notes,attribute_technique,attribute_movement,attribute_physical,attribute_mental,attribute_consistency,attribute_clutch,attribute_recovery,trait_potential_ceiling,trait_growth_curve,trait_professionalism,trait_ambition,trait_travel_tolerance,trait_schedule_aggression,trait_injury_proneness,trait_resilience
bad-1,2027,ZZZ,Unknown Country,,,18,elite,,true,true,,90,,,,,,,,,0.2,0.2,0.2,0.2,0.2,0.2
bad-1,2027,AAA,Duplicate ID,,,18,elite,,true,true,,90,,,,,,,,,0.2,0.2,0.2,0.2,0.2,0.2
bad-3,2027,AAA,Bad Tier,,,18,invalid_tier,,true,true,,90,,,,,,,,,0.2,0.2,0.2,0.2,0.2,0.2
bad-4,2027,AAA,Bad Range,,,18,elite,,true,true,,120,,,,,,,,,1.2,0.2,0.2,0.2,0.2,0.2
"""

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-validation.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, result = _request(
            "POST",
            f"{server.base_url}/world/manual-player-overrides/import",
            {"csv_text": bad_csv, "dry_run": False},
        )
        assert status == 200
        assert result["ok"] is False
        assert result["errors"]
        messages = [item["message"] for item in result["errors"]]
        assert any("does not exist in countries dataset" in message for message in messages)
        assert any("duplicate override_id" in message for message in messages)
        assert any("Input should be 'strong', 'elite', 'special' or 'generational'" in message for message in messages)
        assert any("less than or equal to 99" in message for message in messages)
        assert any("less than or equal to 1" in message for message in messages)

        status, listing = _request("GET", f"{server.base_url}/world/manual-player-overrides")
        assert status == 200
        assert [item["override_id"] for item in listing["overrides"]] == ["aaa-manual-keep"]


def test_manual_overrides_import_rejects_malformed_payload(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-bad-payload.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, response = _request(
            "POST",
            f"{server.base_url}/world/manual-player-overrides/import",
            {"dry_run": True},
        )
        assert status == 422
        assert response["detail"]


def test_manual_overrides_import_rejects_unparseable_csv(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "manual_overrides.json"
    _write_fixture(countries_path, COUNTRIES_FIXTURE)
    _write_fixture(overrides_path, {"overrides": []})

    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'manual-overrides-bad-csv.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
    ) as server:
        status, result = _request(
            "POST",
            f"{server.base_url}/world/manual-player-overrides/import",
            {"csv_text": 'override_id,season\n"oops', "dry_run": True},
        )
        assert status == 200
        assert result["ok"] is False
        assert result["errors"]
        assert "parseable CSV" in result["errors"][0]["message"]
