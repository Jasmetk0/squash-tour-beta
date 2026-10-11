"""Production FastAPI/SQLite read boundary for saved weekly ranking movement."""
from __future__ import annotations

from urllib.parse import quote

import pytest

from test_simulation_api import ApiServer, _request
from test_visible_prospects_api import _database_session
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel, PublishedOfficialRankingModel,
)
from tests.api.test_viewer_official_ranking_api import _ranking
from tests.api.viewer_saved_revision_helpers import canonical_product_run, save_ranking


def _url(server, run: str, branch: str) -> str:
    return (
        f"{server.base_url}/admin/runs/{quote(run, safe='')}"
        f"/branches/{quote(branch, safe='')}/home-ranking-changes"
    )


@pytest.mark.pr_critical
def test_run_home_ranking_empty_is_unpublished_and_scope_isolation(tmp_path):
    url = f"sqlite:///{tmp_path / 'home-ranking-empty.sqlite'}"
    with ApiServer(database_url=url) as server:
        branch, run = canonical_product_run(server, "home-ranking-empty")
        other_branch, other_run = canonical_product_run(server, "home-ranking-other")
        status, empty = _request("GET", _url(server, run, branch))
        assert status == 200, empty
        assert empty["schema_version"] == "run_home_ranking_changes.v1"
        assert empty["status"] == "unpublished"
        assert empty["current_week_ordinal"] is None
        assert empty["total_change_count"] == 0 and empty["changes"] == []
        assert empty["saved_revision_id"]
        assert _request("GET", _url(server, run, other_branch))[0] == 404
        assert _request("GET", _url(server, other_run, branch))[0] == 404


@pytest.mark.pr_critical
def test_run_home_ranking_only_compares_consecutive_saved_publications_and_survives_restart(tmp_path):
    db = tmp_path / "home-ranking-saved.sqlite"
    url = f"sqlite:///{db}"
    with ApiServer(database_url=url) as server:
        branch, run = canonical_product_run(server, "home-ranking-saved")
        endpoint = _url(server, run, branch)
        first = _ranking(run_id=run, branch_id=branch,
                         week=RankingWeek(season_index=0, week=1))
        second = _ranking(run_id=run, branch_id=branch,
                          week=RankingWeek(season_index=0, week=2), previous=first)
        third = _ranking(run_id=run, branch_id=branch,
                         week=RankingWeek(season_index=0, week=3), previous=second)

        with _database_session(db) as session:
            session.add_all([
                PublishedOfficialRankingModel(
                    run_id=run, branch_id=branch,
                    week_ordinal=first.week.ordinal,
                    snapshot_fingerprint=first.fingerprint, payload_json=first.model_dump_json(),
                ),
                AuthoritativeWorldStateModel(
                    run_id=run, branch_id=branch,
                    current_ordinal=first.week.ordinal, ranking_fingerprint=first.fingerprint,
                ),
            ])
        # Live publication not visible before immutable Save.
        assert _request("GET", endpoint)[1]["status"] == "unpublished"
        save_ranking(server, run, branch)
        status, first_saved = _request("GET", endpoint)
        assert status == 200, first_saved
        assert first_saved["status"] == "first_publication"
        assert first_saved["current_week_ordinal"] == 0
        assert first_saved["previous_week_ordinal"] is None

        with _database_session(db) as session:
            session.add(PublishedOfficialRankingModel(
                run_id=run, branch_id=branch,
                week_ordinal=second.week.ordinal,
                snapshot_fingerprint=second.fingerprint,
                payload_json=second.model_dump_json(),
            ))
            world = session.get(AuthoritativeWorldStateModel, (run, branch))
            world.current_ordinal = second.week.ordinal
            world.ranking_fingerprint = second.fingerprint
        assert _request("GET", endpoint)[1] == first_saved
        save_ranking(server, run, branch)
        status, saved = _request("GET", endpoint)
        assert status == 200, saved
        assert saved["status"] == "ready"
        assert saved["previous_week_ordinal"] == 0 and saved["current_week_ordinal"] == 1
        assert saved["current_row_count"] == 2
        first_rows = {row.player_id: row for row in first.rows}
        second_rows = {row.player_id: row for row in second.rows}
        expected_changed_ids = {
            player_id for player_id in first_rows.keys() | second_rows.keys()
            if (
                player_id not in first_rows or player_id not in second_rows or
                first_rows[player_id].rank != second_rows[player_id].rank or
                first_rows[player_id].points != second_rows[player_id].points
            )
        }
        assert saved["total_change_count"] == len(expected_changed_ids)
        assert {change["player_id"] for change in saved["changes"]} == expected_changed_ids
        assert saved["moved_count"] == sum(
            change["movement"] in {"up", "down"} for change in saved["changes"]
        )

        # An extra unpublished/future weekly ranking cannot replace the saved head.
        with _database_session(db) as session:
            session.add(PublishedOfficialRankingModel(
                run_id=run, branch_id=branch,
                week_ordinal=third.week.ordinal,
                snapshot_fingerprint=third.fingerprint,
                payload_json=third.model_dump_json(),
            ))
        assert _request("GET", endpoint)[1] == saved

    with ApiServer(database_url=url) as server:
        assert _request("GET", _url(server, run, branch))[1] == saved
