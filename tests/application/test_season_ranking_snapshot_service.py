from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.season_ranking_snapshot_service import SeasonRankingSnapshotService, WeeklyRankingSnapshotGenerateRequest
from beta_engine.application.season_ranking_table_service import SeasonRankingTableService
from test_initial_pool_season_bootstrap import services


def _service(tmp_path: Path) -> tuple[SeasonRankingSnapshotService, object]:
    pool, bootstrap = services(tmp_path)
    pool.generate_pool(season="2000/2001", seed=7, target_pool_size=4, dry_run=False)
    bootstrap.bootstrap_from_initial_pool(season="2000/2001", seed=123, dry_run=False)
    registry = bootstrap._load_registry()
    players = sorted(registry.players_by_season["2000/2001"], key=lambda player: player.player_id)
    updates = [
        {"player_id": "P-A", "name": "Alpha One", "country_code": "AAA", "nationality": "AAA", "ranking_points": 100, "race_points": 40, "current_ability": 70},
        {"player_id": "P-B", "name": "Bravo Two", "country_code": "BBB", "nationality": "BBB", "ranking_points": 80, "race_points": 110, "current_ability": 69},
        {"player_id": "P-C", "name": "Charlie Three", "country_code": "AAA", "nationality": "AAA", "ranking_points": 30, "race_points": 70, "current_ability": 68},
        {"player_id": "P-D", "name": "Delta Four", "country_code": "BBB", "nationality": "BBB", "ranking_points": 0, "race_points": 0, "current_ability": 67},
    ]
    registry.players_by_season["2000/2001"] = [player.model_copy(update=update) for player, update in zip(players, updates, strict=True)]
    bootstrap._save_registry(registry)
    ranking = SeasonRankingTableService(active_players_service=bootstrap)
    return SeasonRankingSnapshotService(ranking_table_service=ranking, snapshots_path=tmp_path / "season_ranking_snapshots.json"), bootstrap


def test_dry_run_snapshot_does_not_persist(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    result = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=True))

    assert result.snapshot is not None
    assert result.snapshot.persisted is False
    assert result.snapshot.ranking_table.rows[0].player_id == "P-A"
    assert result.snapshot.race_table.rows[0].player_id == "P-B"
    assert not (tmp_path / "season_ranking_snapshots.json").exists()


def test_persist_get_and_overwrite_safety(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    first = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=False))
    assert first.snapshot_exists is True
    loaded = service.get_snapshot(season="2000/2001", season_week=1)
    assert loaded.snapshot is not None
    assert loaded.snapshot.metadata.snapshot_fingerprint == first.snapshot.metadata.snapshot_fingerprint

    rejected = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=False))
    assert rejected.validation_errors
    overwritten = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=False, overwrite_existing=True, seed=999))
    assert overwritten.snapshot is not None
    assert overwritten.snapshot.metadata.generated_seed == 999


def test_movement_independent_for_ranking_and_race(tmp_path: Path) -> None:
    service, bootstrap = _service(tmp_path)
    service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=False))
    registry = bootstrap._load_registry()
    updated = []
    for player in registry.players_by_season["2000/2001"]:
        if player.player_id == "P-B":
            updated.append(player.model_copy(update={"ranking_points": 130, "race_points": 90}))
        elif player.player_id == "P-C":
            updated.append(player.model_copy(update={"ranking_points": 20, "race_points": 120}))
        else:
            updated.append(player)
    registry.players_by_season["2000/2001"] = updated
    bootstrap._save_registry(registry)
    active_before_snapshot_generation = json.loads(bootstrap.active_players_path.read_text(encoding="utf-8"))

    result = service.generate_snapshot(season="2000/2001", season_week=2, request=WeeklyRankingSnapshotGenerateRequest(dry_run=True))
    ranking_by_id = {row.player_id: row for row in result.snapshot.ranking_table.rows}
    race_by_id = {row.player_id: row for row in result.snapshot.race_table.rows}
    assert ranking_by_id["P-B"].movement > 0
    assert ranking_by_id["P-A"].movement < 0
    assert race_by_id["P-C"].movement > 0
    assert race_by_id["P-B"].movement < 0
    assert json.loads(bootstrap.active_players_path.read_text(encoding="utf-8")) == active_before_snapshot_generation


def test_determinism_seed_and_invalid_empty_states(tmp_path: Path) -> None:
    service, _ = _service(tmp_path)
    first = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=True, seed=1))
    second = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=True, seed=1))
    third = service.generate_snapshot(season="2000/2001", season_week=1, request=WeeklyRankingSnapshotGenerateRequest(dry_run=True, seed=2))
    assert first.snapshot.model_dump(mode="json") == second.snapshot.model_dump(mode="json")
    assert first.snapshot.metadata.snapshot_fingerprint != third.snapshot.metadata.snapshot_fingerprint
    assert [row.player_id for row in first.snapshot.ranking_table.rows] == [row.player_id for row in third.snapshot.ranking_table.rows]

    invalid = service.generate_snapshot(season="2000/2001", season_week=62, request=WeeklyRankingSnapshotGenerateRequest())
    assert invalid.validation_errors
    empty = service.generate_snapshot(season="2099/2100", season_week=1, request=WeeklyRankingSnapshotGenerateRequest())
    assert empty.validation_errors
