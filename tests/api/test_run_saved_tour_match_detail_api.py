"""Exact historical Edition match route using real FastAPI + SQLite revisions."""
from itertools import count
from urllib.parse import quote

import pytest

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.api.viewer_saved_revision_helpers import save_ranking
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_viewer_tournament_result_read_model import _source

pytestmark = pytest.mark.pr_critical


def _url(server, run, branch, revision, event="event", match="final", season=2):
    return (
        f"{server.base_url}/admin/runs/{quote(run, safe='')}"
        f"/branches/{quote(branch, safe='')}/tour/editions/{quote(event, safe='')}"
        f"/matches/{quote(match, safe='')}?revision_id={quote(revision, safe='')}"
        f"&season_index={season}&offset=0&limit=25"
    )


def test_exact_saved_edition_match_result_and_missing_replay_survive_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'saved-edition-match.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, empty_revision = _create_run(server, display_name="Edition match")
        foreign_run, foreign_branch, foreign_revision = _create_run(
            server, display_name="Foreign Edition match"
        )
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))
        ids = count(1)
        drafts = RunWorkingDraftService(
            repo, lambda kind: f"{kind}-edition-match-{next(ids)}",
        )
        working = drafts.get_viewer_branch_draft(run_id=run, branch_id=branch)
        earlier_revision = drafts.save(
            run_id=run, branch_id=branch,
            expected_draft_version=working.draft_version,
        ).saved_revision.revision_id

        with repo._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(run_id=run, branch_id=branch, event_id="event"),
            )
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingBootstrapCommand(
                command_id="historical-match-ranking",
                run_id=run, branch_id=branch,
                policy=OfficialRankingPolicy(policy_id="historical-match-policy"),
                players=(), discipline="none",
            )
        )
        assert _request("GET", _url(server, run, branch, earlier_revision))[0] == 404
        save_ranking(server, run, branch)
        status, branch_row = _request(
            "GET", f"{server.base_url}/run-branches/{quote(branch, safe='')}"
        )
        assert status == 200
        saved_revision = branch_row["saved_head_revision_id"]

        status, match = _request("GET", _url(server, run, branch, saved_revision))
        assert status == 200, match
        assert match["schema_version"] == "run_saved_tour_match_detail.v1"
        assert match["source"] == "reachable_saved_revision"
        assert match["branch_id"] == match["revision_branch_id"] == branch
        assert match["saved_revision_id"] == saved_revision
        assert match["match"]["scoreline"] == "3-2"
        assert (match["match"]["winner_player_id"], match["match"]["loser_player_id"]) == ("A", "B")
        assert match["replay_status"] == "unavailable"
        assert match["rallies"] == []
        assert _request("GET", _url(server, run, branch, saved_revision, match="wrong"))[0] == 404
        assert _request("GET", _url(server, run, branch, saved_revision, event="EVENT-OLD", season=0))[0] == 404
        assert _request("GET", _url(server, run, branch, saved_revision, season=0))[0] == 404
        assert _request("GET", _url(server, run, branch, earlier_revision))[0] == 404
        assert _request("GET", _url(server, run, branch, foreign_revision))[0] == 404
        assert _request("GET", _url(server, foreign_run, foreign_branch, saved_revision))[0] == 404
        assert _request("GET", _url(server, run, branch, saved_revision).split("&season_index=")[0])[0] == 422
        assert _request("GET", _url(server, run, branch, saved_revision, season=50))[0] == 422

        # The synthetic ranking fixture is intentionally NOT forgeable into a
        # new fork: its tournament source is not command-owned. Fork the earlier
        # safely materializable Calendar snapshot and prove the later published
        # result is not copied backwards into its shared historical ancestor.
        id_factory = iter(("edition-fork", "edition-fork-draft", "edition-fork-root"))
        RunBranchCreationService(
            repository=repo, id_factory=lambda _kind: next(id_factory),
        ).create_from_saved_revision(
            run_id=run, source_branch_id=branch,
            source_saved_revision_id=earlier_revision,
        )
        assert _request("GET", _url(server, run, "edition-fork", earlier_revision))[0] == 404
        assert _request("GET", _url(server, run, "edition-fork", saved_revision))[0] == 404
        assert _request("GET", _url(server, run, branch, saved_revision)) == (200, match)

    with ApiServer(database_url=db) as reopened:
        assert _request("GET", _url(reopened, run, branch, saved_revision)) == (200, match)
        assert _request("GET", _url(reopened, run, "edition-fork", earlier_revision))[0] == 404
        assert _request("GET", _url(reopened, run, branch, earlier_revision))[0] == 404
