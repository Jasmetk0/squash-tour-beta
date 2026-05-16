from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_event_results_service import EventResultExtractRequest, SeasonEventResultsService
from beta_engine.application.season_match_service import MatchPackageGenerateRequest, SeasonMatchRecord, SeasonMatchesRegistry
from test_season_match_service import make_match_service


def _record(event_id: str, draw_type: str, round_number: int, pos: int, top: tuple[str, str, str] | None, bottom: tuple[str, str, str] | None, winner: str | None, loser: str | None, *, status: str = "completed", scoreline: str | None = "11-7, 11-8, 11-9") -> SeasonMatchRecord:
    top_id, top_name, top_country = top or (None, None, None)
    bot_id, bot_name, bot_country = bottom or (None, None, None)
    return SeasonMatchRecord(
        match_id=f"{event_id}:{draw_type.upper()}:R{round_number}:M{pos}",
        event_id=event_id,
        draw_type=draw_type,  # type: ignore[arg-type]
        round_number=round_number,
        round_name=f"Round {round_number}",
        bracket_position=pos,
        top_slot_id=f"{draw_type}-s{pos}a",
        bottom_slot_id=f"{draw_type}-s{pos}b",
        top_source=f"SLOT:{pos}a",
        bottom_source=f"SLOT:{pos}b",
        top_player_id=top_id,
        bottom_player_id=bot_id,
        top_player_name=top_name,
        bottom_player_name=bot_name,
        top_country_code=top_country,
        bottom_country_code=bot_country,
        status=status,  # type: ignore[arg-type]
        winner_player_id=winner,
        loser_player_id=loser,
        scoreline=scoreline,
        source_draw_fingerprint="draw-fp",
        generated_fingerprint=f"gen-{draw_type}-{round_number}-{pos}",
        result_fingerprint=f"result-{draw_type}-{round_number}-{pos}" if status == "completed" else None,
    )


def _persist_synthetic_package(tmp_path: Path, *, incomplete: bool = False, blocked: bool = False) -> tuple[SeasonEventResultsService, str]:
    match_service, event_id = make_match_service(tmp_path)
    generated = match_service.generate_match_package(event_id=event_id, request=MatchPackageGenerateRequest(seed=101, dry_run=False)).match_package
    assert generated is not None
    q1 = _record(event_id, "qualification", 1, 1, ("P7", "Q Seven", "EGY"), ("P8", "Q Eight", "ENG"), "P7", "P8")
    main = [
        _record(event_id, "main", 1, 1, ("P1", "Alpha One", "EGY"), ("P4", "Delta Four", "ENG"), "P1", "P4"),
        _record(event_id, "main", 1, 2, ("P2", "Bravo Two", "FRA"), ("P7", "Q Seven", "EGY"), "P2", "P7"),
    ]
    if blocked:
        main.append(_record(event_id, "main", 2, 1, ("P1", "Alpha One", "EGY"), ("P2", "Bravo Two", "FRA"), None, None, status="blocked_waiting_for_sources", scoreline=None))
    elif incomplete:
        main.append(_record(event_id, "main", 2, 1, ("P1", "Alpha One", "EGY"), ("P2", "Bravo Two", "FRA"), None, None, status="pending", scoreline=None))
    else:
        main.append(_record(event_id, "main", 2, 1, ("P1", "Alpha One", "EGY"), ("P2", "Bravo Two", "FRA"), "P1", "P2"))
    package = generated.model_copy(update={
        "qualification_matches": [q1],
        "main_draw_matches": main,
        "validation_errors": [],
    })
    package.summary = match_service._summary(event_id=event_id, qualification_matches=package.qualification_matches, main_draw_matches=package.main_draw_matches, warnings=package.validation_warnings, errors=[])
    match_service._save_registry(SeasonMatchesRegistry(matches_by_event_id={event_id: package}))
    result_service = SeasonEventResultsService(match_service=match_service, results_path=tmp_path / "results.json")
    return result_service, event_id


def test_missing_match_package_errors(tmp_path: Path) -> None:
    match_service, _ = make_match_service(tmp_path)
    service = SeasonEventResultsService(match_service=match_service, results_path=tmp_path / "results.json")
    with pytest.raises(ValueError, match="No persisted match package"):
        service.extract_event_result(event_id="EVT-missing", request=EventResultExtractRequest())


def test_dry_run_extracts_complete_result_without_persisting(tmp_path: Path) -> None:
    service, event_id = _persist_synthetic_package(tmp_path)
    result = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=True))
    package = result.result_package
    assert package is not None
    assert package.completion_status == "complete"
    assert package.champion and package.champion.player_name == "Alpha One"
    assert package.finalist and package.finalist.player_name == "Bravo Two"
    assert [p.player_name for p in package.semifinalists] == ["Delta Four", "Q Seven"]
    assert [p.player_name for p in package.qualification_winners] == ["Q Seven"]
    q_result = next(p for p in package.player_results if p.player_id == "P7")
    assert q_result.draw_type == "both"
    assert q_result.qualifier is True
    assert q_result.reached_stage == "semifinal"
    assert q_result.wins == 1 and q_result.losses == 1
    assert all(p.points_awarded == 0 and p.race_points_awarded == 0 for p in package.player_results)
    assert service.get_event_result(event_id=event_id).result_package_exists is False


def test_persist_get_and_overwrite_safety(tmp_path: Path) -> None:
    service, event_id = _persist_synthetic_package(tmp_path)
    persisted = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=False))
    assert persisted.result_package_exists is True
    loaded = service.get_event_result(event_id=event_id)
    assert loaded.result_package and loaded.metadata
    assert loaded.metadata.build_fingerprint == persisted.metadata.build_fingerprint
    with pytest.raises(ValueError, match="already exists"):
        service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=False))
    overwritten = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=11, dry_run=False, overwrite_existing=True))
    assert overwritten.metadata and overwritten.metadata.seed == 11


def test_completion_statuses_and_determinism(tmp_path: Path) -> None:
    service, event_id = _persist_synthetic_package(tmp_path / "complete")
    first = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=True)).result_package
    second = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=10, dry_run=True)).result_package
    different_seed = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(seed=11, dry_run=True)).result_package
    assert first and second and different_seed
    assert first.model_dump() == second.model_dump()
    assert first.metadata.build_fingerprint != different_seed.metadata.build_fingerprint
    assert first.champion == different_seed.champion

    incomplete_service, incomplete_event = _persist_synthetic_package(tmp_path / "incomplete", incomplete=True)
    assert incomplete_service.extract_event_result(event_id=incomplete_event, request=EventResultExtractRequest()).result_package.completion_status == "incomplete"
    blocked_service, blocked_event = _persist_synthetic_package(tmp_path / "blocked", blocked=True)
    assert blocked_service.extract_event_result(event_id=blocked_event, request=EventResultExtractRequest()).result_package.completion_status == "blocked"


def test_impossible_multiple_losses_blocks_persist(tmp_path: Path) -> None:
    service, event_id = _persist_synthetic_package(tmp_path)
    registry = service.match_service._load_registry()
    package = registry.matches_by_event_id[event_id]
    package.main_draw_matches.append(_record(event_id, "main", 1, 3, ("P3", "Charlie Three", "USA"), ("P7", "Q Seven", "EGY"), "P3", "P7"))
    service.match_service._save_registry(registry)
    dry = service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(dry_run=True))
    assert any(issue.code == "player_multiple_losses" for issue in dry.validation_errors)
    with pytest.raises(ValueError, match="validation errors block persistence"):
        service.extract_event_result(event_id=event_id, request=EventResultExtractRequest(dry_run=False))
