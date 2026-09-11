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
        from beta_engine.infrastructure.db.ranking_week_command import verify_ranking_command_inputs
        verify_ranking_command_inputs(receipt, snapshot, snapshots)
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


def inspect_ranking_sources(session: Session, *, run_id: str, branch_id: str, week):
    from beta_engine.application.ranking_inspection import RankingCandidateSources, RankingSourceDetail
    from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore

    history = inspect_ranking_history(session, run_id=run_id, branch_id=branch_id)
    candidate = next((c for c in history.candidates if c.snapshot.week == week), None)
    if candidate is None:
        raise KeyError("Ranking candidate week not found")
    latest = {}
    for version in OfficialRankingResultStore(session).history(run_id=run_id, branch_id=branch_id):
        if version.effective_week.ordinal <= week.ordinal:
            latest[(version.result.edition_id, version.result.player_id)] = version
    from beta_engine.infrastructure.db.ranking_week_command import verify_ranking_command_inputs
    for command_id in candidate.command_ids:
        receipt = session.get(OfficialRankingCommandModel, (run_id, branch_id, command_id))
        manifest = verify_ranking_command_inputs(
            receipt, candidate.snapshot, tuple(c.snapshot for c in history.candidates),
        )
        if manifest is not None and {
            (r.edition_id, r.player_id): r for r in manifest.results
        } != {key: v.result for key, v in latest.items()}:
            raise ValueError("Stored source history differs from complete ranking input manifest")
    counted = {
        (r.edition_id, r.player_id): r
        for row in candidate.snapshot.rows for r in row.counted_results
    }
    for key, result in counted.items():
        if key not in latest or latest[key].result != result:
            raise ValueError("Candidate counted result has missing or inconsistent source history")
    return RankingCandidateSources(
        run_id=run_id, branch_id=branch_id, week=week,
        candidate_fingerprint=candidate.fingerprint,
        sources=tuple(RankingSourceDetail(
            version=latest[key], fingerprint=latest[key].fingerprint, counted=key in counted,
        ) for key in sorted(latest)),
    )


def inspect_ranking_inputs(session: Session, *, run_id: str, branch_id: str, week):
    from beta_engine.application.ranking_inspection import RankingCandidateInputs
    from beta_engine.infrastructure.db.ranking_week_command import verify_ranking_command_inputs

    history = inspect_ranking_history(session, run_id=run_id, branch_id=branch_id)
    candidate = next((c for c in history.candidates if c.snapshot.week == week), None)
    if candidate is None:
        raise KeyError("Ranking candidate week not found")
    manifest = None
    for command_id in candidate.command_ids:
        receipt = session.get(OfficialRankingCommandModel, (run_id, branch_id, command_id))
        verified = verify_ranking_command_inputs(
            receipt, candidate.snapshot, tuple(c.snapshot for c in history.candidates),
        )
        if verified is not None:
            manifest = verified
    from beta_engine.domain.rankings.tie_explanations import explain_ranking_ties
    previous = next((c.snapshot for c in history.candidates if c.snapshot.week.ordinal == week.ordinal - 1), None)
    explanations = explain_ranking_ties(candidate.snapshot, manifest, previous) if manifest is not None else ()
    return RankingCandidateInputs(
        run_id=run_id, branch_id=branch_id, week=week,
        candidate_fingerprint=candidate.fingerprint,
        verification_status="complete_manifest" if manifest is not None else "legacy_without_manifest",
        manifest=manifest, tie_explanations=explanations,
    )
