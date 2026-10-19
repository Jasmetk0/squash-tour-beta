"""Real native Official sporting development + W-birthday as one immutable proposal."""
import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_prospect_admission_bundle import (
    build_native_prospect_admission_bundle,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.calendar_native_sporting_intake import (
    CalendarNativeAdmissionWeekProjection, CalendarNativeSportingBirthAdvance,
    combine_signed_admission_with_sporting_week, project_native_sporting_birth_advance,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy, develop_and_recover,
)
from beta_engine.domain.players.sporting import PlayerSportingRecord
from tests.domain.test_calendar_prospect_birth_event import (
    birth_row, lifecycle, source, week,
)
from tests.domain.test_calendar_prospect_admission_bundle import (
    health_for, checkpoint_for,
)

pytestmark = pytest.mark.pr_critical


def next_week(c, p):
    position = c.position_at_ordinal(p.ordinal + 1)
    return RunWeekPosition(
        calendar=c, season_index=position.season_index, week=position.season_week
    )


def setup_native(width=52, offset=35, current_week=1, number=1):
    c = RunCalendar(width, offset, 2030, 3)
    old = lifecycle(c, week(c, 0, current_week))
    target = next_week(c, old.week)
    snapshot = source(*(birth_row(target, f"new-{n:02d}") for n in range(number)))
    base_cp = checkpoint_for(old)
    cp = SimpleNamespace(
        **(vars(base_cp) | {
            "source_initial_world_fingerprint": old.source_initial_world_fingerprint,
        })
    )
    event = build_calendar_prospect_birth_event(
        predecessor=old, target=target, source=snapshot, world_package_id="world",
    )
    return c, old, cp, event, snapshot


@pytest.mark.parametrize("width,offset,current_week", [
    (52, 1, 52), (52, 35, 52), (61, 37, 61),
    (80, 15, 80), (80, 80, 1), (52, 35, 1),
])
def test_annual_sporting_kernel_is_identical_and_newborns_only_join_after_development(
    width, offset, current_week,
):
    c, old, cp, event, _ = setup_native(width, offset, current_week, number=2)
    source_before = cp.players[0].model_dump_json()
    policy = CalendarAnnualDevelopmentPolicy()
    counts = (("existing", 3),)
    original_developed, original_recovered = develop_and_recover(
        cp, SimpleNamespace(players=old.players, lifecycle_policy=old.policy),
        completed_week=cp.week, seed=1234, policy=policy, counts=counts,
        official=True,
    )
    projection = project_native_sporting_birth_advance(
        checkpoint=cp, predecessor=old, birth_event=event,
        seed=1234, policy=policy, played_counts=counts,
    )
    assert projection.developed_players == original_developed
    assert projection.recovered_players == original_recovered
    assert projection.target_players[0] == original_recovered[0]
    assert [p.player_id for p in projection.target_players] == [
        "existing", "new-00", "new-01",
    ]
    assert len(projection.target_players) == 3
    assert all(len(p.attributes) == 57 for p in projection.target_players)
    for event_birth in event.births:
        joined = next(p for p in projection.target_players if p.player_id == event_birth.player_id)
        assert joined.attributes == event_birth.sporting_profile.attributes
        assert joined.potential_identity == event_birth.sporting_profile.potential_identity
        assert joined.current_form == cp.bootstrap_policy.default_form
        assert joined.long_term_fatigue == cp.bootstrap_policy.default_fatigue
    assert len(projection.played_counts) == 1  # newborns were NOT playing last week
    assert projection.target_week == event.target_week
    assert projection == CalendarNativeSportingBirthAdvance.model_validate_json(
        projection.model_dump_json()
    )
    assert projection.fingerprint == project_native_sporting_birth_advance(
        checkpoint=cp, predecessor=old, birth_event=event,
        seed=1234, policy=policy, played_counts=counts,
    ).fingerprint
    assert cp.players[0].model_dump_json() == source_before


@pytest.mark.parametrize("width,offset,week_no", [
    (52, 1, 52), (61, 37, 61), (80, 80, 80),
])
def test_next_week_all_players_including_last_week_births_develop_from_same_kernel(
    width, offset, week_no,
):
    c, old, cp, event, snapshot = setup_native(width, offset, week_no)
    first = project_native_sporting_birth_advance(
        checkpoint=cp, predecessor=old, birth_event=event, seed=11,
        policy=CalendarAnnualDevelopmentPolicy(), played_counts=(("existing", 0),),
    )
    entered = advance_calendar_lifecycle_with_prospects(old, event)
    target_after_birth = next_week(c, entered.week)
    next_event = build_calendar_prospect_birth_event(
        predecessor=entered, target=target_after_birth,
        source=snapshot, world_package_id="world",
    )
    assert next_event.births == ()
    cp_next = SimpleNamespace(
        run_id=cp.run_id, branch_id=cp.branch_id,
        week=entered.week, players=first.target_players,
        source_initial_world_fingerprint=cp.source_initial_world_fingerprint,
        bootstrap_policy=cp.bootstrap_policy, fingerprint=first.fingerprint,
    )
    second = project_native_sporting_birth_advance(
        checkpoint=cp_next, predecessor=entered,
        birth_event=next_event, seed=12, policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=(("existing", 0), ("new-00", 1)),
    )
    assert [p.player_id for p in second.developed_players] == ["existing", "new-00"]
    assert [p.player_id for p in second.recovered_players] == ["existing", "new-00"]
    assert second.target_players == second.recovered_players
    # Provenance of the birth remains immutable; further weekly RNG uses the
    # new checkpoint hash, not a reroll of the original 57 attributes.
    assert first.source_birth_event.births == event.births
    assert second.completed_week == first.target_week
    assert second.target_week.ordinal == first.target_week.ordinal + 1


def test_full_signed_admission_and_genuine_sporting_age_join_one_review_fingerprint():
    c, old, cp, event, snapshot = setup_native()
    admission = build_native_prospect_admission_bundle(
        predecessor=old, checkpoint=cp, health=health_for(old),
        source=snapshot, target=event.target_week,
        world_package_id="world", saved_head_revision_id="saved-head",
    )
    counts = (("existing", 2),)
    bound = combine_signed_admission_with_sporting_week(
        admission=admission, checkpoint=cp, predecessor=old,
        seed=71, policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=counts,
    )
    assert bound.sporting_week.source_birth_event == admission.event
    assert bound.admission.health.birth_event == admission.event
    assert tuple(p.player_id for p in bound.sporting_week.target_players) == tuple(
        p.player_id for p in bound.admission.lifecycle.players
    )
    assert bound.signed_writer_supported is False
    assert bound == CalendarNativeAdmissionWeekProjection.model_validate_json(
        bound.model_dump_json()
    )
    identical = combine_signed_admission_with_sporting_week(
        admission=admission, checkpoint=cp, predecessor=old,
        seed=71, policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=counts,
    )
    assert identical.fingerprint == bound.fingerprint
    changed_seed = combine_signed_admission_with_sporting_week(
        admission=admission, checkpoint=cp, predecessor=old,
        seed=72, policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=counts,
    )
    assert changed_seed.fingerprint != bound.fingerprint


def test_reject_foreign_lifecycle_wrong_play_count_unsourced_event_and_mutated_receipt():
    c, old, cp, event, _ = setup_native()
    valid = dict(
        checkpoint=cp, predecessor=old, birth_event=event, seed=123,
        policy=CalendarAnnualDevelopmentPolicy(), played_counts=(("existing", 0),),
    )
    with pytest.raises(ValueError, match="exact lifecycle/checkpoint"):
        project_native_sporting_birth_advance(
            **(valid | {"predecessor": old.model_copy(update={"branch_id": "other"})})
        )
    for bad_counts in ((("new-00", 1),), (("existing", -1),), (("existing", 1), ("existing", 2))):
        with pytest.raises(ValueError, match="completed-week counts"):
            project_native_sporting_birth_advance(**(valid | {"played_counts": bad_counts}))
    with pytest.raises(ValueError, match="seed/policy"):
        project_native_sporting_birth_advance(**(valid | {"seed": True}))
    with pytest.raises(ValueError, match="exact lifecycle/checkpoint"):
        project_native_sporting_birth_advance(
            **(valid | {"birth_event": event.model_copy(update={
                "predecessor_fingerprint": "0" * 64,
            })})
        )
    result = project_native_sporting_birth_advance(**valid)
    for forged in [
        result.model_copy(update={"recovered_players": ()}),
        result.model_copy(update={"target_players": result.recovered_players}),
    ]:
        with pytest.raises(ValueError, match="weekly population"):
            CalendarNativeSportingBirthAdvance.model_validate_json(forged.model_dump_json())
    wrong_old = result.target_players[0].model_copy(update={"current_form": 20})
    forged = result.model_copy(update={"target_players": (wrong_old,) + result.target_players[1:]})
    with pytest.raises(ValueError, match="cannot change developed old players"):
        CalendarNativeSportingBirthAdvance.model_validate_json(forged.model_dump_json())


def test_recovered_active_health_blocking_does_not_confer_health_writer_permission():
    c, old, cp, event, snapshot = setup_native()
    bound = combine_signed_admission_with_sporting_week(
        admission=build_native_prospect_admission_bundle(
            predecessor=old, checkpoint=cp, health=health_for(old),
            source=snapshot, target=event.target_week,
            world_package_id="world", saved_head_revision_id="signed",
        ),
        checkpoint=cp, predecessor=old, seed=101,
        policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=(("existing", 0),),
    )
    assert bound.signed_writer_supported is False
    assert bound.admission.tour_signed_writer_supported is False
    assert bound.admission.ranking_and_entry_adoption_supported is False
    assert bound.sporting_week.target_players[-1].health_state == "unsupported"
