import pytest
from sqlalchemy import event
from test_saved_revision_restore import _repository, _run_with_saved_viewer_change, _id_factory
from test_saved_revision_ranking_guard import dump
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.infrastructure.db import WorkingDraftConflictError
from beta_engine.infrastructure.db.models import BranchRevisionAuditEventModel, RunContainerModel
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


@pytest.fixture
def ready(tmp_path):
    path = tmp_path / 'independent-save.db'
    repo = _repository(f'sqlite:///{path}')
    _run_with_saved_viewer_change(repo)
    RankingWeekCommandRunner(repo._session_factory).execute(RankingBootstrapCommand(
        command_id='bootstrap', run_id='run-one', branch_id='branch-one',
        policy=OfficialRankingPolicy(policy_id='policy'), players=(), discipline='none',
    ))
    return path, repo


def save(repo, preview):
    return RunWorkingDraftService(repository=repo, id_factory=_id_factory('ranking-revision', 'ranking-audit')).save_ranking(
        run_id='run-one', branch_id='branch-one', expected_draft_version=preview['draft_version'],
        expected_ranking_fingerprint=preview['ranking_fingerprint'],
    )


@pytest.mark.smoke
def test_save_from_clean_draft_preserves_current_viewer_and_is_recoverable(ready):
    path, repo = ready
    # Another saved selection may differ from this branch's older saved payload.
    with repo._session_factory.begin() as session:
        session.get(RunContainerModel, 'run-one').official_branch_id = 'branch-one'
    before = dump(path)
    preview = repo.preview_ranking_save(run_id='run-one', branch_id='branch-one')
    assert preview['can_save'] and preview['has_unsaved_changes']
    assert dump(path) == before
    result = save(repo, preview)
    assert result.saved_revision.kind == 'ranking_preparation'
    assert result.saved_revision.payload['content']['ranking_preparation']['fingerprint'] == preview['ranking_fingerprint']
    assert result.saved_revision.payload['run']['viewer_branch_id'] == 'branch-one'
    assert repo.get_run_container(run_id='run-one').viewer_branch_id == 'branch-one'
    assert repo.verify_branch_saved_revision_hash(revision_id='ranking-revision')
    assert result.working_draft.status == 'clean'
    latest = repo.preview_ranking_save(run_id='run-one', branch_id='branch-one')
    assert not latest['can_save'] and not latest['has_unsaved_changes']


@pytest.mark.parametrize('damage', ['fingerprint', 'version', 'dirty', 'readonly'])
def test_save_guards_leave_entire_database_unchanged(ready, damage):
    path, repo = ready
    preview = repo.preview_ranking_save(run_id='run-one', branch_id='branch-one')
    if damage == 'fingerprint': preview['ranking_fingerprint'] = '0' * 64
    if damage == 'version': preview['draft_version'] = 0
    if damage == 'dirty':
        repo.stage_viewer_branch_selection(run_id='run-one', branch_id='branch-one', viewer_branch_id='branch-one', expected_draft_version=2)
        preview['draft_version'] = 3
    if damage == 'readonly':
        with repo._session_factory.begin() as session:
            session.get(RunContainerModel, 'run-one').read_only = True
    before = dump(path)
    with pytest.raises(WorkingDraftConflictError): save(repo, preview)
    assert dump(path) == before


@pytest.mark.smoke
def test_audit_failure_rolls_back_ranking_revision_and_draft(ready):
    path, repo = ready
    preview = repo.preview_ranking_save(run_id='run-one', branch_id='branch-one')
    before = dump(path)
    def fail(*args): raise RuntimeError('audit failed')
    event.listen(BranchRevisionAuditEventModel, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError): save(repo, preview)
    finally: event.remove(BranchRevisionAuditEventModel, 'before_insert', fail)
    assert dump(path) == before
