"""Persistence for immutable Run/Branch-owned tournament source snapshots."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.infrastructure.db.models import OwnedTournamentRankingSourceModel


class OwnedTournamentRankingSourceStore:
    def __init__(self, session: Session):
        self.session = session

    def get(self, *, run_id: str, branch_id: str, edition_id: str):
        row = self.session.get(OwnedTournamentRankingSourceModel, (run_id, branch_id, edition_id))
        if row is None:
            return None
        source = OwnedTournamentRankingSource.model_validate_json(row.payload_json)
        if ((source.binding.run_id, source.binding.branch_id, source.binding.edition_id)
                != (run_id, branch_id, edition_id) or source.binding.event_id != row.event_id
                or source.fingerprint != row.source_fingerprint):
            raise ValueError("Owned tournament source identity or fingerprint mismatch")
        return source

    def append(self, source: OwnedTournamentRankingSource):
        binding = source.binding
        existing = self.get(run_id=binding.run_id, branch_id=binding.branch_id, edition_id=binding.edition_id)
        if existing is not None:
            if existing.fingerprint != source.fingerprint:
                raise ValueError("Conflicting owned tournament source")
            return existing
        self.session.add(OwnedTournamentRankingSourceModel(
            run_id=binding.run_id, branch_id=binding.branch_id, edition_id=binding.edition_id,
            event_id=binding.event_id, source_fingerprint=source.fingerprint,
            adopted_by_command_id=source.adopted_by_command_id, payload_json=source.model_dump_json(),
        ))
        self.session.flush()
        return source

    def history(self, *, run_id: str, branch_id: str):
        ids = self.session.scalars(select(OwnedTournamentRankingSourceModel.edition_id).where(
            OwnedTournamentRankingSourceModel.run_id == run_id,
            OwnedTournamentRankingSourceModel.branch_id == branch_id,
        ).order_by(OwnedTournamentRankingSourceModel.edition_id)).all()
        return tuple(self.get(run_id=run_id, branch_id=branch_id, edition_id=value) for value in ids)
