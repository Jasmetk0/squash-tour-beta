"""Saved Revision recovery coordinates ranking, history, draft and Viewer."""

import pytest
from sqlalchemy import event, text
from test_saved_revision_restore import _id_factory, _repository
from test_saved_revision_ranking_capture import prepared, save  # noqa: F401
from test_saved_revision_ranking_guard import dump

from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_saved_revision_restore_service import RunSavedRevisionRestoreService
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db import SavedRevisionRestoreUnsupportedError
from beta_engine.infrastructure.db.models import BranchRevisionAuditEventModel, OfficialRankingCommandModel, RankingRestoreCheckpointModel
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state


def advance(prepared):
    _, _, runner, command, *_ = prepared
    runner.execute(RankingWeekCommand(command_id="week-2", tournaments=(), context=RankingTransitionContext(
        run_id="run-one", branch_id="branch-one", completed_week=RankingWeek(season_index=0, week=1),
        target_week=RankingWeek(season_index=0, week=2), policy=command.policy, players=(), discipline="none",
    )))


def save_second(prepared):
    _, repo, *_ = prepared
    advance(prepared)
    service = RunWorkingDraftService(repository=repo, id_factory=_id_factory("revision-four", "audit-three"))
    staged = service.stage_viewer_branch(run_id="run-one", branch_id="branch-one", viewer_branch_id="branch-two", expected_draft_version=4)
    return service.save(run_id="run-one", branch_id="branch-one", expected_draft_version=staged.draft_version)


def restore(repo, target, head="revision-four", version=6, viewer="branch-two", suffix="one"):
    return RunSavedRevisionRestoreService(repository=repo, id_factory=_id_factory(
        f"recovery-checkpoint-{suffix}", f"recovery-revision-{suffix}", f"recovery-audit-{suffix}",
    )).restore_current_branch(
        run_id="run-one", branch_id="branch-one", target_saved_revision_id=target,
        expected_head_saved_revision_id=head, expected_draft_version=version,
        expected_current_viewer_branch_id=viewer, explicit_confirmation=True,
    )


def capture(repo):
    with repo._session_factory.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        return capture_ranking_revision_state(session, run_id="run-one", branch_id="branch-one")


@pytest.mark.smoke
@pytest.mark.parametrize("target, count", [("revision-one", 0), ("revision-three", 1)])
def test_restore_to_empty_or_older_ranking_and_restore_forward_again(prepared, target, count):
    path, repo, *_ = prepared
    save(prepared)
    saved_second = save_second(prepared)
    before = capture(repo)
    result = restore(repo, target)
    assert len(capture(repo).entries) == count
    assert result.saved_revision.parent_revision_id == "revision-four"
    assert result.safety_checkpoint.saved_revision_id == "revision-four"
    assert result.viewer_branch_id == "branch-one"
    assert result.working_draft.base_saved_revision_id == result.saved_revision.revision_id
    assert repo.get_branch_saved_revision(revision_id="revision-four").payload == saved_second.saved_revision.payload
    with repo._session_factory() as session:
        checkpoint = session.get(RankingRestoreCheckpointModel, ("run-one", "branch-one", result.saved_revision.revision_id))
        assert checkpoint.before_fingerprint == before.fingerprint
        assert checkpoint.target_fingerprint == capture(repo).fingerprint
    reopened = _repository(f"sqlite:///{path}")
    restore(reopened, "revision-four", head=result.saved_revision.revision_id, version=7, viewer="branch-one", suffix="two")
    assert capture(reopened) == before
    assert len(reopened.get_branch_saved_revision_history(run_id="run-one", branch_id="branch-one").saved_revisions) == 6


@pytest.mark.smoke
def test_unsaved_ranking_changes_reject_restore_without_database_changes(prepared):
    path, repo, *_ = prepared
    save(prepared)
    advance(prepared)
    before = dump(path)
    with pytest.raises(SavedRevisionRestoreUnsupportedError, match="stale"):
        restore(repo, "revision-one", head="revision-three", version=4, viewer="branch-one")
    assert dump(path) == before


@pytest.mark.smoke
@pytest.mark.parametrize("failed_model", [BranchRevisionAuditEventModel, OfficialRankingCommandModel])
def test_restore_failure_rolls_back_all_world_and_ranking_writes(prepared, failed_model):
    path, repo, *_ = prepared
    save(prepared)
    save_second(prepared)
    before = dump(path)
    def fail(*args):
        raise RuntimeError("recovery write failed")
    event.listen(failed_model, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="recovery write failed"):
            restore(repo, "revision-three")
    finally:
        event.remove(failed_model, "before_insert", fail)
    assert dump(path) == before


@pytest.mark.smoke
def test_saved_future_zero_history_restores_and_unsaved_correction_blocks(prepared):
    from beta_engine.domain.rankings.official import DisciplinaryZero
    from beta_engine.domain.rankings.zero_history import RankingZeroVersion
    from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore
    path, repo, *_ = prepared
    first = RankingZeroVersion(effective_week=RankingWeek(season_index=0, week=2), previous_fingerprint=None,
        zero=DisciplinaryZero(zero_id='zero', run_id='run-one', branch_id='branch-one', player_id='future-player',
            source_fingerprint='decision', effective_week=RankingWeek(season_index=0, week=2), duration_weeks=3))
    with repo._session_factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        OfficialRankingZeroStore(session).append(first)
    save(prepared)
    before = capture(repo)
    assert before.zero_sources == (first,)
    result = restore(repo, 'revision-one', head='revision-three', version=4, viewer='branch-one')
    assert capture(repo).zero_sources == ()
    reopened = _repository(f'sqlite:///{path}')
    restored = restore(reopened, 'revision-three', head=result.saved_revision.revision_id, version=5,
                       viewer='branch-one', suffix='forward-zeros')
    assert capture(reopened) == before
    correction = RankingZeroVersion(effective_week=RankingWeek(season_index=0, week=3), previous_fingerprint=first.fingerprint,
        zero=first.zero.model_copy(update={'duration_weeks': 1, 'source_fingerprint': 'correction'}))
    with reopened._session_factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        OfficialRankingZeroStore(session).append(correction)
    unsaved = dump(path)
    with pytest.raises(SavedRevisionRestoreUnsupportedError, match='stale'):
        restore(reopened, 'revision-one', head=restored.saved_revision.revision_id, version=6,
                viewer='branch-one', suffix='unsaved-zero')
    assert dump(path) == unsaved
