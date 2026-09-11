"""Production Save embeds the complete ranking preparation atomically."""

import json

import pytest
from sqlalchemy import event
from test_saved_revision_restore import _repository, _run_with_saved_viewer_change, _id_factory
from test_saved_revision_ranking_guard import dump

from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.run_branch_creation_service import RunBranchCreationService
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.infrastructure.db import WorkingDraftConflictError, SavedRevisionBranchForkConflictError, SavedRevisionHistoryConflictError
from beta_engine.infrastructure.db.models import BranchRevisionAuditEventModel, BranchSavedRevisionModel, OfficialRankingCandidateModel
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "saved-ranking.db"
    repo = _repository(f"sqlite:///{path}")
    _run_with_saved_viewer_change(repo)
    runner = RankingWeekCommandRunner(repo._session_factory)
    command = RankingBootstrapCommand(command_id="bootstrap", run_id="run-one", branch_id="branch-one",
                                      policy=OfficialRankingPolicy(policy_id="policy"), players=(), discipline="none")
    runner.execute(command)
    service = RunWorkingDraftService(repository=repo, id_factory=_id_factory("revision-three", "audit-two"))
    staged = service.stage_viewer_branch(run_id="run-one", branch_id="branch-one", viewer_branch_id="branch-one", expected_draft_version=2)
    return path, repo, runner, command, service, staged.draft_version


def save(prepared):
    _, _, _, _, service, version = prepared
    return service.save(run_id="run-one", branch_id="branch-one", expected_draft_version=version)


@pytest.mark.smoke
def test_save_captures_frozen_inputs_and_refreshes_without_mutating_history(prepared):
    path, repo, runner, command, _, _ = prepared
    result = save(prepared)
    saved = load_saved_ranking_component(result.saved_revision.payload, run_id="run-one", branch_id="branch-one")
    assert len(saved.entries) == 1
    assert saved.entries[0].receipts[0].command_id == "bootstrap"
    assert repo.verify_branch_saved_revision_hash(revision_id="revision-three")
    before_payload = result.saved_revision.payload
    runner.execute(RankingWeekCommand(command_id="week-2", tournaments=(), context=RankingTransitionContext(
        run_id="run-one", branch_id="branch-one", completed_week=RankingWeek(season_index=0, week=1),
        target_week=RankingWeek(season_index=0, week=2), policy=command.policy, players=(), discipline="none",
    )))
    service = RunWorkingDraftService(repository=repo, id_factory=_id_factory("revision-four", "audit-three"))
    staged = service.stage_viewer_branch(run_id="run-one", branch_id="branch-one", viewer_branch_id="branch-two", expected_draft_version=4)
    latest = service.save(run_id="run-one", branch_id="branch-one", expected_draft_version=staged.draft_version)
    assert len(load_saved_ranking_component(latest.saved_revision.payload, run_id="run-one", branch_id="branch-one").entries) == 2
    reloaded = _repository(f"sqlite:///{path}")
    assert reloaded.get_branch_saved_revision(revision_id="revision-three").payload == before_payload
    assert reloaded.get_branch_saved_revision(revision_id="revision-one").payload["content"] == {}


@pytest.mark.smoke
def test_failed_save_rolls_back_revision_draft_viewer_and_audit(prepared):
    path, repo, *_ = prepared
    before = dump(path)
    def fail(*args):
        raise RuntimeError("audit failure")
    event.listen(BranchRevisionAuditEventModel, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="audit failure"):
            save(prepared)
    finally:
        event.remove(BranchRevisionAuditEventModel, "before_insert", fail)
    assert dump(path) == before


def test_malformed_live_ranking_blocks_save_without_changes(prepared):
    path, repo, *_ = prepared
    with repo._session_factory.begin() as session:
        session.get(OfficialRankingCandidateModel, ("run-one", "branch-one", 0)).payload_json = "broken"
    before = dump(path)
    with pytest.raises(WorkingDraftConflictError, match="ranking"):
        save(prepared)
    assert dump(path) == before


def test_fork_of_ranking_revision_is_rejected_until_identity_remapping(prepared):
    path, repo, *_ = prepared
    save(prepared)
    before = dump(path)
    with pytest.raises(SavedRevisionBranchForkConflictError, match="remapping"):
        RunBranchCreationService(repository=repo, id_factory=_id_factory("branch-three", "draft-three")).create_from_saved_revision(
            run_id="run-one", source_branch_id="branch-one", source_saved_revision_id="revision-three",
        )
    assert dump(path) == before


@pytest.mark.parametrize("damage", ["hash", "scope", "shape"])
def test_history_rejects_invalid_embedded_ranking(prepared, damage):
    _, repo, *_ = prepared
    save(prepared)
    with repo._session_factory.begin() as session:
        model = session.get(BranchSavedRevisionModel, "revision-three")
        payload = json.loads(model.payload_json)
        component = payload["content"]["ranking_preparation"]
        if damage == "hash":
            component["fingerprint"] = "0" * 64
        elif damage == "scope":
            component["state"]["branch_id"] = "branch-two"
        else:
            component["extra"] = True
        model.payload_json = json.dumps(payload)
    with pytest.raises(SavedRevisionHistoryConflictError, match="ranking content"):
        repo.get_branch_saved_revision_history(run_id="run-one", branch_id="branch-one")
