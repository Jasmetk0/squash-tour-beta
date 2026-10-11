from __future__ import annotations

import pytest

import beta_engine.application.season_entry_batch_service as entry_batch_module
from beta_engine.application.season_entry_batch_service import (
    EntryBatchGenerateRequest,
    SeasonEntryBatchService,
)
from beta_engine.domain.entries import EntryTuningConfig
from test_season_entry_list_service import make_service, write_active


@pytest.mark.pr_critical
def test_frozen_tuning_snapshot_bypasses_global_file_and_binds_batch_identity(
    tmp_path,
    monkeypatch,
):
    service = make_service(tmp_path)
    write_active(tmp_path / "active.json", count=40)
    calendar = service.calendar_service.get_calendar(season="2000/2001").calendar
    assert calendar is not None
    event = calendar.events[0]
    countries = tuple(service.countries_service.list_countries())
    tuning = EntryTuningConfig()

    def forbidden(*args, **kwargs):
        raise AssertionError("global entry_tuning.json must not be read")

    monkeypatch.setattr(entry_batch_module, "load_entry_tuning_config", forbidden)

    first = SeasonEntryBatchService(service).generate_overlapping_entry_lists(
        event_ids=[event.event_id],
        request=EntryBatchGenerateRequest(
            seed=123,
            dry_run=True,
            max_alternates=0,
            include_not_entered=False,
        ),
        event_snapshots={event.event_id: event},
        country_snapshots=countries,
        tuning_snapshot=tuning,
    )
    second_tuning = tuning.model_copy(
        update={"baseline_bias": tuning.baseline_bias + 0.25}
    )
    second = SeasonEntryBatchService(service).generate_overlapping_entry_lists(
        event_ids=[event.event_id],
        request=EntryBatchGenerateRequest(
            seed=123,
            dry_run=True,
            max_alternates=0,
            include_not_entered=False,
        ),
        event_snapshots={event.event_id: event},
        country_snapshots=countries,
        tuning_snapshot=second_tuning,
    )

    assert first.metadata.tuning_snapshot_fingerprint is not None
    assert len(first.metadata.tuning_snapshot_fingerprint) == 64
    assert second.metadata.tuning_snapshot_fingerprint is not None
    assert (
        first.metadata.tuning_snapshot_fingerprint
        != second.metadata.tuning_snapshot_fingerprint
    )
    assert first.metadata.build_fingerprint != second.metadata.build_fingerprint
