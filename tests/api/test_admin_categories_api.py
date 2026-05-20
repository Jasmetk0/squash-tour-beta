from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_admin_categories_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, payload = call("GET", f"{server.base_url}/admin/categories")
        status_second, payload_second = call("GET", f"{server.base_url}/admin/categories")

    assert status == 200
    assert status_second == 200
    assert payload["status"] == "read_only_foundation"
    assert isinstance(payload["categories"], list)
    assert payload["categories"]
    first = payload["categories"][0]
    assert first["status"] == "read_only_foundation"
    assert isinstance(first["source_template_ids"], list)
    assert payload == payload_second
