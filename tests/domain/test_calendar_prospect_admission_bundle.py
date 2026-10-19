"""Native 15yo admission is one W-aware verified lifecycle/sporting/Health roster."""
import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_initial_health import CalendarInitialHealthState
from beta_engine.domain.players.calendar_health import CalendarHealthProfile
from beta_engine.domain.players.calendar_prospect_admission_bundle import (
    CalendarProspectAdmissionBundle, CalendarProspectHealthProjection,
    build_native_prospect_admission_bundle, project_native_birth_health,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.players.sporting import (
    PlayerSportingBootstrapPolicy, PlayerSportingRecord,
)
from beta_engine.domain.players.prospect_sporting_profile import (
    materialize_prospect_sporting_profile,
)
from tests.domain.test_calendar_prospect_birth_event import (
    birth_row, lifecycle, source, week,
)

pytestmark = pytest.mark.pr_critical


def health_for(predecessor, records=()):
    return CalendarInitialHealthState(
        run_id="r", branch_id="b", week=week(predecessor.week.calendar, 0, 1),
        players=(PlayerHealthProfile(player_id="existing", records=records),),
        source_initial_world_fingerprint=predecessor.source_initial_world_fingerprint,
        command_id="health-init", request_fingerprint="c" * 64,
        audit_label="Admin", audit_reason="Explicit untouched initial health",
    )


def checkpoint_for(predecessor):
    generated = materialize_prospect_sporting_profile(
        player_id="existing", profile_seed="prior-ability",
        development_seed="prior-dev", potential_seed="prior-potential",
    )
    original = PlayerSportingRecord(
        player_id="existing", attributes=generated.attributes,
        potential_ovr=generated.potential_ovr,
        potential_identity=generated.potential_identity,
        potential_provenance=generated.potential_provenance,
        development_timing=generated.development_timing,
        current_form=112, long_term_form_norm=105,
        match_sharpness=92, long_term_fatigue=4,
    )
    return SimpleNamespace(
        run_id="r", branch_id="b", week=predecessor.week,
        players=(original,), bootstrap_policy=PlayerSportingBootstrapPolicy(),
        fingerprint="e" * 64,
    )


@pytest.mark.parametrize("w,o,current_week", [
    (52, 1, 52), (52, 35, 52), (61, 37, 61),
    (80, 15, 80), (80, 80, 1), (52, 35, 1),
])
def test_health_sporting_lifecycle_are_same_exact_birth_population(w, o, current_week):
    clock = RunCalendar(w, o, 2030, 3)
    previous = lifecycle(clock, week(clock, 0, current_week))
    position = clock.position_at_ordinal(previous.week.ordinal + 1)
    target = week(clock, position.season_index, position.season_week)
    source_snapshot = source(birth_row(target, "new-b"), birth_row(target, "new-a"))
    old_health = health_for(previous)
    old_cp = checkpoint_for(previous)
    health_json, prior_sporting, old_life = (
        old_health.model_dump_json(), old_cp.players[0].model_dump_json(),
        previous.model_dump_json(),
    )
    bundle = build_native_prospect_admission_bundle(
        predecessor=previous, checkpoint=old_cp, health=old_health,
        source=source_snapshot, target=target, world_package_id="world",
        saved_head_revision_id="signed-revision",
    )
    assert bundle.event.target_week == target
    assert bundle.saved_head_revision_id == "signed-revision"
    assert bundle.source_checkpoint_fingerprint == "e" * 64
    assert bundle.health.source_health_fingerprint == old_health.fingerprint
    assert [r.player_id for r in bundle.lifecycle.players] == [
        "existing", "new-a", "new-b",
    ]
    assert [r.player_id for r in bundle.sporting] == [
        "existing", "new-a", "new-b",
    ]
    assert [r.player_id for r in bundle.health.proposed_profiles] == [
        "existing", "new-a", "new-b",
    ]
    assert bundle.health.predecessor_profiles == old_health.players
    assert all(not h.records and not h.permanent_consequences
               for h in bundle.health.proposed_profiles[1:])
    assert all(len(r.attributes) == 57 for r in bundle.sporting)
    assert bundle.sporting[0] == old_cp.players[0]
    assert bundle.tour_signed_writer_supported is False
    assert bundle.ranking_and_entry_adoption_supported is False
    assert bundle == CalendarProspectAdmissionBundle.model_validate_json(
        bundle.model_dump_json()
    )
    assert bundle == build_native_prospect_admission_bundle(
        predecessor=previous, checkpoint=old_cp, health=old_health,
        source=source_snapshot, target=target, world_package_id="world",
        saved_head_revision_id="signed-revision",
    )
    assert old_health.model_dump_json() == health_json
    assert old_cp.players[0].model_dump_json() == prior_sporting
    assert previous.model_dump_json() == old_life


@pytest.mark.parametrize("damage,match", [
    ("bad_original_health", "rosters disagree"),
    ("bad_world_fingerprint", "Original World"),
    ("future_health_week", "future source week"),
    ("missing_health", "verified calendar Health"),
    ("foreign_health", "Original World"),
])
def test_existing_signed_health_provenance_cannot_be_silently_discarded(damage, match):
    clock = RunCalendar(52, 35, 2030, 3)
    prev = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    event = build_calendar_prospect_birth_event(
        predecessor=prev, target=target,
        source=source(birth_row(target)), world_package_id="world",
    )
    state = health_for(prev)
    if damage == "bad_original_health":
        state = state.model_copy(update={
            "players": (PlayerHealthProfile(player_id="foreign"),),
        })
    elif damage == "bad_world_fingerprint":
        state = state.model_copy(update={
            "source_initial_world_fingerprint": "0" * 64,
        })
    elif damage == "future_health_week":
        state = state.model_copy(update={"week": week(clock, 0, 3)})
        match = "lifecycle|future"
    elif damage == "missing_health":
        state = None
    elif damage == "foreign_health":
        state = state.model_copy(update={"run_id": "another-run"})
    with pytest.raises(ValueError, match=match):
        project_native_birth_health(health=state, event=event, predecessor=prev)


def test_tampering_newborn_health_or_57_attributes_breaks_signed_bundle():
    clock = RunCalendar(80, 15, 2030, 3)
    prev = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    bundle = build_native_prospect_admission_bundle(
        predecessor=prev, checkpoint=checkpoint_for(prev), health=health_for(prev),
        source=source(birth_row(target)), target=target, world_package_id="world",
        saved_head_revision_id="signed-head",
    )
    from beta_engine.domain.players.calendar_health import CalendarHealthProfile, CalendarHealthRecord
    altered = bundle.health.model_copy(update={
        "proposed_profiles": (
            PlayerHealthProfile(player_id="existing"),
            CalendarHealthProfile(
                player_id="prospect-1",
                records=(CalendarHealthRecord(
                    record_id="fake-injury", kind="Injury",
                    condition_key="arm", lifecycle="Active",
                    severity=10, affected_domains=("arm",),
                    started_before_run=True, provenance="Invented",
                ),),
            ),
        )
    })
    with pytest.raises(ValueError, match="invent"):
        CalendarProspectHealthProjection.model_validate_json(altered.model_dump_json())
    forged_health = bundle.model_copy(update={"health": altered})
    with pytest.raises(ValueError, match="invent"):
        CalendarProspectAdmissionBundle.model_validate_json(forged_health.model_dump_json())
    altered_sporting = list(bundle.sporting)
    original = altered_sporting[1]
    attrs = list(original.attributes)
    attrs[0] = (attrs[0][0], (attrs[0][1] + 1) % 201)
    altered_sporting[1] = original.model_copy(update={"attributes": tuple(attrs)})
    tampered = bundle.model_copy(update={"sporting": tuple(altered_sporting)})
    with pytest.raises(ValueError, match="sporting birth"):
        CalendarProspectAdmissionBundle.model_validate_json(tampered.model_dump_json())
    changed = bundle.model_copy(update={"saved_head_revision_id": "different-head"})
    assert changed.fingerprint != bundle.fingerprint
