from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_admin_season_templates_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, payload = call("GET", f"{server.base_url}/admin/seasons/templates")
        status_second, payload_second = call("GET", f"{server.base_url}/admin/seasons/templates")

    assert status == 200
    assert status_second == 200
    assert payload["status"] == "read_only_foundation"
    assert isinstance(payload["templates"], list)
    assert payload["templates"]
    template = payload["templates"][0]
    assert template["week_count"] == 61
    for slot in template["slots"]:
        assert 1 <= slot["season_week_start"] <= 61
        assert 1 <= slot["season_week_end"] <= 61
    assert payload == payload_second
