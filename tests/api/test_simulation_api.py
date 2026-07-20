from __future__ import annotations

from collections import Counter
import json
import socket
import threading
import time
from urllib import error, request

import uvicorn
from sqlalchemy import create_engine, text

from beta_engine.main import create_app
from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import CountryTalentModel
from beta_engine.domain.players import AnnualTalentClassPlanner, PlayerGenerator
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config
from beta_engine.infrastructure.db.repositories import RunProspectRecord, SimulationPersistenceRepository, deterministic_prospect_id
from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class ApiServer:
    def __init__(self, *, database_url: str) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        app = create_app(database_url=database_url)
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



def _insert_api_test_prospect(database_url: str, *, run_id: str, country_code: str = "EGY", season_week: int = 3) -> str:
    engine = create_sqlite_engine(DatabaseSettings(url=database_url))
    repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
    prospect_id = deterministic_prospect_id(
        run_id=run_id, world_id="official_fax_world", season_start_year=2027, season_week=season_week, country_code=country_code, local_sequence=1, profile_version="prospect_profile_v1", cohort_policy_version="intake_volume_v1"
    )
    repository.upsert_run_prospects([RunProspectRecord(
        prospect_id=prospect_id, run_id=run_id, world_id="official_fax_world", season_start_year=2027, season_label="2027/2028", season_week=season_week, calendar_year=2027, year_week=10, birth_year=2012, birth_year_week=10, age=15, country_code=country_code, country_name="Egypt", status="prospect", source_type="weekly_15yo_cohort", cohort_policy_version="intake_volume_v1", profile_version="prospect_profile_v1", first_name=None, last_name=None, display_name=f"{country_code} Prospect 0001", short_name=None, identity_seed="identity", profile_seed="profile", development_seed="development", potential_seed="potential", trait_seed="trait", profile_json={"foundation": True}, development_json={}, potential_json={"reserved": True}, trait_json={}
    )])
    return prospect_id

def _request(
    method: str,
    url: str,
    payload: dict[str, object] | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, method=method)
    req.add_header("content-type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        parsed = json.loads(raw) if raw else {}
        return int(exc.code), parsed


def test_run_container_endpoints_follow_legacy_run_creation_without_changing_runs(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'run-container-api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, empty = _request("GET", f"{server.base_url}/run-containers")
        assert status == 200
        assert empty == {"run_containers": []}

        status, legacy_run = _request(
            "POST", f"{server.base_url}/runs", {"run_id": "save/a #1", "seed": 123, "season": 2027}
        )
        assert status == 201
        assert legacy_run["run_id"] == "save/a #1"

        status, containers = _request("GET", f"{server.base_url}/run-containers")
        assert status == 200
        assert containers["run_containers"][0]["run_id"] == "save/a #1"
        assert containers["run_containers"][0]["mapped_simulation_run_count"] == 1

        status, detail = _request("GET", f"{server.base_url}/run-containers/save%2Fa%20%231")
        assert status == 200
        assert detail["world_id"] == "official_fax_world"

        status, missing = _request("GET", f"{server.base_url}/run-containers/not-found")
        assert status == 404
        assert "not found" in missing["detail"]

        status, runs = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert runs["runs"][0]["run_id"] == "save/a #1"


def _generated_player_ids(*, season: int, seed: int) -> list[str]:
    countries = load_countries_config().countries
    plan = AnnualTalentClassPlanner().plan(year=season, seed=seed, countries=countries)
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    countries_by_code = {country.code: country for country in countries}
    ids: list[str] = []
    for allocation in plan.allocations:
        country = countries_by_code[allocation.country_code]
        for talent in allocation.talents:
            ids.append(
                generator.generate_from_talent_seed(
                    country=country,
                    sequence=talent.sequence,
                    talent_seed_value=talent.seed_value,
                    quality_band=talent.quality_band,
                    bias_profile=allocation.bias_profile,
                ).player_id
            )
    return ids


def test_preflight_options_request_succeeds_for_health_endpoint(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-cors-health.db'}"
    with ApiServer(database_url=database_url) as server:
        req = request.Request(f"{server.base_url}/health", method="OPTIONS")
        req.add_header("Origin", "http://localhost:5173")
        req.add_header("Access-Control-Request-Method", "GET")
        with request.urlopen(req, timeout=60) as response:
            assert response.status == 200
            assert response.headers["access-control-allow-origin"] == "http://localhost:5173"



def test_run_world_id_create_read_and_index_contract(tmp_path) -> None:
    db_path = tmp_path / "world-lock-api.db"
    with ApiServer(database_url=f"sqlite:///{db_path}") as server:
        status, created = _request("POST", f"{server.base_url}/runs", {"run_id": "run-world-lock", "seed": 4242, "season": 2027})
        assert status == 201
        assert created["world_id"] == "official_fax_world"

        status, detail = _request("GET", f"{server.base_url}/runs/run-world-lock")
        assert status == 200
        assert detail["run"]["world_id"] == "official_fax_world"

        status, index = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert index["runs"][0]["world_id"] == "official_fax_world"


def test_run_world_id_validation_contract(tmp_path) -> None:
    db_path = tmp_path / "world-lock-validation-api.db"
    with ApiServer(database_url=f"sqlite:///{db_path}") as server:
        status, created = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-world-official", "seed": 4243, "season": 2027, "world_id": "official_fax_world"},
        )
        assert status == 201
        assert created["world_id"] == "official_fax_world"

        status, unknown = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-world-unknown", "seed": 4244, "season": 2027, "world_id": "missing_world"},
        )
        assert status == 400
        assert "world package 'missing_world' was not found" in unknown["detail"]

def test_run_initialization_and_state_fetch_work(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-init.db'}"
    with ApiServer(database_url=database_url) as server:
        status, run_payload = _request(
            "POST",
            f"{server.base_url}/runs",
            {
                "run_id": "run-init",
                "seed": 1001,
                "season": 2027,
                "config_version": "mvp",
                "config_fingerprint": "cfg-a",
            },
        )
        assert status == 201
        assert run_payload["run_id"] == "run-init"
        assert run_payload["next_event_index"] == 0

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-init")
        assert status == 200
        assert state_payload["season_state"]["next_event_index"] == 0
        assert len(state_payload["season_state"]["ordered_events"]) > 0


def test_run_world_generation_endpoints_return_persisted_plan_and_provenance(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-world-generation.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-gen", "seed": 1001, "season": 2027, "config_version": "mvp", "config_fingerprint": "cfg-1"},
        )
        assert status == 201

        status, plan_payload = _request("GET", f"{server.base_url}/runs/run-gen/world/talent-plan")
        assert status == 200
        assert plan_payload["run_id"] == "run-gen"
        assert plan_payload["seed"] == 1001
        assert plan_payload["total_talents"] > 0
        assert plan_payload["countries"]
        assert sum(country["planned_count"] for country in plan_payload["countries"]) == plan_payload["total_talents"]
        assert "dampener" in plan_payload["countries"][0]

        status, players_payload = _request("GET", f"{server.base_url}/runs/run-gen/world/generated-players")
        assert status == 200
        assert players_payload["run_id"] == "run-gen"
        assert players_payload["players"]
        assert len(players_payload["players"]) == plan_payload["total_talents"]

        sample = players_payload["players"][0]
        assert sample["origin_source_type"] == "planner_generated"
        assert sample["origin_quality_band"] == sample["quality_band"]
        assert sample["origin_season"] == sample["season"]
        status, player_detail = _request(
            "GET",
            f"{server.base_url}/runs/run-gen/world/generated-players/{sample['player_id']}",
        )
        assert status == 200
        assert player_detail["player_id"] == sample["player_id"]
        assert player_detail["quality_band"] == sample["quality_band"]
        assert player_detail["origin_source_type"] == sample["origin_source_type"]

        status, filtered = _request(
            "GET",
            f"{server.base_url}/runs/run-gen/world/generated-players?country_code={sample['country_code']}&quality_band={sample['quality_band']}&limit=5",
        )
        assert status == 200
        assert len(filtered["players"]) <= 5
        assert filtered["players"]
        assert all(player["country_code"] == sample["country_code"] for player in filtered["players"])
        assert all(player["quality_band"] == sample["quality_band"] for player in filtered["players"])


def test_run_players_explorer_endpoints_support_filters_and_detail(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-players.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-players", "seed": 4242, "season": 2027},
        )
        assert status == 201

        status, payload = _request("GET", f"{server.base_url}/runs/run-players/players?limit=30&offset=0")
        assert status == 200
        assert payload["run_id"] == "run-players"
        assert payload["total"] >= len(payload["players"]) > 0
        assert payload["limit"] == 30
        assert payload["offset"] == 0

        sample = payload["players"][0]
        status, country_filtered = _request(
            "GET",
            f"{server.base_url}/runs/run-players/players?country_code={sample['country_code']}",
        )
        assert status == 200
        assert country_filtered["players"]
        assert all(player["country_code"] == sample["country_code"] for player in country_filtered["players"])

        status, source_filtered = _request(
            "GET",
            f"{server.base_url}/runs/run-players/players?source_type={sample['source_type']}",
        )
        assert status == 200
        assert source_filtered["players"]
        assert all(player["source_type"] == sample["source_type"] for player in source_filtered["players"])

        status, searched = _request(
            "GET",
            f"{server.base_url}/runs/run-players/players?search={sample['player_id']}",
        )
        assert status == 200
        assert any(player["player_id"] == sample["player_id"] for player in searched["players"])

        status, detail = _request(
            "GET",
            f"{server.base_url}/runs/run-players/players/{sample['player_id']}",
        )
        assert status == 200
        assert detail["player_id"] == sample["player_id"]
        assert detail["source_type"] == sample["source_type"]
        assert detail["quality_band"] == sample["quality_band"]
        assert "origin_source_type" in detail
        assert "origin_quality_band" in detail
        assert "origin_override_id" in detail
        assert "origin_season" in detail
        assert "hidden_traits" in detail

        status, _ = _request("GET", f"{server.base_url}/runs/run-players/players/not-real-player")
        assert status == 404


def test_run_players_child_run_contains_rollover_and_intake_sources(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-players-child.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-parent", "seed": 5252, "season": 2027},
        )
        assert status == 201

        status, _ = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child", "child_seed": 6262},
        )
        if status != 200:
            status, _ = _request("POST", f"{server.base_url}/runs/run-parent/simulate/full-season")
            assert status == 200
            status, _ = _request("POST", f"{server.base_url}/runs/run-parent/rollover/next-season")
            assert status == 200
            status, _ = _request(
                "POST",
                f"{server.base_url}/runs/run-parent/bootstrap-next-season",
                {"child_run_id": "run-child", "child_seed": 6262},
            )
        assert status == 200

        status, child_players = _request("GET", f"{server.base_url}/runs/run-child/players?limit=500")
        assert status == 200
        assert child_players["players"]
        sources = {player["source_type"] for player in child_players["players"]}
        assert "rollover_carried" in sources
        assert "planner_generated" in sources or "manual_override" in sources
        carried = next(player for player in child_players["players"] if player["source_type"] == "rollover_carried")
        assert carried["origin_source_type"] in {"planner_generated", "manual_override", None}


def test_run_world_status_and_rebuild_endpoints(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-world-status.db'}"
    override_id = f"api-world-stale-{tmp_path.name}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-world", "seed": 5151, "season": 2027})
        assert status == 201

        status, world_status = _request("GET", f"{server.base_url}/runs/run-world/world-status")
        assert status == 200
        assert world_status["is_stale"] is False
        assert world_status["rebuild_supported"] is True
        assert world_status["stored_world_generation_fingerprint"] == world_status["current_world_generation_fingerprint"]

        status, _ = _request(
            "POST",
            f"{server.base_url}/world/manual-player-overrides",
            {
                "override_id": override_id,
                "season": 2027,
                "country_code": "EGY",
                "player_name": "API World Stale",
                "age": 18,
                "profile_tier": "elite",
                "enabled": True,
            },
        )
        assert status == 201

        status, stale_status = _request("GET", f"{server.base_url}/runs/run-world/world-status")
        assert status == 200
        assert stale_status["is_stale"] is True

        status, rebuilt = _request("POST", f"{server.base_url}/runs/run-world/rebuild-world")
        assert status == 200
        assert rebuilt["is_stale"] is False
        assert rebuilt["stored_world_generation_fingerprint"] == rebuilt["current_world_generation_fingerprint"]
        _request("DELETE", f"{server.base_url}/world/manual-player-overrides/{override_id}")


def test_run_world_rebuild_rejects_progressed_and_child_runs(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-world-rebuild-guards.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-progressed", "seed": 6161, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/run-progressed/simulate/next-week")
        assert status == 200
        status, denied = _request("POST", f"{server.base_url}/runs/run-progressed/rebuild-world")
        assert status == 400
        assert "not allowed after simulation progress" in denied["detail"]

        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-parent", "seed": 6262, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/run-parent/simulate/full-season")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-parent/rollover/next-season")
        assert status == 200
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child", "child_seed": 6262},
        )
        assert status == 200
        status, child_status = _request("GET", f"{server.base_url}/runs/run-child/world-status")
        assert status == 200
        assert child_status["rebuild_supported"] is False
        status, denied_child = _request("POST", f"{server.base_url}/runs/run-child/rebuild-world")
        assert status == 400
        assert "not supported for bootstrap/child runs" in denied_child["detail"]


def test_run_nations_summary_and_detail_reflect_run_player_pool(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-nations.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-nations", "seed": 7373, "season": 2027})
        assert status == 201

        status, players_payload = _request("GET", f"{server.base_url}/runs/run-nations/players?limit=500")
        assert status == 200
        players = players_payload["players"]
        assert players

        by_country = Counter(player["country_code"] for player in players)
        by_top_band = Counter(player["country_code"] for player in players if player["is_top_band"])
        by_source = {
            "rollover_carried": Counter(player["country_code"] for player in players if player["source_type"] == "rollover_carried"),
            "planner_generated": Counter(player["country_code"] for player in players if player["source_type"] == "planner_generated"),
            "manual_override": Counter(player["country_code"] for player in players if player["source_type"] == "manual_override"),
        }

        status, nations_payload = _request(
            "GET", f"{server.base_url}/runs/run-nations/nations?sort=total_players_desc&limit=300&offset=0"
        )
        assert status == 200
        assert nations_payload["total"] == len(nations_payload["nations"])
        assert nations_payload["nations"]

        sample_nation = nations_payload["nations"][0]
        nation_code = sample_nation["country_code"]
        nation_players = [player for player in players if player["country_code"] == nation_code]
        expected_avg_overall = round(sum(player["overall"] for player in nation_players) / len(nation_players), 2)
        expected_avg_age = round(sum(player["age"] for player in nation_players) / len(nation_players), 2)

        assert sample_nation["total_players"] == by_country[nation_code]
        assert sample_nation["top_band_count"] == by_top_band[nation_code]
        assert sample_nation["rollover_carried_count"] == by_source["rollover_carried"][nation_code]
        assert sample_nation["planner_generated_count"] == by_source["planner_generated"][nation_code]
        assert sample_nation["manual_override_count"] == by_source["manual_override"][nation_code]
        assert sample_nation["average_overall"] == expected_avg_overall
        assert sample_nation["average_age"] == expected_avg_age

        expected_top = sorted(nation_players, key=lambda player: (-player["overall"], player["name"], player["player_id"]))[0]
        assert sample_nation["top_player_id"] == expected_top["player_id"]
        assert sample_nation["top_player_name"] == expected_top["name"]
        assert sample_nation["top_player_overall"] == expected_top["overall"]

        status, detail_payload = _request("GET", f"{server.base_url}/runs/run-nations/nations/{nation_code}?top_limit=10")
        assert status == 200
        assert detail_payload["country_code"] == nation_code
        assert detail_payload["total_players"] == sample_nation["total_players"]
        assert detail_payload["top_players"]
        assert len(detail_payload["top_players"]) <= 10
        assert detail_payload["top_players"][0]["player_id"] == expected_top["player_id"]
        assert detail_payload["source_mix"]["rollover_carried"] == sample_nation["rollover_carried_count"]
        assert detail_payload["source_mix"]["planner_generated"] == sample_nation["planner_generated_count"]
        assert detail_payload["source_mix"]["manual_override"] == sample_nation["manual_override_count"]
        assert sum(item["count"] for item in detail_payload["band_distribution"]) == sample_nation["total_players"]
        assert "origin_band_distribution" in detail_payload

        status, _ = _request("GET", f"{server.base_url}/runs/run-nations/nations/ZZZ")
        assert status == 404


def test_run_nations_child_run_shows_truthful_source_mix(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-run-nations-child.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-parent", "seed": 8080, "season": 2027})
        assert status == 201

        status, _ = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child", "child_seed": 9090},
        )
        if status != 200:
            status, _ = _request("POST", f"{server.base_url}/runs/run-parent/simulate/full-season")
            assert status == 200
            status, _ = _request("POST", f"{server.base_url}/runs/run-parent/rollover/next-season")
            assert status == 200
            status, _ = _request(
                "POST",
                f"{server.base_url}/runs/run-parent/bootstrap-next-season",
                {"child_run_id": "run-child", "child_seed": 9090},
            )
        assert status == 200

        status, nations_payload = _request("GET", f"{server.base_url}/runs/run-child/nations?limit=300")
        assert status == 200
        assert nations_payload["nations"]
        assert any(item["rollover_carried_count"] > 0 for item in nations_payload["nations"])
        assert any(item["planner_generated_count"] + item["manual_override_count"] > 0 for item in nations_payload["nations"])

def test_simulation_endpoints_and_snapshot_queries_work(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-sim.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-sim", "seed": 2002, "season": 2027},
        )
        assert status == 201

        status, run_state = _request("GET", f"{server.base_url}/runs/run-sim")
        assert status == 200
        ordered_events = run_state["season_state"]["ordered_events"]
        unique_weeks = sorted({event["week"] for event in ordered_events})
        expected_completed_event_ids = [
            event["event_id"] for event in ordered_events if event["week"] in set(unique_weeks[:2])
        ]

        status, next_tournament = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-tournament")
        assert status == 200
        assert next_tournament["step"]["mode"] == "simulate_next_tournament"
        assert next_tournament["run"]["next_event_index"] == 1

        status, next_match = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-match")
        assert status == 200
        assert next_match["step"]["mode"] == "simulate_next_match"
        assert next_match["run"]["next_event_index"] == 1
        assert next_match["step"]["season_state"]["active_tournament"] is not None
        assert next_match["step"]["tournament_result"]["ranking_snapshot"] is None
        assert next_match["step"]["tournament_result"]["race_snapshot"] is None
        assert next_match["step"]["tournament_result"]["completed_tournament_input"] is None

        status, next_round = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-round")
        assert status == 200
        assert next_round["step"]["mode"] == "simulate_next_round"
        assert next_round["step"]["tournament_result"]["ranking_snapshot"] is None
        assert next_round["step"]["tournament_result"]["race_snapshot"] is None
        assert next_round["step"]["tournament_result"]["completed_tournament_input"] is None

        status, next_week = _request("POST", f"{server.base_url}/runs/run-sim/simulate/next-week")
        assert status == 200
        assert next_week["step"]["mode"] == "simulate_next_week"

        status, events_payload = _request("GET", f"{server.base_url}/runs/run-sim/events")
        assert status == 200
        observed_event_ids = [event["event_id"] for event in events_payload["events"]]
        assert observed_event_ids == expected_completed_event_ids

        status, full_season = _request("POST", f"{server.base_url}/runs/run-sim/simulate/full-season")
        assert status == 200
        assert full_season["step"]["mode"] == "simulate_full_season"
        assert full_season["run"]["next_event_index"] == full_season["run"]["total_events"]

        status, ranking_payload = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/ranking")
        assert status == 200
        status, race_payload = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/race")
        assert status == 200

        ranking_sequences = [record["snapshot_sequence"] for record in ranking_payload["snapshots"]]
        race_sequences = [record["snapshot_sequence"] for record in race_payload["snapshots"]]
        assert ranking_sequences == sorted(ranking_sequences)
        assert race_sequences == sorted(race_sequences)
        assert ranking_sequences
        assert race_sequences

        first_ranking_sequence = ranking_sequences[0]
        status, ranking_detail = _request(
            "GET",
            f"{server.base_url}/runs/run-sim/snapshots/ranking/{first_ranking_sequence}",
        )
        assert status == 200
        assert set(ranking_detail.keys()) == {"snapshot_sequence", "snapshot_kind", "source_event_id", "payload"}
        assert ranking_detail["snapshot_sequence"] == first_ranking_sequence

        first_race_sequence = race_sequences[0]
        status, race_detail = _request(
            "GET",
            f"{server.base_url}/runs/run-sim/snapshots/race/{first_race_sequence}",
        )
        assert status == 200
        assert set(race_detail.keys()) == {"snapshot_sequence", "snapshot_kind", "source_event_id", "payload"}
        assert race_detail["snapshot_sequence"] == first_race_sequence

        status, _ = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/ranking/999999")
        assert status == 404
        status, _ = _request("GET", f"{server.base_url}/runs/run-sim/snapshots/race/999999")
        assert status == 404

        first_event_id = events_payload["events"][0]["event_id"]
        status, event_detail = _request("GET", f"{server.base_url}/runs/run-sim/events/{first_event_id}")
        assert status == 200
        assert event_detail["event_id"] == first_event_id
        assert event_detail["tournament_result"] is not None

        status, finals_qualification = _request("GET", f"{server.base_url}/runs/run-sim/finals/qualification")
        assert status == 200
        assert finals_qualification["qualification"]["target_season"] == 2027

        status, finals_summary_pre = _request("GET", f"{server.base_url}/runs/run-sim/finals/summary")
        assert status == 200
        assert finals_summary_pre["qualification"] is not None
        assert finals_summary_pre["result"] is None

        status, finals_result_missing = _request("GET", f"{server.base_url}/runs/run-sim/finals/result")
        assert status == 404

        status, finals_early = _request("POST", f"{server.base_url}/runs/run-sim/simulate/world-tour-finals")
        assert status == 200
        assert finals_early["finals"]["already_simulated"] is False

        status, finals_cached = _request("POST", f"{server.base_url}/runs/run-sim/simulate/world-tour-finals")
        assert status == 200
        assert finals_cached["finals"]["already_simulated"] is True
        assert finals_cached["finals"]["result"] == finals_early["finals"]["result"]

        status, finals_result = _request("GET", f"{server.base_url}/runs/run-sim/finals/result")
        assert status == 200
        assert finals_result["result"]["event_id"] == "WORLD_TOUR_FINALS"

        status, finals_summary = _request("GET", f"{server.base_url}/runs/run-sim/finals/summary")
        assert status == 200
        assert finals_summary["qualification"] is not None
        assert finals_summary["result"] is not None


def test_finals_endpoint_rejects_incomplete_season(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-finals-incomplete.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-finals-incomplete", "seed": 3003, "season": 2027},
        )
        assert status == 201

        status, payload = _request("POST", f"{server.base_url}/runs/run-finals-incomplete/simulate/world-tour-finals")
        assert status == 400
        assert "completed regular season" in payload["detail"]


def test_commissioner_wildcard_assignment_endpoints_validate_and_persist(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-wildcards.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-wildcards", "seed": 5151, "season": 2027},
        )
        assert status == 201

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-wildcards")
        assert status == 200
        ordered_events = state_payload["season_state"]["ordered_events"]

        selected_event_id = None
        for event in ordered_events:
            status, wildcard_state = _request(
                "GET",
                f"{server.base_url}/runs/run-wildcards/events/{event['event_id']}/wildcards",
            )
            assert status == 200
            if wildcard_state["total_slots"] > 0:
                selected_event_id = event["event_id"]
                break
        assert selected_event_id is not None

        status, wildcard_state = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
        )
        assert status == 200
        assert wildcard_state["eligible"] is True

        status, wildcard_candidates_first = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcard-candidates",
        )
        assert status == 200
        assert wildcard_candidates_first["run_id"] == "run-wildcards"
        assert wildcard_candidates_first["event_id"] == selected_event_id
        assert wildcard_candidates_first["candidates"]
        first_candidate = wildcard_candidates_first["candidates"][0]
        assert first_candidate["player_id"]
        assert first_candidate["player_name"]
        assert first_candidate["country_code"]
        assert first_candidate["source"] in {"main_draw_waitlist", "qualification_waitlist", "non_applicant_pool"}

        status, wildcard_candidates_second = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcard-candidates",
        )
        assert status == 200
        assert wildcard_candidates_second == wildcard_candidates_first

        status, wildcard_actions_empty = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcard-actions",
        )
        assert status == 200
        assert wildcard_actions_empty == {"run_id": "run-wildcards", "event_id": selected_event_id, "actions": []}

        status, invalid = _request(
            "POST",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
            {"assignments": [{"slot_index": 1, "player_id": "NOT-A-PLAYER"}]},
        )
        assert status == 400
        assert "was not found" in invalid["detail"]

        status, over_capacity = _request(
            "POST",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
            {"assignments": [{"slot_index": wildcard_state["total_slots"] + 1, "player_id": "EGY-00001"}]},
        )
        assert status == 400
        assert "outside available wildcard slots" in over_capacity["detail"]

        status, duplicate_request = _request(
            "POST",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
            {
                "assignments": [
                    {"slot_index": 1, "player_id": "EGY-00001"},
                    {"slot_index": min(2, wildcard_state["total_slots"]), "player_id": "EGY-00001"},
                ]
            },
        )
        assert status == 400
        assert "provided more than once" in duplicate_request["detail"]

        assigned_player_id = None
        successful_assignment_payload: dict[str, object] | None = None
        for player_id in _generated_player_ids(season=2027, seed=5151):
            status, payload = _request(
                "POST",
                f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
                {"assignments": [{"slot_index": 1, "player_id": player_id}]},
            )
            if status == 200:
                assigned_player_id = player_id
                successful_assignment_payload = payload
                break
        assert assigned_player_id is not None
        assert successful_assignment_payload is not None
        assert successful_assignment_payload["slots"][0]["assigned_player_id"] == assigned_player_id

        second_assigned_player_id = None
        for player_id in _generated_player_ids(season=2027, seed=5151):
            if player_id == assigned_player_id:
                continue
            status, payload = _request(
                "POST",
                f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
                {"assignments": [{"slot_index": 1, "player_id": player_id}]},
            )
            if status == 200:
                second_assigned_player_id = player_id
                assert payload["slots"][0]["assigned_player_id"] == second_assigned_player_id
                break
        assert second_assigned_player_id is not None

        status, wildcard_actions = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcard-actions",
        )
        assert status == 200
        assert wildcard_actions["run_id"] == "run-wildcards"
        assert wildcard_actions["event_id"] == selected_event_id
        assert [item["action_sequence"] for item in wildcard_actions["actions"]] == [1, 2]
        assert [item["action_kind"] for item in wildcard_actions["actions"]] == ["assign_wildcards", "assign_wildcards"]
        assert wildcard_actions["actions"][0]["event_id"] == selected_event_id
        assert wildcard_actions["actions"][0]["assignment_payload_summary"] == [{"slot_index": 1, "player_id": assigned_player_id}]
        assert wildcard_actions["actions"][1]["assignment_payload_summary"] == [
            {"slot_index": 1, "player_id": second_assigned_player_id}
        ]

        status, after_assign = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
        )
        assert status == 200
        assert after_assign["slots"][0]["assigned_player_id"] == second_assigned_player_id

        status, wildcard_candidates_after_assign = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcard-candidates",
        )
        assert status == 200
        candidate_ids = {candidate["player_id"] for candidate in wildcard_candidates_after_assign["candidates"]}
        assert second_assigned_player_id not in candidate_ids

        selected_index = next(index for index, event in enumerate(ordered_events) if event["event_id"] == selected_event_id)
        for _ in range(selected_index + 1):
            status, sim_result = _request("POST", f"{server.base_url}/runs/run-wildcards/simulate/next-tournament")
            assert status == 200

        completed_input = sim_result["step"]["tournament_result"]["acceptance_list"]["main_draw_entries"]
        wildcard_entries = [entry for entry in completed_input if entry["status"] == "WILD_CARD_PLACEHOLDER"]
        assert wildcard_entries
        assert wildcard_entries[0]["player_id"] == second_assigned_player_id

        status, rejected_after_start = _request(
            "POST",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
            {"assignments": [{"slot_index": 1, "player_id": second_assigned_player_id}]},
        )
        assert status == 400
        assert "completed events" in rejected_after_start["detail"]


def test_pre_draw_withdrawal_replacement_endpoints_validate_fold_and_persist(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-pre-draw.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-pre-draw", "seed": 6060, "season": 2027},
        )
        assert status == 201

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-pre-draw")
        assert status == 200
        event_id = state_payload["season_state"]["ordered_events"][0]["event_id"]

        status, initial_state = _request(
            "GET",
            f"{server.base_url}/runs/run-pre-draw/events/{event_id}/pre-draw-withdrawal",
        )
        assert status == 200
        assert initial_state["run_id"] == "run-pre-draw"
        assert initial_state["event_id"] == event_id
        assert initial_state["eligible"] is True
        assert initial_state["withdrawable_main_draw_players"]
        withdrawn_player_id = initial_state["withdrawable_main_draw_players"][0]["player_id"]

        status, invalid_player = _request(
            "POST",
            f"{server.base_url}/runs/run-pre-draw/events/{event_id}/pre-draw-withdrawal",
            {"withdrawn_player_id": "NOT-A-PLAYER"},
        )
        assert status == 400
        assert "was not found" in invalid_player["detail"]

        status, result = _request(
            "POST",
            f"{server.base_url}/runs/run-pre-draw/events/{event_id}/pre-draw-withdrawal",
            {"withdrawn_player_id": withdrawn_player_id},
        )
        assert status == 200
        assert result["event_id"] == event_id
        assert result["withdrawn_player_id"] == withdrawn_player_id
        assert result["replacement_source"] in {"main_draw_waitlist", "qualification_waitlist"}
        assert result["withdrawn_entry_id"]
        assert result["replacement_entry_id"]

        status, history = _request(
            "GET",
            f"{server.base_url}/runs/run-pre-draw/events/{event_id}/pre-draw-withdrawal-actions",
        )
        assert status == 200
        assert [item["action_sequence"] for item in history["actions"]] == [1]
        assert history["actions"][0]["action_kind"] == "pre_draw_withdrawal_replacement"
        assert history["actions"][0]["withdrawn_player_id"] == withdrawn_player_id
        assert history["actions"][0]["replacement_player_id"] == result["replacement_player_id"]
        assert history["actions"][0]["notes"] is None

        status, sim_result = _request("POST", f"{server.base_url}/runs/run-pre-draw/simulate/next-tournament")
        assert status == 200
        main_entries = sim_result["step"]["tournament_result"]["acceptance_list"]["main_draw_entries"]
        withdrawn_entry = next(entry for entry in main_entries if entry["entry_id"] == result["withdrawn_entry_id"])
        replacement_entry = next(entry for entry in main_entries if entry["entry_id"] == result["replacement_entry_id"])
        assert withdrawn_entry["player_id"] is None
        assert replacement_entry["player_id"] == result["replacement_player_id"]

        status, rejected_after_completion = _request(
            "POST",
            f"{server.base_url}/runs/run-pre-draw/events/{event_id}/pre-draw-withdrawal",
            {"withdrawn_player_id": withdrawn_player_id},
        )
        assert status == 400
        assert "already completed" in rejected_after_completion["detail"]


def test_late_replacement_endpoints_validate_fold_and_persist(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-late-replacement.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-late", "seed": 7070, "season": 2027},
        )
        assert status == 201

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-late")
        assert status == 200
        event_id = None
        initial_state: dict[str, object] | None = None
        for event in state_payload["season_state"]["ordered_events"]:
            status, candidate_state = _request(
                "GET",
                f"{server.base_url}/runs/run-late/events/{event['event_id']}/late-replacement",
            )
            assert status == 200
            if candidate_state["eligible"] is True:
                event_id = event["event_id"]
                initial_state = candidate_state
                break
        assert event_id is not None
        assert initial_state is not None
        assert initial_state["remaining_capacity"] >= 1
        assert initial_state["replaceable_main_draw_players"]
        withdrawn_player_id = initial_state["replaceable_main_draw_players"][0]["player_id"]

        status, candidates = _request(
            "GET",
            f"{server.base_url}/runs/run-late/events/{event_id}/late-replacement-candidates",
        )
        assert status == 200
        assert candidates["candidates"]
        source_order = {"qualification_waitlist": 0, "main_draw_waitlist": 1}
        sort_tuples = [
            (
                source_order[item["source"]],
                10_000 if item["ranking_priority"] is None else item["ranking_priority"],
                item["player_id"],
                item["entry_id"],
            )
            for item in candidates["candidates"]
        ]
        assert sort_tuples == sorted(sort_tuples)

        status, invalid_player = _request(
            "POST",
            f"{server.base_url}/runs/run-late/events/{event_id}/late-replacement",
            {"withdrawn_player_id": "NOT-A-PLAYER"},
        )
        assert status == 400
        assert "was not found" in invalid_player["detail"]

        status, result = _request(
            "POST",
            f"{server.base_url}/runs/run-late/events/{event_id}/late-replacement",
            {"withdrawn_player_id": withdrawn_player_id},
        )
        assert status == 200
        assert result["event_id"] == event_id
        assert result["withdrawn_player_id"] == withdrawn_player_id
        assert result["candidate_slot_index"] is not None
        assert result["replacement_source"] in {"qualification_waitlist", "main_draw_waitlist"}
        assert "LATE_REPLACEMENT_PLACEHOLDER" in result["replacement_entry_id"] or result["replacement_entry_id"] == result["withdrawn_entry_id"]

        status, history = _request(
            "GET",
            f"{server.base_url}/runs/run-late/events/{event_id}/late-replacement-actions",
        )
        assert status == 200
        assert [item["action_sequence"] for item in history["actions"]] == [1]
        assert history["actions"][0]["action_kind"] == "late_replacement_lucky_loser"
        assert history["actions"][0]["withdrawn_player_id"] == withdrawn_player_id
        assert history["actions"][0]["candidate_slot_index"] == result["candidate_slot_index"]

        status, sim_result = _request("POST", f"{server.base_url}/runs/run-late/simulate/next-tournament")
        assert status == 200
        main_entries = sim_result["step"]["tournament_result"]["acceptance_list"]["main_draw_entries"]
        withdrawn_entry = next(entry for entry in main_entries if entry["entry_id"] == result["withdrawn_entry_id"])
        replacement_entry = next(entry for entry in main_entries if entry["entry_id"] == result["replacement_entry_id"])
        assert withdrawn_entry["player_id"] is None
        assert replacement_entry["player_id"] == result["replacement_player_id"]


def test_late_replacement_rejects_when_capacity_exhausted(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-late-capacity.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-late-cap", "seed": 7171, "season": 2027},
        )
        assert status == 201
        status, state_payload = _request("GET", f"{server.base_url}/runs/run-late-cap")
        assert status == 200

        target_event_id = None
        target_state = None
        for event in state_payload["season_state"]["ordered_events"]:
            status, candidate_state = _request(
                "GET",
                f"{server.base_url}/runs/run-late-cap/events/{event['event_id']}/late-replacement",
            )
            assert status == 200
            if candidate_state["eligible"]:
                target_event_id = event["event_id"]
                target_state = candidate_state
                break
        assert target_event_id is not None
        assert target_state is not None

        capacity = target_state["remaining_capacity"]
        last_withdrawable_player_id = target_state["replaceable_main_draw_players"][0]["player_id"]
        for _ in range(capacity):
            withdrawn_player_id = target_state["replaceable_main_draw_players"][0]["player_id"]
            last_withdrawable_player_id = withdrawn_player_id
            status, _ = _request(
                "POST",
                f"{server.base_url}/runs/run-late-cap/events/{target_event_id}/late-replacement",
                {"withdrawn_player_id": withdrawn_player_id},
            )
            assert status == 200
            status, target_state = _request(
                "GET",
                f"{server.base_url}/runs/run-late-cap/events/{target_event_id}/late-replacement",
            )
            assert status == 200
        assert target_state["eligible"] is False
        assert "capacity is exhausted" in (target_state["eligibility_reason"] or "")

        status, rejected = _request(
            "POST",
            f"{server.base_url}/runs/run-late-cap/events/{target_event_id}/late-replacement",
            {"withdrawn_player_id": last_withdrawable_player_id},
        )
        assert status == 400
        assert "capacity is exhausted" in rejected["detail"]


def test_next_match_and_next_round_reject_after_finals_phase_begins(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-next-match-finals.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-finals-locked", "seed": 3222, "season": 2027},
        )
        assert status == 201

        status, _ = _request("POST", f"{server.base_url}/runs/run-finals-locked/simulate/full-season")
        assert status == 200
        status, _ = _request("GET", f"{server.base_url}/runs/run-finals-locked/finals/qualification")
        assert status == 200

        status, payload = _request("POST", f"{server.base_url}/runs/run-finals-locked/simulate/next-match")
        assert status == 400
        assert "finals phase has begun" in payload["detail"]

        status, payload = _request("POST", f"{server.base_url}/runs/run-finals-locked/simulate/next-round")
        assert status == 400
        assert "finals phase has begun" in payload["detail"]


def test_rollover_endpoints_execute_and_read_persisted_data(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-rollover.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-rollover", "seed": 4004, "season": 2027},
        )
        assert status == 201

        status, rollover_incomplete = _request("POST", f"{server.base_url}/runs/run-rollover/rollover/next-season")
        assert status == 400
        assert "completed season" in rollover_incomplete["detail"]

        status, _ = _request("POST", f"{server.base_url}/runs/run-rollover/simulate/full-season")
        assert status == 200

        status, rollover = _request("POST", f"{server.base_url}/runs/run-rollover/rollover/next-season")
        assert status == 200
        assert rollover["rollover"]["from_season"] == 2027
        assert rollover["rollover"]["to_season"] == 2028
        assert rollover["rollover"]["already_persisted"] is False

        status, rollover_cached = _request("POST", f"{server.base_url}/runs/run-rollover/rollover/next-season")
        assert status == 200
        assert rollover_cached["rollover"]["already_persisted"] is True
        assert rollover_cached["rollover"]["transitions"] == rollover["rollover"]["transitions"]

        status, latest = _request("GET", f"{server.base_url}/runs/run-rollover/rollover/latest")
        assert status == 200
        assert latest["rollover"]["to_season"] == 2028

        status, by_season = _request("GET", f"{server.base_url}/runs/run-rollover/rollover/2028")
        assert status == 200
        assert by_season["rollover"]["transitioned_players"] == rollover["rollover"]["transitioned_players"]

        status, next_players = _request("GET", f"{server.base_url}/runs/run-rollover/players/next-season/2028")
        assert status == 200
        assert len(next_players["players"]) == rollover["rollover"]["transitioned_players"]

        status, transitions = _request("GET", f"{server.base_url}/runs/run-rollover/players/transitions/2028")
        assert status == 200
        assert len(transitions["transitions"]) == rollover["rollover"]["transitioned_players"]


def test_rollover_final_registry_season_returns_conflict_without_artifacts(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-rollover-final-season.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-final-rollover", "seed": 4054, "season": 2049},
        )
        assert status == 201

        status, _ = _request("POST", f"{server.base_url}/runs/run-final-rollover/simulate/full-season")
        assert status == 200

        status, payload = _request("POST", f"{server.base_url}/runs/run-final-rollover/rollover/next-season")

        assert status == 409
        assert "final registry season 2049/50" in payload["detail"]
        assert "no next season exists" in payload["detail"]

        status, latest = _request("GET", f"{server.base_url}/runs/run-final-rollover/rollover/latest")
        assert status == 404
        assert "No rollover found" in latest["detail"]

        status, next_players = _request("GET", f"{server.base_url}/runs/run-final-rollover/players/next-season/2050")
        assert status == 200
        assert next_players["players"] == []

        status, transitions = _request("GET", f"{server.base_url}/runs/run-final-rollover/players/transitions/2050")
        assert status == 200
        assert transitions["transitions"] == []

        status, runs = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        run_ids = [run["run_id"] for run in runs["runs"]]
        assert run_ids == ["run-final-rollover"]


def test_bootstrap_next_season_and_lineage_endpoints(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-bootstrap.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-parent", "seed": 4114, "season": 2027},
        )
        assert status == 201

        status, missing_rollover = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child"},
        )
        assert status == 400
        assert "No persisted rollover" in missing_rollover["detail"]

        status, _ = _request("POST", f"{server.base_url}/runs/run-parent/simulate/full-season")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-parent/rollover/next-season")
        assert status == 200

        status, bootstrap = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child"},
        )
        assert status == 200
        assert bootstrap["run"]["season"] == 2028
        assert bootstrap["bootstrap"]["already_bootstrapped"] is False

        status, bootstrap_cached = _request(
            "POST",
            f"{server.base_url}/runs/run-parent/bootstrap-next-season",
            {"child_run_id": "run-child"},
        )
        assert status == 200
        assert bootstrap_cached["bootstrap"]["already_bootstrapped"] is True

        status, lineage = _request("GET", f"{server.base_url}/runs/run-parent/lineage")
        assert status == 200
        assert lineage["lineage"]["children"] == ["run-child"]

        status, source = _request("GET", f"{server.base_url}/runs/run-child/source")
        assert status == 200
        assert source["source"]["source_type"] == "rollover_bootstrap"
        assert source["source"]["parent_run_id"] == "run-parent"

        status, child_step = _request("POST", f"{server.base_url}/runs/run-child/simulate/next-week")
        assert status == 200
        assert child_step["step"]["season_state"]["season"] == 2028


def test_run_status_summary_endpoint_returns_compact_aggregates(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-status-summary.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-status", "seed": 5151, "season": 2027},
        )
        assert status == 201

        status, pre = _request("GET", f"{server.base_url}/runs/run-status/status-summary")
        assert status == 200
        total_events = pre["progress"]["total_events"]
        assert pre == {
            "run_id": "run-status",
            "season": 2027,
            "seed": 5151,
            "progress": {"next_event_index": 0, "total_events": total_events, "completed_event_count": 0},
            "finals": {"qualification_available": False, "result_available": False},
            "rollover": None,
            "source": None,
            "lineage": {"child_run_count": 0},
            "history_counts": {"events": 0, "ranking_snapshots": 0, "race_snapshots": 0},
        }

        status, _ = _request("POST", f"{server.base_url}/runs/run-status/simulate/full-season")
        assert status == 200
        status, rollover_payload = _request("POST", f"{server.base_url}/runs/run-status/rollover/next-season")
        assert status == 200
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs/run-status/bootstrap-next-season",
            {"child_run_id": "run-status-child"},
        )
        assert status == 200

        status, post = _request("GET", f"{server.base_url}/runs/run-status/status-summary")
        assert status == 200
        assert post["run_id"] == "run-status"
        assert post["finals"]["qualification_available"] is True
        assert post["finals"]["result_available"] is False
        assert post["rollover"] == {
            "latest_to_season": 2028,
            "transitioned_players": rollover_payload["rollover"]["transitioned_players"],
        }
        assert post["source"] is None
        assert post["lineage"] == {"child_run_count": 1}
        assert post["history_counts"]["events"] == total_events
        assert post["history_counts"]["ranking_snapshots"] > 0
        assert post["history_counts"]["race_snapshots"] > 0

        status, child = _request("GET", f"{server.base_url}/runs/run-status-child/status-summary")
        assert status == 200
        assert child["source"] == {"source_type": "rollover_bootstrap", "parent_run_id": "run-status"}


def test_runs_index_endpoint_lists_runs_with_deterministic_order_and_compact_lineage_fields(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-runs-index.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-z", "seed": 9001, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs/run-z/simulate/next-week")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-z/simulate/full-season")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-z/rollover/next-season")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-z/bootstrap-next-season", {"child_run_id": "run-a"})
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-z/bootstrap-next-season", {"child_run_id": "run-m"})
        assert status == 200

        status, payload = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert list(payload.keys()) == ["runs"]
        run_ids = [row["run_id"] for row in payload["runs"]]
        assert run_ids == ["run-a", "run-m", "run-z"]

        run_z = next(row for row in payload["runs"] if row["run_id"] == "run-z")
        assert run_z["progress"]["next_event_index"] == run_z["progress"]["total_events"]
        assert run_z["progress"]["completed_event_count"] == run_z["progress"]["total_events"]
        assert run_z["source_type"] == "fresh_seed"
        assert run_z["parent_run_id"] is None
        assert run_z["child_run_count"] == 2

        run_a = next(row for row in payload["runs"] if row["run_id"] == "run-a")
        assert run_a["source_type"] == "rollover_bootstrap"
        assert run_a["parent_run_id"] == "run-z"
        assert run_a["child_run_count"] == 0


def test_run_activity_endpoint_returns_compact_deterministic_feed(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-activity.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-activity", "seed": 8080, "season": 2027})
        assert status == 201

        status, empty = _request("GET", f"{server.base_url}/runs/run-activity/activity")
        assert status == 200
        assert empty == {"run_id": "run-activity", "items": []}

        status, state_payload = _request("GET", f"{server.base_url}/runs/run-activity")
        assert status == 200
        selected_event_id = None
        for event in state_payload["season_state"]["ordered_events"]:
            status, wildcard_state = _request(
                "GET",
                f"{server.base_url}/runs/run-activity/events/{event['event_id']}/wildcards",
            )
            assert status == 200
            if wildcard_state["total_slots"] > 0:
                selected_event_id = event["event_id"]
                break
        assert selected_event_id is not None

        status, wildcard_candidates = _request(
            "GET",
            f"{server.base_url}/runs/run-activity/events/{selected_event_id}/wildcard-candidates",
        )
        assert status == 200
        assert wildcard_candidates["candidates"]

        status, wildcard_state_after_assign = _request(
            "POST",
            f"{server.base_url}/runs/run-activity/events/{selected_event_id}/wildcards",
            {"assignments": [{"slot_index": 1, "player_id": wildcard_candidates["candidates"][0]["player_id"]}]},
        )
        assert status == 200
        assert wildcard_state_after_assign["slots"][0]["assigned_player_id"] == wildcard_candidates["candidates"][0]["player_id"]
        pre_draw_event_id = None
        for event in state_payload["season_state"]["ordered_events"]:
            status, pre_draw_state = _request(
                "GET",
                f"{server.base_url}/runs/run-activity/events/{event['event_id']}/pre-draw-withdrawal",
            )
            assert status == 200
            if not pre_draw_state["withdrawable_main_draw_players"]:
                continue
            status, pre_draw_result = _request(
                "POST",
                f"{server.base_url}/runs/run-activity/events/{event['event_id']}/pre-draw-withdrawal",
                {"withdrawn_player_id": pre_draw_state["withdrawable_main_draw_players"][0]["player_id"]},
            )
            if status == 200:
                pre_draw_event_id = event["event_id"]
                break
        assert pre_draw_event_id is not None
        status, late_state = _request(
            "GET",
            f"{server.base_url}/runs/run-activity/events/{pre_draw_event_id}/late-replacement",
        )
        assert status == 200
        if late_state["eligible"] and late_state["replaceable_main_draw_players"]:
            status, _ = _request(
                "POST",
                f"{server.base_url}/runs/run-activity/events/{pre_draw_event_id}/late-replacement",
                {"withdrawn_player_id": late_state["replaceable_main_draw_players"][0]["player_id"]},
            )
            assert status == 200

        status, _ = _request("POST", f"{server.base_url}/runs/run-activity/simulate/full-season")
        assert status == 200
        status, _ = _request("GET", f"{server.base_url}/runs/run-activity/finals/qualification")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-activity/simulate/world-tour-finals")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-activity/rollover/next-season")
        assert status == 200
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs/run-activity/bootstrap-next-season",
            {"child_run_id": "run-activity-child"},
        )
        assert status == 200

        status, payload = _request("GET", f"{server.base_url}/runs/run-activity/activity")
        assert status == 200
        assert list(payload.keys()) == ["run_id", "items"]
        assert payload["run_id"] == "run-activity"
        assert payload["items"]

        kinds = {item["kind"] for item in payload["items"]}
        assert "event" in kinds
        assert "ranking_snapshot" in kinds
        assert "race_snapshot" in kinds
        assert "finals_qualification" in kinds
        assert "finals_result" in kinds
        assert "rollover" in kinds
        assert "bootstrap_child" in kinds
        assert "admin_wildcard_assignment" in kinds
        assert "admin_pre_draw_withdrawal_replacement" in kinds
        if late_state["eligible"] and late_state["replaceable_main_draw_players"]:
            assert "admin_late_replacement_lucky_loser" in kinds

        wildcard_items = [item for item in payload["items"] if item["kind"] == "admin_wildcard_assignment"]
        assert len(wildcard_items) == 1
        assert wildcard_items[0]["sequence"] == 1
        assert wildcard_items[0]["event_id"] == selected_event_id
        assert wildcard_items[0]["label"] == f"Commissioner wildcard assignment ({selected_event_id})"
        pre_draw_items = [item for item in payload["items"] if item["kind"] == "admin_pre_draw_withdrawal_replacement"]
        assert len(pre_draw_items) == 1
        assert pre_draw_items[0]["sequence"] == 1
        assert pre_draw_items[0]["event_id"] == pre_draw_event_id
        assert pre_draw_items[0]["label"] == f"Commissioner pre-draw withdrawal replacement ({pre_draw_event_id})"
        late_items = [item for item in payload["items"] if item["kind"] == "admin_late_replacement_lucky_loser"]
        if late_state["eligible"] and late_state["replaceable_main_draw_players"]:
            assert len(late_items) == 1
            assert late_items[0]["sequence"] == 2
            assert late_items[0]["event_id"] == pre_draw_event_id
            assert late_items[0]["label"] == f"Commissioner late replacement lucky loser ({pre_draw_event_id})"

        first = payload["items"][0]
        assert set(first.keys()) == {
            "kind",
            "sequence",
            "label",
            "season",
            "week",
            "event_id",
            "snapshot_sequence",
            "source_event_id",
            "related_run_id",
        }

        kind_order = {
            "event": 1,
            "ranking_snapshot": 2,
            "race_snapshot": 3,
            "finals_qualification": 4,
            "finals_result": 5,
            "rollover": 6,
            "bootstrap_child": 7,
            "admin_wildcard_assignment": 8,
            "admin_pre_draw_withdrawal_replacement": 9,
            "admin_late_replacement_lucky_loser": 10,
        }
        tuples = [
            (
                item["season"] if item["season"] is not None else 9999,
                item["week"] if item["week"] is not None else 99,
                kind_order[item["kind"]],
                item["sequence"] if item["sequence"] is not None else 999999,
                item["event_id"] or item["source_event_id"] or item["related_run_id"] or item["label"],
            )
            for item in payload["items"]
        ]
        assert tuples == sorted(tuples)


def test_full_season_and_incremental_modes_persist_equivalent_history_artifacts(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-full-vs-incremental.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-full", "seed": 9191, "season": 2027})
        assert status == 201
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-incremental", "seed": 9191, "season": 2027})
        assert status == 201

        status, _ = _request("POST", f"{server.base_url}/runs/run-full/simulate/full-season")
        assert status == 200

        while True:
            status, state = _request("GET", f"{server.base_url}/runs/run-incremental")
            assert status == 200
            if state["season_state"]["next_event_index"] == len(state["season_state"]["ordered_events"]):
                break
            status, _ = _request("POST", f"{server.base_url}/runs/run-incremental/simulate/next-week")
            assert status == 200

        status, full_events = _request("GET", f"{server.base_url}/runs/run-full/events")
        assert status == 200
        status, incremental_events = _request("GET", f"{server.base_url}/runs/run-incremental/events")
        assert status == 200
        assert full_events["events"] == incremental_events["events"]

        status, full_ranking = _request("GET", f"{server.base_url}/runs/run-full/snapshots/ranking")
        assert status == 200
        status, incremental_ranking = _request("GET", f"{server.base_url}/runs/run-incremental/snapshots/ranking")
        assert status == 200
        assert full_ranking["snapshots"] == incremental_ranking["snapshots"]

        status, full_race = _request("GET", f"{server.base_url}/runs/run-full/snapshots/race")
        assert status == 200
        status, incremental_race = _request("GET", f"{server.base_url}/runs/run-incremental/snapshots/race")
        assert status == 200
        assert full_race["snapshots"] == incremental_race["snapshots"]


def test_next_match_and_round_are_allowed_until_finals_marker_is_persisted(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-finals-marker.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request(
            "POST",
            f"{server.base_url}/runs",
            {"run_id": "run-finals-marker", "seed": 6161, "season": 2027},
        )
        assert status == 201

        status, _ = _request("POST", f"{server.base_url}/runs/run-finals-marker/simulate/full-season")
        assert status == 200

        status, _ = _request("POST", f"{server.base_url}/runs/run-finals-marker/simulate/next-match")
        assert status == 200
        status, _ = _request("POST", f"{server.base_url}/runs/run-finals-marker/simulate/next-round")
        assert status == 200

        status, _ = _request("GET", f"{server.base_url}/runs/run-finals-marker/finals/qualification")
        assert status == 200

        status, payload = _request("POST", f"{server.base_url}/runs/run-finals-marker/simulate/next-match")
        assert status == 400
        assert "finals phase has begun" in payload["detail"]

        status, payload = _request("POST", f"{server.base_url}/runs/run-finals-marker/simulate/next-round")
        assert status == 400
        assert "finals phase has begun" in payload["detail"]


def _preview_totals(payload: dict[str, object]) -> tuple[int, int]:
    weeks = payload["weeks"]
    country_totals = payload["country_totals"]
    assert isinstance(weeks, list)
    assert isinstance(country_totals, list)
    return (
        sum(int(week["total_allocated"]) for week in weeks),
        sum(int(country["allocated_count"]) for country in country_totals),
    )


def test_run_weekly_intake_cohort_season_preview_basic_success(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-basic.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-cohort", "seed": 4242, "season": 2027})
        assert status == 201
        status, payload = _request("GET", f"{server.base_url}/runs/run-cohort/weekly-intake/cohort-season/preview")
        assert status == 200
        assert payload["run_id"] == "run-cohort"
        assert payload["world_id"] == "official_fax_world"
        assert payload["season"] == "2027/2028"
        assert len(payload["weeks"]) == 61
        assert payload["annual_target"] > 0
        assert payload["total_weekly_target"] == payload["annual_target"]
        weekly_total, country_total = _preview_totals(payload)
        assert weekly_total == payload["annual_target"]
        assert country_total == payload["annual_target"]
        for week in payload["weeks"]:
            assert week["total_allocated"] == week["target_intake_count"]


def test_run_weekly_intake_cohort_season_preview_calendar_mapping(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-mapping.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-2000", "seed": 123, "season": 2000})
        assert status == 201
        status, payload = _request("GET", f"{server.base_url}/runs/run-2000/weekly-intake/cohort-season/preview")
        assert status == 200
        week_1 = payload["weeks"][0]
        week_26 = payload["weeks"][25]
        assert week_1["year_week"] == 37
        assert week_1["birth_year"] == 1985
        assert week_26["year_week"] == 1
        assert week_26["birth_year"] == 1986


def test_run_weekly_intake_cohort_season_preview_filters(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-filters.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-filters", "seed": 123, "season": 2027})
        assert status == 201
        status, ger = _request("GET", f"{server.base_url}/runs/run-filters/weekly-intake/cohort-season/preview?country_code=GER")
        assert status == 200
        assert {row["country_code"] for row in ger["country_totals"]} == {"GER"}
        assert all({allocation["country_code"] for allocation in week["allocations"]} <= {"GER"} for week in ger["weeks"])

        status, europe = _request("GET", f"{server.base_url}/runs/run-filters/weekly-intake/cohort-season/preview?region=EUROPE")
        assert status == 200
        assert len(europe["country_totals"]) > 0
        assert _preview_totals(europe)[0] == europe["annual_target"]


def test_run_weekly_intake_cohort_season_preview_zero_target(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-zero.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-zero", "seed": 123, "season": 2027})
        assert status == 201
        status, payload = _request("GET", f"{server.base_url}/runs/run-zero/weekly-intake/cohort-season/preview?base_annual_intake_target=0")
        assert status == 200
        assert payload["annual_target"] == 0
        assert payload["total_weekly_target"] == 0
        assert all(week["target_intake_count"] == 0 for week in payload["weeks"])
        assert all(week["total_allocated"] == 0 for week in payload["weeks"])
        assert payload["country_totals"] == []


def test_run_weekly_intake_cohort_season_preview_growth_bounds(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-growth.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-growth", "seed": 123, "season": 2027})
        assert status == 201
        status, _ = _request("GET", f"{server.base_url}/runs/run-growth/weekly-intake/cohort-season/preview?season_growth_rate=0.10")
        assert status == 200
        status, _ = _request("GET", f"{server.base_url}/runs/run-growth/weekly-intake/cohort-season/preview?season_growth_rate=0.11")
        assert status == 422
        status, _ = _request("GET", f"{server.base_url}/runs/run-growth/weekly-intake/cohort-season/preview?season_growth_rate=-0.01")
        assert status == 422


def test_run_weekly_intake_cohort_season_preview_errors(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-errors.db'}") as server:
        status, _ = _request("GET", f"{server.base_url}/runs/unknown/weekly-intake/cohort-season/preview")
        assert status == 404
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-before", "seed": 123, "season": 1999})
        assert status == 201
        status, _ = _request("GET", f"{server.base_url}/runs/run-before/weekly-intake/cohort-season/preview")
        assert status == 422
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-after", "seed": 123, "season": 2050})
        assert status == 201
        status, _ = _request("GET", f"{server.base_url}/runs/run-after/weekly-intake/cohort-season/preview")
        assert status == 422

        db_url = f"sqlite:///{tmp_path / 'run-cohort-errors.db'}"
        engine = create_engine(db_url)
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-missing-world", "seed": 123, "season": 2027})
        assert status == 201
        with engine.begin() as connection:
            connection.execute(text("UPDATE simulation_runs SET world_id = 'missing_world' WHERE run_id = 'run-missing-world'"))
        status, missing_world = _request("GET", f"{server.base_url}/runs/run-missing-world/weekly-intake/cohort-season/preview")
        assert status == 404
        assert "locked world package" in missing_world["detail"]


def test_run_weekly_intake_cohort_season_preview_read_only(tmp_path) -> None:
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'run-cohort-readonly.db'}") as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-readonly", "seed": 123, "season": 2027})
        assert status == 201
        status, before_run = _request("GET", f"{server.base_url}/runs/run-readonly")
        assert status == 200
        status, before_index = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        status, preview = _request("GET", f"{server.base_url}/runs/run-readonly/weekly-intake/cohort-season/preview")
        assert status == 200
        assert preview["annual_target"] > 0
        status, after_run = _request("GET", f"{server.base_url}/runs/run-readonly")
        assert status == 200
        status, after_index = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert after_run == before_run
        assert after_index == before_index


def test_run_prospects_endpoint_is_read_only_and_filterable(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api.db'}"
    with ApiServer(database_url=database_url) as server:
        status, missing = _request("GET", f"{server.base_url}/runs/missing/prospects")
        assert status == 404
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-prospects", "seed": 9090, "season": 2027})
        assert status == 201
        status, empty = _request("GET", f"{server.base_url}/runs/run-prospects/prospects")
        assert status == 200
        assert empty["prospects"] == []
        assert empty["total"] == 0

        prospect_id = _insert_api_test_prospect(database_url, run_id="run-prospects")
        status, payload = _request("GET", f"{server.base_url}/runs/run-prospects/prospects?country_code=EGY&status=prospect&season_start_year=2027&season_week=3")
        assert status == 200
        assert payload["total"] == 1
        assert payload["prospects"][0]["prospect_id"] == prospect_id
        assert payload["prospects"][0]["profile_version"] == "prospect_profile_v1"
        assert payload["prospects"][0]["profile_json"] == {"foundation": True}

        status, unmatched = _request("GET", f"{server.base_url}/runs/run-prospects/prospects?country_code=ENG")
        assert status == 200
        assert unmatched["prospects"] == []


def test_run_prospects_materialize_15yo_cohort_basic_idempotent_filter_and_zero(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'materialize.db'}"
    with ApiServer(database_url=database_url) as server:
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-materialize", "seed": 9090, "season": 2027})
        assert status == 201

        status, payload = _request("POST", f"{server.base_url}/runs/run-materialize/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 6})
        assert status == 200
        assert payload["run_id"] == "run-materialize"
        assert payload["world_id"] == "official_fax_world"
        assert payload["requested_prospect_count"] == payload["annual_target"]
        assert payload["created_count"] == payload["annual_target"]
        assert payload["existing_count"] == 0

        status, listed = _request("GET", f"{server.base_url}/runs/run-materialize/prospects?limit=500")
        assert status == 200
        assert listed["total"] == payload["annual_target"]
        for prospect in listed["prospects"]:
            assert prospect["age"] == 15
            assert prospect["status"] == "prospect"
            assert prospect["source_type"] == "weekly_15yo_cohort"
            assert prospect["world_id"] == "official_fax_world"
            assert prospect["profile_version"] == "prospect_profile_v1"
            assert prospect["display_name"]
            assert all(prospect[key] for key in ["identity_seed", "profile_seed", "development_seed", "potential_seed", "trait_seed"])
            assert prospect["profile_json"]["reserved_for_future_attributes"] is True
            assert prospect["development_json"]["reserved_for_future_development"] is True
            assert prospect["potential_json"]["reserved_for_future_potential"] is True
            assert prospect["trait_json"]["reserved_for_future_traits"] is True

        status, again = _request("POST", f"{server.base_url}/runs/run-materialize/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 6})
        assert status == 200
        assert again["created_count"] == 0
        assert again["skipped_count"] == payload["annual_target"]
        assert again["already_materialized"] is True

        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-materialize-filter", "seed": 9091, "season": 2027})
        assert status == 201
        status, ger = _request("POST", f"{server.base_url}/runs/run-materialize-filter/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 3, "country_code": "GER"})
        assert status == 200
        assert ger["requested_prospect_count"] == ger["annual_target"]
        status, listed_ger = _request("GET", f"{server.base_url}/runs/run-materialize-filter/prospects?country_code=GER&limit=500")
        assert status == 200
        assert listed_ger["total"] >= 3
        assert {p["country_code"] for p in listed_ger["prospects"]} == {"GER"}

        status, zero = _request("POST", f"{server.base_url}/runs/run-materialize/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 0})
        assert status == 200
        assert zero["requested_prospect_count"] == 0
        assert zero["created_count"] == 0


def test_run_prospects_materialize_15yo_cohort_conflict_overwrite_and_errors(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'materialize-conflict.db'}"
    with ApiServer(database_url=database_url) as server:
        status, missing = _request("POST", f"{server.base_url}/runs/missing/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 1})
        assert status == 404
        status, _ = _request("POST", f"{server.base_url}/runs", {"run_id": "run-conflict", "seed": 9090, "season": 2027})
        assert status == 201
        status, first = _request("POST", f"{server.base_url}/runs/run-conflict/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 2, "country_code": "GER"})
        assert status == 200
        assert first["created_count"] == first["annual_target"]

        engine = create_sqlite_engine(DatabaseSettings(url=database_url))
        repository = SimulationPersistenceRepository(engine=engine, session_factory=create_session_factory(engine))
        record = repository.list_run_prospects(run_id="run-conflict", country_code="GER", limit=None)[0]
        repository.upsert_run_prospects([RunProspectRecord(**(record.__dict__ | {"profile_json": {"tampered": True}}))])

        status, conflict = _request("POST", f"{server.base_url}/runs/run-conflict/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 2, "country_code": "GER"})
        assert status == 409
        assert record.prospect_id in conflict["detail"]["conflicts"]

        status, repaired = _request("POST", f"{server.base_url}/runs/run-conflict/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 2, "country_code": "GER", "overwrite": True})
        assert status == 200
        assert repaired["conflict_count"] == 1
        assert repository.get_run_prospect(run_id="run-conflict", prospect_id=record.prospect_id).profile_json != {"tampered": True}

        status, policy_conflict = _request(
            "POST",
            f"{server.base_url}/runs/run-conflict/prospects/materialize-15yo-cohort",
            {"base_annual_intake_target": 4, "country_code": "GER"},
        )
        assert status == 409
        assert policy_conflict["detail"]["conflicts"]
        status, policy_overwrite = _request(
            "POST",
            f"{server.base_url}/runs/run-conflict/prospects/materialize-15yo-cohort",
            {"base_annual_intake_target": 4, "country_code": "GER", "overwrite": True},
        )
        assert status == 200
        assert policy_overwrite["conflict_count"] > 0
        assert repository.count_run_prospects(
            run_id="run-conflict",
            country_code="GER",
            season_start_year=2027,
        ) == policy_overwrite["requested_prospect_count"]

        status, bad_season = _request("POST", f"{server.base_url}/runs", {"run_id": "run-before-materialize", "seed": 1, "season": 1999})
        assert status == 201
        status, unsupported = _request("POST", f"{server.base_url}/runs/run-before-materialize/prospects/materialize-15yo-cohort", {"base_annual_intake_target": 1})
        assert status == 422
