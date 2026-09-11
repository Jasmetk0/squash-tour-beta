"""Caller-transaction-owned immutable ranking source history."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import DisciplinaryZero, RankingWeek
from beta_engine.domain.rankings.zero_history import (
    RankingZeroVersion,
    validate_zero_successor,
    resolve_zero_versions,
)
from beta_engine.infrastructure.db.models import (
    OfficialRankingZeroVersionModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)


class OfficialRankingZeroStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False):
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Ranking zero scope does not exist")
        if branch.forked_from_branch_id is not None:
            raise ValueError(
                "Ranking zero fork ancestry requires a dedicated adapter"
            )
        if writing and (run.read_only or branch.read_only):
            raise ValueError("Ranking zero scope is read-only")

    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[RankingZeroVersion, ...]:
        self._scope(run_id, branch_id)
        records = self.session.scalars(
            select(OfficialRankingZeroVersionModel)
            .where(
                OfficialRankingZeroVersionModel.run_id == run_id,
                OfficialRankingZeroVersionModel.branch_id == branch_id,
            )
            .order_by(
                OfficialRankingZeroVersionModel.zero_id,
                OfficialRankingZeroVersionModel.effective_ordinal,
            )
        ).all()
        versions = []
        latest = {}
        for record in records:
            version = RankingZeroVersion.model_validate_json(record.payload_json)
            if (
                version.zero.run_id,
                version.zero.branch_id,
                version.zero.zero_id,
                version.effective_week.ordinal,
                version.fingerprint,
            ) != (
                run_id,
                branch_id,
                record.zero_id,
                record.effective_ordinal,
                record.fingerprint,
            ):
                raise ValueError("Stored ranking zero identity/fingerprint mismatch")
            key = version.zero.zero_id
            previous = latest.get(key)
            if previous is None:
                if version.previous_fingerprint is not None:
                    raise ValueError("Missing initial ranking zero version")
            else:
                validate_zero_successor(previous, version)
            latest[key] = version
            versions.append(version)
        return tuple(versions)

    def resolve(
        self, *, run_id: str, branch_id: str, week: RankingWeek
    ) -> tuple[DisciplinaryZero, ...]:
        """Latest effective decision per zero, including expired decisions."""
        return resolve_zero_versions(self.history(run_id=run_id, branch_id=branch_id), week)

    def append(self, version: RankingZeroVersion) -> RankingZeroVersion:
        version = RankingZeroVersion.model_validate_json(version.model_dump_json())
        self._scope(version.zero.run_id, version.zero.branch_id, writing=True)
        history = self.history(run_id=version.zero.run_id, branch_id=version.zero.branch_id)
        lineage = [v for v in history if v.zero.zero_id == version.zero.zero_id]
        for existing in lineage:
            if existing.effective_week == version.effective_week:
                if existing.fingerprint != version.fingerprint:
                    raise ValueError("Conflicting ranking zero version")
                return existing
        if lineage:
            validate_zero_successor(lineage[-1], version)
        elif version.previous_fingerprint is not None:
            raise ValueError(
                "Initial ranking zero cannot reference a missing predecessor"
            )
        candidates = OfficialRankingCandidateStore(self.session).history(
            run_id=version.zero.run_id, branch_id=version.zero.branch_id
        )
        if candidates and version.effective_week.ordinal <= candidates[-1].week.ordinal:
            raise ValueError(
                "Cannot backdate ranking zeros into already staged history"
            )
        self.session.add(
            OfficialRankingZeroVersionModel(
                run_id=version.zero.run_id,
                branch_id=version.zero.branch_id,
                zero_id=version.zero.zero_id,
                effective_ordinal=version.effective_week.ordinal,
                fingerprint=version.fingerprint,
                payload_json=version.model_dump_json(),
            )
        )
        self.session.flush()
        return version
