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
