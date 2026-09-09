"""Transactional candidate history for future Official Ranking publication.

The caller owns the Session and its commit/rollback. No independent commit,
Viewer publication, week advancement or source resolution happens here.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import (
    OfficialRankingSnapshot,
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.infrastructure.db.models import (
    OfficialRankingCandidateModel,
    RunBranchModel,
    RunContainerModel,
)


class RankingCandidateConflict(ValueError):
    """The requested write does not extend the stored candidate lineage."""


class OfficialRankingCandidateStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False):
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Ranking Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only):
            raise ValueError("Ranking scope is read-only")

    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[OfficialRankingSnapshot, ...]:
        """Read and validate the complete locally stored lineage, oldest first."""
        self._scope(run_id, branch_id)
        records = self.session.scalars(
            select(OfficialRankingCandidateModel)
            .where(
                OfficialRankingCandidateModel.run_id == run_id,
                OfficialRankingCandidateModel.branch_id == branch_id,
            )
            .order_by(OfficialRankingCandidateModel.week_ordinal)
        ).all()
        history = []
        previous = None
        for record in records:
            week = RankingWeek(
                season_index=record.week_ordinal // 61,
                week=record.week_ordinal % 61 + 1,
            )
            snapshot = load_official_ranking_snapshot(
                record.payload_json,
                expected_fingerprint=record.fingerprint,
                run_id=run_id,
                branch_id=branch_id,
                week=week,
            )
            if snapshot.previous_fingerprint != (
                previous.fingerprint if previous else None
            ):
                raise ValueError("Stored ranking lineage fingerprint mismatch")
            if previous and previous.week.ordinal + 1 != snapshot.week.ordinal:
                raise ValueError("Stored ranking lineage has a week gap")
            history.append(snapshot)
            previous = snapshot
        return tuple(history)

    def append(
        self, snapshot: OfficialRankingSnapshot, *, bootstrap: bool = False
    ) -> OfficialRankingSnapshot:
        """Stage a candidate in the caller's transaction; exact retries are reads.

        DB primary-key uniqueness protects competing writes. On a concurrent
        IntegrityError the caller must roll back and retry the whole transaction.
        Bootstrap is an internal explicit intent, not permission to publish.
        Fork ancestry is not imported or fabricated by this local-chain store.
        """
        snapshot = OfficialRankingSnapshot.model_validate_json(
            snapshot.model_dump_json()
        )
        self._scope(snapshot.run_id, snapshot.branch_id, writing=True)
        history = self.history(run_id=snapshot.run_id, branch_id=snapshot.branch_id)
        for existing in history:
            if existing.week == snapshot.week:
                if existing.fingerprint != snapshot.fingerprint:
                    raise RankingCandidateConflict(
                        "Ranking week already has a different candidate"
                    )
                return existing
        if history:
            head = history[-1]
            if (
                bootstrap
                or snapshot.week.ordinal != head.week.ordinal + 1
                or snapshot.previous_fingerprint != head.fingerprint
            ):
                raise RankingCandidateConflict(
                    "Candidate must extend the current ranking head"
                )
        elif not bootstrap or snapshot.previous_fingerprint is not None:
            raise RankingCandidateConflict(
                "Empty history requires explicit parentless bootstrap"
            )
        elif (
            self.session.get(RunBranchModel, snapshot.branch_id).forked_from_branch_id
            is not None
        ):
            raise RankingCandidateConflict(
                "Forked ranking ancestry requires a dedicated adapter"
            )
        self.session.add(
            OfficialRankingCandidateModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                week_ordinal=snapshot.week.ordinal,
                fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        return snapshot
