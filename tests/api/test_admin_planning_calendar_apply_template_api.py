from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib import error, parse, request
from uuid import uuid4

import uvicorn

from beta_engine.application.calendar_template_compare_service import CalendarTemplateCompareDryRunRequest, CalendarTemplateCompareService
from beta_engine.application.calendar_template_service import CalendarTemplate, CalendarTemplateService
from beta_engine.application.planning_calendar_apply_template_service import REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION
from beta_engine.application.planning_season_calendar_service import PlanningSeasonCalendar, PlanningSeasonCalendarRegistry, PlanningSeasonCalendarService
from beta_engine.main import create_app


def call(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    req = request.Request(url, data=None if payload is None else json.dumps(payload).encode(), method=method)
    req.add_header("content-type", "application/json")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode()
        body = json.loads(raw) if raw else {}
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
        self.template_path = tmp_path / "calendar_templates.json"
        self.planning_path = tmp_path / "planning_season_calendars.json"
        self.season_calendar_path = tmp_path / "season_calendars.json"
        self.audit_path = tmp_path / "planning_calendar_apply_audit.jsonl"
        self.backup_dir = tmp_path / "planning_calendar_apply_backups"
        app = create_app(
            database_url=f"sqlite:///{tmp_path / f'api-{uuid4().hex}.db'}",
            calendar_templates_registry_path=str(self.template_path),
            planning_season_calendar_registry_path=str(self.planning_path),
            season_calendar_registry_path=str(self.season_calendar_path),
            planning_calendar_apply_audit_log_path=str(self.audit_path),
            planning_calendar_apply_backup_dir=str(self.backup_dir),
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


def write_template(path: Path) -> CalendarTemplate:
    service = CalendarTemplateService(registry_path=path)
    return service.create_template(
        template=CalendarTemplate.model_validate(
            {
                "id": "template-a",
                "name": "Template A",
                "status": "draft",
                "events": [
                    {
                        "id": "event-a",
                        "name": "Event A",
                        "category_code": "DIAMOND",
                        "weeks": [6],
                        "qualification_weeks": [5],
                        "locked": False,
                        "country_code": "EGY",
                        "city": "Cairo",
                    }
                ],
            }
        )
    )


def write_planning(path: Path, events: list[dict] | None = None) -> PlanningSeasonCalendar:
    calendar = PlanningSeasonCalendar.model_validate(
        {
            "season_label": "2000/01",
            "normalized_season_label": "2000/01",
            "status": "draft",
            "events": events or [],
            "metadata": {"source": "api-test"},
        }
    )
    path.write_text(json.dumps(PlanningSeasonCalendarRegistry(calendars_by_season={calendar.normalized_season_label: calendar}).model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    return calendar


def valid_payload(server: Server, **overrides) -> dict:
    template = CalendarTemplateService(registry_path=server.template_path).get_template(template_id="template-a").template
    assert template is not None
    planning_service = PlanningSeasonCalendarService(registry_path=server.planning_path)
    calendar = planning_service.get_calendar("2000/01")
    assert calendar is not None
    diff = CalendarTemplateCompareService(
        template_service=CalendarTemplateService(registry_path=server.template_path),
        planning_calendar_service=planning_service,
    ).compare_dry_run(
        CalendarTemplateCompareDryRunRequest(
            target_season_label="2000/01",
            source_template_id="template-a",
            target_source="planning_calendar",
            policy=overrides.get("policy", "copy_missing_only") if overrides.get("policy", "copy_missing_only") != "replace_all" else "copy_missing_only",
            selected_source_event_ids=overrides.get("selected_source_event_ids"),
        )
    )
    payload = {
        "source_template_id": "template-a",
        "policy": "copy_missing_only",
        "selected_source_event_ids": None,
        "expected_planning_calendar_fingerprint": calendar.calendar_fingerprint,
        "source_template_fingerprint": template.template_fingerprint,
        "reviewed_diff_fingerprint": diff.diff_fingerprint,
        "requested_by": "api-qa",
        "audit_reason": "reviewed planning apply diff",
        "explicit_confirmation": REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
    }
    payload.update(overrides)
    return payload


def apply_url(server: Server, season: str = "2000/01") -> str:
    return f"{server.base_url}/admin/seasons/planning-calendars/{parse.quote(season, safe='')}/apply-template"


def test_successful_apply_endpoint_creates_event_audit_and_backup_without_season_calendar(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        write_template(server.template_path)
        before = write_planning(server.planning_path)
        status, body = call("POST", apply_url(server), valid_payload(server))

        assert status == 200
        assert body["mutation_performed"] is True
        assert body["created_event_count"] == 1
        saved = PlanningSeasonCalendarService(registry_path=server.planning_path).get_calendar("2000/01")
        assert saved is not None
        assert saved.calendar_fingerprint != before.calendar_fingerprint
        assert server.audit_path.exists()
        assert len(server.audit_path.read_text(encoding="utf-8").splitlines()) == 2
        assert list(server.backup_dir.rglob("*.before.json"))
        assert not server.season_calendar_path.exists()


def test_missing_planning_calendar_returns_404_and_no_mutation(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        write_template(server.template_path)
        status, _ = call("POST", apply_url(server), {
            "source_template_id": "template-a",
            "policy": "copy_missing_only",
            "expected_planning_calendar_fingerprint": "pl_cal_missing",
            "source_template_fingerprint": "tpl_missing",
            "reviewed_diff_fingerprint": "diff_missing",
            "requested_by": "api-qa",
            "audit_reason": "reviewed",
            "explicit_confirmation": REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
        })
        assert status == 404
        assert not server.planning_path.exists()
        assert not server.season_calendar_path.exists()


def test_missing_source_template_returns_404_and_no_mutation(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        write_planning(server.planning_path)
        status, _ = call("POST", apply_url(server), {
            "source_template_id": "missing",
            "policy": "copy_missing_only",
            "expected_planning_calendar_fingerprint": "pl_cal_missing",
            "source_template_fingerprint": "tpl_missing",
            "reviewed_diff_fingerprint": "diff_missing",
            "requested_by": "api-qa",
            "audit_reason": "reviewed",
            "explicit_confirmation": REQUIRED_PLANNING_CALENDAR_APPLY_CONFIRMATION,
        })
        assert status == 404
        assert not server.season_calendar_path.exists()


import pytest


@pytest.mark.parametrize(
    ("override", "expected_status"),
    [
        ({"expected_planning_calendar_fingerprint": "pl_cal_stale"}, 409),
        ({"source_template_fingerprint": "tpl_stale"}, 409),
        ({"reviewed_diff_fingerprint": "diff_stale"}, 409),
        ({"explicit_confirmation": "wrong"}, 400),
        ({"policy": "replace_unlocked_only"}, 400),
    ],
)
def test_apply_endpoint_rejections_have_no_mutation(tmp_path: Path, override: dict, expected_status: int) -> None:
    with Server(tmp_path) as server:
        write_template(server.template_path)
        write_planning(server.planning_path)
        before = server.planning_path.read_text(encoding="utf-8")
        payload = valid_payload(server)
        payload.update(override)

        status, body = call("POST", apply_url(server), payload)

        assert status == expected_status
        assert body["mutation_performed"] is False
        assert server.planning_path.read_text(encoding="utf-8") == before
        assert server.audit_path.exists()
        assert not server.season_calendar_path.exists()


def test_bare_planning_calendars_post_and_viewer_route_remain_unavailable(tmp_path: Path) -> None:
    with Server(tmp_path) as server:
        status, _ = call("POST", f"{server.base_url}/admin/seasons/planning-calendars", {})
        assert status in {404, 405}
        status, _ = call("POST", f"{server.base_url}/planning-calendars/2000%2F01/apply-template", {})
        assert status == 404
