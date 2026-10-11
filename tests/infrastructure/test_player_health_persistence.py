"""Health V1 persistence, Saved Revision, restore, and fork-remap tests."""

import pytest

from beta_engine.domain.players.health import (
    PlayerHealthProfile,
    PlayerHealthRecord,
    bootstrap_health_state,
    carry_health_state_forward,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import Base
from beta_engine.infrastructure.db.player_health_state import (
    PLAYER_HEALTH_COMPONENT_KEY,
    _component,
    capture_saved_health,
    get_health,
    load_saved_health,
    put_health,
    remap_saved_health_component,
    restore_saved_health,
)

pytestmark = pytest.mark.pr_critical


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'health-v1.db'}")
    )
    Base.metadata.create_all(engine)
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()


def _history(*, branch_id="branch"):
    first = bootstrap_health_state(
        run_id="run",
        branch_id=branch_id,
        source_initial_world_fingerprint="shared-origin-world",
        player_ids=("p1",),
    )
    record = PlayerHealthRecord(
        record_id="r001",
        kind="Injury",
        condition_key="ankle",
        lifecycle="Active",
        severity=40,
        affected_domains=("movement",),
        onset_week=first.week,
        provenance="explicit test health",
    )
    first = first.model_copy(
        update={
            "players": (
                PlayerHealthProfile(player_id="p1", records=(record,)),
            )
        }
    )
    second = carry_health_state_forward(
        first,
        target=RankingWeek(season_index=0, week=2),
        target_player_ids=("p1",),
    )
    return first, second


def test_health_persistence_is_immutable_and_saved_component_round_trips(database):
    first, second = _history()
    with database.begin() as session:
        assert put_health(session, first).fingerprint == first.fingerprint
        assert put_health(session, first).fingerprint == first.fingerprint
        put_health(session, second)

        payload = {"content": {}}
        capture_saved_health(
            session,
            payload,
            run_id="run",
            branch_id="branch",
        )

    component = payload["content"][PLAYER_HEALTH_COMPONENT_KEY]
    assert len(component["states"]) == 2
    loaded = load_saved_health(payload, run_id="run", branch_id="branch")
    assert loaded == (first, second)

    with database() as session:
        assert get_health(
            session,
            run_id="run",
            branch_id="branch",
            week=RankingWeek(season_index=0, week=2),
        ) == second


def test_health_fork_remap_rebuilds_branch_identity_and_predecessor_chain():
    source = _history(branch_id="source")
    payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: _component(source)
        }
    }

    remapped = remap_saved_health_component(
        payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
    )
    assert remapped is not None

    target_payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: remapped
        }
    }
    target = load_saved_health(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert target is not None
    assert [state.branch_id for state in target] == ["target", "target"]
    assert target[0].fingerprint != source[0].fingerprint
    assert target[1].fingerprint != source[1].fingerprint
    assert target[1].predecessor_fingerprint == target[0].fingerprint
    assert (
        target[0].source_initial_world_fingerprint
        == source[0].source_initial_world_fingerprint
    )


def test_health_restore_replaces_live_history_only_when_saved_head_matches(database):
    first, second = _history()
    current_payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: _component((first, second))
        }
    }
    target_payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: _component((first,))
        }
    }
    with database.begin() as session:
        put_health(session, first)
        put_health(session, second)
        restore_saved_health(
            session,
            current_payload=current_payload,
            target_payload=target_payload,
            run_id="run",
            branch_id="branch",
        )

    with database() as session:
        assert get_health(
            session,
            run_id="run",
            branch_id="branch",
            week=first.week,
        ) == first
        assert get_health(
            session,
            run_id="run",
            branch_id="branch",
            week=second.week,
        ) is None


def test_health_restore_fails_closed_when_live_history_differs_from_saved_head(database):
    first, second = _history()
    current_payload = {
        "content": {
            PLAYER_HEALTH_COMPONENT_KEY: _component((first,))
        }
    }
    target_payload = current_payload
    with database.begin() as session:
        put_health(session, first)
        put_health(session, second)
        with pytest.raises(ValueError, match="differs from saved head"):
            restore_saved_health(
                session,
                current_payload=current_payload,
                target_payload=target_payload,
                run_id="run",
                branch_id="branch",
            )
