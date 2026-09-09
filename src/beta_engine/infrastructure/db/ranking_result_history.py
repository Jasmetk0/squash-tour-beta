"""Caller-transaction-owned immutable ranking source history."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import OfficialRankingResult, RankingWeek
from beta_engine.domain.rankings.result_history import (
    RankingResultVersion,
    validate_result_successor,
)
from beta_engine.infrastructure.db.models import (
    OfficialRankingResultVersionModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)


class OfficialRankingResultStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False):
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Ranking result scope does not exist")
        if branch.forked_from_branch_id is not None:
            raise ValueError(
                "Ranking result fork ancestry requires a dedicated adapter"
            )
        if writing and (run.read_only or branch.read_only):
            raise ValueError("Ranking result scope is read-only")

    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[RankingResultVersion, ...]:
        self._scope(run_id, branch_id)
        records = self.session.scalars(
            select(OfficialRankingResultVersionModel)
            .where(
                OfficialRankingResultVersionModel.run_id == run_id,
                OfficialRankingResultVersionModel.branch_id == branch_id,
            )
            .order_by(
                OfficialRankingResultVersionModel.edition_id,
                OfficialRankingResultVersionModel.player_id,
                OfficialRankingResultVersionModel.effective_ordinal,
            )
        ).all()
        versions = []
        latest = {}
        for record in records:
            version = RankingResultVersion.model_validate_json(record.payload_json)
            if (
                version.run_id,
                version.branch_id,
                version.result.edition_id,
                version.result.player_id,
                version.effective_week.ordinal,
                version.fingerprint,
            ) != (
                run_id,
                branch_id,
                record.edition_id,
                record.player_id,
                record.effective_ordinal,
                record.fingerprint,
            ):
                raise ValueError("Stored ranking result identity/fingerprint mismatch")
            key = (version.result.edition_id, version.result.player_id)
            previous = latest.get(key)
            if previous is None:
                if version.previous_fingerprint is not None:
                    raise ValueError("Missing initial ranking result version")
            else:
                validate_result_successor(previous, version)
            latest[key] = version
            versions.append(version)
        return tuple(versions)

    def resolve(
        self, *, run_id: str, branch_id: str, week: RankingWeek
    ) -> tuple[OfficialRankingResult, ...]:
        """Latest effective version per Edition/player, including non-Best-N results."""
        latest = {}
        for version in self.history(run_id=run_id, branch_id=branch_id):
            if version.effective_week.ordinal <= week.ordinal:
                latest[(version.result.edition_id, version.result.player_id)] = (
                    version.result
                )
        return tuple(latest[key] for key in sorted(latest))

    def append(self, version: RankingResultVersion) -> RankingResultVersion:
        version = RankingResultVersion.model_validate_json(version.model_dump_json())
        self._scope(version.run_id, version.branch_id, writing=True)
        history = self.history(run_id=version.run_id, branch_id=version.branch_id)
        lineage = [
            v
            for v in history
            if (v.result.edition_id, v.result.player_id)
            == (version.result.edition_id, version.result.player_id)
        ]
        for existing in lineage:
            if existing.effective_week == version.effective_week:
                if existing.fingerprint != version.fingerprint:
                    raise ValueError("Conflicting ranking result version")
                return existing
        if lineage:
            validate_result_successor(lineage[-1], version)
        elif version.previous_fingerprint is not None:
            raise ValueError(
                "Initial ranking result cannot reference a missing predecessor"
            )
        candidates = OfficialRankingCandidateStore(self.session).history(
            run_id=version.run_id, branch_id=version.branch_id
        )
        if candidates and version.effective_week.ordinal <= candidates[-1].week.ordinal:
            raise ValueError(
                "Cannot backdate ranking sources into already staged history"
            )
        self.session.add(
            OfficialRankingResultVersionModel(
                run_id=version.run_id,
                branch_id=version.branch_id,
                edition_id=version.result.edition_id,
                player_id=version.result.player_id,
                effective_ordinal=version.effective_week.ordinal,
                fingerprint=version.fingerprint,
                payload_json=version.model_dump_json(),
            )
        )
        self.session.flush()
        return version
