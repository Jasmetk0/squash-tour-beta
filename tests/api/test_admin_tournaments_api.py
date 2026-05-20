from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_admin_tournaments_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, payload = call("GET", f"{server.base_url}/admin/tournaments")
        status_second, payload_second = call("GET", f"{server.base_url}/admin/tournaments")

    assert status == 200
    assert status_second == 200
    assert payload["status"] == "read_only_foundation"
    assert isinstance(payload["tournaments"], list)
    assert payload["tournaments"]
    first = payload["tournaments"][0]
    assert first["status"] == "read_only_foundation"
    assert first["source_template_ids"] == sorted(first["source_template_ids"])
    assert payload == payload_second
