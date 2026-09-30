from __future__ import annotations

from urllib.parse import quote

import pytest

from tests.api.test_admin_world_tour_finals_participants_api import (
    _seed_calendar_and_race,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import canonical_product_run, save_simulation


@pytest.mark.pr_critical
def test_viewer_finals_race_is_published_only_from_saved_simulation_component(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-finals-race.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, run_id = canonical_product_run(
            server,
            run_id="viewer-finals-race",
        )
        factory = server.app.state.runtime.repository._session_factory
        race = _seed_calendar_and_race(
            factory,
            run_id=run_id,
            branch_id=branch_id,
        )

        participant_root = (
            f"{server.base_url}/admin/runs/{quote(run_id, safe='')}"
            f"/branches/{quote(branch_id, safe='')}/finals-participants/0"
        )
        status, configured = _request(
            "POST",
            participant_root + "/configuration",
            {
                "direct_entry_event_ids": [],
                "command_id": "viewer-race-participant-config",
            },
        )
        assert status == 201
        assert configured["participant_capacity"] == 3

        status, selected = _request("POST", participant_root + "/snapshot")
        assert status == 201
        assert [row["player_id"] for row in selected["participants"]] == [
            row.player_id for row in race.rows[:3]
        ]

        viewer_url = (
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/race/finals"
        )

        # Live Finals Race / participant authority is not itself a Viewer publication.
        status, before_save = _request("GET", viewer_url)
        assert status == 200, (status, before_save)
        assert before_save["publications"] == []
        assert before_save["latest_target_season_index"] is None

        save_simulation(server, run_id, branch_id)

        status, published = _request("GET", viewer_url)
        assert status == 200
        assert published["schema_version"] == "viewer_finals_race_history.v1"
        assert published["product_run_id"] == run_id
        assert published["viewer_branch_id"] == branch_id
        assert published["latest_target_season_index"] == 0
        assert len(published["publications"]) == 1

        publication = published["publications"][0]
        assert publication["target_season_index"] == 0
        assert publication["cutoff_week"] == 10
        assert publication["best_n"] == 2
        assert publication["selection_published"] is True
        assert publication["finals_event_id"] == "FINALS"
        assert [row["player_id"] for row in publication["rows"]] == [
            row.player_id for row in race.rows
        ]
        assert [
            row["finals_selected"] for row in publication["rows"][:3]
        ] == [True, True, True]
        assert all(
            row["finals_selected"] is False
            for row in publication["rows"][3:]
        )

        rendered = str(published)
        for forbidden in (
            "fingerprint",
            "tie_break_token",
            "policy_id",
            "command_id",
            "source_award",
            "withdrawn_player_ids",
            "predecessor",
        ):
            assert forbidden not in rendered


@pytest.mark.pr_critical
def test_viewer_finals_race_empty_saved_history_is_public_empty_state(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-finals-race-empty.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        _, run_id = canonical_product_run(
            server,
            run_id="viewer-empty-finals-race",
        )
        status, payload = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/race/finals",
        )
        assert status == 200
        assert payload["latest_target_season_index"] is None
        assert payload["publications"] == []
