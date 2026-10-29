"""Real HTTP + persistent SQLite Saved roster ranking filters, no mocked repository.

This exercises the exact selected Branch Saved HEAD boundary, not the legacy
Run-level player finder, live Official Ranking or a fabricated service response.
"""
from urllib.parse import quote, urlencode

import pytest

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer, OfficialRankingPolicy, RankingWeek, calculate_official_ranking,
)
from beta_engine.infrastructure.db.initial_world_state import put_initial_world
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
)
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.api.viewer_saved_revision_helpers import save_ranking
from tests.application.test_viewer_people_read_model import _initial_player, _world


pytestmark = pytest.mark.pr_critical


def _url(server, run, branch, **filters):
    root = (
        f"{server.base_url}/admin/runs/{quote(run, safe='')}/branches/"
        f"{quote(branch, safe='')}/saved-players"
    )
    return root + ("?" + urlencode(filters) if filters else "")


def _read(server, run, branch, **filters):
    status, response = _request("GET", _url(server, run, branch, **filters))
    assert status == 200, (status, response, filters)
    return response


def _save_initial_world(server, run, branch):
    root = (
        f"{server.base_url}/admin/players/runs/{quote(run, safe='')}"
        f"/branches/{quote(branch, safe='')}/initial-world/save"
    )
    status, preview = _request("GET", root + "/preview")
    assert status == 200 and preview["can_save"], (status, preview)
    status, saved = _request("POST", root, {
        "expected_draft_version": preview["draft_version"],
        "expected_initial_world_fingerprint": preview["initial_world_fingerprint"],
    })
    assert status == 201, (status, saved)
    return saved


def _publish_real_ranking(server, run, branch):
    week = RankingWeek(season_index=0, week=1)
    snapshot = calculate_official_ranking(
        run_id=run, branch_id=branch, week=week,
        policy=OfficialRankingPolicy(policy_id="saved-roster-http", best_n=15),
        players=tuple(
            OfficialRankingPlayer(
                player_id=player_id,
                tie_break_token=token * 64,
                tour_entry_week=week,
            )
            for player_id, token in (("player-a", "a"), ("player-b", "b"))
        ),
        results=(),
    )
    repo = server.app.state.runtime.repository
    with repo._session_factory.begin() as session:
        session.add_all((
            PublishedOfficialRankingModel(
                run_id=run, branch_id=branch,
                week_ordinal=week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            ),
            AuthoritativeWorldStateModel(
                run_id=run, branch_id=branch,
                current_ordinal=week.ordinal,
                ranking_fingerprint=snapshot.fingerprint,
            ),
        ))
    return snapshot


def test_saved_country_ranking_filter_real_http_sqlite_publish_and_restart(tmp_path):
    db = f"sqlite:///{tmp_path / 'saved-roster-ranking-filter.sqlite'}"
    with ApiServer(database_url=db) as server:
        run, branch, _ = _create_run(server, display_name="Saved roster HTTP filter")
        other_run, other_branch, _ = _create_run(server, display_name="Foreign roster")
        initial = _world().model_copy(update={
            "run_id": run, "branch_id": branch,
            "players": (
                _initial_player("player-a", "Alpha Current", "CZE"),
                _initial_player("player-b", "Beta Current", "EGY"),
                _initial_player("player-c", "Charlie Current", "CZE"),
            ),
        })
        with server.app.state.runtime.repository._session_factory.begin() as session:
            put_initial_world(session, initial)

        # Working Draft is not the Saved source. Never leak unsaved identities.
        before = _read(server, run, branch)
        assert before["total"] == 0 and before["players"] == []
        assert before["ranking_status_filter"] == ""

        _save_initial_world(server, run, branch)
        unpublished = _read(server, run, branch, country_code="CZE",
                            ranking_status_filter="unpublished")
        assert unpublished["source"] == "selected_branch_saved_revision"
        assert unpublished["time_context"] == "present"
        assert unpublished["total"] == 2
        assert [row["player_id"] for row in unpublished["players"]] == [
            "player-a", "player-c"
        ]
        assert all(row["rank"] is None and row["ranking_status"] == "unpublished"
                   for row in unpublished["players"])
        assert _read(server, run, branch, ranking_status_filter="ranked")["total"] == 0
        assert _read(server, run, branch, ranking_status_filter="unranked")["total"] == 0
        old_head = unpublished["saved_revision_id"]

        # The live Ranking publication must not leak until an explicit Save.
        _publish_real_ranking(server, run, branch)
        assert _read(server, run, branch, country_code="CZE",
                     ranking_status_filter="unpublished") == unpublished
        assert _read(server, run, branch, ranking_status_filter="ranked")["total"] == 0
        save_ranking(server, run, branch)
        ranked = _read(server, run, branch, ranking_status_filter="ranked")
        unranked = _read(server, run, branch, ranking_status_filter="unranked")
        assert ranked["saved_revision_id"] != old_head
        assert ranked["ranking_week_ordinal"] == 0
        assert ranked["total"] == 2 and unranked["total"] == 1
        assert [row["player_id"] for row in ranked["players"]] == [
            "player-a", "player-b"
        ]
        assert [row["player_id"] for row in unranked["players"]] == ["player-c"]
        assert all(row["ranking_status"] == "ranked" and row["rank"] is not None
                   for row in ranked["players"])
        assert unranked["players"][0]["rank"] is None
        assert _read(server, run, branch, ranking_status_filter="unpublished")["total"] == 0

        # Combined server filters must apply before paging, never to one UI page.
        czech_ranked = _read(server, run, branch,
                             country_code="CZE", ranking_status_filter="ranked",
                             search="Alpha", status_filter="active", limit=1, offset=0)
        assert czech_ranked["total"] == 1 and len(czech_ranked["players"]) == 1
        assert czech_ranked["players"][0]["player_id"] == "player-a"
        assert not czech_ranked["has_more"]
        page = _read(server, run, branch, ranking_status_filter="ranked", limit=1, offset=1)
        assert page["total"] == 2 and len(page["players"]) == 1
        assert page["players"][0]["player_id"] == "player-b" and not page["has_more"]
        assert _read(server, run, branch, ranking_status_filter="ranked", limit=1, offset=2)[
            "players"] == []
        assert _request("GET", _url(server, run, branch, ranking_status_filter="guessed"))[0] == 422
        assert _request("GET", _url(server, run, other_branch))[0] == 404
        assert _request("GET", _url(server, other_run, branch))[0] == 404

    # Exact immutable Saved HEAD and published ranking survive a physical DB reopen.
    with ApiServer(database_url=db) as reopened:
        assert _read(reopened, run, branch, ranking_status_filter="ranked") == ranked
        assert _read(reopened, run, branch, ranking_status_filter="unranked") == unranked
        assert _read(reopened, run, branch,
                     country_code="CZE", ranking_status_filter="ranked",
                     search="Alpha", status_filter="active", limit=1, offset=0) == czech_ranked
