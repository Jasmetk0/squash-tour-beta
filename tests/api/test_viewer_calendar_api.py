from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from tests.api.test_saved_revision_history_api import _create_run
from test_season_point_awards_service import make_points_service


@pytest.mark.pr_critical
def test_viewer_calendar_uses_saved_calendar_package_boundary(tmp_path) -> None:
    points, _ = make_points_service(tmp_path / "source")
    source_calendar_service = points.calendar_service
    source = source_calendar_service.get_calendar(season="2000/2001").calendar
    assert source is not None and source.events

    database_url = f"sqlite:///{tmp_path / 'viewer-calendar.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        server.app.state.season_calendar_registry_path = (
            source_calendar_service.calendar_registry_path
        )
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Viewer canonical calendar",
        )
        viewer_url = (
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/calendar"
        )

        # Initial Saved Revision has no Calendar Package.
        assert _request("GET", viewer_url)[0] == 404

        base = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/packages"
        )
        source_root = base + "/source-calendar/2000-2001"
        status, preview = _request("POST", source_root + "/preview")
        assert status == 200, preview
        status, applied = _request(
            "POST",
            source_root + "/confirm",
            {
                "command_id": "apply-viewer-calendar",
                "expected_head_revision_id": preview["saved_head_revision_id"],
                "expected_draft_version": preview["draft_version"],
                "expected_state_fingerprint": preview["current_state_fingerprint"],
                "expected_preview_fingerprint": preview["preview_fingerprint"],
                "conflict_resolutions": {},
            },
        )
        assert status == 200, applied

        # Live Package state cannot cross the Viewer Saved Revision boundary.
        assert _request("GET", viewer_url)[0] == 404

        save_url = (
            f"{server.base_url}/run-containers/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/working-draft/save"
        )
        status, saved = _request(
            "POST",
            save_url,
            {"expected_draft_version": applied["draft_version"]},
        )
        assert status == 201, saved

        status, payload = _request("GET", viewer_url)
        assert status == 200, payload
        assert payload["schema_version"] == "viewer_run_calendar.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["calendar_count"] == 1
        assert payload["event_count"] == len(source.events)
        assert [row["event_id"] for row in payload["events"]] == [
            event.event_id
            for event in sorted(
                source.events, key=lambda event: (event.season_week, event.event_id)
            )
        ]
        first = payload["events"][0]
        source_first = sorted(
            source.events, key=lambda event: (event.season_week, event.event_id)
        )[0]
        assert first["season"] == str(source_first.season)
        assert first["season_index"] == 0
        assert first["season_week"] == source_first.season_week
        assert first["template_id"] == source_first.template_id
        assert first["event_name"] == source_first.event_name
        assert first["category"] == source_first.category
        assert first["host_country"] == source_first.host_country
        assert first["result"] is None

        rendered = str(payload)
        for forbidden in (
            "fingerprint",
            "run_local_id",
            "source_package_id",
            "source_package_version",
            "provenance",
            "command_id",
        ):
            assert forbidden not in rendered


@pytest.mark.pr_critical
def test_viewer_calendar_returns_not_found_without_saved_calendar_package(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'viewer-calendar-empty.sqlite'}"
    ) as server:
        run_id, _, _ = _create_run(server, display_name="Viewer empty calendar")
        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/calendar",
        )
        assert status == 404
