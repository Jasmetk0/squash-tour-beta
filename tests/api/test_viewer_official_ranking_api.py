from __future__ import annotations

import pytest
from urllib.parse import quote

from test_simulation_api import ApiServer, _request
from test_visible_prospects_api import _canonical_run, _database_session

from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
    calculate_official_ranking,
)
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
)


def _ranking(*, branch_id: str, week: RankingWeek, previous=None):
    return calculate_official_ranking(
        run_id="run",
        branch_id=branch_id,
        week=week,
        policy=OfficialRankingPolicy(policy_id="viewer-ranking-policy", best_n=15),
        players=(
            OfficialRankingPlayer(
                player_id="player-a",
                tie_break_token="a" * 64,
                tour_entry_week=RankingWeek(season_index=0, week=1),
            ),
            OfficialRankingPlayer(
                player_id="player-b",
                tie_break_token="b" * 64,
                tour_entry_week=RankingWeek(season_index=0, week=1),
            ),
        ),
        results=(),
        previous=previous,
    )


@pytest.mark.pr_critical
def test_viewer_current_ranking_uses_public_world_head_and_ignores_future_publication(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-official-ranking.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week_one = RankingWeek(season_index=0, week=1)
        week_two = RankingWeek(season_index=0, week=2)
        week_three = RankingWeek(season_index=0, week=3)
        opening = _ranking(branch_id=branch_id, week=week_one)
        current = _ranking(branch_id=branch_id, week=week_two, previous=opening)
        future = _ranking(branch_id=branch_id, week=week_three, previous=current)

        with _database_session(path) as session:
            session.add_all(
                [
                    PublishedOfficialRankingModel(
                        run_id="run",
                        branch_id=branch_id,
                        week_ordinal=current.week.ordinal,
                        snapshot_fingerprint=current.fingerprint,
                        payload_json=current.model_dump_json(),
                    ),
                    PublishedOfficialRankingModel(
                        run_id="run",
                        branch_id=branch_id,
                        week_ordinal=future.week.ordinal,
                        snapshot_fingerprint=future.fingerprint,
                        payload_json=future.model_dump_json(),
                    ),
                    AuthoritativeWorldStateModel(
                        run_id="run",
                        branch_id=branch_id,
                        current_ordinal=current.week.ordinal,
                        ranking_fingerprint=current.fingerprint,
                    ),
                ]
            )

        status, payload = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote('run', safe='')}/rankings/current",
        )
        assert status == 200
        assert payload["schema_version"] == "viewer_official_ranking.v1"
        assert payload["product_run_id"] == "run"
        assert payload["viewer_branch_id"] == branch_id
        assert payload["season_index"] == 0
        assert payload["week"] == 2
        assert payload["week_ordinal"] == week_two.ordinal
        assert payload["snapshot_fingerprint"] == current.fingerprint
        assert payload["snapshot_fingerprint"] != future.fingerprint
        assert payload["policy_id"] == "viewer-ranking-policy"
        assert payload["best_n"] == 15
        assert payload["row_count"] == 2
        assert [row["player_id"] for row in payload["rows"]] == ["player-a", "player-b"]


@pytest.mark.pr_critical
def test_viewer_current_ranking_fails_closed_when_publication_and_world_head_disagree(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-official-ranking-corrupt.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week = RankingWeek(season_index=0, week=1)
        ranking = _ranking(branch_id=branch_id, week=week)

        with _database_session(path) as session:
            session.add(
                PublishedOfficialRankingModel(
                    run_id="run",
                    branch_id=branch_id,
                    week_ordinal=week.ordinal,
                    snapshot_fingerprint=ranking.fingerprint,
                    payload_json=ranking.model_dump_json(),
                )
            )
            session.add(
                AuthoritativeWorldStateModel(
                    run_id="run",
                    branch_id=branch_id,
                    current_ordinal=week.ordinal,
                    ranking_fingerprint="f" * 64,
                )
            )

        status, payload = _request(
            "GET",
            f"{server.base_url}/viewer/runs/{quote('run', safe='')}/rankings/current",
        )
        assert status == 409
        assert payload["detail"]["code"] == "viewer_official_ranking_unavailable"
        assert "does not match the public world head" in payload["detail"]["message"]


@pytest.mark.pr_critical
def test_viewer_ranking_history_lists_only_public_branch_publications_and_detail_is_historical(
    tmp_path,
) -> None:
    path = tmp_path / "viewer-ranking-history.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        branch_id, _ = _canonical_run(server)
        week_one = RankingWeek(season_index=0, week=1)
        week_two = RankingWeek(season_index=0, week=2)
        week_three = RankingWeek(season_index=0, week=3)
        opening = _ranking(branch_id=branch_id, week=week_one)
        current = _ranking(branch_id=branch_id, week=week_two, previous=opening)
        future = _ranking(branch_id=branch_id, week=week_three, previous=current)

        with _database_session(path) as session:
            session.add_all(
                [
                    PublishedOfficialRankingModel(
                        run_id="run",
                        branch_id=branch_id,
                        week_ordinal=opening.week.ordinal,
                        snapshot_fingerprint=opening.fingerprint,
                        payload_json=opening.model_dump_json(),
                    ),
                    PublishedOfficialRankingModel(
                        run_id="run",
                        branch_id=branch_id,
                        week_ordinal=current.week.ordinal,
                        snapshot_fingerprint=current.fingerprint,
                        payload_json=current.model_dump_json(),
                    ),
                    PublishedOfficialRankingModel(
                        run_id="run",
                        branch_id=branch_id,
                        week_ordinal=future.week.ordinal,
                        snapshot_fingerprint=future.fingerprint,
                        payload_json=future.model_dump_json(),
                    ),
                    AuthoritativeWorldStateModel(
                        run_id="run",
                        branch_id=branch_id,
                        current_ordinal=current.week.ordinal,
                        ranking_fingerprint=current.fingerprint,
                    ),
                ]
            )

        root = f"{server.base_url}/viewer/runs/{quote('run', safe='')}/rankings"
        status, history = _request("GET", root + "/history")
        assert status == 200
        assert history["schema_version"] == "viewer_official_ranking_history.v1"
        assert history["viewer_branch_id"] == branch_id
        assert history["public_head_ordinal"] == current.week.ordinal
        assert history["publication_count"] == 2
        assert [item["week_ordinal"] for item in history["publications"]] == [
            current.week.ordinal,
            opening.week.ordinal,
        ]
        assert future.week.ordinal not in {
            item["week_ordinal"] for item in history["publications"]
        }

        status, detail = _request("GET", root + f"/history/{opening.week.ordinal}")
        assert status == 200
        assert detail["week"] == 1
        assert detail["snapshot_fingerprint"] == opening.fingerprint

        status, blocked = _request("GET", root + f"/history/{future.week.ordinal}")
        assert status == 409
        assert blocked["detail"]["code"] == "viewer_official_ranking_unavailable"
        assert "future publication" in blocked["detail"]["message"]
