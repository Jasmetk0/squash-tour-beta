"""Persistence and validation for authoritative ranking boundary inputs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.models import RankingTransitionAuthorityModel


def authority_carried_to_saved_head(session: Session, authority, branch, draft) -> bool:
    """Accept a newer base only when its saved payload carries the exact snapshot."""
    if draft.base_revision_id == authority.base_revision_id:
        return True
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component
    import json

    revision = session.get(BranchSavedRevisionModel, draft.base_revision_id)
    if revision is None or (revision.run_id, revision.branch_id) != (authority.run_id, authority.branch_id):
        return False
    state = load_saved_ranking_component(
        json.loads(revision.payload_json), run_id=authority.run_id, branch_id=authority.branch_id
    )
    return branch.saved_head_revision_id == draft.base_revision_id and state is not None and any(
        a.fingerprint == authority.fingerprint for a in state.transition_authorities
    )


class RankingTransitionAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def get(self, *, run_id: str, branch_id: str, target_ordinal: int):
        row = self.session.get(RankingTransitionAuthorityModel, (run_id, branch_id, target_ordinal))
        if row is None:
            return None
        value = RankingTransitionAuthority.model_validate_json(row.payload_json)
        if (value.run_id, value.branch_id, value.target_week.ordinal, value.fingerprint) != (run_id, branch_id, target_ordinal, row.fingerprint):
            raise ValueError("Ranking transition authority identity or fingerprint mismatch")
        return value

    def append(self, value: RankingTransitionAuthority):
        old = self.get(run_id=value.run_id, branch_id=value.branch_id, target_ordinal=value.target_week.ordinal)
        if old is not None:
            if old.fingerprint != value.fingerprint:
                raise ValueError("Ranking transition authority already exists with different inputs")
            return old
        self.session.add(RankingTransitionAuthorityModel(run_id=value.run_id, branch_id=value.branch_id,
            target_ordinal=value.target_week.ordinal, fingerprint=value.fingerprint, payload_json=value.model_dump_json()))
        self.session.flush()
        return value

    def history(self, *, run_id: str, branch_id: str):
        ordinals = self.session.scalars(select(RankingTransitionAuthorityModel.target_ordinal).where(
            RankingTransitionAuthorityModel.run_id == run_id, RankingTransitionAuthorityModel.branch_id == branch_id
        ).order_by(RankingTransitionAuthorityModel.target_ordinal)).all()
        return tuple(self.get(run_id=run_id, branch_id=branch_id, target_ordinal=o) for o in ordinals)
