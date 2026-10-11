from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_ranking_table_service import SeasonRankingTableService
from test_initial_pool_season_bootstrap import services


def _service_with_ranked_players(tmp_path: Path) -> SeasonRankingTableService:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=5, dry_run=False)
    bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=123, dry_run=False)
    registry = bootstrap._load_registry()
    players = sorted(registry.players_by_season["2000/2001"], key=lambda player: player.player_id)
    updates = [
        {"player_id": "P-A", "name": "Alpha One", "country_code": "AAA", "nationality": "AAA", "ranking_points": 100, "race_points": 25, "current_ability": 70},
        {"player_id": "P-B", "name": "Bravo Two", "country_code": "BBB", "nationality": "BBB", "ranking_points": 80, "race_points": 90, "current_ability": 69},
        {"player_id": "P-C", "name": "Charlie Three", "country_code": "AAA", "nationality": "AAA", "ranking_points": 80, "race_points": 70, "current_ability": 68},
        {"player_id": "P-D", "name": "Delta Four", "country_code": "BBB", "nationality": "BBB", "ranking_points": 0, "race_points": 0, "current_ability": 67},
        {"player_id": "P-E", "name": "Echo Five", "country_code": "AAA", "nationality": "AAA", "ranking_points": 80, "race_points": 70, "current_ability": 68},
    ]
    controlled_players = []
    for player, update in zip(players, updates, strict=True):
        hidden = player.hidden_career_traits.model_copy(
            update={"potential_ceiling": max(90, player.hidden_career_traits.potential_ceiling)}
        )
        controlled_players.append(
            player.model_copy(
                update={
                    **update,
                    "potential_ability": 90,
                    "hidden_career_traits": hidden,
                }
            )
        )
    registry.players_by_season["2000/2001"] = controlled_players
    bootstrap._save_registry(registry)
    return SeasonRankingTableService(active_players_service=bootstrap)


def test_ranking_table_sorts_by_ranking_points_descending(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    response = service.get_table(season="2000/2001", table_type="ranking")

    assert [row.player_id for row in response.rows[:5]] == ["P-A", "P-B", "P-C", "P-E", "P-D"]
    assert [row.table_points for row in response.rows[:4]] == [100, 80, 80, 80]
    assert response.metadata.ranking_basis == "current active season player ranking_points"


def test_race_table_sorts_by_race_points_descending(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    response = service.get_table(season="2000/2001", table_type="race")

    assert [row.player_id for row in response.rows[:4]] == ["P-B", "P-C", "P-E", "P-A"]
    assert [row.table_points for row in response.rows[:4]] == [90, 70, 70, 25]
    assert response.metadata.ranking_basis == "current active season player race_points"


def test_tie_behavior_competition_dense_and_ordinal(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    response = service.get_table(season="2000/2001", table_type="ranking")

    tied_rows = response.rows[1:4]
    assert [row.rank for row in response.rows[:5]] == [1, 2, 2, 2, 5]
    assert [row.dense_rank for row in response.rows[:5]] == [1, 2, 2, 2, 3]
    assert [row.ordinal_position for row in response.rows[:5]] == [1, 2, 3, 4, 5]
    assert {row.table_points for row in tied_rows} == {80}


def test_filters_preserve_original_world_rank(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    response = service.get_table(season="2000/2001", table_type="ranking", country_code="BBB")

    assert [row.player_id for row in response.rows] == ["P-B", "P-D"]
    assert [row.rank for row in response.rows] == [2, 5]
    assert response.summary.player_count == 2
    assert response.summary.total_source_players == 5


def test_include_zero_points_false_removes_zero_rows(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    response = service.get_table(season="2000/2001", table_type="ranking", include_zero_points=False)

    assert "P-D" not in [row.player_id for row in response.rows]
    assert response.summary.zero_point_players == 0


def test_country_search_min_points_and_limit_work(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    country = service.get_table(season="2000/2001", table_type="race", country_code="aaa")
    assert [row.country_code for row in country.rows] == ["AAA", "AAA", "AAA"]

    search = service.get_table(season="2000/2001", table_type="ranking", search="echo")
    assert [row.player_id for row in search.rows] == ["P-E"]

    by_id = service.get_table(season="2000/2001", table_type="ranking", search="p-b")
    assert [row.player_id for row in by_id.rows] == ["P-B"]

    min_points = service.get_table(season="2000/2001", table_type="race", min_points=70)
    assert [row.player_id for row in min_points.rows] == ["P-B", "P-C", "P-E"]

    limited = service.get_table(season="2000/2001", table_type="ranking", limit=2)
    assert [row.player_id for row in limited.rows] == ["P-A", "P-B"]


def test_deterministic_response_and_fingerprint(tmp_path: Path) -> None:
    service = _service_with_ranked_players(tmp_path)

    first = service.get_table(season="2000/2001", table_type="ranking", limit=4)
    second = service.get_table(season="2000/2001", table_type="ranking", limit=4)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint


def test_empty_season_errors_cleanly(tmp_path: Path) -> None:
    _, bootstrap = services(tmp_path)
    service = SeasonRankingTableService(active_players_service=bootstrap)

    with pytest.raises(ValueError, match="No active season players"):
        service.get_table(season="2000/2001")
