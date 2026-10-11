from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request


pytestmark = pytest.mark.pr_critical


def test_pre_alpha_fax_acceptance_profile_api_reports_missing_release_inputs(
    tmp_path,
) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-acceptance-profile.db'}"
    ) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="FAX acceptance profile",
        )
        status, body = _request(
            "GET",
            (
                f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
                "/authoritative-simulation/pre-alpha/fax-acceptance-profile"
            ),
        )

        assert status == 200, body
        assert body["schema_version"] == "pre_alpha_fax_acceptance_profile.v1"
        assert body["run_id"] == run_id
        assert body["branch_id"] == branch_id
        assert body["timeline_start_season"] == 2000
        assert body["timeline_end_season"] == 2049
        assert body["timeline_season_count"] == 50
        assert body["required_min_initial_players"] == 1000
        assert body["required_world_tour_edition_count"] == 80
        assert body["ready_for_long_acceptance"] is False
        assert len(body["profile_fingerprint"]) == 64
        assert {
            issue["code"]
            for issue in body["issues"]
            if issue["severity"] == "error"
        } == {
            "FAX_ACCEPTANCE_INITIAL_WORLD_MISSING",
            "FAX_ACCEPTANCE_CALENDAR_PACKAGE_MISSING",
        }
