from __future__ import annotations

import pytest
from urllib.parse import quote

from tests.api.test_admin_tournament_entry_fields_api import _install_entry_field
from test_simulation_api import ApiServer, _request
from test_visible_prospects_api import _canonical_run


@pytest.mark.pr_critical
def test_viewer_entry_field_projects_selected_branch_public_sporting_state(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'viewer-entry-field.sqlite'}"
    ) as server:
        run_id = "run"
        branch_id, _ = _canonical_run(server, run_id)
        event_id = "viewer-event"
        field = _install_entry_field(
            server,
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )

        status, payload = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                f"/tournaments/{quote(event_id, safe='')}/entry-field"
            ),
        )

        assert status == 200
        assert payload["schema_version"] == "viewer_tournament_entry_field.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["event_id"] == event_id
        assert payload["field_sequence"] == 1
        assert payload["mode"] == "initial"
        assert payload["main_draw_capacity"] == 4
        assert payload["active_main_entrant_count"] == field.active_main_entrant_count
        assert payload["effective_main_bye_count"] == field.effective_main_bye_count
        assert payload["direct_main_player_ids"] == list(field.direct_main_player_ids)
        assert payload["qualification_player_ids"] == list(field.qualification_player_ids)
        assert payload["alternate_player_ids"] == list(
            field.below_qualification_cut_player_ids
        )
        assert payload["withdrawn_player_ids"] == list(field.withdrawn_player_ids)

        # Viewer projection deliberately excludes authority/provenance internals.
        assert "field_fingerprint" not in payload
        assert "main_diagnostics" not in payload
        assert "pre_draw_repair_locked_by_draw_input" not in payload


@pytest.mark.pr_critical
def test_viewer_entry_field_returns_not_found_when_selected_branch_has_no_field(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'viewer-entry-field-missing.sqlite'}"
    ) as server:
        run_id = "run"
        _canonical_run(server, run_id)

        status, _ = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                "/tournaments/missing-event/entry-field"
            ),
        )
        assert status == 404
