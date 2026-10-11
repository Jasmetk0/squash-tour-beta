"""Real HTTP and SQLite Saved Revision match detail: saved-only and reopen."""
from itertools import count
from urllib.parse import quote

import pytest

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.api.viewer_saved_revision_helpers import save_ranking
from tests.application.test_viewer_people_read_model import _world, _initial_player
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_viewer_tournament_result_read_model import _source

pytestmark = pytest.mark.pr_critical


def url(server, run, branch, player="A", event="event", match="final", query=""):
    return (f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
            f"{quote(branch, safe='')}/player-profiles/{quote(player, safe='')}"
            f"/matches/{quote(event, safe='')}/{quote(match, safe='')}{query}")


def test_saved_detail_reads_real_canonical_match_only_after_save_and_reopens(tmp_path):
    db = f"sqlite:///{tmp_path / 'saved-match-detail.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(server, display_name="Match detail Save")
        other, foreign_branch, _ = _create_run(server, display_name="Other match detail")
        repo = server.app.state.runtime.repository
        world = _world().model_copy(update={
            "run_id": run, "branch_id": branch,
            "players": (_initial_player("A", "Player A", "CZE"),
                        _initial_player("B", "Player B", "EGY")),
        })
        with repo._session_factory.begin() as session:
            put_initial_world(session, world)
        root = (f"{server.base_url}/admin/players/runs/{quote(run, safe='')}"
                f"/branches/{quote(branch, safe='')}/initial-world/save")
        status, preview = _request("GET", root + "/preview")
        assert status == 200 and preview["can_save"], (status, preview)
        status, _ = _request("POST", root, {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
        })
        assert status == 201
        with repo._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))
        ids = count(1)
        draft_service = RunWorkingDraftService(repo, lambda kind: f"{kind}-detail-{next(ids)}")
        draft = draft_service.get_viewer_branch_draft(run_id=run, branch_id=branch)
        draft_service.save(run_id=run, branch_id=branch, expected_draft_version=draft.draft_version)

        # Real canonical result exists live but is not yet in immutable Saved HEAD.
        with repo._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(run_id=run, branch_id=branch, event_id="event")
            )
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingBootstrapCommand(
                command_id="detail-ranking-bootstrap",
                run_id=run, branch_id=branch,
                policy=OfficialRankingPolicy(policy_id="saved-match-detail-policy"),
                players=(), discipline="none",
            )
        )
        assert _request("GET", url(server, run, branch))[0] == 404
        save_ranking(server, run, branch)

        status, saved = _request("GET", url(server, run, branch))
        assert status == 200, saved
        assert saved["source"] == "selected_branch_saved_revision"
        assert saved["match"]["event_name"] == "Current Open"
        assert saved["match"]["season_index"] == 2
        assert (saved["winner_player_id"], saved["loser_player_id"]) == ("A", "B")
        assert saved["match"]["scoreline"] == "3-2"
        assert saved["replay_status"] == "unavailable"
        assert saved["total_rallies"] == 0 and saved["rallies"] == []
        # Two real Saved HEAD player viewpoints cannot disagree on the same
        # published final; a replay-less cursor does not manufacture frames.
        status, finalist_view = _request("GET", url(server, run, branch, "B"))
        assert status == 200, finalist_view
        assert finalist_view["saved_revision_id"] == saved["saved_revision_id"]
        assert finalist_view["match"]["outcome"] == "loss"
        assert finalist_view["match"]["opponent_player_id"] == "A"
        assert finalist_view["match"]["scoreline"] == saved["match"]["scoreline"]
        status, beyond = _request("GET", url(
            server, run, branch, query="?offset=25&limit=25"
        ))
        assert status == 200, beyond
        assert beyond["replay_status"] == "unavailable"
        assert beyond["rallies"] == [] and beyond["total_rallies"] == 0
        assert not beyond["has_more"]
        assert _request("GET", url(server, run, branch, "A", "event", "nonexistent"))[0] == 404
        assert _request("GET", url(server, run, branch, "A", "EVENT-OLD"))[0] == 404
        assert _request("GET", url(server, run, branch, "D"))[0] == 404
        assert _request("GET", url(server, run, foreign_branch))[0] == 404
        assert _request("GET", url(server, other, branch))[0] == 404
        assert _request("GET", url(server, run, branch, query="?limit=26"))[0] == 422
    with ApiServer(database_url=db) as reopened:
        assert _request("GET", url(reopened, run, branch))[1] == saved
