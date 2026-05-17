from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import request
from urllib.error import HTTPError

import uvicorn

from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer, SeasonActivePlayersRegistry
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.main import create_app


def write_countries(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"countries": [
        {"code": "AAA", "name": "Alpha", "region": "EUROPE", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5, "travel_region": "EUROPE"},
        {"code": "BBB", "name": "Beta", "region": "ASIA", "population": 5_000_000, "wealth_support": 5, "squash_popularity": 5, "squash_tradition": 5, "system_quality": 5, "travel_region": "ASIA"},
    ]}), encoding="utf-8")


def write_templates(path: Path, *, main_draw_size: int = 8) -> None:
    path.write_text(json.dumps({"templates": [{
        "template_id": "wt_a", "tour_level": "WORLD_TOUR", "category": "PLATINUM", "event_name": "World A", "region": "EUROPE", "host_country": "AAA", "main_draw_size": main_draw_size, "qualification_draw_size": 4, "seeds_count": 4, "qualifier_spots": 2, "wild_cards": 1, "byes": 0, "lucky_loser_rules": {"enabled": True, "max_spots": 2, "replacement_window": "pre_main_draw_round_1"}, "point_distribution_ref": "world", "prize_money": 100000, "prestige": 9, "event_duration_days": 6, "qualification_duration_days": 2, "duration_in_season_weeks": 1, "active": True
    }]}), encoding="utf-8")


def active_player(index: int, country: str = "AAA", ability: int = 88) -> SeasonActivePlayer:
    return SeasonActivePlayer(
        player_id=f"P{index:03d}", name=f"Player {index:03d}", country_code=country, nationality=country,
        birth_year=1975, birth_year_week=1, age_years_at_season_start=25, age_weeks_at_season_start=1300,
        current_ability=ability, potential_ability=max(ability, 90), potential_tier="A", career_stage="prime", play_style="balanced", archetype="all_court",
        attributes=GeneratedPlayerAttributes(technique=ability, movement=ability, physical=ability, mental=ability, consistency=ability, clutch=ability, recovery=ability),
        hidden_career_traits=HiddenCareerTraits(potential_ceiling=max(ability, 90), growth_curve="steady", professionalism=0.9, ambition=0.9, travel_tolerance=0.9, schedule_aggression=0.9, injury_proneness=0.1, resilience=0.9),
        season="2000/2001", source_pool_player_id=f"P{index:03d}", source_generation_fingerprint=f"src-{index}", source_generation="initial_pool", manual_override=False, locked_from_initial_pool=True, bootstrap_fingerprint=f"boot-{index}", bootstrap_seed=1, bootstrap_id="BOOT-test"
    )


def write_active(path: Path, count: int = 20) -> None:
    players = [active_player(i, "AAA" if i % 2 else "BBB", 90 - (i % 10)) for i in range(1, count + 1)]
    registry = SeasonActivePlayersRegistry(players_by_season={"2000/2001": players}, bootstrap_metadata_by_season={})
    path.write_text(json.dumps(registry.model_dump(mode="json")), encoding="utf-8")


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    with request.urlopen(req, timeout=60) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def free_port() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path, *, active: bool = True) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        countries_path = tmp_path / "countries.json"; write_countries(countries_path)
        templates_path = tmp_path / "templates.json"; write_templates(templates_path)
        active_path = tmp_path / "active.json"
        if active:
            write_active(active_path)
        self.entry_path = tmp_path / "entries.json"
        app = create_app(
            database_url=f"sqlite:///{tmp_path / 'api.db'}",
            countries_config_path=str(countries_path),
            tournament_templates_config_path=str(templates_path),
            calendar_config_dir=str(tmp_path / "legacy"),
            season_active_players_config_path=str(active_path),
            season_calendar_registry_path=str(tmp_path / "calendars.json"),
            season_entry_lists_registry_path=str(self.entry_path),
        )
        self.server = uvicorn.Server(uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                call("GET", f"{self.base_url}/health")
                return self
            except OSError:
                time.sleep(0.05)
        raise RuntimeError("server did not start")

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)

    def persist_calendar(self) -> str:
        _, body = call("POST", f"{self.base_url}/admin/seasons/2000%2F2001/calendar/build", {"seed": 1, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": 1})
        return body["calendar"]["events"][0]["event_id"]


def test_get_empty_entry_list_state(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, body = call("GET", f"{server.base_url}/admin/entries/EVT-missing")
        assert status == 200
        assert body["entry_list"] is None
        assert body["entry_list_exists"] is False


def test_post_dry_run_and_persist_entry_list(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        payload = {"seed": 123, "dry_run": True, "overwrite_existing": False, "max_alternates": 4, "include_not_entered": True}
        status, preview = call("POST", f"{server.base_url}/admin/entries/{event_id}/generate", payload)
        assert status == 200
        assert preview["entry_list"]["summary"]["total_active_players"] == 20
        assert not server.entry_path.exists()

        payload["dry_run"] = False
        status, persisted = call("POST", f"{server.base_url}/admin/entries/{event_id}/generate", payload)
        assert status == 200
        assert persisted["entry_list"]["persisted"] is True
        _, loaded = call("GET", f"{server.base_url}/admin/entries/{event_id}")
        assert loaded["entry_list_exists"] is True
        assert loaded["metadata"]["build_fingerprint"] == persisted["metadata"]["build_fingerprint"]


def test_overwrite_safety_and_missing_prerequisites(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        event_id = server.persist_calendar()
        payload = {"seed": 123, "dry_run": False, "overwrite_existing": False, "max_alternates": 4, "include_not_entered": False}
        call("POST", f"{server.base_url}/admin/entries/{event_id}/generate", payload)
        try:
            call("POST", f"{server.base_url}/admin/entries/{event_id}/generate", payload)
        except HTTPError as exc:
            assert exc.code == 400
            assert "already exists" in exc.read().decode()
        else:
            raise AssertionError("overwrite safety should reject existing entry list")

    with Server(tmp_path / "missing", active=False) as server:
        event_id = server.persist_calendar()
        try:
            call("POST", f"{server.base_url}/admin/entries/{event_id}/generate", {"seed": 123, "dry_run": True, "overwrite_existing": False, "max_alternates": 4, "include_not_entered": False})
        except HTTPError as exc:
            assert exc.code == 400
            assert "No active season players" in exc.read().decode()
        else:
            raise AssertionError("missing active players should fail")
