"""Run/Branch-owned tournament binding to a published Official Ranking."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.domain.rankings.official import (
    RankingWeek,
    load_official_ranking_snapshot,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.infrastructure.db.models import (
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    TournamentRankingSnapshotAuthorityModel,
)


class TournamentRankingSnapshotAuthorityConflict(ValueError):
    """One Tournament Edition/Event already froze a different ranking snapshot."""


class TournamentRankingSnapshotAuthorityStore:
    def __init__(self, session: Session):
        self.session = session

    def _scope(self, run_id: str, branch_id: str, *, writing: bool = False) -> None:
        run = self.session.get(RunContainerModel, run_id)
        branch = self.session.get(RunBranchModel, branch_id)
        if run is None or branch is None or branch.run_id != run_id:
            raise ValueError("Tournament Ranking Snapshot Run/Branch scope does not exist")
        if writing and (run.read_only or branch.read_only or branch.status == "archived"):
            raise ValueError("Tournament Ranking Snapshot scope is not writable")

    def _load_row(
        self, row: TournamentRankingSnapshotAuthorityModel
    ) -> TournamentRankingSnapshotAuthority:
        authority = TournamentRankingSnapshotAuthority.model_validate_json(
            row.payload_json
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.ranking_week.ordinal,
            authority.ranking_snapshot_fingerprint,
            authority.fingerprint,
            authority.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.ranking_week_ordinal,
            row.ranking_snapshot_fingerprint,
            row.authority_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError("Stored Tournament Ranking Snapshot authority is corrupt")
        published = self.session.get(
            PublishedOfficialRankingModel,
            (row.run_id, row.branch_id, row.ranking_week_ordinal),
        )
        if published is None:
            raise ValueError(
                "Tournament Ranking Snapshot authority references a missing publication"
            )
        snapshot = load_official_ranking_snapshot(
            published.payload_json,
            expected_fingerprint=published.snapshot_fingerprint,
            run_id=row.run_id,
            branch_id=row.branch_id,
            week=authority.ranking_week,
        )
        if snapshot != authority.ranking_snapshot:
            raise ValueError(
                "Tournament Ranking Snapshot authority differs from publication"
            )
        return authority

    def get(
        self, *, run_id: str, branch_id: str, event_id: str
    ) -> TournamentRankingSnapshotAuthority | None:
        self._scope(run_id, branch_id)
        row = self.session.get(
            TournamentRankingSnapshotAuthorityModel,
            (run_id, branch_id, event_id),
        )
        return None if row is None else self._load_row(row)

    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[TournamentRankingSnapshotAuthority, ...]:
        self._scope(run_id, branch_id)
        rows = self.session.scalars(
            select(TournamentRankingSnapshotAuthorityModel)
            .where(
                TournamentRankingSnapshotAuthorityModel.run_id == run_id,
                TournamentRankingSnapshotAuthorityModel.branch_id == branch_id,
            )
            .order_by(TournamentRankingSnapshotAuthorityModel.event_id)
        ).all()
        return tuple(self._load_row(row) for row in rows)

    def adopt(
        self,
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        ranking_week: RankingWeek,
        command_id: str,
    ) -> TournamentRankingSnapshotAuthority:
        self._scope(run_id, branch_id, writing=True)
        publication = self.session.get(
            PublishedOfficialRankingModel,
            (run_id, branch_id, ranking_week.ordinal),
        )
        if publication is None:
            raise ValueError(
                "Tournament Ranking Snapshot requires an existing published Official Ranking"
            )
        snapshot = load_official_ranking_snapshot(
            publication.payload_json,
            expected_fingerprint=publication.snapshot_fingerprint,
            run_id=run_id,
            branch_id=branch_id,
            week=ranking_week,
        )
        return self.append(
            TournamentRankingSnapshotAuthority(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                ranking_week=ranking_week,
                ranking_snapshot=snapshot,
                adopted_by_command_id=command_id,
            )
        )

    def append(
        self, authority: TournamentRankingSnapshotAuthority
    ) -> TournamentRankingSnapshotAuthority:
        """Stage frozen authority in the caller transaction.

        Used both by explicit adoption and trusted Saved Revision restore.
        """
        authority = TournamentRankingSnapshotAuthority.model_validate_json(
            authority.model_dump_json()
        )
        self._scope(authority.run_id, authority.branch_id, writing=True)
        publication = self.session.get(
            PublishedOfficialRankingModel,
            (
                authority.run_id,
                authority.branch_id,
                authority.ranking_week.ordinal,
            ),
        )
        if publication is None:
            raise ValueError(
                "Tournament Ranking Snapshot source publication is missing"
            )
        published = load_official_ranking_snapshot(
            publication.payload_json,
            expected_fingerprint=publication.snapshot_fingerprint,
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            week=authority.ranking_week,
        )
        if published != authority.ranking_snapshot:
            raise ValueError(
                "Tournament Ranking Snapshot authority does not match publication"
            )

        existing = self.get(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
        )
        if existing is not None:
            if existing == authority:
                return existing
            raise TournamentRankingSnapshotAuthorityConflict(
                "Tournament event already adopted a different ranking snapshot authority"
            )

        self.session.add(
            TournamentRankingSnapshotAuthorityModel(
                run_id=authority.run_id,
                branch_id=authority.branch_id,
                event_id=authority.event_id,
                ranking_week_ordinal=authority.ranking_week.ordinal,
                ranking_snapshot_fingerprint=authority.ranking_snapshot_fingerprint,
                authority_fingerprint=authority.fingerprint,
                adopted_by_command_id=authority.adopted_by_command_id,
                payload_json=authority.model_dump_json(),
            )
        )
        self.session.flush()
        return authority
