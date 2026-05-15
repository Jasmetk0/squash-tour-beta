from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_draw_service import DrawGenerateRequest, SeasonDrawService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.application.season_match_service import MatchPackageGenerateRequest, MatchSimulateRequest, SeasonMatchService
from test_season_entry_list_service import first_event_id, make_service


def make_match_service(tmp_path: Path, *, active: bool = True, draw: bool = True) -> tuple[SeasonMatchService, str]:
    entry_service = make_service(tmp_path, calendar=True, active=active)
    event_id = first_event_id(entry_service)
    if active:
        entry_service.generate_entry_list(event_id=event_id, request=EntryListGenerateRequest(seed=123, dry_run=False, overwrite_existing=False))
    draw_service = SeasonDrawService(entry_list_service=entry_service, calendar_service=entry_service.calendar_service, draws_path=tmp_path / "draws.json")
    if active and draw:
        draw_service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=222, dry_run=False, overwrite_existing=False))
    service = SeasonMatchService(draw_service=draw_service, active_players_service=entry_service.active_players_service, matches_path=tmp_path / "matches.json")
    return service, event_id


def test_missing_prerequisites_block_match_generation(tmp_path: Path) -> None:
    service, event_id = make_match_service(tmp_path / "missing-draw", active=True, draw=False)
    with pytest.raises(ValueError, match="No persisted draw package"):
        service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest())

    service, event_id = make_match_service(tmp_path / "missing-active", active=False, draw=False)
    # Seed a minimal persisted draw path is not possible without active entries, so no draw remains the first hard prerequisite.
    with pytest.raises(ValueError, match="No persisted draw package"):
        service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest())

    service, event_id = make_match_service(tmp_path / "draw-errors", active=True, draw=True)
    registry = service.draw_service._load_registry()
    package = registry.draws_by_event_id[event_id]
    package.validation_errors.append(service.draw_service._issue("error", "synthetic_draw_error", "synthetic", event_id=event_id))
    service.draw_service._save_registry(registry)
    with pytest.raises(ValueError, match="validation errors"):
        service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest())


def test_dry_run_persist_overwrite_and_determinism(tmp_path: Path) -> None:
    service, event_id = make_match_service(tmp_path)

    first = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=True))
    second = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=True))
    different = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=102, dry_run=True))

    assert first.match_package is not None and second.match_package is not None and different.match_package is not None
    assert first.match_package.model_dump() == second.match_package.model_dump()
    assert first.metadata and second.metadata and first.metadata.build_fingerprint == second.metadata.build_fingerprint
    assert different.metadata and different.metadata.build_fingerprint != first.metadata.build_fingerprint
    assert service.get_match_package(event_id=event_id).match_package_exists is False

    persisted = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=False))
    assert persisted.match_package and persisted.match_package.persisted is True
    assert service.get_match_package(event_id=event_id).match_package_exists is True
    with pytest.raises(ValueError, match="already exists"):
        service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=False))
    overwritten = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=102, dry_run=False, overwrite_existing=True))
    assert overwritten.metadata and overwritten.metadata.seed == 102


def test_status_classification_and_warnings(tmp_path: Path) -> None:
    service, event_id = make_match_service(tmp_path)

    package = service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=True)).match_package

    assert package is not None
    matches = package.qualification_matches + package.main_draw_matches
    assert package.summary.total_matches == len(matches)
    assert any(match.status == "pending" and match.top_player_id and match.bottom_player_id for match in matches)
    assert any(match.status == "blocked_waiting_for_sources" for match in matches)
    assert any(issue.code in {"blocked_matches_waiting_for_sources", "qualification_promotion_not_connected"} for issue in package.validation_warnings)
    assert any(issue.code == "ranking_race_not_implemented" for issue in package.validation_warnings)


def test_simulate_selected_next_deterministic_propagates_and_preserves_points(tmp_path: Path) -> None:
    service, event_id = make_match_service(tmp_path)
    service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=False))
    active_before = service.active_players_service.get_active_players(season="2000/2001").players
    points_before = {player.player_id: (player.ranking_points, player.race_points) for player in active_before}

    package = service.get_match_package(event_id=event_id).match_package
    assert package is not None
    first_pending = next(match for match in sorted(package.qualification_matches + package.main_draw_matches, key=lambda m: (m.draw_type != "qualification", m.round_number, m.bracket_position)) if match.status == "pending")
    selected = service.simulate_match(event_id=event_id, match_id=first_pending.match_id, request=MatchSimulateRequest(seed=555)).match_package

    assert selected is not None
    completed = next(match for match in selected.qualification_matches + selected.main_draw_matches if match.match_id == first_pending.match_id)
    assert completed.status == "completed"
    assert completed.winner_player_id is not None
    assert completed.loser_player_id is not None
    assert completed.scoreline
    assert completed.result_fingerprint
    assert completed.simulation_seed
    if completed.winner_to_match_id:
      downstream = next(match for match in selected.qualification_matches + selected.main_draw_matches if match.match_id == completed.winner_to_match_id)
      assert completed.winner_player_id in {downstream.top_player_id, downstream.bottom_player_id}

    active_after = service.active_players_service.get_active_players(season="2000/2001").players
    assert {player.player_id: (player.ranking_points, player.race_points) for player in active_after} == points_before



def test_simulate_rejects_non_pending_and_missing_player_match(tmp_path: Path) -> None:
    service, event_id = make_match_service(tmp_path)
    service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=False))
    package = service.get_match_package(event_id=event_id).match_package
    assert package is not None
    blocked = next(match for match in package.qualification_matches + package.main_draw_matches if match.status == "blocked_waiting_for_sources")
    with pytest.raises(ValueError, match="not pending"):
        service.simulate_match(event_id=event_id, match_id=blocked.match_id, request=MatchSimulateRequest(seed=1))
    with pytest.raises(ValueError, match="not found"):
        service.simulate_match(event_id=event_id, match_id="missing", request=MatchSimulateRequest(seed=1))


def test_simulate_next_completes_first_pending_and_is_replay_deterministic(tmp_path: Path) -> None:
    service_a, event_id_a = make_match_service(tmp_path / "a")
    service_b, event_id_b = make_match_service(tmp_path / "b")
    service_a.generate_match_package(event_id=event_id_a, request=MatchPackageGenerateRequest(seed=101, dry_run=False))
    service_b.generate_match_package(event_id=event_id_b, request=MatchPackageGenerateRequest(seed=101, dry_run=False))

    a = service_a.simulate_next_match(event_id=event_id_a, request=MatchSimulateRequest(seed=777)).match_package
    b = service_b.simulate_next_match(event_id=event_id_b, request=MatchSimulateRequest(seed=777)).match_package

    assert a is not None and b is not None
    a_completed = next(match for match in a.qualification_matches + a.main_draw_matches if match.status == "completed")
    b_completed = next(match for match in b.qualification_matches + b.main_draw_matches if match.status == "completed")
    assert a_completed.model_dump() == b_completed.model_dump()
