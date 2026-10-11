"""Real Saved Revision HTTP/SQLite player match history isolation and recovery."""
from urllib.parse import quote

import pytest

from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.application.test_viewer_people_read_model import _world


def url(server, run, branch, player="P1", query=""):
    return (f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
            f"{quote(branch, safe='')}/player-profiles/{quote(player, safe='')}/matches{query}")


@pytest.mark.pr_critical
def test_match_history_empty_unsaved_saved_restart_and_foreign_scope(tmp_path):
    db = f"sqlite:///{tmp_path / 'saved-player-matches.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(server, display_name="Saved Match Career")
        other, other_branch, _ = _create_run(server, display_name="Other Match Career")
        status, empty = _request("GET", url(server, run, branch))
        assert status == 200, empty
        assert empty["status"] == "identity_unavailable" and empty["matches"] == []
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_initial_world(session, _world().model_copy(update={"run_id": run, "branch_id": branch}))
        assert _request("GET", url(server, run, branch))[1] == empty
        save_root = (f"{server.base_url}/admin/players/runs/{quote(run, safe='')}"
                     f"/branches/{quote(branch, safe='')}/initial-world/save")
        status, preview = _request("GET", save_root + "/preview")
        assert status == 200 and preview["can_save"], (status, preview)
        status, _ = _request("POST", save_root, {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
        })
        assert status == 201
        status, saved = _request("GET", url(server, run, branch))
        assert status == 200, saved
        assert saved["status"] == "ready" and saved["total_results"] == 0
        assert saved["career_played_wins"] == saved["career_played_losses"] == 0
        assert saved["saved_revision_id"] != empty["saved_revision_id"]
        assert _request("GET", url(server, run, branch, query="?season_index=50"))[0] == 422
        assert _request("GET", url(server, run, branch, query="?limit=21"))[0] == 422
        assert _request("GET", url(server, run, other_branch))[0] == 404
        assert _request("GET", url(server, other, branch))[0] == 404
    with ApiServer(database_url=db) as reopened:
        assert _request("GET", url(reopened, run, branch))[1] == saved


@pytest.mark.pr_critical
def test_saved_canonical_tournament_matches_are_real_http_saved_and_restartable(tmp_path):
    from itertools import count

    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.application.run_working_draft_service import RunWorkingDraftService
    from beta_engine.domain.rankings.official import OfficialRankingPolicy
    from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
    from beta_engine.infrastructure.db.run_package_state import put_run_package_state
    from tests.api.viewer_saved_revision_helpers import save_ranking
    from tests.application.test_viewer_people_read_model import _initial_player
    from tests.application.test_viewer_tournament_history_read_model import _state
    from tests.application.test_viewer_tournament_result_read_model import _source

    db = f"sqlite:///{tmp_path / 'saved-player-canonical-match.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(server, display_name="Canonical saved match records")
        repo = server.app.state.runtime.repository
        world = _world().model_copy(update={
            "run_id": run, "branch_id": branch,
            "players": (
                _initial_player("A", "Player A", "CZE"),
                _initial_player("B", "Player B", "EGY"),
            ),
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
        service = RunWorkingDraftService(repo, lambda kind: f"{kind}-matches-{next(ids)}")
        draft = service.get_viewer_branch_draft(run_id=run, branch_id=branch)
        service.save(run_id=run, branch_id=branch, expected_draft_version=draft.draft_version)

        with repo._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(run_id=run, branch_id=branch, event_id="event")
            )
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingBootstrapCommand(
                command_id="canonical-matches-ranking-bootstrap",
                run_id=run, branch_id=branch,
                policy=OfficialRankingPolicy(policy_id="saved-match-policy"),
                players=(), discipline="none",
            )
        )
        # The source is present in live SQLite but still absent from Saved HEAD.
        status, before = _request("GET", url(server, run, branch, "A"))
        assert status == 200, before
        assert before["status"] == "ready" and before["total_results"] == 0

        save_ranking(server, run, branch)
        status, saved = _request("GET", url(server, run, branch, "A"))
        assert status == 200, saved
        assert saved["source"] == "selected_branch_saved_revision"
        assert saved["career_played_wins"] == 2 and saved["career_played_losses"] == 0
        assert saved["total_results"] == 2 and saved["available_seasons"] == [2]
        assert [row["match_id"] for row in saved["matches"]] == ["final", "semi-a"]
        assert all(row["opponent_player_id"] in ("B", "Q") for row in saved["matches"])
        assert "result_fingerprint" not in str(saved)
        status, page = _request("GET", url(
            server, run, branch, "A", "?season_index=2&limit=1&offset=1"
        ))
        assert status == 200, page
        assert page["total_results"] == 2 and len(page["matches"]) == 1
        assert page["matches"][0]["match_id"] == "semi-a"
        assert not page["has_more"]
        status, old = _request("GET", url(server, run, branch, "A", "?season_index=0"))
        assert status == 200 and old["total_results"] == 0
        assert old["career_played_wins"] == 2
    with ApiServer(database_url=db) as reopened:
        assert _request("GET", url(reopened, run, branch, "A"))[1] == saved
