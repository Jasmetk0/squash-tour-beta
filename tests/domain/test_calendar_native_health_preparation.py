"""Full native Health preparation; pure replay with externally verified inputs."""
import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_native_health_transition import (
    prepare_native_health_history,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
)
from tests.domain.test_calendar_prospect_admission_bundle import health_for
from tests.domain.test_calendar_prospect_birth_event import birth_row, lifecycle, source, week

pytestmark = pytest.mark.pr_critical


def history(width=61, offset=37):
    clock = RunCalendar(width, offset, 2030, 3)
    first = lifecycle(clock, week(clock, 0, 1))
    states = [first]
    prospects = source(birth_row(week(clock, 0, 3), "born-early"),
                       birth_row(week(clock, 0, 5), "born-next"))
    for number in range(2, 6):
        target = week(clock, 0, number)
        event = build_calendar_prospect_birth_event(
            predecessor=states[-1], target=target, source=prospects,
            world_package_id="world",
        )
        states.append(advance_calendar_lifecycle_with_prospects(states[-1], event)
                      if event.births else advance_calendar_lifecycle(states[-1], target))
    return tuple(states), health_for(first)


@pytest.mark.parametrize("width,offset", [(52,1),(52,35),(61,37),(80,15),(80,80)])
def test_prepares_every_missing_week_with_each_birthday_only_at_its_actual_week(width,offset):
    life, baseline = history(width,offset)
    original = baseline.model_dump_json()
    result = prepare_native_health_history(
        saved_health=(baseline,), signed_lifecycle=life[:-1], next_lifecycle=life[-1],
    )
    assert result[0] is baseline
    assert len(result) == 5
    assert [h.week.ordinal for h in result] == list(range(5))
    assert [tuple(p.player_id for p in h.players) for h in result] == [
        ("existing",), ("existing",), ("born-early","existing"),
        ("born-early","existing"), ("born-early","born-next","existing"),
    ]
    assert all(h.source_lifecycle_fingerprint == life[i].fingerprint
               for i,h in enumerate(result) if i)
    assert result[-1].birth_event == life[-1].birth_event
    assert baseline.model_dump_json() == original
    assert result == prepare_native_health_history(
        saved_health=(baseline,), signed_lifecycle=life[:-1], next_lifecycle=life[-1],
    )
    # Restart with an already materialized Health prefix keeps every prior byte.
    resumed = prepare_native_health_history(
        saved_health=result[:3], signed_lifecycle=life[:-1], next_lifecycle=life[-1],
    )
    assert resumed == result
    assert all(resumed[i] is result[i] for i in range(3))


def test_preparation_never_heals_or_erases_existing_health_and_admin_evidence():
    from beta_engine.domain.players.calendar_health import (
        CalendarHealthRecord, CalendarHealthProfile, CalendarHealthState,
        CalendarHealthOrigin, CalendarHealthEditEvidence,
    )
    life, baseline = history()
    record = CalendarHealthRecord(record_id="prior-injury", kind="Injury",condition_key="arm",
        lifecycle="Active", severity=25, affected_domains=("arm",),
        started_before_run=True,provenance="Signed Admin input")
    edit = CalendarHealthEditEvidence(command_id="prior-edit", request_fingerprint="a"*64,
        before_state_fingerprint=baseline.fingerprint, source_run_id="r",source_branch_id="b",
        player_id="existing",mode="pre_start_input",audit_label="Admin",audit_reason="Recorded fact")
    edited = CalendarHealthState(
        **{k:getattr(baseline,k) for k in ("run_id","branch_id","week","source_initial_world_fingerprint")},
        players=(CalendarHealthProfile(player_id="existing", records=(record,)),),
        origin=CalendarHealthOrigin.from_baseline(baseline),admin_edits=(edit,),
        stage_provenance="admin-pre-start",
    )
    result=prepare_native_health_history(saved_health=(edited,),
        signed_lifecycle=life[:-1],next_lifecycle=life[-1])
    for h in result[1:]:
        assert next(p for p in h.players if p.player_id=="existing").records == (record,)
        assert h.admin_edits == (edit,)
        assert h.origin == edited.origin


@pytest.mark.parametrize("damage", ["missing_life","foreign_life","future_health",
    "missing_health","broken_health_predecessor","forged_natural_health","wrong_target",
    "broken_origin","extra_health","contracting_life"])
def test_preparation_rejects_incomplete_or_incompatible_signed_inputs(damage):
    life, baseline = history()
    full = prepare_native_health_history(saved_health=(baseline,),
        signed_lifecycle=life[:-1],next_lifecycle=life[-1])
    prefix, signed, target = (baseline,), life[:-1], life[-1]
    if damage=="missing_life": signed=(life[0],*life[2:-1])
    elif damage=="foreign_life": signed=(life[0],life[1].model_copy(update={"branch_id":"elsewhere"}),*life[2:-1])
    elif damage=="future_health": prefix=full
    elif damage=="missing_health": prefix=()
    elif damage=="broken_health_predecessor": prefix=(baseline,full[1].model_copy(update={"predecessor_fingerprint":"0"*64}))
    elif damage=="forged_natural_health": prefix=(baseline,full[1].model_copy(update={"source_lifecycle_fingerprint":"0"*64}))
    elif damage=="wrong_target": target=life[-2]
    elif damage=="broken_origin": prefix=(baseline.model_copy(update={"predecessor_fingerprint":"0"*64}),)
    elif damage=="extra_health": prefix=tuple(baseline for _ in range(8))
    elif damage=="contracting_life":
        smaller=RunCalendar(61,37,2030,2)
        signed=(life[0],life[1].model_copy(update={"week":week(smaller,0,2)}),*life[2:-1])
    frozen=json.dumps([h.model_dump(mode="json") for h in full],sort_keys=True)
    with pytest.raises(ValueError):
        prepare_native_health_history(saved_health=prefix,signed_lifecycle=signed,next_lifecycle=target)
    assert json.dumps([h.model_dump(mode="json") for h in full],sort_keys=True)==frozen
