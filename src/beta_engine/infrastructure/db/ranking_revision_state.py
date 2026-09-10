"""Read-only capture inside the caller's consistent SQLite transaction."""

from sqlalchemy.orm import Session

from beta_engine.domain.rankings.revision_state import (
    RankingRevisionState, RankingRevisionEntry, RankingRevisionReceipt,
)
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
from beta_engine.infrastructure.db.ranking_inspection import inspect_ranking_history
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.infrastructure.db.ranking_week_command import verify_ranking_command_inputs


def capture_ranking_revision_state(session: Session, *, run_id: str, branch_id: str) -> RankingRevisionState:
    if not session.in_transaction():
        raise ValueError("Ranking revision capture requires a caller transaction")
    connection = session.connection()
    if connection.dialect.name != "sqlite" or not connection.connection.driver_connection.in_transaction:
        raise ValueError("Ranking revision capture requires a physical SQLite transaction")
    history = inspect_ranking_history(session, run_id=run_id, branch_id=branch_id)
    snapshots = tuple(c.snapshot for c in history.candidates)
    entries = []
    for candidate in history.candidates:
        manifest = None
        receipts = []
        for command_id in candidate.command_ids:
            receipt = session.get(OfficialRankingCommandModel, (run_id, branch_id, command_id))
            inputs = verify_ranking_command_inputs(receipt, candidate.snapshot, snapshots)
            if inputs is None:
                raise ValueError("Legacy ranking receipt has no complete input manifest")
            manifest = inputs
            receipts.append(RankingRevisionReceipt(command_id=command_id, request_fingerprint=receipt.request_fingerprint))
        if manifest is None:
            raise ValueError("Ranking candidate has no complete command inputs")
        entries.append(RankingRevisionEntry(snapshot=candidate.snapshot, inputs=manifest, receipts=tuple(receipts)))
    return RankingRevisionState(
        run_id=run_id, branch_id=branch_id, entries=tuple(entries),
        sources=OfficialRankingResultStore(session).history(run_id=run_id, branch_id=branch_id),
    )


def install_ranking_revision_state(
    session: Session, payload: str, *, expected_fingerprint: str,
    run_id: str, branch_id: str,
) -> RankingRevisionState:
    """Install a trusted same-scope bundle into empty ranking storage only.

    The caller starts BEGIN IMMEDIATE before any restore reads and commits all
    restored components together. An identical installed state is a read-only
    retry. No existing history is deleted or replaced by this component.
    """
    from beta_engine.domain.rankings.revision_state import load_ranking_revision_state
    from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
    from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore

    state = load_ranking_revision_state(
        payload, expected_fingerprint=expected_fingerprint, run_id=run_id, branch_id=branch_id,
    )
    # Capture also checks physical transaction presence, scope and fork support.
    current = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
    if current.fingerprint == state.fingerprint:
        return current
    if current.entries or current.sources:
        raise ValueError("Ranking restore target is not empty and differs from saved state")
    if session.get(RunContainerModel, run_id).read_only or session.get(RunBranchModel, branch_id).read_only:
        raise ValueError("Ranking restore target is read-only")
    with session.begin_nested():
        # Sources precede candidates because ordinary source writes cannot backdate
        # into an already staged history. All are still inside the same savepoint.
        sources = OfficialRankingResultStore(session)
        for version in state.sources:
            sources.append(version)
        candidates = OfficialRankingCandidateStore(session)
        for index, entry in enumerate(state.entries):
            candidates.append(entry.snapshot, bootstrap=index == 0)
            for receipt in entry.receipts:
                session.add(OfficialRankingCommandModel(
                    run_id=run_id, branch_id=branch_id, command_id=receipt.command_id,
                    request_fingerprint=receipt.request_fingerprint,
                    target_ordinal=entry.snapshot.week.ordinal,
                    snapshot_fingerprint=entry.snapshot.fingerprint,
                    input_manifest_version=1,
                    input_manifest_json=entry.inputs.model_dump_json(),
                ))
        session.flush()
        installed = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
        if installed.fingerprint != expected_fingerprint:
            raise ValueError("Installed ranking state differs from trusted saved state")
        return installed
