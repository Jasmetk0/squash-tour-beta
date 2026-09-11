"""Atomic guarded replacement of real SQLite ranking history."""

import pytest
from sqlalchemy import event, select, text
from test_official_ranking_storage import database  # noqa: F401
from test_ranking_revision_state import captured  # noqa: F401
from test_ranking_bootstrap_command import command

from beta_engine.domain.rankings.revision_state import RankingRevisionState, load_ranking_revision_state
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel, RankingRestoreCheckpointModel, RunBranchModel
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state
from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


def initial(state):
    return RankingRevisionState(run_id=state.run_id, branch_id=state.branch_id, entries=state.entries[:1], sources=())


def capture(session, branch="branch"):
    return capture_ranking_revision_state(session, run_id="run", branch_id=branch)


def restore(session, before, target=None, **kwargs):
    target = initial(before) if target is None else target
    args = dict(expected_fingerprint=target.fingerprint, expected_current_fingerprint=before.fingerprint,
                command_id="restore-1", run_id="run", branch_id="branch")
    args.update(kwargs)
    return restore_ranking_revision_state(session, target.model_dump_json(), **args)


@pytest.mark.smoke
def test_restore_preserves_predecessor_other_branch_and_replay(database, captured):
    RankingWeekCommandRunner(database).execute(command().model_copy(update={"branch_id": "other"}))
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        other = capture(session, "other")
        assert restore(session, captured) == initial(captured)
        assert capture(session) == initial(captured)
        assert capture(session, "other") == other
        checkpoint = session.get(RankingRestoreCheckpointModel, ("run", "branch", "restore-1"))
        assert load_ranking_revision_state(checkpoint.before_payload_json, expected_fingerprint=checkpoint.before_fingerprint,
                                          run_id="run", branch_id="branch") == captured
    assert RankingWeekCommandRunner(database).execute(command()) == captured.entries[0].snapshot
    with database.begin() as session:
        session.get(RunBranchModel, "branch").read_only = True
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert restore(session, captured) == initial(captured)
        assert len(session.scalars(select(RankingRestoreCheckpointModel)).all()) == 1
        assert not session.new and not session.dirty and not session.deleted


@pytest.mark.smoke
def test_caught_install_failure_restores_deleted_history_and_checkpoint(database, captured):
    def fail(*args):
        raise RuntimeError("receipt failure")
    event.listen(OfficialRankingCommandModel, "before_insert", fail)
    try:
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            session.get(RunBranchModel, "branch").display_name = "Outer change"
            with pytest.raises(RuntimeError, match="receipt failure"):
                restore(session, captured)
            assert capture(session) == captured
            assert session.scalars(select(RankingRestoreCheckpointModel)).all() == []
    finally:
        event.remove(OfficialRankingCommandModel, "before_insert", fail)
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert capture(session) == captured
        assert session.get(RunBranchModel, "branch").display_name == "Outer change"


@pytest.mark.smoke
def test_outer_rollback_restores_history_and_removes_checkpoint(database, captured):
    with pytest.raises(RuntimeError):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            restore(session, captured)
            raise RuntimeError("world restore failed")
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert capture(session) == captured
        assert session.scalars(select(RankingRestoreCheckpointModel)).all() == []


@pytest.mark.parametrize("damage", ["stale", "hash", "scope", "readonly", "transaction", "command"])
def test_invalid_restore_leaves_history_intact(database, captured, damage):
    if damage == "readonly":
        with database.begin() as session:
            session.get(RunBranchModel, "branch").read_only = True
    overrides = {"stale": {"expected_current_fingerprint": "0" * 64}, "hash": {"expected_fingerprint": "0" * 64},
                 "scope": {"branch_id": "other"}, "command": {"command_id": " "}}.get(damage, {})
    with database.begin() as session:
        if damage != "transaction":
            session.execute(text("BEGIN IMMEDIATE"))
        with pytest.raises(ValueError):
            restore(session, captured, **overrides)
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert capture(session) == captured
        assert session.scalars(select(RankingRestoreCheckpointModel)).all() == []


@pytest.mark.parametrize("change", ["target", "before", "later_state", "checkpoint"])
def test_retry_rejects_conflicts_without_overwriting(database, captured, change):
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        restore(session, captured)
        if change == "later_state":
            restore(session, initial(captured), captured, command_id="restore-2")
        if change == "checkpoint":
            session.get(RankingRestoreCheckpointModel, ("run", "branch", "restore-1")).before_payload_json = "{}"
            session.flush()
        before = capture(session)
        with pytest.raises(ValueError):
            restore(session, captured, captured if change == "target" else None,
                    **({"expected_current_fingerprint": "0" * 64} if change == "before" else {}))
        assert capture(session) == before
