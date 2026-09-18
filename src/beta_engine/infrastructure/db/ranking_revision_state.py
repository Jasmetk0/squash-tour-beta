"""Read-only capture inside the caller's consistent SQLite transaction."""

from sqlalchemy.orm import Session
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore

from beta_engine.domain.rankings.revision_state import (
    RankingRevisionState, RankingRevisionEntry, RankingRevisionReceipt,
)
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
from beta_engine.infrastructure.db.ranking_inspection import inspect_ranking_history
from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
from beta_engine.infrastructure.db.ranking_week_command import verify_ranking_command_inputs
from beta_engine.infrastructure.db.owned_tournament_sources import OwnedTournamentRankingSourceStore
from beta_engine.infrastructure.db.ranking_transition_authority import RankingTransitionAuthorityStore
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.models import (AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel, AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel)
from sqlalchemy import select


def capture_ranking_revision_state(session: Session, *, run_id: str, branch_id: str) -> RankingRevisionState:
    if not session.in_transaction():
        raise ValueError("Ranking revision capture requires a caller transaction")
    connection = session.connection()
    driver_connection = connection.connection.driver_connection
    if (connection.dialect.name != "sqlite" or driver_connection is None
            or not driver_connection.in_transaction):
        raise ValueError("Ranking revision capture requires a physical SQLite transaction")
    history = inspect_ranking_history(session, run_id=run_id, branch_id=branch_id)
    snapshots = tuple(c.snapshot for c in history.candidates)
    entries = []
    for candidate in history.candidates:
        manifest = None
        receipts = []
        for command_id in candidate.command_ids:
            receipt = session.get(OfficialRankingCommandModel, (run_id, branch_id, command_id))
            if receipt is None:
                raise ValueError("Ranking candidate receipt is missing")
            inputs = verify_ranking_command_inputs(receipt, candidate.snapshot, snapshots)
            if inputs is None:
                raise ValueError("Legacy ranking receipt has no complete input manifest")
            manifest = inputs
            receipts.append(RankingRevisionReceipt(command_id=command_id, request_fingerprint=receipt.request_fingerprint, request_payload_json=receipt.request_payload_json))
        if manifest is None:
            raise ValueError("Ranking candidate has no complete command inputs")
        entries.append(RankingRevisionEntry(snapshot=candidate.snapshot, inputs=manifest, receipts=tuple(receipts)))
    world = session.get(AuthoritativeWorldStateModel, (run_id, branch_id))
    def rows(model, order):
        values = session.scalars(select(model).where(model.run_id == run_id, model.branch_id == branch_id).order_by(order)).all()
        return [dict((column.name, getattr(value, column.name)) for column in model.__table__.columns) for value in values]
    transition_state = None
    publications = rows(PublishedOfficialRankingModel, PublishedOfficialRankingModel.week_ordinal)
    receipts = rows(AuthoritativeWeekTransitionReceiptModel, AuthoritativeWeekTransitionReceiptModel.command_id)
    events = rows(AuthoritativeWorldEventModel, AuthoritativeWorldEventModel.command_id)
    if world is not None or publications or receipts or events:
        transition_state = {"world": None if world is None else {
            "run_id": world.run_id, "branch_id": world.branch_id,
            "current_ordinal": world.current_ordinal, "ranking_fingerprint": world.ranking_fingerprint},
            "publications": publications, "receipts": receipts, "events": events}
    tournament_sources = OwnedTournamentRankingSourceStore(session).history(run_id=run_id, branch_id=branch_id)
    authorities = RankingTransitionAuthorityStore(session).history(run_id=run_id, branch_id=branch_id)
    tournament_ranking_authorities = TournamentRankingSnapshotAuthorityStore(
        session
    ).history(run_id=run_id, branch_id=branch_id)
    if (
        any(value is None for value in tournament_sources)
        or any(value is None for value in authorities)
        or any(value is None for value in tournament_ranking_authorities)
    ):
        raise ValueError("Ranking revision source identity is missing")
    return RankingRevisionState(
        run_id=run_id, branch_id=branch_id, entries=tuple(entries),
        sources=OfficialRankingResultStore(session).history(run_id=run_id, branch_id=branch_id),
        zero_sources=OfficialRankingZeroStore(session).history(run_id=run_id, branch_id=branch_id),
        tournament_sources=tuple(value for value in tournament_sources if value is not None),
        transition_authorities=tuple(value for value in authorities if value is not None),
        tournament_ranking_snapshot_authorities=tuple(
            value for value in tournament_ranking_authorities if value is not None
        ),
        authoritative_transition_state=transition_state,
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
    from beta_engine.domain.rankings.revision_state import (
        load_ranking_revision_state, ranking_revision_states_equivalent,
    )
    from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
    from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore

    state = load_ranking_revision_state(
        payload, expected_fingerprint=expected_fingerprint, run_id=run_id, branch_id=branch_id,
    )
    # Capture also checks physical transaction presence, scope and fork support.
    current = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
    if current.fingerprint == state.fingerprint:
        return current
    if (
        current.entries
        or current.sources
        or current.zero_sources
        or current.tournament_sources
        or current.transition_authorities
        or current.tournament_ranking_snapshot_authorities
    ):
        raise ValueError("Ranking restore target is not empty and differs from saved state")
    run = session.get(RunContainerModel, run_id)
    branch = session.get(RunBranchModel, branch_id)
    if run is None or branch is None:
        raise ValueError("Ranking restore scope does not exist")
    if run.read_only or branch.read_only:
        raise ValueError("Ranking restore target is read-only")
    with session.begin_nested():
        owned = OwnedTournamentRankingSourceStore(session)
        for source in state.tournament_sources:
            owned.append(source)
        authorities = RankingTransitionAuthorityStore(session)
        for authority in state.transition_authorities:
            authorities.append(authority)
        # Sources precede candidates because ordinary source writes cannot backdate
        # into an already staged history. All are still inside the same savepoint.
        sources = OfficialRankingResultStore(session)
        for version in state.sources:
            sources.append(version)
        zeros = OfficialRankingZeroStore(session)
        for version in state.zero_sources:
            zeros.append(version)
        candidates = OfficialRankingCandidateStore(session)
        for index, entry in enumerate(state.entries):
            candidates.append(entry.snapshot, bootstrap=index == 0)
            for receipt in entry.receipts:
                session.add(OfficialRankingCommandModel(
                    run_id=run_id, branch_id=branch_id, command_id=receipt.command_id,
                    request_fingerprint=receipt.request_fingerprint,
                    request_payload_json=receipt.request_payload_json,
                    target_ordinal=entry.snapshot.week.ordinal,
                    snapshot_fingerprint=entry.snapshot.fingerprint,
                    input_manifest_version=1,
                    input_manifest_json=entry.inputs.model_dump_json(),
                ))
        transition = state.authoritative_transition_state
        if transition is not None:
            if transition["world"] is not None:
                session.add(AuthoritativeWorldStateModel(**transition["world"]))
            for row in transition["publications"]:
                session.add(PublishedOfficialRankingModel(**row))
            for row in transition["receipts"]:
                session.add(AuthoritativeWeekTransitionReceiptModel(**row))
            for row in transition["events"]:
                session.add(AuthoritativeWorldEventModel(**row))
            # Tournament Ranking Snapshot authority must resolve only against
            # already restored immutable Official Ranking publications.
            session.flush()
        tournament_rankings = TournamentRankingSnapshotAuthorityStore(session)
        for authority in state.tournament_ranking_snapshot_authorities:
            tournament_rankings.append(authority)
        session.flush()
        installed = capture_ranking_revision_state(session, run_id=run_id, branch_id=branch_id)
        if not ranking_revision_states_equivalent(installed, state):
            raise ValueError("Installed ranking state differs from trusted saved state")
        return installed
