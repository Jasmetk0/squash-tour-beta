from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_point_awards_service import PointAwardApplyRequest, PointAwardGenerateRequest
from beta_engine.application.season_point_breakdown_service import SeasonPointBreakdownService
from test_season_point_awards_service import make_points_service


def _breakdown_service(tmp_path: Path, *, apply: bool = True) -> tuple[SeasonPointBreakdownService, str]:
    point_service, event_id = make_points_service(tmp_path)
    point_service.generate_event_point_awards(event_id=event_id, request=PointAwardGenerateRequest(seed=77, dry_run=False))
    if apply:
        point_service.apply_event_point_awards(event_id=event_id, request=PointAwardApplyRequest(seed=88))
    return SeasonPointBreakdownService(
        point_awards_service=point_service,
        active_players_service=point_service.active_players_service,
        calendar_service=point_service.calendar_service,
    ), event_id


def test_empty_awards_returns_warning_when_active_players_exist(tmp_path: Path) -> None:
    point_service, _ = make_points_service(tmp_path)
    service = SeasonPointBreakdownService(
        point_awards_service=point_service,
        active_players_service=point_service.active_players_service,
        calendar_service=point_service.calendar_service,
    )
    response = service.get_player_point_breakdown(season="2000/2001", limit=3)
    assert response.breakdown is None
    assert len(response.summary_rows) == 3
    assert any("No persisted point award packages" in warning for warning in response.validation_warnings)
    assert response.metadata.source == "season_point_awards"


def test_player_breakdown_from_applied_awards_matches_active_totals(tmp_path: Path) -> None:
    service, event_id = _breakdown_service(tmp_path, apply=True)
    player_id = service.point_awards_service.get_event_point_awards(event_id=event_id).award_package.awards[0].player_id  # type: ignore[union-attr]
    response = service.get_player_point_breakdown(season="2000/2001", player_id=player_id)
    assert response.breakdown is not None
    assert response.breakdown.entries
    entry = response.breakdown.entries[0]
    assert entry.event_id == event_id
    assert entry.reached_stage
    assert entry.ranking_points_awarded >= 0
    assert entry.race_points_awarded >= 0
    assert entry.applied is True
    assert response.breakdown.applied_ranking_points_total == response.breakdown.current_ranking_points
    assert response.breakdown.consistency.ranking_points_match_active_player is True


def test_applied_only_excludes_unapplied_packages(tmp_path: Path) -> None:
    service, event_id = _breakdown_service(tmp_path, apply=False)
    player_id = service.point_awards_service.get_event_point_awards(event_id=event_id).award_package.awards[0].player_id  # type: ignore[union-attr]
    applied_only = service.get_player_point_breakdown(season="2000/2001", player_id=player_id, applied_only=True)
    all_awards = service.get_player_point_breakdown(season="2000/2001", player_id=player_id, applied_only=False)
    assert applied_only.breakdown is not None and all_awards.breakdown is not None
    assert applied_only.breakdown.entries == []
    assert all_awards.breakdown.entries
    assert all_awards.breakdown.unapplied_ranking_points_total > 0
    assert any("Unapplied" in warning for warning in all_awards.validation_warnings)


def test_consistency_mismatch_warns_and_reports_delta(tmp_path: Path) -> None:
    service, event_id = _breakdown_service(tmp_path, apply=True)
    package = service.point_awards_service.get_event_point_awards(event_id=event_id).award_package
    assert package is not None
    player_id = package.awards[0].player_id
    registry = service.active_players_service._load_registry()
    players = registry.players_by_season["2000/2001"]
    registry.players_by_season["2000/2001"] = [
        player.model_copy(update={"ranking_points": player.ranking_points + 5}) if player.player_id == player_id else player
        for player in players
    ]
    service.active_players_service._save_registry(registry)
    response = service.get_player_point_breakdown(season="2000/2001", player_id=player_id)
    assert response.breakdown is not None
    assert response.breakdown.consistency.ranking_points_delta == 5
    assert response.breakdown.consistency.ranking_points_match_active_player is False
    assert any(player_id in warning and "ranking_delta=5" in warning for warning in response.validation_warnings)


def test_search_country_filters_and_summary_sort_are_deterministic(tmp_path: Path) -> None:
    service, _ = _breakdown_service(tmp_path, apply=True)
    response = service.get_player_point_breakdown(season="2000/2001", search="Two", country_code="ENG", limit=10)
    assert [row.player_name for row in response.summary_rows] == ["Bravo Two"]
    assert response.breakdown is not None
    all_response = service.get_player_point_breakdown(season="2000/2001", limit=5)
    ordered = sorted(all_response.summary_rows, key=lambda row: (-row.ranking_points, -row.race_points, -row.breakdown_ranking_points_total, row.player_name.casefold(), row.player_id))
    assert all_response.summary_rows == ordered


def test_entry_sorting_and_generated_fingerprint_are_deterministic(tmp_path: Path) -> None:
    service, event_id = _breakdown_service(tmp_path, apply=True)
    package = service.point_awards_service.get_event_point_awards(event_id=event_id).award_package
    assert package is not None
    player_id = package.awards[0].player_id
    first = service.get_player_point_breakdown(season="2000/2001", player_id=player_id)
    second = service.get_player_point_breakdown(season="2000/2001", player_id=player_id)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.metadata.generated_fingerprint == second.metadata.generated_fingerprint
    assert first.breakdown is not None
    assert first.breakdown.entries == sorted(first.breakdown.entries, key=service._entry_sort_key)


def test_missing_active_players_errors(tmp_path: Path) -> None:
    point_service, _ = make_points_service(tmp_path)
    registry = point_service.active_players_service._load_registry()
    registry.players_by_season.pop("2000/2001")
    point_service.active_players_service._save_registry(registry)
    service = SeasonPointBreakdownService(point_awards_service=point_service, active_players_service=point_service.active_players_service)
    with pytest.raises(ValueError, match="No active season players"):
        service.get_player_point_breakdown(season="2000/2001")
