"""Ranking preparation component embedded in immutable Saved Revision content."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.revision_state import RankingRevisionState, load_ranking_revision_state
from beta_engine.infrastructure.db.models import OfficialRankingCandidateModel, OfficialRankingCommandModel, OfficialRankingResultVersionModel, OfficialRankingZeroVersionModel
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state

RANKING_COMPONENT_KEY = "ranking_preparation"


def load_saved_ranking_component(payload: dict, *, run_id: str, branch_id: str) -> RankingRevisionState | None:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    if RANKING_COMPONENT_KEY not in content:
        return None
    component = content[RANKING_COMPONENT_KEY]
    if not isinstance(component, dict) or set(component) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved Revision ranking component")
    return load_ranking_revision_state(
        json.dumps(component["state"]), expected_fingerprint=component["fingerprint"],
        run_id=run_id, branch_id=branch_id,
    )


def capture_saved_ranking_component(session: Session, payload: dict, *, run_id: str, branch_id: str) -> None:
    """Update a newly constructed payload inside its caller's write transaction."""
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    has_rows = any(session.scalar(select(model.run_id).where(
        model.run_id == run_id, model.branch_id == branch_id,
    ).limit(1)) is not None for model in (
        OfficialRankingCandidateModel, OfficialRankingCommandModel, OfficialRankingResultVersionModel, OfficialRankingZeroVersionModel,
    ))
    # Preserve the exact legacy empty representation, including empty forks.
    if not has_rows and RANKING_COMPONENT_KEY not in content:
        return
    state = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
    content[RANKING_COMPONENT_KEY] = {"fingerprint": state.fingerprint, "state": state.model_dump(mode="json")}


def restore_saved_ranking_component(
    session: Session, *, current_payload: dict, target_payload: dict,
    run_id: str, branch_id: str, command_id: str,
) -> None:
    """Restore only when live preparation still equals the saved head.

    The enclosing Saved Revision transaction owns validation, writer lock and
    commit. Its pre-restore checkpoint references the verified current revision.
    """
    from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state

    empty = RankingRevisionState(run_id=run_id, branch_id=branch_id, entries=(), sources=())
    current = load_saved_ranking_component(current_payload, run_id=run_id, branch_id=branch_id) or empty
    target = load_saved_ranking_component(target_payload, run_id=run_id, branch_id=branch_id) or empty
    restore_ranking_revision_state(
        session, target.model_dump_json(), expected_fingerprint=target.fingerprint,
        expected_current_fingerprint=current.fingerprint, command_id=command_id,
        run_id=run_id, branch_id=branch_id,
    )
