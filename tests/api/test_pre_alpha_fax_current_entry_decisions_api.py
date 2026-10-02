from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def test_copied_fax_current_entry_preview_requires_current_entry_position(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-current-entry-preview.db'}"
    ) as server:
        status, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "FAX current Entry preview"},
        )
        assert status == 201, run

        status, body = _request(
            "GET",
            (
                f"{server.base_url}/admin/runs/{run['run_id']}/branches/{run['viewer_branch_id']}"
                "/authoritative-simulation/pre-alpha/fax-current-entry/preview"
            ),
        )

        assert status == 409, body
        assert body["detail"]["code"] == "pre_alpha_fax_current_entry_preview_conflict"
