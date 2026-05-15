from __future__ import annotations

from pathlib import Path

import pytest

from beta_engine.application.season_draw_service import DrawGenerateRequest, SeasonDrawService
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from test_season_entry_list_service import first_event_id, make_service


def make_draw_service(tmp_path: Path) -> SeasonDrawService:
    entry_service = make_service(tmp_path, calendar=True, active=True)
    return SeasonDrawService(entry_list_service=entry_service, calendar_service=entry_service.calendar_service, draws_path=tmp_path / "draws.json")


def persist_entry_list(draw_service: SeasonDrawService, *, seed: int = 222) -> str:
    event_id = first_event_id(draw_service.entry_list_service)
    draw_service.entry_list_service.generate_entry_list(
        event_id=event_id,
        request=EntryListGenerateRequest(seed=seed, dry_run=False, overwrite_existing=False),
    )
    return event_id


def test_missing_entry_list_blocks_draw_generation(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = first_event_id(service.entry_list_service)

    with pytest.raises(ValueError, match="No persisted entry list"):
        service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest())


def test_dry_run_generates_without_persisting(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = persist_entry_list(service)

    result = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=101, dry_run=True))

    assert result.draw_package is not None
    assert result.draw_package.persisted is False
    assert result.draw_package.main_draw.slots
    assert result.draw_package.qualification_draw is not None
    assert service.get_draw_package(event_id=event_id).draw_package_exists is False


def test_persist_get_and_overwrite_safety(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = persist_entry_list(service)

    persisted = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=101, dry_run=False))
    assert persisted.draw_package is not None
    assert persisted.draw_package.persisted is True
    assert service.get_draw_package(event_id=event_id).draw_package is not None

    with pytest.raises(ValueError, match="already exists"):
        service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=101, dry_run=False, overwrite_existing=False))

    overwritten = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=102, dry_run=False, overwrite_existing=True))
    assert overwritten.metadata is not None
    assert overwritten.metadata.seed == 102


def test_determinism_and_seed_changes_fingerprint(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = persist_entry_list(service)

    first = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=303, dry_run=True)).draw_package
    second = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=303, dry_run=True)).draw_package
    different = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=304, dry_run=True)).draw_package

    assert first is not None and second is not None and different is not None
    assert first.model_dump() == second.model_dump()
    assert first.metadata.build_fingerprint != different.metadata.build_fingerprint


def test_capacity_byes_provenance_and_warnings(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = persist_entry_list(service)

    package = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=909, dry_run=True)).draw_package

    assert package is not None
    event = service._find_event(event_id)
    assert len(package.main_draw.slots) == package.main_draw.draw_size
    assert len(package.main_draw.slots) <= event.main_draw_size + event.byes
    assert package.qualification_draw is not None
    assert len(package.qualification_draw.slots) <= event.qualification_draw_size
    assert len(package.main_draw.qualifier_placeholders) == event.qualifier_spots
    assert len(package.main_draw.seeds) == min(event.seeds_count, package.summary.main_draw_players)
    assert package.metadata.entry_list_fingerprint == service.entry_list_service.get_entry_list(event_id=event_id).entry_list.metadata.build_fingerprint  # type: ignore[union-attr]
    assert package.metadata.calendar_event_fingerprint == event.calendar_fingerprint
    assert any(issue.code == "wildcards_not_implemented" for issue in package.validation_warnings)


def test_duplicate_player_ids_rejected(tmp_path: Path) -> None:
    service = make_draw_service(tmp_path)
    event_id = persist_entry_list(service)
    registry = service.entry_list_service._load_registry()
    entry_list = registry.entry_lists_by_event_id[event_id]
    duplicate = entry_list.entries[0].model_copy(update={"entry_id": f"{entry_list.entries[0].entry_id}:dup"})
    entry_list.entries.append(duplicate)
    service.entry_list_service._save_registry(registry)

    result = service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=1, dry_run=True))
    assert any(issue.code == "duplicate_player_id" for issue in result.validation_errors)
    with pytest.raises(ValueError, match="duplicate_player_id"):
        service.generate_draw_package(event_id=event_id, request=DrawGenerateRequest(seed=1, dry_run=False, overwrite_existing=True))
