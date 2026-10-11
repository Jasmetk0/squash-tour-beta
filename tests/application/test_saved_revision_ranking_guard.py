"""Saved Revision restore must not report success while leaving ranking behind."""

import sqlite3

import pytest
from sqlalchemy import event
from test_saved_revision_restore import _repository, _run_with_saved_viewer_change, _id_factory

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_saved_revision_restore_service import RunSavedRevisionRestoreService
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db import SavedRevisionRestoreUnsupportedError
from beta_engine.infrastructure.db.models import (
    OfficialRankingCandidateModel, OfficialRankingCommandModel, OfficialRankingResultVersionModel, OfficialRankingZeroVersionModel,
)
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


def restore(repository):
    return RunSavedRevisionRestoreService(
        repository=repository, id_factory=_id_factory("checkpoint-new", "revision-new", "audit-new"),
    ).restore_current_branch(
        run_id="run-one", branch_id="branch-one", target_saved_revision_id="revision-one",
        expected_head_saved_revision_id="revision-two", expected_draft_version=2,
        expected_current_viewer_branch_id="branch-two", explicit_confirmation=True,
    )


def dump(path):
    with sqlite3.connect(path) as connection:
        return tuple(connection.iterdump())


@pytest.mark.smoke
def test_valid_prepared_ranking_blocks_restore_without_any_database_changes(tmp_path):
    path = tmp_path / "ranking-restore.db"
    repository = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repository)
    RankingWeekCommandRunner(repository._session_factory).execute(RankingBootstrapCommand(
        command_id="bootstrap", run_id="run-one", branch_id="branch-one",
        policy=OfficialRankingPolicy(policy_id="policy"), players=(), discipline="none",
    ))
    before = dump(path)
    with pytest.raises(SavedRevisionRestoreUnsupportedError, match="ranking preparation"):
        restore(repository)
    assert dump(path) == before


@pytest.mark.parametrize("kind", ["candidate", "receipt", "source", "zero_source"])
@pytest.mark.parametrize("scope", ["current", "other_branch", "other_run"])
def test_partial_ranking_rows_are_blocking_only_in_restored_scope(tmp_path, kind, scope):
    path = tmp_path / "ranking-fragment.db"
    repository = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repository)
    # Deliberately malformed fragments: a presence guard must not depend on parsing.
    values = dict(run_id="other-run" if scope == "other_run" else "run-one",
                  branch_id="branch-two" if scope == "other_branch" else "branch-one")
    if kind == "candidate":
        row = OfficialRankingCandidateModel(**values, week_ordinal=0, fingerprint="0" * 64, payload_json="broken")
    elif kind == "receipt":
        row = OfficialRankingCommandModel(**values, command_id="orphan", request_fingerprint="0" * 64,
                                          target_ordinal=0, snapshot_fingerprint="0" * 64)
    elif kind == "zero_source":
        row = OfficialRankingZeroVersionModel(**values, zero_id="zero", effective_ordinal=1,
                                              fingerprint="0" * 64, payload_json="broken")
    else:
        row = OfficialRankingResultVersionModel(**values, edition_id="edition", player_id="player",
                                                effective_ordinal=1, fingerprint="0" * 64, payload_json="broken")
    with repository._session_factory.begin() as session:
        session.add(row)
    before = dump(path)
    if scope == "current":
        with pytest.raises(SavedRevisionRestoreUnsupportedError, match="ranking preparation"):
            restore(repository)
        assert dump(path) == before
    else:
        assert restore(repository).saved_revision.revision_id == "revision-new"
        with repository._session_factory() as session:
            assert session.query(type(row)).count() == 1


@pytest.mark.smoke
def test_restore_reserves_writer_before_first_state_read(tmp_path):
    path = tmp_path / "restore-lock.db"
    repository = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repository)
    checked = []

    def try_competing_write(conn, cursor, statement, parameters, context, executemany):
        if checked or not statement.lstrip().upper().startswith("SELECT"):
            return
        checked.append(True)
        with sqlite3.connect(path, timeout=0) as competing:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                competing.execute("UPDATE runs SET display_name = 'Concurrent mutation' WHERE run_id = 'run-one'")

    event.listen(repository._engine, "before_cursor_execute", try_competing_write)
    try:
        assert restore(repository).saved_revision.revision_id == "revision-new"
    finally:
        event.remove(repository._engine, "before_cursor_execute", try_competing_write)
    assert checked == [True]
