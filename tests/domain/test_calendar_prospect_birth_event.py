"""Pure native prospect birth receipt: real 57 attributes, W/O and v4 lifecycle.

Unlike a preview-only count, this constructs the complete immutable target
lifecycle. No Tour writer is called, and historical lifecycle v3 stays byte stable.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleIdentity, CalendarPlayerLifecycleState,
    calendar_lifecycle_history,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarProspectBirthEvent, CalendarTourLifecycleIntakeState,
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.players.prospect_sporting_profile import (
    materialize_prospect_sporting_profile,
)
from beta_engine.domain.run_packages import canonical_hash

pytestmark = pytest.mark.pr_critical


def week(clock, index, number):
    return RunWeekPosition(calendar=clock, season_index=index, week=number)


def lifecycle(clock, current):
    start = week(clock, 0, 1)
    opening = start.calendar_position
    # Existing older player has the exact current birthday; age matches policy.
    from beta_engine.domain.calendar.season_weeks import age_at_calendar_position
    birth_year = opening.calendar_year - 22
    birth_week = opening.year_week
    return CalendarPlayerLifecycleState(
        run_id="r", branch_id="b", week=start,
        players=(CalendarPlayerLifecycleIdentity(
            player_id="existing", birth_year=birth_year,
            birth_year_week=birth_week,
            age=age_at_calendar_position(
                birth_year=birth_year, birth_year_week=birth_week,
                calendar_year=opening.calendar_year, year_week=opening.year_week,
                weeks_per_calendar_year=clock.weeks_per_year,
            ),
            source_generation_fingerprint="a" * 64,
        ),),
        source_initial_world_fingerprint="b" * 64,
        policy=PlayerLifecyclePolicy(
            policy_id="stored", automatic_retirement_age=46,
            provenance="Original saved World age threshold",
        ),
    ) if current.ordinal == 0 else calendar_lifecycle_history(
        CalendarPlayerLifecycleState(
            run_id="r", branch_id="b", week=start,
            players=(CalendarPlayerLifecycleIdentity(
                player_id="existing", birth_year=birth_year,
                birth_year_week=birth_week, age=22,
                source_generation_fingerprint="a" * 64,
            ),),
            source_initial_world_fingerprint="b" * 64,
            policy=PlayerLifecyclePolicy(
                policy_id="stored", automatic_retirement_age=46,
                provenance="Original saved World age threshold",
            ),
        ),
        current,
    )[-1]


def birth_row(target, pid="prospect-1"):
    position = target.calendar_position
    profile = materialize_prospect_sporting_profile(
        player_id=pid, profile_seed="seed-profile",
        development_seed="seed-development", potential_seed="seed-potential",
    )
    return {
        "prospect_id": pid, "run_id": "r", "world_id": "world",
        "source_type": "native_calendar_15yo_cohort",
        "cohort_policy_version": "native_calendar_15yo_cohort_v1",
        "profile_version": "prospect_profile_v1", "status": "prospect",
        "country_code": "CZE",
        "season_start_year": target.calendar.start_year + target.season_index,
        "season_week": target.week,
        "calendar_year": position.calendar_year,
        "year_week": position.year_week,
        "birth_year": position.calendar_year - 15,
        "birth_year_week": position.year_week,
        "age": 15,
        "profile_seed": "seed-profile",
        "development_seed": "seed-development",
        "potential_seed": "seed-potential",
        "profile": {
            "canonical_sporting_profile": profile.model_dump(mode="json"),
            "canonical_sporting_profile_fingerprint": profile.fingerprint,
        },
        "development": {
            "sporting_profile_fingerprint": profile.fingerprint,
            "development_timing": profile.development_timing,
            "source_development_seed_digest": profile.source_development_seed_digest,
        },
        "potential": {
            "sporting_profile_fingerprint": profile.fingerprint,
            "potential_ovr": profile.potential_ovr,
            "potential_identity": profile.potential_identity,
            "potential_provenance": profile.potential_provenance,
            "source_potential_seed_digest": profile.source_potential_seed_digest,
        },
    }


def source(*rows):
    return SimpleNamespace(
        run_id="r", records=tuple(sorted(rows, key=lambda p: p["prospect_id"])),
        fingerprint="f" * 64,
    )


@pytest.mark.parametrize("width,offset,current_week", [
    (52, 1, 52), (52, 35, 52), (61, 37, 61),
    (80, 15, 80), (80, 80, 1), (52, 35, 1),
])
def test_actual_birth_admission_v4_is_exact_replayable_and_original_unchanged(
    width, offset, current_week,
):
    clock = RunCalendar(width, offset, 2030, 3)
    predecessor = lifecycle(clock, week(clock, 0, current_week))
    before = predecessor.model_dump_json()
    target_position = clock.position_at_ordinal(predecessor.week.ordinal + 1)
    target = week(clock, target_position.season_index, target_position.season_week)
    previous_week = week(clock, 0, 1)
    rows = (
        birth_row(target, "new-b"),
        birth_row(target, "new-a"),
        birth_row(previous_week, "old-source"),
    )
    snapshot = source(*rows)
    event = build_calendar_prospect_birth_event(
        predecessor=predecessor, target=target,
        source=snapshot, world_package_id="world",
    )
    assert [p.player_id for p in event.births] == ["new-a", "new-b"]
    assert event.target_week == target
    assert all(len(p.sporting_profile.attributes) == 57 for p in event.births)
    assert all(
        p.source_generation_fingerprint ==
        canonical_hash({
            "source_run_prospect_fingerprint": snapshot.fingerprint,
            "source_record_fingerprint": p.source_record_fingerprint,
            "player_id": p.player_id,
            "sporting_profile_fingerprint": p.sporting_profile.fingerprint,
        }) for p in event.births
    )
    successor = advance_calendar_lifecycle_with_prospects(predecessor, event)
    assert successor.schema_version == "player_lifecycle_calendar_state.v4"
    assert [p.player_id for p in successor.players] == ["existing", "new-a", "new-b"]
    assert successor.predecessor_fingerprint == predecessor.fingerprint
    assert all(
        p.tour_entry_week is None and p.tie_break_token is None
        for p in successor.players[1:]
    )
    assert successor == CalendarTourLifecycleIntakeState.model_validate_json(
        successor.model_dump_json()
    )
    assert successor == advance_calendar_lifecycle_with_prospects(predecessor, event)
    assert predecessor.model_dump_json() == before
    following = clock.position_at_ordinal(target.ordinal + 1)
    next_event = build_calendar_prospect_birth_event(
        predecessor=successor,
        target=week(clock, following.season_index, following.season_week),
        source=snapshot, world_package_id="world",
    )
    assert next_event.births == ()
    next_state = advance_calendar_lifecycle_with_prospects(successor, next_event)
    assert len(next_state.players) == 3
    assert next_state.predecessor_fingerprint == successor.fingerprint


@pytest.mark.parametrize("mutation,error", [
    ({"world_id": "foreign"}, "Saved World"),
    ({"source_type": "weekly_15yo_cohort"}, "native source policy"),
    ({"cohort_policy_version": "weekly_15yo_cohort_v1"}, "native source policy"),
    ({"birth_year_week": 1}, "source birth date"),
    ({"year_week": 1}, "source birth date"),
    ({"age": 16}, "source birth date"),
    ({"status": "retired"}, "native source policy"),
    ({"country_code": "XX"}, "canonical country"),
    ({"profile_seed": "forged"}, "regenerated"),
])
def test_foreign_or_tampered_prospects_fail_closed(mutation, error):
    clock = RunCalendar(52, 35, 2030, 3)
    predecessor = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    row = birth_row(target)
    row.update(mutation)
    with pytest.raises(ValueError, match=error):
        build_calendar_prospect_birth_event(
            predecessor=predecessor, target=target,
            source=source(row), world_package_id="world",
        )


def test_collisions_foreign_scope_and_tampered_birth_receipts_rejected():
    clock = RunCalendar(80, 15, 2030, 3)
    predecessor = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    row = birth_row(target, pid="existing")
    with pytest.raises(ValueError, match="collides"):
        build_calendar_prospect_birth_event(
            predecessor=predecessor, target=target,
            source=source(row), world_package_id="world",
        )
    event = build_calendar_prospect_birth_event(
        predecessor=predecessor, target=target,
        source=source(birth_row(target)), world_package_id="world",
    )
    with pytest.raises(ValueError, match="predecessor"):
        advance_calendar_lifecycle_with_prospects(
            predecessor, event.model_copy(update={"predecessor_fingerprint": "0" * 64})
        )
    payload = event.model_dump(mode="json")
    payload["births"][0]["source_record_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="proof"):
        CalendarProspectBirthEvent.model_validate(payload)
    successor = advance_calendar_lifecycle_with_prospects(predecessor, event)
    changed = successor.model_dump(mode="json")
    changed["players"][-1]["source_generation_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="signed birth"):
        CalendarTourLifecycleIntakeState.model_validate(changed)


def test_source_with_empty_next_week_yields_versioned_no_birth_step():
    clock = RunCalendar(52, 1, 2030, 2)
    predecessor = lifecycle(clock, week(clock, 0, 1))
    target = week(clock, 0, 2)
    event = build_calendar_prospect_birth_event(
        predecessor=predecessor, target=target,
        source=source(birth_row(week(clock, 0, 5))),
        world_package_id="world",
    )
    assert event.births == ()
    projected = advance_calendar_lifecycle_with_prospects(predecessor, event)
    assert len(projected.players) == 1
    assert projected.birth_event.fingerprint == event.fingerprint
