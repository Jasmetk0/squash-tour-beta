from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from tests.api.test_viewer_tournament_entry_field_api import _repository
from tests.api.viewer_saved_revision_helpers import (
    canonical_product_run as _canonical_run,
    save_ranking,
)
from tests.application.test_viewer_tournament_result_read_model import _source

from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    OwnedTournamentRankingSourceModel,
)
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


@pytest.mark.pr_critical
def test_viewer_tournament_result_is_published_only_from_saved_ranking_component(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-tournament-result.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        branch_id, run_id = _canonical_run(server)
        event_id = "viewer-result-event"
        source = _source(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )

        repository = _repository(database_url)
        with repository._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(source)

        # A live owned source by itself is not a Saved-Revision publication.
        # Stage a real Ranking component change so the normal explicit Ranking Save
        # can capture both the ranking entry and the owned tournament source.
        RankingWeekCommandRunner(repository._session_factory).execute(
            RankingBootstrapCommand(
                command_id="viewer-result-ranking-bootstrap",
                run_id=run_id,
                branch_id=branch_id,
                policy=OfficialRankingPolicy(policy_id="viewer-result-test-policy"),
                players=(),
                discipline="none",
            )
        )

        root = (
            f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
            f"/tournaments/{quote(event_id, safe='')}/result"
        )

        # Live canonical close evidence cannot cross the Viewer Saved Revision boundary.
        assert _request("GET", root)[0] == 404

        save_ranking(server, run_id, branch_id)

        status, payload = _request("GET", root)
        assert status == 200
        assert payload["schema_version"] == "viewer_tournament_result.v1"
        assert payload["product_run_id"] == run_id
        assert payload["viewer_branch_id"] == branch_id
        assert payload["event_id"] == event_id
        assert payload["completed_season_index"] == 2
        assert payload["completed_week"] == 17
        assert payload["champion_player_id"] == "A"
        assert payload["finalist_player_id"] == "B"
        assert payload["qualification_winner_ids"] == ["Q"]
        assert [player["player_id"] for player in payload["players"]] == ["A", "B", "Q", "C", "D"]
        assert [match["match_id"] for match in payload["matches"]] == [
            "q-final",
            "semi-a",
            "semi-b",
            "final",
        ]
        assert payload["matches"][-1]["scoreline"] == "3-2"

        serialized = str(payload)
        for forbidden in (
            "fingerprint",
            "command_id",
            "provenance",
            "canonical_awards",
            "canonical_prize_awards",
            "point_distribution",
            "draw_authority_fingerprint",
            "match_package_fingerprint",
            "result_fingerprint",
        ):
            assert forbidden not in serialized

        # Successful Viewer GET is a pure read.
        with repository._session_factory() as session:
            before = (
                session.query(BranchSavedRevisionModel).count(),
                session.query(OwnedTournamentRankingSourceModel).count(),
            )
        assert _request("GET", root)[0] == 200
        with repository._session_factory() as session:
            assert before == (
                session.query(BranchSavedRevisionModel).count(),
                session.query(OwnedTournamentRankingSourceModel).count(),
            )


@pytest.mark.pr_critical
def test_viewer_tournament_result_returns_not_found_when_saved_branch_has_no_result(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'viewer-tournament-result-missing.sqlite'}"
    with ApiServer(database_url=database_url) as server:
        _, run_id = _canonical_run(server)
        status, _ = _request(
            "GET",
            (
                f"{server.base_url}/viewer/runs/{quote(run_id, safe='')}"
                "/tournaments/missing-event/result"
            ),
        )
        assert status == 404
