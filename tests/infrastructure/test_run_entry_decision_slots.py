import pytest

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import SimulationMatchEventPlan
from beta_engine.domain.tournaments.run_entry_decision_slot import (
    EntryDecisionEvidence,
    RunEntryDecisionSlotAuthority,
)
from beta_engine.infrastructure.db.run_entry_decision_slots import (
    RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY,
    RunEntryDecisionSlotConflict,
    RunEntryDecisionSlotStore,
    capture_saved_run_entry_decision_slots,
    load_saved_run_entry_decision_slots,
    restore_saved_run_entry_decision_slots,
    validate_saved_entry_match_slot_collisions,
)
from test_authoritative_slot_matches import session_at


WEEK = RankingWeek(season_index=0, week=1)


def _entry_slot(**overrides):
    payload = {
        "run_id": "run",
        "branch_id": "branch",
        "week": WEEK,
        "decision_slot_ordinal": 1,
        "source_entry_batch_fingerprint": "a" * 64,
        "source_application_decisions_fingerprint": "b" * 64,
        "source_active_players_fingerprint": "c" * 64,
        "decisions": (
            EntryDecisionEvidence(
                event_id="entry-event",
                player_id="a",
                target="MAIN",
                source_decision_fingerprint="d" * 64,
            ),
        ),
    }
    payload.update(overrides)
    return RunEntryDecisionSlotAuthority(**payload)


def _match_plan(executor, *, ordinal=1):
    return executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id=f"match-slot-{ordinal}",
        ordinal=ordinal,
        group_ids=(f"group-{ordinal}",),
        match_events=(
            SimulationMatchEventPlan(
                group_id=f"group-{ordinal}",
                event_id="match-event",
                match_id=f"match-{ordinal}",
                direct_player_ids=("a", "b"),
            ),
        ),
    )


@pytest.mark.pr_critical
def test_entry_slot_store_is_idempotent_and_immutable(tmp_path):
    session = session_at(tmp_path / "entry-slot.sqlite")
    try:
        store = RunEntryDecisionSlotStore(session)
        authority = _entry_slot()
        assert store.append(authority) == authority
        assert store.append(authority) == authority
        assert store.list(run_id="run", branch_id="branch") == (authority,)

        conflicting = _entry_slot(source_entry_batch_fingerprint="e" * 64)
        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="already has different authority",
        ):
            store.append(conflicting)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_match_slot_then_entry_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "match-first.sqlite")
    try:
        executor = AuthoritativeSlotMatchExecutor(session)
        _match_plan(executor, ordinal=1)

        with pytest.raises(
            RunEntryDecisionSlotConflict,
            match="already belongs to a match slot",
        ):
            RunEntryDecisionSlotStore(session).append(_entry_slot())
    finally:
        session.close()


@pytest.mark.pr_critical
def test_entry_slot_then_match_slot_collision_fails_closed(tmp_path):
    session = session_at(tmp_path / "entry-first.sqlite")
    try:
        RunEntryDecisionSlotStore(session).append(_entry_slot())

        with pytest.raises(
            ValueError,
            match="already belongs to an entry-decision slot",
        ):
            _match_plan(AuthoritativeSlotMatchExecutor(session), ordinal=1)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_component_round_trip_restores_entry_slots(tmp_path):
    session = session_at(tmp_path / "saved-entry-slots.sqlite")
    try:
        empty_payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert empty_payload["content"][RUN_ENTRY_DECISION_SLOT_COMPONENT_KEY][
            "slots"
        ] == []

        authority = _entry_slot()
        RunEntryDecisionSlotStore(session).append(authority)
        current_payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert load_saved_run_entry_decision_slots(
            current_payload,
            run_id="run",
            branch_id="branch",
        ) == (authority,)

        restore_saved_run_entry_decision_slots(
            session,
            current_payload=current_payload,
            target_payload=empty_payload,
            run_id="run",
            branch_id="branch",
        )
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == ()

        restore_saved_run_entry_decision_slots(
            session,
            current_payload=empty_payload,
            target_payload=current_payload,
            run_id="run",
            branch_id="branch",
        )
        assert RunEntryDecisionSlotStore(session).list(
            run_id="run",
            branch_id="branch",
        ) == (authority,)
    finally:
        session.close()


@pytest.mark.pr_critical
def test_saved_revision_target_rejects_entry_match_global_slot_collision(tmp_path):
    session = session_at(tmp_path / "saved-collision.sqlite")
    try:
        authority = _entry_slot()
        RunEntryDecisionSlotStore(session).append(authority)
        payload = {"content": {}}
        capture_saved_run_entry_decision_slots(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )
        payload["content"]["simulation_slot_match_state"] = {
            "slots": [
                {
                    "run_id": "run",
                    "branch_id": "branch",
                    "week_ordinal": WEEK.ordinal,
                    "slot_ordinal": 1,
                }
            ]
        }

        with pytest.raises(
            ValueError,
            match="claim the same global position",
        ):
            validate_saved_entry_match_slot_collisions(
                payload,
                run_id="run",
                branch_id="branch",
            )
    finally:
        session.close()
