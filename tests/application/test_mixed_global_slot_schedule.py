import json

import pytest
from sqlalchemy import select

from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.application_validation_authority import (
    ResolvedApplicationValidationSlot,
    TournamentApplicationValidationAuthority,
)
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.infrastructure.db.models import SimulationSlotModel
from beta_engine.infrastructure.db.application_validation_slots import (
    ApplicationValidationSlotStore,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RunEntryDecisionSlotConflict,
    RunEntryDecisionSlotStore,
)
from test_authoritative_slot_matches import (
    _driver_command,
    _multi_driver_fixture,
)


def _entry_slot(week, *, ordinal):
    return RunEntryDecisionSlotAuthority(
        run_id="run",
        branch_id="branch",
        week=week,
        decision_slot_ordinal=ordinal,
        source_entry_batch_fingerprint="a" * 64,
        source_application_decisions_fingerprint="b" * 64,
        source_active_players_fingerprint="c" * 64,
        decisions=(
            EntryDecisionEvidence(
                event_id="entry-event",
                player_id="P1",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
        ),
    )


def _resolve_entry_slot(session, authority):
    decision = authority.decisions[0]
    validation = TournamentApplicationValidationAuthority(
        validation_id=f"validation-{authority.decision_slot_ordinal}",
        application_id=f"application-{authority.decision_slot_ordinal}",
        run_id=authority.run_id,
        branch_id=authority.branch_id,
        week=authority.week,
        decision_slot_ordinal=authority.decision_slot_ordinal,
        source_slot_fingerprint=authority.fingerprint,
        event_id=decision.event_id,
        player_id=decision.player_id,
        entry_window="main",
        source_decision_fingerprint=decision.source_decision_fingerprint,
        outcome="invalid",
        nr_tie_break_token=None,
        validation_policy_id="test-policy.v1",
        validation_policy_fingerprint="f" * 64,
        reasons=("test_invalid",),
        provenance="mixed chronology test",
    )
    ApplicationValidationSlotStore(session).append(
        ResolvedApplicationValidationSlot(
            slot=authority,
            validations=(validation,),
        )
    )


@pytest.mark.pr_critical
def test_topological_match_schedule_skips_persisted_entry_global_ordinal(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "entry-reserved-first"
    )
    with factory.begin() as session:
        authority = _entry_slot(week, ordinal=1)
        RunEntryDecisionSlotStore(session).append(authority)
        _resolve_entry_slot(session, authority)

    inspected = driver.inspect_schedule(run_id="run", branch_id="branch")
    assert inspected["required"] is True
    assert inspected["reserved_entry_slot_ordinals"] == [1]

    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(json.dumps(proposal["schedule"], sort_keys=True, separators=(",", ":")))
    match_ordinals = tuple(slot.ordinal for slot in schedule.slots)
    assert match_ordinals == tuple(sorted(match_ordinals))
    assert match_ordinals[0] == 2
    assert 1 not in match_ordinals

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="schedule-with-entry-gap",
        expected_week=week,
        expected_schedule_fingerprint=schedule.fingerprint,
        expected_position_fingerprint=proposal["position_fingerprint"],
    )

    command, before = _driver_command(driver, week, "first-sparse-match-slot")
    assert before.slot_ordinal == 2
    driver.simulate_next_slot(command)

    with factory() as session:
        first_match_slot = session.scalar(
            select(SimulationSlotModel)
            .where(
                SimulationSlotModel.run_id == "run",
                SimulationSlotModel.branch_id == "branch",
                SimulationSlotModel.week_ordinal == week.ordinal,
            )
            .order_by(SimulationSlotModel.slot_ordinal)
            .limit(1)
        )
        assert first_match_slot is not None
        assert first_match_slot.slot_ordinal == 2


@pytest.mark.pr_critical
def test_adopted_match_schedule_reservation_blocks_late_entry_slot(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "schedule-reserved-first"
    )
    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(json.dumps(proposal["schedule"], sort_keys=True, separators=(",", ":")))
    first_match_ordinal = schedule.slots[0].ordinal

    driver.adopt_topological_schedule_proposal(
        run_id="run",
        branch_id="branch",
        request_id="schedule-first",
        expected_week=week,
        expected_schedule_fingerprint=schedule.fingerprint,
        expected_position_fingerprint=proposal["position_fingerprint"],
    )

    with factory.begin() as session:
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="reserved by the adopted match schedule",
        ):
            RunEntryDecisionSlotStore(session).append(
                _entry_slot(week, ordinal=first_match_ordinal)
            )


@pytest.mark.pr_critical
def test_multiple_leading_entry_slots_shift_first_match_layer(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "two-leading-entry-slots"
    )
    with factory.begin() as session:
        store = RunEntryDecisionSlotStore(session)
        first = _entry_slot(week, ordinal=1)
        store.append(first)
        _resolve_entry_slot(session, first)
        second = _entry_slot(week, ordinal=2).model_copy(
            update={
                "source_entry_batch_fingerprint": "e" * 64,
                "source_application_decisions_fingerprint": "f" * 64,
            }
        )
        store.append(second)

    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate_json(
        json.dumps(proposal["schedule"], sort_keys=True, separators=(",", ":"))
    )
    ordinals = tuple(slot.ordinal for slot in schedule.slots)

    assert ordinals[0] == 3
    assert 1 not in ordinals
    assert 2 not in ordinals


@pytest.mark.pr_critical
def test_manual_sparse_match_schedule_rejects_unowned_global_gap(tmp_path):
    driver, _, _, _, _ = _multi_driver_fixture(
        tmp_path / "unowned-match-gap"
    )
    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    canonical = WeekSimulationSchedule.model_validate_json(json.dumps(proposal["schedule"], sort_keys=True, separators=(",", ":")))
    sparse = WeekSimulationSchedule(
        run_id=canonical.run_id,
        branch_id=canonical.branch_id,
        week=canonical.week,
        slots=tuple(
            slot.model_copy(update={"ordinal": slot.ordinal + 1})
            for slot in canonical.slots
        ),
    )

    with pytest.raises(
        ValueError,
        match="global-slot gap not owned by an entry-decision slot",
    ):
        driver.preview_schedule(sparse)
