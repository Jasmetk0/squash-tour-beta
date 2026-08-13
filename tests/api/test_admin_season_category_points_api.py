from __future__ import annotations

import json
from urllib.error import HTTPError

from tests.api.test_admin_season_calendar_api import Server, call


def test_get_is_read_only_initialize_and_update_round_trip(tmp_path):
    registry = tmp_path / "season_category_points.json"
    with Server(tmp_path) as server:
        _, empty = call("GET", f"{server.base_url}/admin/seasons/2000%2F01/category-points")
        assert not empty["initialized"] and not registry.exists()
        _, initialized = call("POST", f"{server.base_url}/admin/seasons/2000%2F01/category-points/initialize")
        assert initialized["initialized"] and registry.exists()
        category = initialized["categories"][0]["category"]
        _, updated = call("PUT", f"{server.base_url}/admin/seasons/2000%2F01/category-points/{category}", {"ranking_points_table": {"champion": 0}})
        assert updated["ranking_points_table"] == {"champion": 0}
        assert updated["provenance"] == "manually_edited"
        _, loaded = call("GET", f"{server.base_url}/admin/seasons/2000%2F01/category-points")
        assert next(row for row in loaded["categories"] if row["category"] == category)["ranking_points_table"] == {"champion": 0}


def test_invalid_update_is_controlled_and_atomic(tmp_path):
    registry = tmp_path / "season_category_points.json"
    with Server(tmp_path) as server:
        _, initialized = call("POST", f"{server.base_url}/admin/seasons/2000%2F01/category-points/initialize")
        category = initialized["categories"][0]["category"]
        before = registry.read_bytes()
        try:
            call("PUT", f"{server.base_url}/admin/seasons/2000%2F01/category-points/{category}", {"ranking_points_table": {"champion": True}})
        except HTTPError as exc:
            assert exc.code == 422
            assert json.loads(exc.read())["detail"]
        else:
            raise AssertionError("invalid points must fail")
        assert registry.read_bytes() == before


def test_long_labels_prefill_edited_previous_season_and_snapshot_target_season(tmp_path):
    with Server(tmp_path) as server:
        _, first = call("POST", f"{server.base_url}/admin/seasons/2000%2F2001/category-points/initialize")
        category = next(row["category"] for row in first["categories"] if row["category"] == "PLATINUM")
        call("PUT", f"{server.base_url}/admin/seasons/2000%2F2001/category-points/{category}", {"ranking_points_table": {"champion": 1234}})
        _, second = call("POST", f"{server.base_url}/admin/seasons/2001%2F2002/category-points/initialize")
        inherited = next(row for row in second["categories"] if row["category"] == category)
        assert inherited["ranking_points_table"] == {"champion": 1234}
        assert inherited["provenance"] == "prefilled_from_previous_season"
        assert inherited["source_season"] == "2000/2001"
        build = {"seed": 1, "dry_run": False, "overwrite_existing": False, "season_start_calendar_year": 2001, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        _, calendar = call("POST", f"{server.base_url}/admin/seasons/2001%2F2002/calendar/build", build)
        edition = next(event for event in calendar["calendar"]["events"] if event["category"] == category)
        assert edition["ranking_points_table"] == {"champion": 1234}


def test_compact_and_mixed_aliases_share_one_registry_season(tmp_path):
    registry = tmp_path / "season_category_points.json"
    with Server(tmp_path) as server:
        call("POST", f"{server.base_url}/admin/seasons/2000%2F01/category-points/initialize")
        _, first = call("GET", f"{server.base_url}/admin/seasons/2000%2F2001/category-points")
        category = next(row["category"] for row in first["categories"] if row["category"] == "PLATINUM")
        call("PUT", f"{server.base_url}/admin/seasons/2000%2F2001/category-points/{category}", {"ranking_points_table": {"champion": 2345}})
        _, second = call("POST", f"{server.base_url}/admin/seasons/2001%2F02/category-points/initialize")
        inherited = next(row for row in second["categories"] if row["category"] == category)
        assert inherited["ranking_points_table"] == {"champion": 2345}
        assert inherited["source_season"] == "2000/2001"
        stored = json.loads(registry.read_text(encoding="utf-8"))["seasons"]
        assert set(stored) == {"2000/2001", "2001/2002"}
        assert "2000/01" not in stored and "2001/02" not in stored


def test_next_season_dry_run_inherits_edit_without_persisting_target(tmp_path):
    registry = tmp_path / "season_category_points.json"
    calendar_registry = tmp_path / "season_calendars.json"
    with Server(tmp_path) as server:
        _, first = call("POST", f"{server.base_url}/admin/seasons/2000%2F01/category-points/initialize")
        category = next(row["category"] for row in first["categories"] if row["category"] == "PLATINUM")
        call("PUT", f"{server.base_url}/admin/seasons/2000%2F01/category-points/{category}", {"ranking_points_table": {"champion": 3456}})
        before = registry.read_bytes()
        build = {"seed": 1, "dry_run": True, "overwrite_existing": False, "season_start_calendar_year": 2001, "season_start_year_week": 37, "include_inactive_templates": False, "max_events": None}
        _, preview = call("POST", f"{server.base_url}/admin/seasons/2001%2F02/calendar/build", build)
        edition = next(event for event in preview["calendar"]["events"] if event["category"] == category)
        assert edition["ranking_points_table"] == {"champion": 3456}
        assert registry.read_bytes() == before
        assert "2001/2002" not in json.loads(before)["seasons"]
        assert not calendar_registry.exists()
