from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_event_results_service import EventResultExtractRequest
from beta_engine.application.season_point_awards_service import PointAwardApplyRequest, PointAwardGenerateRequest, SeasonPointAwardsService
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayersRegistry
from test_season_event_results_service import _persist_synthetic_package


def make_points_service(tmp_path: Path, *, incomplete: bool = False) -> tuple[SeasonPointAwardsService, str]:
    result_service, event_id = _persist_synthetic_package(tmp_path, incomplete=incomplete)
    result_service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=False))
    active_registry = result_service.match_service.active_players_service._load_registry()
    players = active_registry.players_by_season["2000/2001"]
    for index in range(min(8, len(players))):
        players[index] = players[index].model_copy(update={"player_id": f"P{index + 1}", "name": ["Alpha One", "Bravo Two", "Charlie Three", "Delta Four", "Echo Five", "Foxtrot Six", "Q Seven", "Q Eight"][index], "country_code": "EGY" if index in {0, 6} else "ENG"})
    active_registry.players_by_season["2000/2001"] = players
    result_service.match_service.active_players_service._save_registry(active_registry)
    service = SeasonPointAwardsService(
        result_service=result_service,
        active_players_service=result_service.match_service.active_players_service,
        calendar_service=result_service.calendar_service,
        awards_path=tmp_path / "points.json",
        points_config_path=tmp_path / "missing-points.json",
    )
    return service, event_id


def points_by_stage(service: SeasonPointAwardsService, event_id: str) -> dict[str, int]:
    package = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=True)).award_package
    assert package is not None
    return {award.reached_stage: award.ranking_points_awarded for award in package.awards}


def test_missing_result_package_errors(tmp_path: Path) -> None:
    result_service, _ = _persist_synthetic_package(tmp_path)
    service = SeasonPointAwardsService(result_service=result_service, active_players_service=result_service.match_service.active_players_service, awards_path=tmp_path / "points.json")
    with pytest.raises(ValueError, match="Persist event results first"):
        service.generate_event_point_awards(event_id="EVT-missing", request=PointAwardGenerateRequest())


def test_dry_run_awards_do_not_persist_or_mutate_players(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path)
    before = {p.player_id: (p.ranking_points, p.race_points) for p in service.active_players_service.get_active_players(season="2000/2001").players}
    result = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=True))
    package = result.award_package
    assert package is not None
    assert package.persisted is False
    assert result.award_package_exists is False
    assert package.summary.champion_points == 1000
    assert package.summary.finalist_points == 650
    assert any(issue.code == "point_distribution_fallback_used" for issue in package.validation_warnings)
    assert service.get_event_point_awards(event_id=event_id).award_package_exists is False
    after = {p.player_id: (p.ranking_points, p.race_points) for p in service.active_players_service.get_active_players(season="2000/2001").players}
    assert after == before


def test_persist_get_overwrite_safety_and_stage_mapping(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path)
    persisted = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False))
    assert persisted.award_package_exists is True
    assert service.awards_path.exists()
    loaded = service.get_event_point_awards(event_id=event_id)
    assert loaded.metadata and persisted.metadata
    assert loaded.metadata.build_fingerprint == persisted.metadata.build_fingerprint
    with pytest.raises(ValueError, match="already exists"):
        service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False))
    overwritten = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=78, dry_run=False, overwrite_existing=True))
    assert overwritten.metadata and overwritten.metadata.seed == 78
    stage_points = {award.reached_stage: award.ranking_points_awarded for award in overwritten.award_package.awards}  # type: ignore[union-attr]
    assert stage_points["champion"] == 1000
    assert stage_points["finalist"] == 650
    assert stage_points["semifinal"] == 400
    if "qualification_winner" in stage_points:
        assert stage_points["qualification_winner"] == 25


def test_apply_mutates_only_awarded_players_and_blocks_duplicates(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path)
    persisted = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False)).award_package
    assert persisted is not None
    before_players = service.active_players_service.get_active_players(season="2000/2001").players
    before = {p.player_id: (p.ranking_points, p.race_points) for p in before_players}
    result = service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest(seed=99))
    assert result.applied is True
    assert result.award_package and result.award_package.applied is True
    after_players = service.active_players_service.get_active_players(season="2000/2001").players
    after = {p.player_id: (p.ranking_points, p.race_points) for p in after_players}
    award_by_player = {award.player_id: award for award in persisted.awards}
    for player_id, old_points in before.items():
        award = award_by_player.get(player_id)
        expected = old_points if award is None else (old_points[0] + award.ranking_points_awarded, old_points[1] + award.race_points_awarded)
        assert after[player_id] == expected
    assert result.updated_players
    with pytest.raises(ValueError, match="already been applied"):
        service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest(seed=99))


def test_missing_active_player_apply_errors_without_partial_mutation(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path)
    service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False))
    registry = service.active_players_service._load_registry()
    before = registry.model_dump(mode="json")
    awarded_id = service.get_event_point_awards(event_id=event_id).award_package.awards[0].player_id  # type: ignore[union-attr]
    registry.players_by_season["2000/2001"] = [p for p in registry.players_by_season["2000/2001"] if p.player_id != awarded_id]
    service.active_players_service._save_registry(registry)
    with pytest.raises(ValueError, match="missing from active season players"):
        service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest())
    # Ensure no awarded player received a partial update before the missing-player validation failed.
    current = service.active_players_service._load_registry().model_dump(mode="json")
    assert current != before
    assert all(player["ranking_points"] == 0 and player["race_points"] == 0 for player in current["players_by_season"]["2000/2001"])


def test_incomplete_event_preview_persist_allowed_but_apply_blocked(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path, incomplete=True)
    preview = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(dry_run=True)).award_package
    assert preview is not None
    assert any(issue.code == "event_result_incomplete" for issue in preview.validation_warnings)
    service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(dry_run=False))
    with pytest.raises(ValueError, match="completion_status is 'incomplete'"):
        service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest())


def test_determinism_and_seed_fingerprint(tmp_path: Path) -> None:
    service, event_id = make_points_service(tmp_path)
    first = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=1, dry_run=True)).award_package
    second = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=1, dry_run=True)).award_package
    different = service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=2, dry_run=True)).award_package
    assert first and second and different
    assert first.model_dump() == second.model_dump()
    assert [a.ranking_points_awarded for a in first.awards] == [a.ranking_points_awarded for a in different.awards]
    assert first.metadata.build_fingerprint != different.metadata.build_fingerprint
