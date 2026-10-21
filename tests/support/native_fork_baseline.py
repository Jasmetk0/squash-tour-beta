"""Assertions against actual Saved payloads, without replacing runtime services."""

from beta_engine.domain.native_fork_baseline import NativeForkBaseline
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    decode_prevalidated_calendar_sources,
)
from beta_engine.infrastructure.db.player_health_state import load_saved_health
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle


def assert_native_baseline_facts(baseline, source):
    payload = source.payload
    life = load_saved_lifecycle(
        payload, run_id=source.run_id, branch_id=source.branch_id
    )
    health = load_saved_health(
        payload, run_id=source.run_id, branch_id=source.branch_id
    )
    _, checkpoint, tour = decode_prevalidated_calendar_sources(
        payload, run_id=source.run_id, branch_id=source.branch_id
    )
    assert baseline.lifecycle_players == life[-1].players
    assert tuple(p.model_dump(mode="json") for p in baseline.health_players) == tuple(
        p.model_dump(mode="json") for p in health[-1].players
    )
    assert baseline.sporting_players == checkpoint.players
    assert baseline.lifecycle_policy == life[-1].policy
    assert baseline.source_lifecycle_fingerprint == life[-1].fingerprint
    assert baseline.source_health_fingerprint == health[-1].fingerprint
    assert baseline.source_health_week == health[-1].week
    assert baseline.source_checkpoint_fingerprint == checkpoint.fingerprint
    assert baseline.source_tour_fingerprint == tour.fingerprint
    assert baseline.source_ranking_fingerprint == tour.rankings[-1].fingerprint
    assert baseline.slot_cursor == tour.slot_cursor
    assert baseline.source_binding.source.content_hash == source.content_hash
    assert baseline.week.calendar.to_metadata() == payload["run"]["run_calendar"]
    assert baseline.week.ordinal == tour.week.ordinal
    assert all(len(p.attributes) == 57 for p in baseline.sporting_players)


def roundtrip_verify_native_baseline(service, baseline):
    decoded = NativeForkBaseline.model_validate_json(baseline.model_dump_json())
    assert decoded == baseline and decoded.fingerprint == baseline.fingerprint
    assert service.verify(decoded, **baseline_scope(decoded)) == baseline
    return decoded


def baseline_scope(baseline):
    return {
        "run_id": baseline.run_id,
        "source_branch_id": baseline.selected_source_branch_id,
        "source_revision_id": baseline.source_binding.source.revision_id,
        "target_branch_id": baseline.branch_id,
    }
