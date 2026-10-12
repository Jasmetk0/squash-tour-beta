"""Post-ranking selected Add rejection at the real repository/SQLite boundary.

The paired scoped Chromium gate exercises the entire create/save/publish/attempt
flow without mocking, while this cheap test checks raw SQL rollback invariants.
"""
import hashlib
import sqlite3

import pytest

from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel
from tests.api.test_selected_initial_world_append import _prepared, _install, SHA

pytestmark = pytest.mark.pr_critical


def _database_digest(filename):
    """Every persisted SQL row, including old revisions, not only the roster."""
    with sqlite3.connect(filename) as connection:
        return hashlib.sha256(
            "\n".join(connection.iterdump()).encode("utf-8")
        ).hexdigest()


def test_published_initial_ranking_denies_selected_append_without_any_sql_write(
    tmp_path, monkeypatch
):
    repo, run_id, branch_id, initial, source, command, appended, saved = _prepared(
        tmp_path, monkeypatch
    )
    with repo._session_factory.begin() as session:
        session.add(PublishedOfficialRankingModel(
            run_id=run_id, branch_id=branch_id,
            week_ordinal=0, snapshot_fingerprint=SHA, payload_json="{}",
        ))
    filename = tmp_path / "selected-append.sqlite"
    baseline = _database_digest(filename)
    for _ in range(2):
        with pytest.raises(ValueError, match="ranking or sporting activity"):
            _install(repo, run_id, branch_id, initial, appended, saved)
        assert _database_digest(filename) == baseline
        assert repo.get_initial_world(
            run_id=run_id, branch_id=branch_id
        ) == initial
        state = repo.get_branch_revision_state(branch_id=branch_id)
        assert state.saved_revision.revision_id == saved.saved_revision.revision_id


def test_browser_script_has_real_published_ranking_then_commit_409_assertion():
    """Fast CI verifies expensive workflow retains its independent safety gate."""
    from pathlib import Path
    source = (
        Path(__file__).resolve().parents[2] /
        "scripts/admin_selected_append_browser.py"
    ).read_text(encoding="utf-8")
    assert "Publish initial ranking" in source
    assert "Save published ranking revision" in source
    assert 'r.status == 409' in source
    assert "full_database_digest" in source
    assert "post_ranking_sql_digest_unchanged" in source
    assert "post-ranking-append-denied.png" in source


def test_preflight_shared_eligibility_rejects_post_ranking_without_sql_writes(
    tmp_path, monkeypatch
):
    from beta_engine.infrastructure.db.selected_initial_world_append import (
        require_pristine_initial_world_append_eligible,
    )
    repo, run_id, branch_id, initial, _, _, _, _ = _prepared(tmp_path, monkeypatch)
    with repo._session_factory.begin() as session:
        session.add(PublishedOfficialRankingModel(
            run_id=run_id, branch_id=branch_id, week_ordinal=0,
            snapshot_fingerprint=SHA, payload_json="{}",
        ))
    filename = tmp_path / "selected-append.sqlite"
    baseline = _database_digest(filename)
    with repo._session_factory() as session:
        with pytest.raises(ValueError, match="ranking or sporting activity"):
            require_pristine_initial_world_append_eligible(session, previous=initial)
    assert _database_digest(filename) == baseline


def test_preview_and_commit_reference_same_read_only_guard():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    preview = (root / "src/beta_engine/api/routers/admin_players.py").read_text()
    commit = (root / "src/beta_engine/infrastructure/db/selected_initial_world_append.py").read_text()
    assert "require_pristine_initial_world_append_eligible(session, previous=current)" in preview
    assert "require_pristine_initial_world_append_eligible(session, previous=previous)" in commit
    assert "BEGIN IMMEDIATE" in commit
