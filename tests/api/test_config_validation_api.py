from __future__ import annotations

import json
import socket
import threading
import time
from unittest.mock import patch
from urllib import error, request

import uvicorn

from beta_engine.domain.countries.models import CountriesConfig
from beta_engine.domain.entries.models import EntryTuningConfig
from beta_engine.domain.tournaments.models import SeasonCalendar, TournamentTemplatesConfig
from beta_engine.infrastructure.world_config import PlayerIdentityConfig
from beta_engine.main import create_app


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


def test_config_validation_endpoint_reports_structured_result_for_live_config(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-config-live.db'}"
    with ApiServer(database_url=database_url) as server:
        status, payload = _request("GET", f"{server.base_url}/config/validation")
        assert status == 200
        assert payload["valid"] == (len(payload["errors"]) == 0)

        covered_domains = {domain["domain"] for domain in payload["domains"]}
        assert covered_domains == {
            "season_calendar",
            "tournament_templates",
            "countries",
            "player_identity",
            "points",
            "entry_tuning",
        }

        expected_top_level_keys = {"valid", "warnings", "errors", "domains"}
        assert set(payload.keys()) == expected_top_level_keys


def test_config_validation_endpoint_can_return_successful_report(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-config-success.db'}"
    with patch(
        "beta_engine.application.config_validation_service.load_season_calendar",
        return_value=SeasonCalendar.model_validate({
            "season": 2027,
            "events": [
                {
                    "event_id": "ev_2027_w01_test",
                    "season": 2027,
                    "week": 1,
                    "template_id": "template_1",
                    "start_day": "Mon",
                    "region": "Europe",
                    "host_country": "ENG",
                    "is_world_tour": True,
                    "is_elite_tour": False,
                    "cluster_id": "cluster-1",
                    "travel_group": "EU",
                    "status": "scheduled",
                }
            ],
        }),
    ), patch(
        "beta_engine.application.config_validation_service.load_tournament_templates_config",
        return_value=TournamentTemplatesConfig.model_validate({
            "templates": [
                {
                    "template_id": "template_1",
                    "tour_level": "WORLD_TOUR",
                    "category": "PLATINUM",
                    "event_name": "Test Open",
                    "region": "Europe",
                    "host_country": "ENG",
                    "main_draw_size": 32,
                    "qualification_draw_size": 16,
                    "seeds_count": 8,
                    "qualifier_spots": 4,
                    "wild_cards": 2,
                    "byes": 0,
                    "lucky_loser_rules": {"enabled": True, "max_spots": 2},
                    "point_distribution_ref": "WT_PLATINUM",
                    "event_duration_days": 6,
                    "qualification_duration_days": 2,
                }
            ]
        }),
    ), patch(
        "beta_engine.application.config_validation_service.WorldPackageCountryStore.load_config",
        return_value=CountriesConfig.model_validate({
            "countries": [
                {
                    "code": "ENG",
                    "name": "England",
                    "region": "Europe",
                    "population": 1,
                    "flag_asset": None,
                    "squash_popularity": 5,
                    "wealth_support": 5,
                    "squash_tradition": 5,
                    "system_quality": 5,
                }
            ]
        }),
    ), patch(
        "beta_engine.application.config_validation_service.load_player_identity_config",
        return_value=PlayerIdentityConfig.model_validate({
            "given_names": ["A"],
            "family_names": ["B"],
            "play_styles": ["ATTACK"],
            "archetypes": ["ALL_ROUNDER"],
            "growth_curves": ["LINEAR"],
        }),
    ), patch(
        "beta_engine.application.config_validation_service.load_points_config",
        return_value={"WT_PLATINUM": {"winner": 1000}},
    ), patch(
        "beta_engine.application.config_validation_service.load_entry_tuning_config",
        return_value=EntryTuningConfig.model_validate({"main_quality_target": 0.6}),
    ):
        with ApiServer(database_url=database_url) as server:
            status, payload = _request("GET", f"{server.base_url}/config/validation")
            assert status == 200
            assert payload["valid"] is True
            assert payload["warnings"] == []
            assert payload["errors"] == []
            assert all(domain["valid"] is True for domain in payload["domains"])


def test_config_validation_endpoint_surfaces_loader_failure(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-config-invalid.db'}"
    with patch(
        "beta_engine.application.config_validation_service.load_points_config",
        side_effect=ValueError("points config must contain non-empty point_distributions mapping"),
    ):
        with ApiServer(database_url=database_url) as server:
            status, payload = _request("GET", f"{server.base_url}/config/validation")
            assert status == 200
            assert payload["valid"] is False
            assert len(payload["errors"]) == 1

            error_issue = payload["errors"][0]
            assert error_issue["severity"] == "error"
            assert error_issue["domain"] == "points"
            assert error_issue["check_id"] == "load_error"
            assert "point_distributions" in error_issue["message"]

            points_domain = next(domain for domain in payload["domains"] if domain["domain"] == "points")
            assert points_domain["valid"] is False
            assert len(points_domain["errors"]) == 1


def test_config_validation_endpoint_is_read_only_for_run_state(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'api-config-readonly.db'}"
    with ApiServer(database_url=database_url) as server:
        status, before_runs = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert before_runs == {"runs": []}

        status, validation_payload = _request("GET", f"{server.base_url}/config/validation")
        assert status == 200
        assert "valid" in validation_payload

        status, after_runs = _request("GET", f"{server.base_url}/runs")
        assert status == 200
        assert after_runs == before_runs
