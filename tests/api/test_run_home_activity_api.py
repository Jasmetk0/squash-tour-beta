"""Real FastAPI + SQLite acceptance of strictly saved, Branch-scoped Home data."""

from __future__ import annotations

from itertools import count
from urllib.parse import quote

import pytest

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.api.viewer_saved_revision_helpers import save_ranking
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_viewer_tournament_result_read_model import _source


def _endpoint(server, run: str, branch: str) -> str:
    return (
        f"{server.base_url}/admin/runs/{quote(run, safe='')}"
        f"/branches/{quote(branch, safe='')}/home-activity"
    )


@pytest.mark.pr_critical
def test_empty_run_home_is_a_real_empty_saved_state_and_fails_closed_across_runs(tmp_path):
    url = f"sqlite:///{tmp_path / 'home-empty.sqlite'}"
    with ApiServer(database_url=url) as server:
        run, branch, _ = _create_run(server, display_name="Home activity empty")
        other, other_branch, _ = _create_run(server, display_name="Home activity other")
        response_url = _endpoint(server, run, branch)
        status, empty = _request("GET", response_url)
        assert status == 200, empty
        assert empty["source"] == "selected_branch_saved_revision"
        assert empty["run_id"] == run and empty["branch_id"] == branch
        assert empty["calendar_status"] == "empty"
        assert empty["result_status"] == "empty"
        assert empty["upcoming"] == [] and empty["recent_results"] == []
        assert empty["total_calendar_events"] == 0
        assert empty["published_result_count"] == 0
        assert empty["ranking_changes_status"] == "unsupported"
        assert _request("GET", response_url)[1] == empty
        assert _request("GET", _endpoint(server, run, other_branch))[0] == 404
        assert _request("GET", _endpoint(server, other, branch))[0] == 404


@pytest.mark.pr_critical
def test_home_calendar_and_published_results_read_saved_revision_only(tmp_path):
    url = f"sqlite:///{tmp_path / 'home-published.sqlite'}"
    with ApiServer(database_url=url) as server:
        run, branch, _ = _create_run(server, display_name="Home published tournament")
        repo = server.app.state.runtime.repository
        endpoint = _endpoint(server, run, branch)

        with repo._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))

        # Live package edits must not leak into the saved read model.
        status, unsaved = _request("GET", endpoint)
        assert status == 200 and unsaved["calendar_status"] == "empty"

        ids = count(1)
        service = RunWorkingDraftService(
            repo, lambda kind: f"{kind}-home-{next(ids)}",
        )
        draft = service.get_viewer_branch_draft(run_id=run, branch_id=branch)
        service.save(run_id=run, branch_id=branch, expected_draft_version=draft.draft_version)

        status, saved = _request("GET", endpoint)
        assert status == 200, saved
        assert saved["total_calendar_events"] == 2
        assert saved["calendar_status"] == "unpositioned"
        assert saved["upcoming"] == []
        assert saved["published_result_count"] == 0

        with repo._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(run_id=run, branch_id=branch, event_id="event")
            )
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingBootstrapCommand(
                command_id="home-ranking-bootstrap",
                run_id=run,
                branch_id=branch,
                policy=OfficialRankingPolicy(policy_id="home-test-policy"),
                players=(),
                discipline="none",
            )
        )
        assert _request("GET", endpoint)[1]["published_result_count"] == 0
        save_ranking(server, run, branch)
        status, published = _request("GET", endpoint)
        assert status == 200, published
        assert published["published_result_count"] == 1
        assert published["result_status"] == "ready"
        assert len(published["recent_results"]) == 1
        assert published["recent_results"][0]["event_id"] == "event"
        assert published["recent_results"][0]["champion_player_id"] == "A"
        assert published["recent_results"][0]["finalist_player_id"] == "B"
        assert all("fingerprint" not in str(item) for item in published["recent_results"])

    # Persistence/restart must yield the same read-only projection.
    with ApiServer(database_url=url) as reopened:
        assert _request("GET", _endpoint(reopened, run, branch))[1] == published
