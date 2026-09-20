"""Append-only persistence for archived Season Closing Rankings."""

from sqlalchemy.orm import Session

from beta_engine.domain.rankings.season_closing import SeasonClosingRankingSnapshot
from beta_engine.infrastructure.db.models import (
    RunBranchModel,
    RunContainerModel,
    SeasonClosingRankingModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore


class SeasonClosingRankingConflict(ValueError):
    """A season already has different archived closing-ranking evidence."""


class SeasonClosingRankingStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False):
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Season Closing Ranking Run/Branch scope does not exist")
        if writing and (
            run.read_only
            or branch.read_only
            or branch.status != "active"
        ):
            raise ValueError(
                "Season Closing Ranking requires a writable active Run/Branch"
            )

    @staticmethod
    def _load(
        record: SeasonClosingRankingModel,
        *,
        run_id: str,
        branch_id: str,
        season_index: int,
    ) -> SeasonClosingRankingSnapshot:
        snapshot = SeasonClosingRankingSnapshot.model_validate_json(
            record.payload_json
        )
        if (
            snapshot.run_id,
            snapshot.branch_id,
            snapshot.completed_week.season_index,
            snapshot.completed_week.ordinal,
            snapshot.fingerprint,
        ) != (
            run_id,
            branch_id,
            season_index,
            record.completed_ordinal,
            record.fingerprint,
        ):
            raise ValueError(
                "Stored Season Closing Ranking identity or fingerprint mismatch"
            )
        return snapshot

    def get(
        self, *, run_id: str, branch_id: str, season_index: int
    ) -> SeasonClosingRankingSnapshot | None:
        self._scope(run_id, branch_id)
        record = self.session.get(
            SeasonClosingRankingModel,
            (run_id, branch_id, season_index),
        )
        return (
            None
            if record is None
            else self._load(
                record,
                run_id=run_id,
                branch_id=branch_id,
                season_index=season_index,
            )
        )

    def append(
        self, snapshot: SeasonClosingRankingSnapshot
    ) -> SeasonClosingRankingSnapshot:
        snapshot = SeasonClosingRankingSnapshot.model_validate_json(
            snapshot.model_dump_json()
        )
        self._scope(snapshot.run_id, snapshot.branch_id, writing=True)
        season_index = snapshot.completed_week.season_index

        existing = self.get(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=season_index,
        )
        if existing is not None:
            if existing.fingerprint != snapshot.fingerprint:
                raise SeasonClosingRankingConflict(
                    "Season already has a different Closing Ranking"
                )
            return existing

        history = OfficialRankingCandidateStore(self.session).history(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
        )
        if not history:
            raise ValueError(
                "Season Closing Ranking requires an Official Ranking Week 61 head"
            )
        head = history[-1]
        if (
            head.week != snapshot.completed_week
            or head.fingerprint != snapshot.predecessor_official_fingerprint
        ):
            raise ValueError(
                "Season Closing Ranking must bind to the current Official Ranking Week 61 head"
            )
        if head.policy != snapshot.policy:
            raise ValueError(
                "Season Closing Ranking must preserve the outgoing Week 61 policy"
            )

        self.session.add(
            SeasonClosingRankingModel(
                run_id=snapshot.run_id,
                branch_id=snapshot.branch_id,
                season_index=season_index,
                completed_ordinal=snapshot.completed_week.ordinal,
                fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        self.session.flush()
        installed = self.get(
            run_id=snapshot.run_id,
            branch_id=snapshot.branch_id,
            season_index=season_index,
        )
        if installed is None:  # pragma: no cover
            raise ValueError("Season Closing Ranking write could not be verified")
        return installed
