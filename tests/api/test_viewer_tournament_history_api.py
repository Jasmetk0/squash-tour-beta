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


@pytest.mark.pr_critical
def test_viewer_tournament_history_publishes_saved_package_then_saved_results(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-tournament-history.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run_id, branch_id, _ = _create_run(
            server,
            display_name="Canonical Viewer Tournament History",
        )
        repository = server.app.state.runtime.repository
        root = f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments"

        state = _state(run_id=run_id, branch_id=branch_id)
        with repository._session_factory.begin() as session:
            put_run_package_state(session, state)

        # Live Package state must not leak through the Viewer Saved Revision boundary.
        assert _request("GET", root)[0] == 404

        ids = count(1)
        service = RunWorkingDraftService(
            repository,
            lambda kind: f"{kind}-viewer-history-{next(ids)}",
        )
        draft = service.get_viewer_branch_draft(run_id=run_id, branch_id=branch_id)
        service.save(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=draft.draft_version,
        )

        status, package_only = _request("GET", root)
        assert status == 200, package_only
        assert package_only["schema_version"] == "viewer_tournament_history.v1"
        assert package_only["product_run_id"] == run_id
        assert package_only["viewer_branch_id"] == branch_id
        assert package_only["tournament_count"] == 2
        assert package_only["published_result_count"] == 0
        assert [
            (item["season"], item["season_week"], item["event_id"])
            for item in package_only["tournaments"]
        ] == [
            ("2000/2001", 5, "EVENT-OLD"),
            ("2002/2003", 17, "event"),
        ]
        assert all(not item["result_published"] for item in package_only["tournaments"])

        # Canonical close evidence is live but still unpublished.
        with repository._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(
                    run_id=run_id,
                    branch_id=branch_id,
                    event_id="event",
                )
            )
        RankingWeekCommandRunner(repository._session_factory).execute(
            RankingBootstrapCommand(
                command_id="viewer-history-ranking-bootstrap",
                run_id=run_id,
                branch_id=branch_id,
                policy=OfficialRankingPolicy(policy_id="viewer-history-test-policy"),
                players=(),
                discipline="none",
            )
        )
        status, before_ranking_save = _request("GET", root)
        assert status == 200
        assert before_ranking_save["published_result_count"] == 0

        save_ranking(server, run_id, branch_id)

        status, published = _request("GET", root)
        assert status == 200, published
        assert published["published_result_count"] == 1
        current = next(
            item for item in published["tournaments"] if item["event_id"] == "event"
        )
        assert current["result_published"] is True
        assert current["champion_player_id"] == "A"
        assert current["finalist_player_id"] == "B"

        serialized = str(published)
        for forbidden in (
            "fingerprint",
            "command_id",
            "provenance",
            "run_local_id",
            "source_package",
            "canonical_result",
            "canonical_awards",
        ):
            assert forbidden not in serialized


@pytest.mark.pr_critical
def test_viewer_tournament_history_returns_not_found_without_saved_calendar(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-tournament-history-empty.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        run_id, _, _ = _create_run(server, display_name="Empty Viewer History")
        status, _ = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}/tournaments",
        )
        assert status == 404
