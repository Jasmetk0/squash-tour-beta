from __future__ import annotations

import pytest

from beta_engine.application.season_entry_batch_service import (
    EntryBatchGenerateRequest,
    SeasonEntryBatchService,
)
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest
from beta_engine.domain.tournaments import SeasonCalendar, SeasonCalendarMetadata
from test_season_entry_list_service import make_service, write_active


def add_overlapping_event(service) -> tuple[str, str]:
    registry = service.calendar_service._load_registry()
    calendar = registry.calendars_by_season["2000/2001"]
    first = calendar.events[0]
    second = first.model_copy(
        update={
            "event_id": "EVT-2000-W01-wt_b",
            "template_id": "wt_b",
        }
    )
    registry.calendars_by_season["2000/2001"] = SeasonCalendar(
        season="2000/2001",
        events=[first, second],
        metadata=SeasonCalendarMetadata(
            season="2000/2001",
            season_start_calendar_year=2000,
            season_start_year_week=37,
        ),
    )
    service.calendar_service._save_registry(registry)
    return first.event_id, second.event_id


def accepted_ids(entry_list):
    return {
        entry.player_id
        for entry in entry_list.entries
        if entry.decision in {"accepted_main_draw", "accepted_qualification"}
    }


@pytest.mark.pr_critical
@pytest.mark.smoke
def test_overlapping_entry_batch_is_shared_atomic_and_order_independent(tmp_path):
    service = make_service(tmp_path)
    # A larger deterministic population guarantees meaningful competition for the
    # two identical overlapping event snapshots while keeping the production
    # EntryEngine and its event-specific RNG fully in charge of entry decisions.
    write_active(tmp_path / "active.json", count=80)
    first_id, second_id = add_overlapping_event(service)

    first_preview = service.generate_entry_list(
        event_id=first_id,
        request=EntryListGenerateRequest(seed=123, dry_run=True),
    ).entry_list
    second_preview = service.generate_entry_list(
        event_id=second_id,
        request=EntryListGenerateRequest(seed=123, dry_run=True),
    ).entry_list
    assert first_preview is not None and second_preview is not None
    assert accepted_ids(first_preview) & accepted_ids(second_preview)

    batch_service = SeasonEntryBatchService(service)
    request = EntryBatchGenerateRequest(
        seed=123,
        dry_run=True,
        max_alternates=16,
        include_not_entered=True,
    )
    forward = batch_service.generate_overlapping_entry_lists(
        event_ids=[first_id, second_id], request=request
    )
    reverse = batch_service.generate_overlapping_entry_lists(
        event_ids=[second_id, first_id], request=request
    )

    assert forward.metadata.build_fingerprint == reverse.metadata.build_fingerprint
    assert forward.metadata.active_players_fingerprint == reverse.metadata.active_players_fingerprint
    assert forward.metadata.resolved_conflict_player_count == 0
    assert forward.metadata.unresolved_conflict_player_count > 0
    assert forward.application_decisions == reverse.application_decisions
    assert (
        forward.metadata.application_decisions_fingerprint
        == reverse.metadata.application_decisions_fingerprint
    )
    assert forward.application_decisions
    assert all(
        decision.target.value in {"MAIN", "QUALIFICATION"}
        for decision in forward.application_decisions
    )
    assert (
        accepted_ids(forward.entry_lists_by_event_id[first_id])
        & accepted_ids(forward.entry_lists_by_event_id[second_id])
    )
    assert all(
        entry_list.metadata.active_players_fingerprint
        == forward.metadata.active_players_fingerprint
        for entry_list in forward.entry_lists_by_event_id.values()
    )
    assert not (tmp_path / "entries.json").exists()

    compact = batch_service.generate_overlapping_entry_lists(
        event_ids=[second_id, first_id],
        request=request.model_copy(
            update={
                "include_not_entered": False,
                "max_alternates": 0,
            }
        ),
    )
    assert compact.application_decisions == forward.application_decisions
    assert (
        compact.metadata.application_decisions_fingerprint
        == forward.metadata.application_decisions_fingerprint
    )
    compact_visible_pairs = {
        (entry_list.event_id, entry.player_id)
        for entry_list in compact.entry_lists_by_event_id.values()
        for entry in entry_list.entries
        if entry.player_id is not None
    }
    submitted_pairs = {
        (decision.event_id, decision.player_id)
        for decision in compact.application_decisions
    }
    assert compact_visible_pairs < submitted_pairs

    persisted = batch_service.generate_overlapping_entry_lists(
        event_ids=[second_id, first_id],
        request=request.model_copy(update={"dry_run": False}),
    )
    assert persisted.metadata.persisted is True
    assert service.get_entry_list(event_id=first_id).entry_list_exists is True
    assert service.get_entry_list(event_id=second_id).entry_list_exists is True
    loaded_first = service.get_entry_list(event_id=first_id).entry_list
    loaded_second = service.get_entry_list(event_id=second_id).entry_list
    assert loaded_first is not None and loaded_second is not None
    assert accepted_ids(loaded_first) & accepted_ids(loaded_second)
    assert any(
        issue.code == "player_week_overlap_unresolved"
        for issue in loaded_first.validation_warnings
    )
    assert any(
        issue.code == "player_week_overlap_unresolved"
        for issue in loaded_second.validation_warnings
    )

    with pytest.raises(ValueError, match="overwrite_existing"):
        batch_service.generate_overlapping_entry_lists(
            event_ids=[first_id, second_id],
            request=request.model_copy(update={"dry_run": False}),
        )
