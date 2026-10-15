"""Append-only schedule inspection is strictly read-only, never approval."""
import pytest

from beta_engine.application.next_week_extension_inspection import (
    inspect_frozen_next_week_extension as inspect,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import WeekSimulationSchedule, WeekSimulationScheduleSlot


def schedule(*slots):
    return WeekSimulationSchedule(
        schema_version="week_simulation_schedule.v2",
        run_id="run", branch_id="branch",
        week=RankingWeek(season_index=0, week=1),
        slots=slots,
    )


def slot(ordinal, group, day, order, phase="group"):
    return WeekSimulationScheduleSlot(
        ordinal=ordinal, group_ids=(group,), match_day_ordinal=day,
        match_order=order, event_id="hybrid", draw_phase=phase,
        round_number=1,
    )


def example():
    base = schedule(slot(1,"group-A",1,1),slot(2,"group-B",1,2))
    current = schedule(*base.slots,slot(3,"final",2,1,"main"))
    frozen = {
        "schema_version":"authoritative_week_operation.v1",
        "run_id":"run", "branch_id":"branch",
        "week":{"season_index":0,"week":1},
        "schedule_fingerprint":base.fingerprint,
        "target_slot_ordinals":[1,2],
        "target_group_ids":["group-A","group-B"],
        "child_commands":{"1":None,"2":None},
        "week_transition":None,
    }
    return base,current,frozen


@pytest.mark.pr_critical
def test_only_genuine_authoritative_hybrid_append_is_proven():
    base,current,frozen=example()
    actual=inspect(frozen,current,base,{("hybrid","final")})
    assert actual["status"]=="append_only_proven"
    assert actual["new_slots"]==[{"ordinal":3,"group_id":"final","event_id":"hybrid","round_number":1}]
    assert actual["read_only"] is True and actual["automatic_rebase"] is False
    assert frozen["target_slot_ordinals"]==[1,2]


@pytest.mark.pr_critical
def test_unrelated_prefix_change_and_nonhybrid_extension_fail_closed():
    base,current,frozen=example()
    changed=schedule(slot(1,"group-A",1,1),slot(2,"changed",1,2),slot(3,"final",2,1,"main"))
    assert inspect(frozen,changed,base,{("hybrid","final")})["reason"]=="frozen_schedule_prefix_changed"
    assert inspect(frozen,current,base,set())["reason"]=="new_slots_not_from_frozen_hybrid_bracket"
    assert inspect(frozen,base,base,{("hybrid","final")})["status"]=="unchanged"


@pytest.mark.pr_critical
def test_frozen_children_corrupt_identity_or_transition_are_not_applicable():
    base,current,frozen=example()
    with pytest.raises(ValueError,match="sporting range"):
        inspect(frozen|{"target_slot_ordinals":[2,1]},current,base,{("hybrid","final")})
    with pytest.raises(ValueError,match="child identity"):
        inspect(frozen|{"child_commands":{"1":False,"2":None}},current,base,{("hybrid","final")})
    assert inspect(frozen|{"week_transition":{"command_id":"older"}},current,base,{("hybrid","final")})["reason"]=="week_transition_already_frozen"
    assert inspect(frozen|{"week":{"season_index":0,"week":2}},current,base,{("hybrid","final")})["reason"]=="scope_or_week_changed"


@pytest.mark.pr_critical
def test_reserved_ordinal_gap_not_claimed_safe():
    base,current,frozen=example()
    gapped=schedule(*base.slots,slot(4,"final",2,1,"main"))
    assert inspect(frozen,gapped,base,{("hybrid","final")})["status"]=="append_only_proven"
    # Only a gap among newly appended slots is blocked; this isolated extra
    # integer may be a reserved Entry ordinal before the first new match.
    gapped_two=schedule(*base.slots,slot(3,"semi",2,1,"main"),slot(5,"final",3,1,"main"))
    assert inspect(frozen,gapped_two,base,{("hybrid","semi"),("hybrid","final")})["reason"]=="new_slots_cross_reserved_global_ordinals"
