"""Real SQLite acceptance tests for the first authoritative slot match slice."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.application.authoritative_slot_matches import (
    AuthoritativeSlotMatchExecutor,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.sporting import (
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.simulation_slots import CanonicalMatchInputProjectionPolicy
from beta_engine.infrastructure.db.models import Base, SimulationEventGroupModel
from beta_engine.infrastructure.db.player_sporting_state import (
    put_sporting,
    resolve_completed_context_from_authoritative_matches,
    transition_sporting,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)

WEEK = RankingWeek(season_index=0, week=1)


def player(player_id: str, value: int) -> PlayerSportingRecord:
    return PlayerSportingRecord(
        player_id=player_id,
        attributes=tuple((name, value) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=180,
        potential_identity=f"potential:{player_id}",
        potential_provenance="test",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=50,
        long_term_fatigue=0,
    )


def session_at(path: Path) -> Session:
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    put_sporting(
        session,
        PlayerSportingWeekState(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            players=tuple(
                player(pid, value)
                for pid, value in (("a", 130), ("b", 100), ("c", 125), ("d", 95))
            ),
            effective_development_policy=PlayerDevelopmentPolicy(),
            completed_context_fingerprint="bootstrap",
            source_initial_world_fingerprint="world",
            stage_provenance="test",
        ),
    )
    session.commit()
    return session


def run_semifinals(path: Path, order: tuple[str, str]):
    session = session_at(path)
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-1",
        ordinal=1,
        group_ids=("sf-1", "sf-2"),
    )
    participants = {"sf-1": ("a", "b", 101), "sf-2": ("c", "d", 202)}
    results = {}
    for group in order:
        a, b, seed = participants[group]
        results[group] = executor.execute_match_group(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="slot-1",
            group_id=group,
            event_id="event",
            match_id=group,
            player_a_id=a,
            player_b_id=b,
            seed=seed,
            expected_slot_start_fingerprint=plan.slot_start_fingerprint,
        )
        session.commit()
    checkpoint = executor.terminal_checkpoint(
        run_id="run", branch_id="branch", week=WEEK
    )
    return session, executor, plan, results, checkpoint


def test_same_slot_frozen_snapshot_and_iteration_order_independence(tmp_path):
    one = run_semifinals(tmp_path / "one.sqlite", ("sf-1", "sf-2"))
    two = run_semifinals(tmp_path / "two.sqlite", ("sf-2", "sf-1"))
    assert one[2].slot_start_fingerprint == two[2].slot_start_fingerprint
    for group in ("sf-1", "sf-2"):
        assert one[3][group].authoritative_input == two[3][group].authoritative_input
        assert one[3][group].result == two[3][group].result
        assert one[3][group].effects == two[3][group].effects
        assert (
            one[3][group].authoritative_input.slot_start_fingerprint
            == one[2].slot_start_fingerprint
        )
    assert one[4] == two[4]


def test_semifinal_effects_feed_later_final_and_replay_is_historical(tmp_path):
    session, executor, first, semifinals, after = run_semifinals(
        tmp_path / "tournament.sqlite", ("sf-1", "sf-2")
    )
    finalists = tuple(result.result.winner_player_id for result in semifinals.values())
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        ordinal=2,
        group_ids=("final",),
        dependency_ids=("sf-1", "sf-2"),
    )
    assert plan.slot_start_fingerprint != first.slot_start_fingerprint
    final = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot-2",
        group_id="final",
        event_id="event",
        match_id="final",
        player_a_id=finalists[0],
        player_b_id=finalists[1],
        seed=303,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    session.commit()
    after_players = {p.player_id: p for p in after.players}
    projected = {p.player_id: p for p in final.authoritative_input.player_projections}
    for finalist in finalists:
        assert projected[finalist].current_form == after_players[finalist].current_form
        assert (
            projected[finalist].match_sharpness
            == after_players[finalist].match_sharpness
        )
        assert (
            projected[finalist].long_term_fatigue
            == after_players[finalist].long_term_fatigue
        )
    stored_hash = final.authoritative_input.fingerprint
    session.close()
    reopened = Session(create_engine(f"sqlite:///{tmp_path / 'tournament.sqlite'}"))
    replay = AuthoritativeSlotMatchExecutor(reopened).replay(
        run_id="run", branch_id="branch", week=WEEK, slot_id="slot-2", group_id="final"
    )
    assert replay.authoritative_input.fingerprint == stored_hash
    assert replay.result == final.result


def test_retry_conflict_exactly_once_branch_isolation_and_faults(tmp_path):
    session = session_at(tmp_path / "faults.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
    )
    session.commit()
    with pytest.raises(ValueError, match="complete predecessor"):
        executor.create_slot(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            slot_id="final-too-early",
            ordinal=2,
            group_ids=("final",),
            dependency_ids=("g",),
        )
    kwargs = dict(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="e",
        match_id="m",
        player_a_id="a",
        player_b_id="b",
        seed=1,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    for fault in ("after_match_staging", "after_effect_staging", "before_group_commit"):
        with pytest.raises(RuntimeError):
            executor.execute_match_group(**kwargs, fault_at=fault)
        session.rollback()
        assert (
            session.get(
                SimulationEventGroupModel, ("run", "branch", WEEK.ordinal, "slot", "g")
            )
            is None
        )
    result = executor.execute_match_group(**kwargs)
    session.commit()
    retry = executor.execute_match_group(**kwargs)
    assert retry.exact_retry and retry.effects == result.effects
    with pytest.raises(ValueError, match="conflicts"):
        executor.execute_match_group(**(kwargs | {"seed": 2}))
    with pytest.raises(ValueError, match="fingerprint changed"):
        executor.execute_match_group(
            **(kwargs | {"expected_slot_start_fingerprint": "0" * 64})
        )
    assert (
        session.query(SimulationEventGroupModel).filter_by(branch_id="other").count()
        == 0
    )


def test_projection_policy_is_versioned_and_changes_protected_input(tmp_path):
    session = session_at(tmp_path / "projection.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
    )
    base = dict(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="e",
        match_id="m",
        player_a_id="a",
        player_b_id="b",
        seed=4,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    result = executor.execute_match_group(**base)
    projection = result.authoritative_input.player_projections[0]
    assert len(projection.canonical_attributes) == 57
    assert projection.current_form == 100
    assert projection.match_sharpness == 50
    assert projection.long_term_fatigue == 0
    assert (
        projection.projection_policy_id
        == "canonical-57-to-legacy-match-engine.provisional.v1"
    )
    changed = CanonicalMatchInputProjectionPolicy(
        policy_id="canonical-57-to-legacy-match-engine.provisional.v2"
    )
    with pytest.raises(ValueError, match="conflicts"):
        executor.execute_match_group(**base, projection_policy=changed)


def test_slot_history_saved_reopened_and_restored_backward_forward(tmp_path):
    path = tmp_path / "restore.sqlite"
    session = session_at(path)
    before = {"content": {}}
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("g",),
    )
    executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=77,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    after = {"content": {}}
    capture_saved_simulation_slots(session, after, run_id="run", branch_id="branch")
    session.commit()
    session.close()

    reopened = Session(create_engine(f"sqlite:///{path}"))
    restore_saved_simulation_slots(
        reopened,
        current_payload=after,
        target_payload=before,
        run_id="run",
        branch_id="branch",
    )
    reopened.commit()
    assert reopened.query(SimulationEventGroupModel).count() == 0
    restore_saved_simulation_slots(
        reopened,
        current_payload=before,
        target_payload=after,
        run_id="run",
        branch_id="branch",
    )
    reopened.commit()
    replay = AuthoritativeSlotMatchExecutor(reopened).replay(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="g",
    )
    assert replay.exact_retry is False


def test_week_transition_development_reads_terminal_post_match_form(tmp_path):
    session = session_at(tmp_path / "transition.sqlite")
    executor = AuthoritativeSlotMatchExecutor(session)
    plan = executor.create_slot(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        ordinal=1,
        group_ids=("match",),
    )
    played = executor.execute_match_group(
        run_id="run",
        branch_id="branch",
        week=WEEK,
        slot_id="slot",
        group_id="match",
        event_id="event",
        match_id="match",
        player_a_id="a",
        player_b_id="b",
        seed=88,
        expected_slot_start_fingerprint=plan.slot_start_fingerprint,
    )
    terminal = played.terminal_checkpoint
    resolve_completed_context_from_authoritative_matches(
        session,
        run_id="run",
        branch_id="branch",
        completed_week=WEEK,
        player_ids=("a", "b", "c", "d"),
    )
    target = transition_sporting(
        session,
        run_id="run",
        branch_id="branch",
        completed=WEEK,
        target=RankingWeek(season_index=0, week=2),
        lifecycle=SimpleNamespace(
            players=tuple(
                SimpleNamespace(player_id=pid, age=25) for pid in ("a", "b", "c", "d")
            )
        ),
    )
    terminal_players = {p.player_id: p for p in terminal.players}
    target_players = {p.player_id: p for p in target.players}
    policy = target.effective_development_policy
    for pid in ("a", "b"):
        difference = (
            terminal_players[pid].long_term_form_norm
            - terminal_players[pid].current_form
        )
        regression = int(difference / policy.form_regression_divisor)
        if regression == 0 and difference:
            regression = 1 if difference > 0 else -1
        expected_regressed = terminal_players[pid].current_form + regression
        assert target_players[pid].current_form == expected_regressed
