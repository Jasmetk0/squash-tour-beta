from __future__ import annotations

import json

import pytest

from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.player_lifecycle_state import (
    PLAYER_LIFECYCLE_COMPONENT_KEY,
    load_saved_lifecycle,
    remap_saved_lifecycle_component,
)

pytestmark = pytest.mark.pr_critical


def _source_payload():
    first = PlayerLifecycleWeekState(
        run_id="run",
        branch_id="source",
        week=RankingWeek(season_index=0, week=1),
        players=(),
        source_initial_world_fingerprint="shared-origin-world",
    )
    second = PlayerLifecycleWeekState(
        run_id="run",
        branch_id="source",
        week=RankingWeek(season_index=0, week=2),
        players=(),
        source_initial_world_fingerprint="shared-origin-world",
        predecessor_fingerprint=first.fingerprint,
    )
    body = [first.model_dump(mode="json"), second.model_dump(mode="json")]
    import hashlib
    fingerprint = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "content": {
            PLAYER_LIFECYCLE_COMPONENT_KEY: {
                "fingerprint": fingerprint,
                "states": body,
            }
        }
    }, (first, second)


def test_saved_lifecycle_chain_rebinds_branch_and_predecessor_identity():
    payload, source = _source_payload()

    component = remap_saved_lifecycle_component(
        payload,
        run_id="run",
        source_branch_id="source",
        target_branch_id="target",
    )

    assert component is not None
    target_payload = {"content": {PLAYER_LIFECYCLE_COMPONENT_KEY: component}}
    target = load_saved_lifecycle(
        target_payload,
        run_id="run",
        branch_id="target",
    )
    assert target is not None
    assert [state.branch_id for state in target] == ["target", "target"]
    assert target[0].predecessor_fingerprint is None
    assert target[1].predecessor_fingerprint == target[0].fingerprint
    assert target[0].fingerprint != source[0].fingerprint
    assert target[1].fingerprint != source[1].fingerprint
    assert [state.players for state in target] == [state.players for state in source]
    assert [state.policy for state in target] == [state.policy for state in source]
    assert all(
        state.source_initial_world_fingerprint == "shared-origin-world"
        for state in target
    )


def test_saved_lifecycle_remap_rejects_wrong_source_scope():
    payload, _ = _source_payload()

    with pytest.raises(ValueError, match="identity or fingerprint mismatch"):
        remap_saved_lifecycle_component(
            payload,
            run_id="run",
            source_branch_id="other",
            target_branch_id="target",
        )


def test_restore_retains_exact_lifecycle_prefix_and_rebuilds_the_tail(tmp_path):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import DatabaseSettings, create_session_factory, create_sqlite_engine
    from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel
    from beta_engine.infrastructure.db.player_lifecycle_state import (
        capture_saved_lifecycle, get_lifecycle, put_lifecycle, restore_saved_lifecycle,
    )

    later, (first, second) = _source_payload()
    earlier = {"content": {}}
    engine = create_sqlite_engine(DatabaseSettings(url=f"sqlite:///{tmp_path / 'lifecycle.sqlite'}"))
    PlayerLifecycleWeekStateModel.__table__.create(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        put_lifecycle(session, first)
        capture_saved_lifecycle(session, earlier, run_id="run", branch_id="source")
        put_lifecycle(session, second)
        session.execute(text("""
            CREATE TRIGGER keep_first_week
            BEFORE DELETE ON player_lifecycle_week_states
            WHEN OLD.run_id = 'run' AND OLD.branch_id = 'source' AND OLD.week_ordinal = 0
            BEGIN
                SELECT RAISE(ABORT, 'unchanged lifecycle row was rewritten');
            END
        """))
    with factory.begin() as session:
        restore_saved_lifecycle(session, current_payload=later, target_payload=earlier,
                                run_id="run", branch_id="source")
        assert get_lifecycle(session, run_id="run", branch_id="source", week=first.week) == first
        assert get_lifecycle(session, run_id="run", branch_id="source", week=second.week) is None
        restore_saved_lifecycle(session, current_payload=earlier, target_payload=later,
                                run_id="run", branch_id="source")
        assert get_lifecycle(session, run_id="run", branch_id="source", week=second.week) == second
    engine.dispose()
