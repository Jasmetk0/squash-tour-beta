"""Real SQLite installation into an isolated empty ranking subsystem."""

import pytest
from sqlalchemy import delete, event, select, text
from test_official_ranking_storage import database  # noqa: F401
from test_ranking_revision_state import captured  # noqa: F401
from test_ranking_bootstrap_command import command

from beta_engine.infrastructure.db.models import (
    OfficialRankingCandidateModel, OfficialRankingCommandModel,
    OfficialRankingResultVersionModel, RunBranchModel,
)
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state, install_ranking_revision_state
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


@pytest.fixture
def empty_target(database, captured):
    # Simulate a new target subsystem while retaining its existing Run/Branch.
    with database.begin() as session:
        for model in (OfficialRankingCommandModel, OfficialRankingCandidateModel, OfficialRankingResultVersionModel):
            session.execute(delete(model))
    return captured


def install(session, state):
    return install_ranking_revision_state(session, state.model_dump_json(), expected_fingerprint=state.fingerprint, run_id="run", branch_id="branch")


def assert_empty(session):
    for model in (OfficialRankingCommandModel, OfficialRankingCandidateModel, OfficialRankingResultVersionModel):
        assert session.scalars(select(model)).all() == []


@pytest.mark.smoke
def test_install_recapture_retry_and_original_command_replay(database, empty_target):
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert install(session, empty_target) == empty_target
        assert install(session, empty_target) == empty_target
    assert RankingWeekCommandRunner(database).execute(command()) == empty_target.entries[0].snapshot
    with database.begin() as session:
        session.get(RunBranchModel, "branch").read_only = True
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        assert install(session, empty_target) == empty_target
        assert not session.new and not session.dirty and not session.deleted


@pytest.mark.smoke
def test_later_restore_failure_rolls_back_installed_ranking(database, empty_target):
    with pytest.raises(RuntimeError):
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            install(session, empty_target)
            raise RuntimeError("later world component failed")
    with database() as session:
        assert_empty(session)


@pytest.mark.smoke
def test_caught_receipt_failure_rolls_back_all_install_writes(database, empty_target):
    def fail(*args):
        raise RuntimeError("receipt failure")
    event.listen(OfficialRankingCommandModel, "before_insert", fail)
    try:
        with database.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            session.get(RunBranchModel, "branch").display_name = "Outer change"
            with pytest.raises(RuntimeError, match="receipt failure"):
                install(session, empty_target)
            assert_empty(session)
    finally:
        event.remove(OfficialRankingCommandModel, "before_insert", fail)
    with database() as session:
        assert_empty(session)
        assert session.get(RunBranchModel, "branch").display_name == "Outer change"


def test_different_existing_history_is_not_replaced(database, empty_target):
    RankingWeekCommandRunner(database).execute(command())
    with database.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        before = capture_ranking_revision_state(session, run_id="run", branch_id="branch")
        with pytest.raises(ValueError, match="not empty"):
            install(session, empty_target)
        assert capture_ranking_revision_state(session, run_id="run", branch_id="branch") == before


@pytest.mark.parametrize("damage", ["hash", "scope", "readonly", "transaction"])
def test_install_rejects_invalid_target_without_writes(database, empty_target, damage):
    if damage == "readonly":
        with database.begin() as session:
            session.get(RunBranchModel, "branch").read_only = True
    with database.begin() as session:
        if damage != "transaction":
            session.execute(text("BEGIN IMMEDIATE"))
        with pytest.raises(ValueError):
            install_ranking_revision_state(
                session, empty_target.model_dump_json(),
                expected_fingerprint="0" * 64 if damage == "hash" else empty_target.fingerprint,
                run_id="run", branch_id="other" if damage == "scope" else "branch",
            )
    with database() as session:
        assert_empty(session)
