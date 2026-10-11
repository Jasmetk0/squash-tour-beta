from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_admin_tour_seasons_validation_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, payload = call("GET", f"{server.base_url}/admin/tour-seasons/validation")
        status_second, payload_second = call("GET", f"{server.base_url}/admin/tour-seasons/validation")

    assert status == 200
    assert status_second == 200
    assert payload["status"] == "read_only_foundation"
    assert payload["summary"]["total_checks"] == (
        payload["summary"]["warning_count"]
        + payload["summary"]["info_count"]
        + payload["summary"]["ok_count"]
    )
    sections = {section["title"] for section in payload["sections"]}
    assert sections == {"Registry", "Category", "Tournament", "Season Template"}
    assert isinstance(payload["planned_future"], list)
    assert payload["planned_future"]
    assert payload == payload_second
