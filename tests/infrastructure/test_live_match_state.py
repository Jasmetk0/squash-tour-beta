from __future__ import annotations

import pytest

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchInputSnapshot,
    MatchParticipantContext,
    official_match_format_snapshot,
)
from beta_engine.domain.players import Player
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.live_match_state import PersistedLiveMatchStore
from beta_engine.infrastructure.db.models import Base


def _player(player_id: str, base: int) -> Player:
    return Player(
        player_id=player_id,
        name=player_id,
        age=27,
        nationality="TST",
        technique=base,
        movement=base,
        physical=base,
        mental=base,
        consistency=base,
        clutch=base,
        recovery=base,
        play_style="tempo-controller",
        archetype="all-court tactician",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="balanced",
            professionalism=0.7,
            ambition=0.7,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.8,
        ),
    )


def _snapshot(seed: int = 8128) -> MatchInputSnapshot:
    context = MatchContext(
        match_id="LIVE-MATCH-1",
        player_a=MatchParticipantContext(player=_player("A", 86)),
        player_b=MatchParticipantContext(player=_player("B", 82)),
    )
    return MatchInputSnapshot.create(
        context=context,
        effective_match_format=official_match_format_snapshot(),
        simulation_seed=seed,
        match_engine_version="match_engine_v10",
    )


def _session_factory(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'live.db'}")
    )
    Base.metadata.create_all(engine)
    return create_session_factory(engine)


@pytest.mark.pr_critical
def test_persisted_live_match_survives_session_restart_and_matches_full_engine(
    tmp_path,
) -> None:
    snapshot = _snapshot()
    expected = MatchEngine(
        rng=DeterministicRng(snapshot.simulation_seed)
    ).simulate(
        snapshot.context,
        log_anchor_hash=snapshot.snapshot_hash,
        effective_match_timing=snapshot.effective_match_timing,
        effective_match_stamina=snapshot.effective_match_stamina,
        rally_calibration_profile=snapshot.rally_calibration_profile,
        effective_match_gameplans=snapshot.effective_match_gameplans,
        effective_rally_rules=snapshot.effective_rally_rules,
    )
    sessions = _session_factory(tmp_path)

    with sessions() as session:
        state = PersistedLiveMatchStore(session).start_from_engine_input(
            run_id="RUN",
            branch_id="BRANCH",
            week_ordinal=0,
            slot_id="SLOT-1",
            group_id="GROUP-1",
            engine_input=snapshot,
        )
        session.commit()
        state_fingerprint = state.fingerprint

    rallies = []
    command = 0
    final = None
    while final is None:
        command += 1
        with sessions() as session:
            response = PersistedLiveMatchStore(session).simulate_next_rally(
                run_id="RUN",
                branch_id="BRANCH",
                week_ordinal=0,
                slot_id="SLOT-1",
                group_id="GROUP-1",
                command_id=f"rally-{command}",
                expected_state_fingerprint=state_fingerprint,
            )
            session.commit()
            if response["rally"] is not None:
                rallies.append(response["rally"])
            state_fingerprint = response["state_fingerprint"]
            final = response["final_result"]
        assert command < 1000

    assert final == expected.model_dump(mode="json")
    assert rallies == [
        event.model_dump(mode="json") for event in expected.rally_log.events
    ]


@pytest.mark.pr_critical
def test_live_next_rally_exact_retry_is_idempotent_and_stale_cursor_fails(tmp_path) -> None:
    snapshot = _snapshot(seed=991)
    sessions = _session_factory(tmp_path)

    with sessions() as session:
        state = PersistedLiveMatchStore(session).start_from_engine_input(
            run_id="RUN",
            branch_id="BRANCH",
            week_ordinal=0,
            slot_id="SLOT-1",
            group_id="GROUP-1",
            engine_input=snapshot,
        )
        session.commit()
        first_state = state.fingerprint

    with sessions() as session:
        store = PersistedLiveMatchStore(session)
        first = store.simulate_next_rally(
            run_id="RUN",
            branch_id="BRANCH",
            week_ordinal=0,
            slot_id="SLOT-1",
            group_id="GROUP-1",
            command_id="cmd-1",
            expected_state_fingerprint=first_state,
        )
        session.commit()

    with sessions() as session:
        replay = PersistedLiveMatchStore(session).simulate_next_rally(
            run_id="RUN",
            branch_id="BRANCH",
            week_ordinal=0,
            slot_id="SLOT-1",
            group_id="GROUP-1",
            command_id="cmd-1",
            expected_state_fingerprint=first_state,
        )
        assert replay["idempotent_replay"] is True
        assert replay["state_fingerprint"] == first["state_fingerprint"]
        assert replay["rally"] == first["rally"]

    with sessions() as session:
        with pytest.raises(ValueError, match="state changed"):
            PersistedLiveMatchStore(session).simulate_next_rally(
                run_id="RUN",
                branch_id="BRANCH",
                week_ordinal=0,
                slot_id="SLOT-1",
                group_id="GROUP-1",
                command_id="cmd-2",
                expected_state_fingerprint=first_state,
            )


def test_live_match_scope_cannot_be_reused_with_different_frozen_input(tmp_path) -> None:
    sessions = _session_factory(tmp_path)
    first = _snapshot(seed=100)
    second = _snapshot(seed=101)

    with sessions() as session:
        PersistedLiveMatchStore(session).start_from_engine_input(
            run_id="RUN",
            branch_id="BRANCH",
            week_ordinal=0,
            slot_id="SLOT-1",
            group_id="GROUP-1",
            engine_input=first,
        )
        session.commit()

    with sessions() as session:
        with pytest.raises(ValueError, match="different frozen working input"):
            PersistedLiveMatchStore(session).start_from_engine_input(
                run_id="RUN",
                branch_id="BRANCH",
                week_ordinal=0,
                slot_id="SLOT-1",
                group_id="GROUP-1",
                engine_input=second,
            )
