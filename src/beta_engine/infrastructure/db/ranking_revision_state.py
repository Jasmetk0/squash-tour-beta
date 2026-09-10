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
