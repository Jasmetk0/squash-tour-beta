from __future__ import annotations

import pytest

from test_saved_revision_history_api import ApiServer, _request

from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel


pytestmark = pytest.mark.pr_critical


def test_branch_player_prize_money_history_api_is_read_only_and_scoped(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'player-prize-api.db'}"
    with ApiServer(database_url=database_url) as server:
        factory = server.app.state.runtime.repository._session_factory
        with factory.begin() as session:
            session.add(
                RunContainerModel(
                    run_id="run",
                    timeline_start_season=2000,
                    timeline_end_season=2049,
                )
            )
            session.add(
                RunBranchModel(
                    run_id="run",
                    branch_id="branch",
                    display_name="Timeline 1",
                )
            )

        url = (
            f"{server.base_url}/admin/runs/run/branches/branch/"
            "players/A/prize-money"
        )
        status, payload = _request("GET", url)

        assert status == 200
        assert payload == {
            "run_id": "run",
            "branch_id": "branch",
            "player_id": "A",
            "coverage_status": "complete",
            "reporting_currency_status": "requires_historical_fx_authority",
            "entries": [],
            "season_summaries": [],
            "career_known_totals_by_currency": [],
            "known_payout_count": 0,
            "unknown_payout_count": 0,
            "not_configured_count": 0,
            "historical_unavailable_count": 0,
        }

        status, missing = _request(
            "GET",
            f"{server.base_url}/admin/runs/other/branches/branch/"
            "players/A/prize-money",
        )
        assert status == 404
        assert "Run/Branch scope" in missing["detail"]
