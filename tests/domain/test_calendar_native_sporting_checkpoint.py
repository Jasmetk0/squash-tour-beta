"""Native v11 ledger, exact prefix hashes and independently replayed weekly sport."""
import json
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_native_health_transition import advance_native_health_week
from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingCheckpoint, append_native_sporting_week,
    verify_native_sporting_checkpoint,
)
from beta_engine.domain.players.calendar_native_sporting_intake import project_native_sporting_birth_advance
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy, CalendarSportingWeekAdvance,
    append_sporting_week, develop_and_recover, records_fingerprint, played_counts,
)
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
from tests.domain.test_calendar_native_checkpoint_compatibility import initial
from tests.domain.test_calendar_prospect_admission_bundle import health_for
from tests.domain.test_calendar_prospect_birth_event import birth_row, lifecycle, source, week

pytestmark = pytest.mark.pr_critical


def prepared(width=61, offset=37, *, boundary=False, extend=False):
    """Pure fixture; the separate HTTP case proves the real root World/matches."""
    clock = RunCalendar(width, offset, 2030, 3)
    root = initial().model_copy(update={"week": week(clock, 0, 1)})
    first = lifecycle(clock, week(clock, 0, 1))
    first = first.model_copy(update={
        "run_id": root.run_id, "branch_id": root.branch_id,
        "source_initial_world_fingerprint": root.source_initial_world_fingerprint,
        "players": tuple(first.players[0].model_copy(update={"player_id": p.player_id}) for p in root.players),
    })
    if boundary:
        # Domain replay begins at this already authenticated last-week root.
        from tests.domain.test_calendar_canonical_match import canonical_bracket
        current, history = first, [first]
        knockout = canonical_bracket()
        world = SimpleNamespace(players=first.players, lifecycle_policy=first.policy)
        for n in range(2, width+1):
            counts=played_counts(root,knockout)
            developed,recovered=develop_and_recover(root,world,completed_week=root.week,
                seed=n,policy=CalendarAnnualDevelopmentPolicy(),counts=counts)
            command=dict(command_id=f"week-{n}",expected_saved_head="head",
                expected_checkpoint_fingerprint=root.fingerprint,seed=n,
                operator_label="Admin",audit_reason="Pure historical week fixture")
            event=CalendarSportingWeekAdvance(run_id=root.run_id,branch_id=root.branch_id,
                command_id=command["command_id"],source_saved_head="head",
                source_checkpoint_fingerprint=root.fingerprint,completed_week=root.week,
                target_week=week(clock,0,n),seed=n,operator_label="Admin",
                audit_reason=command["audit_reason"],
                request_fingerprint=canonical_hash(dict(run_id=root.run_id,branch_id=root.branch_id,command=command)),
                played_counts=counts,developed_players_fingerprint=records_fingerprint(developed),
                recovered_players_fingerprint=records_fingerprint(recovered))
            root=append_sporting_week(root,world,knockout,event)
            current = advance_calendar_lifecycle(current, week(clock,0,n))
            history.append(current)
    else:
        current, history = first, [first]
    health = health_for(first).model_copy(update={
        "run_id": root.run_id, "branch_id": root.branch_id,
        "players": tuple(PlayerHealthProfile(player_id=p.player_id) for p in root.players),
    })
    health_history = [health]
    for before, after in zip(history,history[1:]):
        health_history.append(advance_native_health_week(previous_health=health_history[-1],
            previous_lifecycle=before,next_lifecycle=after))
    target_clock = RunCalendar(width,offset,2030,5) if extend else clock
    pos = target_clock.position_at_ordinal(current.week.ordinal+1)
    target = week(target_clock,pos.season_index,pos.season_week)
    row = birth_row(target,"newborn")
    row["run_id"] = root.run_id
    snapshot = source(row)
    snapshot.run_id = root.run_id
    event = build_calendar_prospect_birth_event(predecessor=current,target=target,
        source=snapshot,world_package_id="world")
    after = advance_calendar_lifecycle_with_prospects(current,event)
    target_health = advance_native_health_week(previous_health=health_history[-1],
        previous_lifecycle=current,next_lifecycle=after)
    health_history.append(target_health)
    history.append(after)
    # Opening fixture's exact matches determine counts; later root weeks have none.
    from tests.domain.test_calendar_canonical_match import canonical_bracket
    knockout = canonical_bracket()
    policy = CalendarAnnualDevelopmentPolicy()
    sport = project_native_sporting_birth_advance(checkpoint=root,predecessor=current,
        birth_event=event,seed=120,policy=policy,played_counts=played_counts(root,knockout))
    state = append_native_sporting_week(root,sport,lifecycle_fingerprint=after.fingerprint,
        health_fingerprint=target_health.fingerprint,
        health_history_fingerprint=canonical_hash([h.model_dump(mode="json") for h in health_history]))
    context = dict(lifecycle=tuple(history),health=tuple(health_history),source=snapshot,
        world_package_id="world",knockout=knockout,policy_for_week=lambda _:policy)
    return state, context


@pytest.mark.parametrize("width,offset", [(52,1),(52,35),(61,37),(80,15),(80,80)])
def test_native_checkpoint_roundtrip_rebuilds_old_development_and_exact_newborn(width,offset):
    state, context = prepared(width,offset)
    original = state.source_checkpoint.model_dump_json()
    verify_native_sporting_checkpoint(state,**context)
    assert parse_checkpoint_json(state.model_dump_json()) == state
    assert len(state.players)==5
    assert state.players[-1].player_id=="newborn"
    assert len(state.players[-1].attributes)==57
    assert state.source_checkpoint.model_dump_json()==original
    assert state.fingerprint==parse_checkpoint_json(state.model_dump_json()).fingerprint


@pytest.mark.parametrize("width,offset", [(52,35),(61,37),(80,80)])
def test_birth_checkpoint_crosses_exact_season_boundary_and_strict_extension(width,offset):
    state, context=prepared(width,offset,boundary=True,extend=True)
    verify_native_sporting_checkpoint(state,**context)
    assert (state.week.season_index,state.week.week)==(1,1)
    assert state.week.calendar.season_count==5
    assert state.source_checkpoint.week.calendar.season_count==3


def test_later_natural_week_develops_the_previously_born_player_without_rebirth():
    state, context=prepared()
    previous=context["lifecycle"][-1]
    target=week(state.week.calendar,0,3)
    event=build_calendar_prospect_birth_event(predecessor=previous,target=target,
        source=context["source"],world_package_id="world")
    assert not event.births
    life=advance_calendar_lifecycle(previous,target)
    health=advance_native_health_week(previous_health=context["health"][-1],
        previous_lifecycle=previous,next_lifecycle=life)
    all_health=(*context["health"],health)
    sport=project_native_sporting_birth_advance(checkpoint=state,predecessor=previous,
        birth_event=event,seed=121,policy=CalendarAnnualDevelopmentPolicy(),
        played_counts=tuple((p.player_id,0) for p in state.players))
    next_state=append_native_sporting_week(state,sport,lifecycle_fingerprint=life.fingerprint,
        health_fingerprint=health.fingerprint,
        health_history_fingerprint=canonical_hash([h.model_dump(mode="json") for h in all_health]))
    verify_native_sporting_checkpoint(next_state,**{**context,
        "lifecycle":(*context["lifecycle"],life),"health":all_health})
    assert next_state.native_weeks[:-1]==state.native_weeks
    assert next_state.native_weeks[-1].advance.source_checkpoint_fingerprint==state.fingerprint
    assert next_state.source_checkpoint is state.source_checkpoint
    assert next_state.players==sport.recovered_players


@pytest.mark.parametrize("damage", ["development","counts","health","life","source","policy","scope","prefix"])
def test_recomputed_outer_hash_cannot_authenticate_changed_inputs(damage):
    state, context=prepared()
    raw=state.model_dump(mode="json")
    entry=raw["native_weeks"][0]
    if damage=="development": entry["advance"]["developed_players"][0]["attributes"][0][1]+=1
    elif damage=="counts": entry["advance"]["played_counts"][0][1]+=1
    elif damage=="health": entry["health_fingerprint"]="0"*64
    elif damage=="life": entry["lifecycle_fingerprint"]="0"*64
    elif damage=="source": context={**context,"source":type(context["source"])(**(vars(context["source"])|{"fingerprint":"0"*64}))}
    elif damage=="policy": context={**context,"policy_for_week":lambda _:CalendarAnnualDevelopmentPolicy(annual_change_basis_points=1)}
    elif damage=="scope": raw["branch_id"]="other"
    elif damage=="prefix": entry["advance"]["source_checkpoint_fingerprint"]="0"*64
    with pytest.raises(ValueError):
        changed=CalendarNativeSportingCheckpoint.model_validate_json(json.dumps(raw))
        verify_native_sporting_checkpoint(changed,**context)


@pytest.mark.parametrize("raw", ["null", "[]", '{"schema_version":"calendar_sporting_checkpoint.v12"}'])
def test_unknown_or_nonobject_sporting_schema_never_claims_native_authority(raw):
    with pytest.raises(ValueError):
        parse_checkpoint_json(raw)


def test_v11_requires_real_birth_and_complete_signed_inputs():
    state, context=prepared()
    raw=state.model_dump(mode="json")
    raw["native_weeks"]=[]
    with pytest.raises(ValueError):
        parse_checkpoint_json(json.dumps(raw))
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import verify_checkpoint
    with pytest.raises(ValueError,match="complete Signed native inputs"):
        verify_checkpoint(state,None,None)
    with pytest.raises(ValueError,match="Signed lifecycle, Health and prospect source"):
        verify_native_sporting_checkpoint(state,**{**context,"source":None})
