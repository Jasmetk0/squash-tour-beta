"""Real Signed Saved native Health history, including authentic 15yo newcomer."""
import json
import hashlib

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_lifecycle import advance_calendar_lifecycle
from beta_engine.domain.players.calendar_native_health_transition import (
    CalendarNativeHealthTransitionState, advance_native_health_week,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    advance_calendar_lifecycle_with_prospects,
    build_calendar_prospect_birth_event,
)
from beta_engine.infrastructure.db.player_health_state import (
    _component, _parse_health_json, load_saved_health,
    remap_saved_health_component,
)
from tests.domain.test_calendar_prospect_birth_event import (
    birth_row, source, week,
)
from tests.domain.test_calendar_prospect_admission_bundle import health_for
from tests.infrastructure.test_calendar_native_v4_saved_lifecycle import _signed_fixture

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("width,offset", [
    (52, 1), (52, 35), (61, 37), (80, 15), (80, 80),
])
def test_real_saved_birth_health_and_signed_lifecycle_roundtrip(monkeypatch,width,offset):
    payload, lifecycle, event = _signed_fixture(monkeypatch,width,offset)
    initial = health_for(lifecycle[0])
    next_health = advance_native_health_week(
        previous_health=initial, previous_lifecycle=lifecycle[0],
        next_lifecycle=lifecycle[1],
    )
    states = (initial,next_health)
    payload["content"]["player_health_state"] = _component(states)
    encoded = json.dumps(payload,sort_keys=True)
    assert next_health.schema_version == "player_health_calendar_state.v3"
    assert next_health.birth_event == event
    assert next_health.source_lifecycle_fingerprint == lifecycle[1].fingerprint
    assert [p.player_id for p in next_health.players] == ["born","existing"]
    assert all(not p.records and not p.permanent_consequences for p in next_health.players)
    assert next_health == CalendarNativeHealthTransitionState.model_validate_json(
        next_health.model_dump_json()
    )
    assert next_health == _parse_health_json(next_health.model_dump_json())
    assert load_saved_health(payload,run_id="r",branch_id="b") == states
    assert next_health == advance_native_health_week(
        previous_health=initial,previous_lifecycle=lifecycle[0],
        next_lifecycle=lifecycle[1],
    )
    with pytest.raises(ValueError,match="signed source/event re-authority"):
        remap_saved_health_component(
            payload,run_id="r",source_branch_id="b",target_branch_id="fork",
        )
    assert json.dumps(payload,sort_keys=True) == encoded


@pytest.mark.parametrize("attack,reason",[
    ("missing_health_birth","requires its Signed native Health transition"),
    ("forged_birth_event","Native birth source generation proof is invalid"),
    ("forged_health_player","differs from actual Signed birthdays"),
    ("missing_player","population/calendar"),
    ("old_player_modified","differs from actual Signed birthdays"),
    ("wrong_life_fingerprint","actual Signed lifecycle"),
    ("forged_predecessor","predecessor chain"),
    ("duplicate_id","unique sorted"),
    ("foreign_branch","foreign birthday event"),
    ("out_of_scope_birth","population/calendar"),
])
def test_actual_saved_replay_rejects_health_forgery(monkeypatch,attack,reason):
    payload,life,event = _signed_fixture(monkeypatch)
    origin=health_for(life[0])
    next_state=advance_native_health_week(
        previous_health=origin,previous_lifecycle=life[0],next_lifecycle=life[1],
    )
    payload["content"]["player_health_state"]=_component((origin,next_state))
    component=payload["content"]["player_health_state"]
    target=component["states"][-1]
    if attack=="missing_health_birth":
        component["states"]=[component["states"][0]]
    elif attack=="forged_birth_event":
        target["birth_event"]["source_run_prospect_fingerprint"]="0"*64
    elif attack=="forged_health_player":
        target["players"].append({"player_id":"foreign","records":[],"permanent_consequences":[]})
        target["players"].sort(key=lambda p:p["player_id"])
    elif attack=="missing_player":
        target["players"]=target["players"][:-1]
    elif attack=="old_player_modified":
        target["players"][1]["records"]=[{
            "record_id":"fake-record","kind":"Injury","condition_key":"arm",
            "lifecycle":"Active","severity":10,"affected_domains":["arm"],
            "started_before_run":True,"provenance":"forged",
        }]
    elif attack=="wrong_life_fingerprint":
        target["source_lifecycle_fingerprint"]="0"*64
    elif attack=="forged_predecessor":
        target["predecessor_fingerprint"]="0"*64
    elif attack=="duplicate_id":
        target["players"].append(target["players"][0])
    elif attack=="foreign_branch":
        target["branch_id"]="other"
    elif attack=="out_of_scope_birth":
        target["players"][0]["player_id"]="aa"
    # Recompute even deliberately corrupt model data from the raw canonical
    # JSON so this test reaches the native Saved validator instead of failing
    # on an old, trivially incorrect outer SHA-256.
    component["fingerprint"]=hashlib.sha256(json.dumps(
        component["states"],sort_keys=True,separators=(",",":"),
    ).encode()).hexdigest()
    with pytest.raises(ValueError,match=reason):
        load_saved_health(payload,run_id="r",branch_id="b")


def test_natural_no_birth_week_remains_canonical_and_does_not_invent_health_history():
    from tests.domain.test_calendar_prospect_birth_event import lifecycle
    clock=RunCalendar(61,37,2030,3)
    initial_life=lifecycle(clock,week(clock,0,1))
    later=advance_calendar_lifecycle(initial_life,week(clock,0,2))
    first_health=health_for(initial_life)
    carry=advance_native_health_week(
        previous_health=first_health,
        previous_lifecycle=initial_life,next_lifecycle=later,
    )
    assert carry.birth_event is None
    assert carry.players[0].player_id=="existing"
    assert not carry.players[0].records
    assert carry.origin.baseline_fingerprint == first_health.fingerprint
    assert carry.admin_edits==()
    assert carry == CalendarNativeHealthTransitionState.model_validate_json(
        carry.model_dump_json()
    )


def test_one_newcomer_receives_no_fake_previous_week_health_and_further_carry_is_exact(monkeypatch):
    payload,life,event=_signed_fixture(monkeypatch)
    initial=health_for(life[0])
    birth=advance_native_health_week(
        previous_health=initial,previous_lifecycle=life[0],next_lifecycle=life[1],
    )
    next_life=advance_calendar_lifecycle(life[1],week(life[0].week.calendar,0,3))
    later=advance_native_health_week(
        previous_health=birth,previous_lifecycle=life[1],
        next_lifecycle=next_life,
    )
    assert later.birth_event is None
    assert later.predecessor_fingerprint==birth.fingerprint
    assert later.players==birth.players
    assert tuple(p.player_id for p in later.players)==("born","existing")
    assert later.source_lifecycle_fingerprint==next_life.fingerprint
    assert later.origin==birth.origin
