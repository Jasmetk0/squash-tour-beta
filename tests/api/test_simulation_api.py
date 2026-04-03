from __future__ import annotations

import json
import socket
import threading
import time
from urllib import error, request

import uvicorn

from beta_engine.main import create_app
from beta_engine.core import DeterministicRng
from beta_engine.domain.countries import CountryTalentModel
from beta_engine.domain.players import PlayerGenerator
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config


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


def _generated_player_ids(seed: int, per_country: int = 24) -> list[str]:
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    ids: list[str] = []
    for country in load_countries_config().countries:
        ids.extend(generator.generate(country=country, sequence=index + 1).player_id for index in range(per_country))
    return ids


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
        for player_id in _generated_player_ids(seed=5151):
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

        status, after_assign = _request(
            "GET",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
        )
        assert status == 200
        assert after_assign["slots"][0]["assigned_player_id"] == assigned_player_id

        selected_index = next(index for index, event in enumerate(ordered_events) if event["event_id"] == selected_event_id)
        for _ in range(selected_index + 1):
            status, sim_result = _request("POST", f"{server.base_url}/runs/run-wildcards/simulate/next-tournament")
            assert status == 200

        completed_input = sim_result["step"]["tournament_result"]["acceptance_list"]["main_draw_entries"]
        wildcard_entries = [entry for entry in completed_input if entry["status"] == "WILD_CARD_PLACEHOLDER"]
        assert wildcard_entries
        assert wildcard_entries[0]["player_id"] == assigned_player_id

        status, rejected_after_start = _request(
            "POST",
            f"{server.base_url}/runs/run-wildcards/events/{selected_event_id}/wildcards",
            {"assignments": [{"slot_index": 1, "player_id": assigned_player_id}]},
        )
        assert status == 400
        assert "completed events" in rejected_after_start["detail"]


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
