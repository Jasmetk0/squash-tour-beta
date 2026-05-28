from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from urllib import error, parse, request
from uuid import uuid4

import pytest
import uvicorn

from beta_engine.main import create_app


CREATE_ONLY_CONFIRMATION = "I understand this will create a new season calendar."
CREATE_ONLY_COMMAND_PATH = "/admin/seasons/builder/apply-create-only-command"


def write_templates(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "template_id": "wt_a",
                        "tour_level": "WORLD_TOUR",
                        "category": "PLATINUM",
                        "event_name": "World A",
                        "region": "EUROPE",
                        "host_country": "ENG",
                        "main_draw_size": 32,
                        "qualification_draw_size": 16,
                        "seeds_count": 8,
                        "qualifier_spots": 4,
                        "wild_cards": 2,
                        "byes": 0,
                        "lucky_loser_rules": {
                            "enabled": True,
                            "max_spots": 2,
                            "replacement_window": "pre_main_draw_round_1",
                        },
                        "point_distribution_ref": "world",
                        "prize_money": 100000,
                        "prestige": 9,
                        "event_duration_days": 6,
                        "qualification_duration_days": 2,
                        "duration_in_season_weeks": 1,
                        "active": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        method=method,
    )
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        body = json.loads(exc.read().decode())
        if isinstance(body.get("detail"), dict):
            return exc.code, body["detail"]
        return exc.code, body


def free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, tmp_path: Path) -> None:
        self.port = free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.registry_path = tmp_path / "season_calendars.json"
        template_path = tmp_path / "templates.json"
        write_templates(template_path)
        app = create_app(
            database_url=f"sqlite:///{tmp_path / f'api-{uuid4().hex}.db'}",
            tournament_templates_config_path=str(template_path),
            season_calendar_registry_path=str(self.registry_path),
        )
        self.server = uvicorn.Server(
            uvicorn.Config(app=app, host="127.0.0.1", port=self.port, log_level="error")
        )
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
        if self.thread.is_alive():
            raise RuntimeError("server did not shut down")


def build_valid_payload(server: Server, season: str = "2035/2036") -> dict:
    preflight_payload = {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
    }
    preflight_status, preflight = call(
        "POST", f"{server.base_url}/admin/seasons/builder/preflight", preflight_payload
    )
    assert preflight_status == 200
    dry_run_status, dry_run = call(
        "POST",
        f"{server.base_url}/admin/seasons/builder/dry-run-build",
        {
            "target_season_label": season,
            "source_type": "season_template",
            "source_template_id": "default_msa_template_preview",
            "preflight_fingerprint": preflight["preflight_fingerprint"],
            "reviewed_diff_id": preflight["reviewed_diff_id"],
            "requested_by": "qa",
            "audit_reason": "phase24b negative apply coverage",
            "explicit_confirmation": CREATE_ONLY_CONFIRMATION,
            "mutation_scope": "create_only",
        },
    )
    assert dry_run_status == 200
    dry_run_preview = dry_run["dry_run_result_preview"]
    assert dry_run_preview["candidate_events"]
    return {
        "target_season_label": season,
        "source_type": "season_template",
        "source_template_id": "default_msa_template_preview",
        "overwrite_policy": None,
        "preflight_fingerprint": preflight["preflight_fingerprint"],
        "reviewed_diff_id": preflight["reviewed_diff_id"],
        "dry_run_result_fingerprint": dry_run_preview["dry_run_result_fingerprint"],
        "dry_run_result_id": dry_run_preview["dry_run_result_id"],
        "requested_by": "qa",
        "audit_reason": "phase24b negative apply coverage",
        "explicit_confirmation": CREATE_ONLY_CONFIRMATION,
        "mutation_scope": "create_only",
    }


def calendar_url(server: Server, season: str) -> str:
    return f"{server.base_url}/admin/seasons/{parse.quote(season, safe='')}/calendar"


def validation_url(server: Server, season: str) -> str:
    return f"{server.base_url}/admin/seasons/{parse.quote(season, safe='')}/calendar/validation"


def read_persisted_calendar(server: Server, season: str) -> dict | None:
    if not server.registry_path.exists():
        return None
    registry = json.loads(server.registry_path.read_text(encoding="utf-8"))
    return registry.get("calendars_by_season", {}).get(season)


def assert_command_rejected_without_application(
    status: int,
    body: dict,
    *,
    expected_status: int | set[int] = {400, 409, 422},
) -> None:
    expected_statuses = {expected_status} if isinstance(expected_status, int) else expected_status
    assert status in expected_statuses
    if "applied" in body:
        assert body["applied"] is False
        assert body["can_mutate"] is False
        assert body["created_calendar_summary"] == {}
        assert body["created_event_preview"] == []
        assert body["created_calendar_validation_preview"] == {}


def assert_target_calendar_absent(server: Server, season: str) -> None:
    status, calendar = call("GET", calendar_url(server, season))
    assert status == 200
    assert calendar["calendar"] is None
    assert calendar["summary"]["calendar_exists"] is False

    validation_status, validation = call("GET", validation_url(server, season))
    assert validation_status == 200
    assert validation["calendar_exists"] is False
    assert validation["validation_summary"]["event_count"] == 0

    assert read_persisted_calendar(server, season) is None

    readiness_payload = build_valid_payload(server, season=season)
    readiness_status, readiness = call(
        "POST",
        f"{server.base_url}/admin/seasons/builder/apply-create-only-readiness",
        readiness_payload,
    )
    assert readiness_status == 200
    assert readiness["can_execute_apply"] is True
    assert readiness["would_create_calendar"] is True
    assert readiness["apply_gate_summary"]["target_absent_before_apply"] is True


def apply_create_only(server: Server, payload: dict) -> tuple[int, dict]:
    return call("POST", f"{server.base_url}{CREATE_ONLY_COMMAND_PATH}", payload)


@pytest.mark.parametrize(
    ("field", "value", "expected_status"),
    [
        pytest.param("explicit_confirmation", "I understand.", 400, id="wrong-confirmation-phrase"),
        pytest.param("mutation_scope", "merge_preview", 400, id="wrong-mutation-scope-preview"),
        pytest.param("mutation_scope", "repair", 400, id="wrong-mutation-scope-repair"),
        pytest.param("source_type", "calendar_clone", 400, id="wrong-source-type"),
        pytest.param("source_template_id", None, 400, id="missing-source-template-id-null"),
        pytest.param("source_template_id", "", 422, id="missing-source-template-id-empty"),
        pytest.param("dry_run_result_fingerprint", "drf_stale", 400, id="stale-dry-run-fingerprint"),
        pytest.param("dry_run_result_id", "drr_stale", 400, id="stale-dry-run-id"),
        pytest.param("overwrite_policy", "merge", 400, id="merge-overwrite-policy-attempt"),
        pytest.param("overwrite_policy", "overwrite", 400, id="overwrite-policy-attempt"),
        pytest.param("requested_by", "", 400, id="missing-requested-by-empty"),
        pytest.param("requested_by", None, 422, id="missing-requested-by-null"),
        pytest.param("audit_reason", "", 400, id="missing-audit-reason-empty"),
        pytest.param("audit_reason", None, 422, id="missing-audit-reason-null"),
    ],
)
def test_apply_create_only_guard_rejections_do_not_create_calendar(
    tmp_path: Path,
    field: str,
    value: object,
    expected_status: int,
) -> None:
    season = "2035/2036"
    with Server(tmp_path) as server:
        payload = build_valid_payload(server, season=season)
        payload[field] = value

        status, body = apply_create_only(server, payload)

        assert_command_rejected_without_application(status, body, expected_status=expected_status)
        assert_target_calendar_absent(server, season)


def test_apply_create_only_rejects_target_that_already_exists_without_modifying_it(
    tmp_path: Path,
) -> None:
    season = "2036/2037"
    with Server(tmp_path) as server:
        first_payload = build_valid_payload(server, season=season)
        first_status, first_body = apply_create_only(server, first_payload)
        assert first_status == 200
        assert first_body["applied"] is True
        before_status, before_calendar = call("GET", calendar_url(server, season))
        assert before_status == 200
        before_persisted = read_persisted_calendar(server, season)
        assert before_persisted is not None

        second_payload = build_valid_payload(server, season=season)
        status, body = apply_create_only(server, second_payload)

        assert_command_rejected_without_application(status, body, expected_status=409)
        after_status, after_calendar = call("GET", calendar_url(server, season))
        assert after_status == 200
        assert after_calendar == before_calendar
        assert len(after_calendar["calendar"]["events"]) == len(before_calendar["calendar"]["events"])
        assert read_persisted_calendar(server, season) == before_persisted


def test_apply_create_only_rejects_identical_duplicate_request_after_success(
    tmp_path: Path,
) -> None:
    season = "2037/2038"
    with Server(tmp_path) as server:
        payload = build_valid_payload(server, season=season)
        first_status, first_body = apply_create_only(server, copy.deepcopy(payload))
        assert first_status == 200
        assert first_body["applied"] is True
        before_status, before_calendar = call("GET", calendar_url(server, season))
        assert before_status == 200
        before_persisted = read_persisted_calendar(server, season)
        assert before_persisted is not None
        before_event_count = len(before_calendar["calendar"]["events"])

        status, body = apply_create_only(server, copy.deepcopy(payload))

        assert_command_rejected_without_application(status, body, expected_status=409)
        after_status, after_calendar = call("GET", calendar_url(server, season))
        assert after_status == 200
        assert len(after_calendar["calendar"]["events"]) == before_event_count
        assert after_calendar == before_calendar
        assert read_persisted_calendar(server, season) == before_persisted
