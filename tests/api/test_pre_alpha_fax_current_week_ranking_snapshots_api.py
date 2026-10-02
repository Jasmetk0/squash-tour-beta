from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def test_current_week_ranking_snapshot_preview_requires_opening_world_head(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-ranking-snapshot-preview.db'}"
    ) as server:
        status, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "FAX ranking snapshot preview"},
        )
        assert status == 201, run

        status, body = _request(
            "GET",
            (
                f"{server.base_url}/admin/runs/{run['run_id']}/branches/{run['viewer_branch_id']}"
                "/authoritative-simulation/pre-alpha/fax-current-week/ranking-snapshots/preview"
            ),
        )

        assert status == 409, body
        assert (
            body["detail"]["code"]
            == "pre_alpha_fax_current_week_ranking_snapshot_preview_conflict"
        )
        assert "authoritative world head" in body["detail"]["message"]
