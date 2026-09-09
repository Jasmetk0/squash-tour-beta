"""Inspect persisted candidates and receipts without recalculation or writes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from beta_engine.application.ranking_inspection import (
    RankingCandidateDetail,
    RankingCandidateHistory,
)
from beta_engine.infrastructure.db.models import (
    OfficialRankingCommandModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)


def inspect_ranking_history(
    session: Session, *, run_id: str, branch_id: str
) -> RankingCandidateHistory:
    branch = session.get(RunBranchModel, branch_id)
    if (
        session.get(RunContainerModel, run_id) is None
        or branch is None
        or branch.run_id != run_id
    ):
        raise KeyError("Ranking Run/Branch scope does not exist")
    if branch.forked_from_branch_id is not None:
        raise ValueError("Ranking fork ancestry inspection is not supported yet")
    snapshots = OfficialRankingCandidateStore(session).history(
        run_id=run_id, branch_id=branch_id
    )
    by_week = {s.week.ordinal: s for s in snapshots}
    commands = {}
    receipts = session.scalars(
        select(OfficialRankingCommandModel)
        .where(
            OfficialRankingCommandModel.run_id == run_id,
            OfficialRankingCommandModel.branch_id == branch_id,
        )
        .order_by(OfficialRankingCommandModel.command_id)
    ).all()
    for receipt in receipts:
        snapshot = by_week.get(receipt.target_ordinal)
        if snapshot is None or snapshot.fingerprint != receipt.snapshot_fingerprint:
            raise ValueError("Ranking command receipt has missing or corrupt snapshot")
        commands.setdefault(receipt.target_ordinal, []).append(receipt.command_id)
    return RankingCandidateHistory(
        run_id=run_id,
        branch_id=branch_id,
        candidates=tuple(
            RankingCandidateDetail(
                snapshot=s,
                fingerprint=s.fingerprint,
                command_ids=tuple(commands.get(s.week.ordinal, ())),
            )
            for s in snapshots
        ),
    )
