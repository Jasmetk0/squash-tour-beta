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
    ("forged_health_player","population/calendar"),
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
        from beta_engine.domain.players.calendar_health import CalendarHealthRecord
        target["players"][1]["records"]=[CalendarHealthRecord(
            record_id="fake-record",kind="Injury",condition_key="arm",
            lifecycle="Active",severity=10,affected_domains=("arm",),
            started_before_run=True,provenance="forged",
        ).model_dump(mode="json")]
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


def test_health_accepts_strict_extension_without_rewriting_saved_origin(monkeypatch):
    """Production Saved loaders must accept old World and a newer native clock."""
    from beta_engine.domain.tournaments.calendar_tour import CalendarTourState
    from tests.infrastructure.test_calendar_native_v4_saved_lifecycle import _digest
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source

    payload, life, _ = _signed_fixture(monkeypatch)
    original_clock = life[0].week.calendar
    extended = RunCalendar(
        original_clock.weeks_per_year, original_clock.season_start_year_week,
        original_clock.start_year, original_clock.season_count + 2,
    )
    target = week(extended, 0, 2)
    event = build_calendar_prospect_birth_event(
        predecessor=life[0], target=target,
        source=load_saved_run_prospect_source(payload, run_id="r"), world_package_id="world",
    )
    successor = advance_calendar_lifecycle_with_prospects(life[0], event)
    payload["content"]["player_lifecycle"] = {
        "fingerprint": _digest((life[0], successor)),
        "states": [s.model_dump(mode="json") for s in (life[0], successor)],
    }
    tour = CalendarTourState.model_validate_json(json.dumps(payload["content"]["calendar_tour_authority"]["state"]))
    # The real Tour keeps historical clocks and explicitly extends its head.
    tour = tour.model_copy(update={
        "week": target, "lifecycle_fingerprint": successor.fingerprint,
    })
    payload["content"]["calendar_tour_authority"]["state"] = tour.model_dump(mode="json")
    initial = health_for(life[0])
    health = advance_native_health_week(
        previous_health=initial, previous_lifecycle=life[0], next_lifecycle=successor,
    )
    payload["content"]["player_health_state"] = _component((initial, health))
    before = canonical_hash(payload)
    assert load_saved_health(payload, run_id="r", branch_id="b") == (initial, health)
    assert health.week.calendar.season_count == extended.season_count
    assert initial.week.calendar == original_clock
    assert canonical_hash(payload) == before


@pytest.mark.parametrize("damage", ["width", "offset", "year", "horizon"])
def test_same_ordinal_health_cannot_alias_a_foreign_calendar(damage):
    from tests.domain.test_calendar_prospect_birth_event import lifecycle
    clock = RunCalendar(61, 37, 2030, 3)
    life = lifecycle(clock, week(clock, 0, 1))
    successor = advance_calendar_lifecycle(life, week(clock, 0, 2))
    changes = {"width": (52, 37, 2030, 3), "offset": (61, 36, 2030, 3),
               "year": (61, 37, 2029, 3), "horizon": (61, 37, 2030, 4)}
    forged = health_for(life).model_copy(update={"week": week(RunCalendar(*changes[damage]), 0, 1)})
    with pytest.raises(ValueError, match="exact consecutive Signed lifecycle"):
        advance_native_health_week(
            previous_health=forged, previous_lifecycle=life, next_lifecycle=successor,
        )


def test_native_v3_admin_downgrade_is_rejected_before_sqlite_mutation(monkeypatch, tmp_path):
    from beta_engine.domain.players.calendar_health import CalendarHealthState, CalendarHealthEditEvidence
    from beta_engine.infrastructure.db.engine import DatabaseSettings, create_sqlite_engine, create_session_factory
    from beta_engine.infrastructure.db.models import PlayerHealthWeekStateModel
    from beta_engine.infrastructure.db.player_health_state import put_health, replace_health_head, get_health

    _, life, _ = _signed_fixture(monkeypatch)
    initial = health_for(life[0])
    health = advance_native_health_week(
        previous_health=initial, previous_lifecycle=life[0], next_lifecycle=life[1],
    )
    edit = CalendarHealthEditEvidence(
        command_id="attempt-v2-edit", request_fingerprint="a"*64,
        before_state_fingerprint=health.fingerprint, source_run_id="r", source_branch_id="b",
        player_id="existing", mode="current_state_correction", audit_label="Admin",
        audit_reason="Explicit correction cannot erase birth authority",
    )
    attempted = CalendarHealthState(
        **{k: getattr(health,k) for k in ("run_id","branch_id","week","players",
            "source_initial_world_fingerprint","predecessor_fingerprint","origin")},
        admin_edits=(edit,), stage_provenance="admin-current-correction",
    )
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'v3-edit.db'}"))
    PlayerHealthWeekStateModel.__table__.create(engine)
    try:
        with create_session_factory(engine).begin() as session:
            put_health(session, initial)
            put_health(session, health)
            with pytest.raises(ValueError, match="versioned Admin correction authority"):
                replace_health_head(session, attempted, expected_fingerprint=health.fingerprint)
            assert get_health(session, run_id="r", branch_id="b", week=health.week) == health
    finally:
        engine.dispose()
