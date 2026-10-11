from __future__ import annotations

import pytest

from tests.api.test_saved_revision_history_api import ApiServer, _request


pytestmark = pytest.mark.pr_critical


def test_fax_long_acceptance_probe_api_requires_ready_input_profile(tmp_path) -> None:
    with ApiServer(
        database_url=f"sqlite:///{tmp_path / 'fax-long-acceptance-probe.db'}"
    ) as server:
        status, run = _request(
            "POST",
            f"{server.base_url}/run-containers",
            {"display_name": "FAX long acceptance probe"},
        )
        assert status == 201, run
        run_id = run["run_id"]
        branch_id = run["viewer_branch_id"]

        status, body = _request(
            "POST",
            (
                f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
                "/authoritative-simulation/pre-alpha/fax-long-acceptance/probe"
            ),
            {
                "command_id": "fax-probe-api-1",
                "operator_label": "Pre-alpha acceptance",
                "audit_reason": "Confirm long acceptance refuses an unprepared copied-FAX Run.",
            },
        )

        assert status == 409, body
        assert body["detail"]["code"] == "pre_alpha_fax_long_acceptance_probe_conflict"
        assert "input gate passes" in body["detail"]["message"]
