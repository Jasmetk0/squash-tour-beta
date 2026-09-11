"""Guarded ranking-only replacement inside a larger recovery transaction."""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.revision_state import RankingRevisionState, load_ranking_revision_state
from beta_engine.infrastructure.db.models import (
    OfficialRankingCandidateModel, OfficialRankingCommandModel,
    OfficialRankingResultVersionModel, RankingRestoreCheckpointModel,
    RunBranchModel, RunContainerModel,
)
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state, install_ranking_revision_state


def restore_ranking_revision_state(
    session: Session, payload: str, *, expected_fingerprint: str,
    expected_current_fingerprint: str, command_id: str, run_id: str, branch_id: str,
) -> RankingRevisionState:
    """Restore a verified same-scope state, retaining the exact predecessor.

    Caller acquires BEGIN IMMEDIATE before recovery reads and commits all world
    components together. A savepoint prevents partial replacement on caught errors.
    This neither selects Viewer nor advances the simulation clock.
    """
    if not isinstance(command_id, str) or not command_id.strip() or len(command_id) > 128:
        raise ValueError("Ranking restore requires a valid command ID")
    target = load_ranking_revision_state(payload, expected_fingerprint=expected_fingerprint, run_id=run_id, branch_id=branch_id)
    current = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
    key = (run_id, branch_id, command_id)
    checkpoint = session.get(RankingRestoreCheckpointModel, key)
    if checkpoint is not None:
        if (checkpoint.before_fingerprint, checkpoint.target_fingerprint) != (expected_current_fingerprint, expected_fingerprint):
            raise ValueError("Ranking restore command ID already has a different request")
        load_ranking_revision_state(checkpoint.before_payload_json, expected_fingerprint=checkpoint.before_fingerprint, run_id=run_id, branch_id=branch_id)
        if current.fingerprint != target.fingerprint:
            raise ValueError("Ranking state changed after this restore; retry cannot overwrite it")
        return current
    if current.fingerprint != expected_current_fingerprint:
        raise ValueError("Ranking restore expected current state is stale")
    if session.get(RunContainerModel, run_id).read_only or session.get(RunBranchModel, branch_id).read_only:
        raise ValueError("Ranking restore target is read-only")
    with session.begin_nested():
        session.add(RankingRestoreCheckpointModel(
            run_id=run_id, branch_id=branch_id, command_id=command_id,
            before_fingerprint=current.fingerprint, before_payload_json=current.model_dump_json(),
            target_fingerprint=target.fingerprint,
        ))
        session.flush()
        for model in (OfficialRankingCommandModel, OfficialRankingCandidateModel, OfficialRankingResultVersionModel):
            session.execute(delete(model).where(model.run_id == run_id, model.branch_id == branch_id))
        return install_ranking_revision_state(session, payload, expected_fingerprint=target.fingerprint, run_id=run_id, branch_id=branch_id)
