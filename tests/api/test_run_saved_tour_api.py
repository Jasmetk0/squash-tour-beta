"""Real FastAPI + SQLite Saved Tour Calendar/Edition read-only acceptance."""
from itertools import count
from urllib.parse import quote

import pytest

from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.application.test_viewer_tournament_history_read_model import _state

pytestmark = pytest.mark.pr_critical


def _url(server, run, branch, revision, season=2, event_id=None):
    endpoint = "tour/calendar" if event_id is None else (
        "tour/editions/" + quote(event_id, safe="")
    )
    return (
        f"{server.base_url}/admin/runs/{quote(run, safe='')}"
        f"/branches/{quote(branch, safe='')}/{endpoint}"
        f"?revision_id={quote(revision, safe='')}&season_index={season}"
    )


def _save(repository, run, branch):
    ids = count(1)
    service = RunWorkingDraftService(
        repository, lambda kind: f"{kind}-tour-{next(ids)}",
    )
    draft = service.get_viewer_branch_draft(run_id=run, branch_id=branch)
    return service.save(
        run_id=run, branch_id=branch,
        expected_draft_version=draft.draft_version,
    ).saved_revision.revision_id


def test_saved_calendar_multi_season_immutable_shared_ancestor_and_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'run-tour-revision.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, empty_rev = _create_run(
            server, display_name="Exact Tour calendar",
        )
        foreign, foreign_branch, foreign_rev = _create_run(
            server, display_name="Foreign Tour calendar",
        )
        empty = _request("GET", _url(server, run, branch, empty_rev))
        assert empty[0] == 200, empty
        assert empty[1]["calendar_status"] == "empty"
        assert empty[1]["week_count"] == 61
        assert empty[1]["editions"] == []
        assert _request("GET", _url(server, run, branch, empty_rev, event_id="event"))[0] == 404

        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))
        # A live draft is never substituted for an immutable earlier revision.
        assert _request("GET", _url(server, run, branch, empty_rev)) == empty
        saved_rev = _save(repo, run, branch)
        old = _request("GET", _url(server, run, branch, saved_rev, season=0))
        later = _request("GET", _url(server, run, branch, saved_rev, season=2))
        assert old[0] == later[0] == 200, (old, later)
        assert [e["event_id"] for e in old[1]["editions"]] == ["EVENT-OLD"]
        assert [e["event_id"] for e in later[1]["editions"]] == ["event"]
        assert old[1]["season_index"] == 0 and later[1]["season_index"] == 2
        assert later[1]["edition_count"] == 1
        assert later[1]["calendar_status"] == "ready"

        edition = _request(
            "GET", _url(server, run, branch, saved_rev, event_id="event"),
        )
        assert edition[0] == 200, edition
        assert edition[1]["edition"]["event_id"] == "event"
        assert edition[1]["published_result"] is None
        assert edition[1]["lifecycle_status"] == "unavailable"
        assert _request(
            "GET", _url(server, run, branch, saved_rev, season=0, event_id="event"),
        )[0] == 404
        assert _request(
            "GET", _url(server, run, branch, saved_rev, season=49, event_id="event"),
        )[0] == 404
        assert _request("GET", _url(server, run, branch, foreign_rev))[0] == 404
        assert _request("GET", _url(server, foreign, foreign_branch, saved_rev))[0] == 404
        assert _request("GET", _url(server, run, foreign_branch, saved_rev))[0] == 404
        assert _request("GET", _url(server, run, branch, saved_rev, season=50))[0] == 422
        assert _request("GET", _url(server, run, branch, saved_rev).split("&season_index=")[0])[0] == 422

        # A selected fork can read its shared original ancestor without changing
        # the original Calendar or claiming ownership of the source result.
        identifiers = iter(("tour-fork", "tour-fork-draft", "tour-fork-root"))
        RunBranchCreationService(
            repository=repo, id_factory=lambda _kind: next(identifiers),
        ).create_from_saved_revision(
            run_id=run, source_branch_id=branch,
            source_saved_revision_id=saved_rev,
        )
        ancestor = _request("GET", _url(server, run, "tour-fork", saved_rev))
        assert ancestor[0] == 200, ancestor
        assert ancestor[1]["branch_id"] == "tour-fork"
        assert ancestor[1]["revision_branch_id"] == branch
        assert ancestor[1]["editions"] == later[1]["editions"]
        assert _request("GET", _url(server, run, branch, empty_rev)) == empty

    with ApiServer(database_url=db) as reopened:
        assert _request("GET", _url(reopened, run, branch, saved_rev)) == later
        assert _request("GET", _url(reopened, run, branch, saved_rev, event_id="event")) == edition
        assert _request("GET", _url(reopened, run, "tour-fork", saved_rev)) == ancestor
        assert _request("GET", _url(reopened, run, branch, empty_rev)) == empty


def test_saved_edition_published_results_are_real_not_calendar_status(tmp_path):
    from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
    from beta_engine.domain.rankings.official import OfficialRankingPolicy
    from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
    from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
    from tests.api.viewer_saved_revision_helpers import save_ranking
    from tests.application.test_viewer_tournament_result_read_model import _source

    db = f"sqlite:///{tmp_path / 'run-tour-result.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(
            server, display_name="Canonical published Edition",
        )
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))
        pre_result_rev = _save(repo, run, branch)
        before = _request(
            "GET", _url(server, run, branch, pre_result_rev, event_id="event"),
        )
        assert before[0] == 200 and before[1]["published_result"] is None
        with repo._session_factory.begin() as session:
            OwnedTournamentRankingSourceStore(session).append(
                _source(run_id=run, branch_id=branch, event_id="event"),
            )
        RankingWeekCommandRunner(repo._session_factory).execute(
            RankingBootstrapCommand(
                command_id="tour-ranking-bootstrap",
                run_id=run, branch_id=branch,
                policy=OfficialRankingPolicy(policy_id="tour-policy"),
                players=(), discipline="none",
            )
        )
        # Published sport must be in a Saved Revision, never just live ranking.
        assert _request(
            "GET", _url(server, run, branch, pre_result_rev, event_id="event"),
        ) == before
        save_ranking(server, run, branch)
        state = _request("GET", f"{server.base_url}/run-branches/{branch}")
        assert state[0] == 200
        post_result_rev = state[1]["saved_head_revision_id"]
        after = _request(
            "GET", _url(server, run, branch, post_result_rev, event_id="event"),
        )
        assert after[0] == 200, after
        assert after[1]["published_result"]["champion_player_id"] == "A"
        assert after[1]["published_result"]["matches"][-1]["match_id"] == "final"
        assert after[1]["edition"]["result_published"] is True
        assert after[1]["lifecycle_status"] == "unavailable"
        assert _request(
            "GET", _url(server, run, branch, pre_result_rev, event_id="event"),
        ) == before
    with ApiServer(database_url=db) as reopened:
        assert _request(
            "GET", _url(reopened, run, branch, post_result_rev, event_id="event"),
        ) == after


def test_readonly_ui_navigation_query_contract(tmp_path):
    """Browser route query uses one immutable revision across seasons and URLs."""
    db = f"sqlite:///{tmp_path / 'saved-tour-ui-query.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, initial = _create_run(
            server, display_name="Saved Tour browser URL contract",
        )
        scope = f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/{quote(branch, safe='')}"
        saved = _request("GET", scope + "/tour/calendar?revision_id=" + quote(initial, safe="") + "&season_index=0")
        assert saved[0] == 200
        assert saved[1]["schema_version"] == "run_saved_tour_calendar.v1"
        assert saved[1]["saved_revision_id"] == initial
        assert saved[1]["season_index"] == 0 and saved[1]["week_count"] == 61
        assert saved[1]["edition_count"] == 0

        other_season = _request("GET", scope + "/tour/calendar?revision_id=" + quote(initial, safe="") + "&season_index=49")
        assert other_season[0] == 200 and other_season[1]["season_index"] == 49
        assert other_season[1]["saved_revision_id"] == initial
        assert other_season[1]["editions"] == []

        assert _request("GET", scope + "/tour/calendar?season_index=0")[0] == 422
        assert _request("GET", scope + "/tour/calendar?revision_id=" + quote(initial, safe=""))[0] == 422
        assert _request("GET", scope + "/tour/calendar?revision_id=nonexistent&season_index=0")[0] == 404
        assert _request("GET", scope + "/tour/editions/unknown?revision_id=" + quote(initial, safe="") + "&season_index=0")[0] == 404

        # An unsaved Calendar copy must never be imported into this pinned URL.
        with server.app.state.runtime.repository._session_factory.begin() as session:
            put_run_package_state(session, _state(run_id=run, branch_id=branch))
        assert _request("GET", scope + "/tour/calendar?revision_id=" + quote(initial, safe="") + "&season_index=0") == saved
