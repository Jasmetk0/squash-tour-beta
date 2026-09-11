"""Ranking preparation component embedded in immutable Saved Revision content."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.revision_state import RankingRevisionState, load_ranking_revision_state
from beta_engine.infrastructure.db.models import OfficialRankingCandidateModel, OfficialRankingCommandModel, OfficialRankingResultVersionModel
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
        OfficialRankingCandidateModel, OfficialRankingCommandModel, OfficialRankingResultVersionModel,
    ))
    # Preserve the exact legacy empty representation, including empty forks.
    if not has_rows and RANKING_COMPONENT_KEY not in content:
        return
    state = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
    content[RANKING_COMPONENT_KEY] = {"fingerprint": state.fingerprint, "state": state.model_dump(mode="json")}
