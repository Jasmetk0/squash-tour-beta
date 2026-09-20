import pytest
from sqlalchemy import select

from beta_engine.domain.simulation_slots import WeekSimulationSchedule
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.infrastructure.db.models import SimulationSlotModel
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


@pytest.mark.pr_critical
def test_topological_match_schedule_skips_persisted_entry_global_ordinal(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "entry-reserved-first"
    )
    with factory.begin() as session:
        RunEntryDecisionSlotStore(session).append(_entry_slot(week, ordinal=1))

    inspected = driver.inspect_schedule(run_id="run", branch_id="branch")
    assert inspected["required"] is True
    assert inspected["reserved_entry_slot_ordinals"] == [1]

    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate(proposal["schedule"])
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
    schedule = WeekSimulationSchedule.model_validate(proposal["schedule"])
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
def test_sparse_match_schedule_can_reserve_middle_entry_ordinal(tmp_path):
    driver, factory, week, _, _ = _multi_driver_fixture(
        tmp_path / "entry-reserved-middle"
    )
    with factory.begin() as session:
        RunEntryDecisionSlotStore(session).append(_entry_slot(week, ordinal=2))

    proposal = driver.propose_topological_schedule(
        run_id="run",
        branch_id="branch",
    )
    schedule = WeekSimulationSchedule.model_validate(proposal["schedule"])
    ordinals = tuple(slot.ordinal for slot in schedule.slots)

    assert ordinals[0] == 1
    assert 2 not in ordinals
    if len(ordinals) > 1:
        assert ordinals[1] == 3
