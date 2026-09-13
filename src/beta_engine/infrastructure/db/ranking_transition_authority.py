"""Persistence and validation for authoritative ranking boundary inputs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.infrastructure.db.models import RankingTransitionAuthorityModel


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
