from __future__ import annotations

import json
from urllib.error import HTTPError

from tests.api.test_admin_season_calendar_api import Server, call


BUILD = {"seed": 5, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2000, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": 1}


def build(server: Server) -> tuple[str, dict]:
    _, body = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/calendar/build", BUILD)
    event = body["calendar"]["events"][0]
    return event["event_id"], event


def patch(server: Server, event_id: str, payload: dict):
    return call("PATCH", f"{server.base_url}/admin/seasons/2000%2F01/calendar/events/{event_id}/ranking", payload)


def error_body(exc: HTTPError) -> dict:
    return json.loads(exc.read().decode())


def test_planned_edition_ranking_status_and_points_round_trip(tmp_path):
    with Server(tmp_path) as server:
        event_id, _ = build(server)
        status, unranked = patch(server, event_id, {"ranking_status": "unranked", "ranking_points_table": {}})
        assert status == 200
        assert unranked["ranking_status"] == "unranked"
        assert unranked["points_table_complete"] is True
        assert unranked["missing_required_point_stages"] == []

        table = {stage: index * 10 for index, stage in enumerate(unranked["required_ranking_point_stages"], start=1)}
        _, ranked = patch(server, event_id, {"ranking_status": "ranked", "ranking_points_table": table})
        assert ranked["ranking_status"] == "ranked"
        assert ranked["ranking_points_table"] == table
        assert ranked["points_table_complete"] is True
        assert ranked["missing_required_point_stages"] == []
        _, loaded = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/calendar")
        assert loaded["calendar"]["events"][0]["ranking_points_table"] == table


def test_invalid_status_returns_controlled_client_error(tmp_path):
    with Server(tmp_path) as server:
        event_id, _ = build(server)
        try:
            patch(server, event_id, {"ranking_status": "exhibition", "ranking_points_table": {}})
        except HTTPError as exc:
            assert exc.code == 400
            assert error_body(exc)["detail"]
        else:
            raise AssertionError("invalid ranking status should fail validation")


def test_non_editable_rejection_is_atomic(tmp_path):
    registry_path = tmp_path / "season_calendars.json"
    with Server(tmp_path) as server:
        event_id, original = build(server)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["calendars_by_season"]["2000/2001"]["events"][0]["status"] = "active"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        before = registry_path.read_bytes()
        try:
            patch(server, event_id, {"ranking_status": "unranked", "ranking_points_table": {}})
        except HTTPError as exc:
            assert exc.code == 400
            assert "after competition has begun" in error_body(exc)["detail"]
        else:
            raise AssertionError("non-editable Edition should reject mutation")
        assert registry_path.read_bytes() == before
