"""SQLite transaction owner for tournament ingestion and candidate preparation."""

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.official_ranking_transition import (
    stage_official_ranking_from_history,
)
from beta_engine.application.ranking_tournament_ingestion import (
    ingest_tournament_ranking_sources,
)
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.official import (
    OfficialRankingSnapshot, calculate_official_ranking,
)
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.zero_history import resolve_zero_versions
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore
from beta_engine.infrastructure.db.official_rankings import (
    OfficialRankingCandidateStore,
)
from beta_engine.infrastructure.db.ranking_result_history import (
    OfficialRankingResultStore,
)


class RankingWeekCommandRunner:
    """One owned transaction; never advances the simulation clock or Viewer.

    The future full Week Transition must incorporate this work in its own unit
    of work, not call this committing runner halfway through a transition.
    """

    def __init__(
        self, factory: sessionmaker[Session], awards: SeasonPointAwardsService | None = None
    ):
        self.factory = factory
        self.awards = awards

    def execute(self, command: RankingWeekCommand | RankingBootstrapCommand) -> OfficialRankingSnapshot:
        command = _validated_command(command)
        with self.factory.begin() as session:
            # Lock before reading the head/receipt: competing SQLite commands
            # cannot both decide that a request is new and then stage different data.
            session.execute(text("BEGIN IMMEDIATE"))
            return stage_ranking_week_command(session, self.awards, command)


def stage_ranking_week_command(
    session: Session,
    awards: SeasonPointAwardsService | None,
    command: RankingWeekCommand | RankingBootstrapCommand,
) -> OfficialRankingSnapshot:
    """Prepare inside a caller-owned SQLite transaction, without committing it.

    The caller starts BEGIN IMMEDIATE before reading transition inputs and owns
    final commit/rollback. A savepoint removes this component's writes on failure,
    even when the caller catches that failure. Existing pending ORM work is flushed
    by SQLAlchemy before the savepoint and remains the caller's responsibility.
    """
    command = _validated_command(command)
    if not session.in_transaction():
        raise ValueError("Ranking staging requires an active caller transaction")
    connection = session.connection()
    if (
        connection.dialect.name != "sqlite"
        or not connection.connection.driver_connection.in_transaction
    ):
        # ORM autobegin alone is insufficient: under sqlite legacy transaction
        # control, releasing the first SAVEPOINT could otherwise commit the work.
        raise ValueError("Ranking staging requires a physical SQLite transaction")
    context = command if isinstance(command, RankingBootstrapCommand) else command.context
    with session.begin_nested():
        candidates = OfficialRankingCandidateStore(session)
        history = candidates.history(
            run_id=context.run_id, branch_id=context.branch_id
        )
        key = (context.run_id, context.branch_id, command.command_id)
        receipt = session.get(OfficialRankingCommandModel, key)
        if receipt is not None:
            if (
                receipt.request_fingerprint != command.fingerprint
                or receipt.target_ordinal != context.target_week.ordinal
            ):
                raise ValueError(
                    "Ranking command ID already has a different request"
                )
            snapshot = next(
                (s for s in history if s.week == context.target_week), None
            )
            if (
                snapshot is None
                or snapshot.fingerprint != receipt.snapshot_fingerprint
            ):
                raise ValueError(
                    "Ranking command receipt has missing or corrupt snapshot"
                )
            verify_ranking_command_inputs(receipt, snapshot, history)
            return snapshot
        if any(s.week == context.target_week for s in history):
            raise ValueError("Ranking target already staged by another command or pathway")
        stored_zeros = context.discipline == "stored_zeros"
        zero_history = OfficialRankingZeroStore(session).history(run_id=context.run_id, branch_id=context.branch_id)
        if zero_history and not stored_zeros:
            raise ValueError("Persisted zero history requires stored_zeros mode")
        if stored_zeros:
            context = context.model_copy(update={
                "discipline": "resolved_zeros",
                "disciplinary_zeros": resolve_zero_versions(zero_history, context.target_week),
            })
        if isinstance(command, RankingBootstrapCommand):
            snapshot = candidates.append(
                calculate_official_ranking(
                    run_id=command.run_id, branch_id=command.branch_id,
                    week=command.target_week, policy=command.policy,
                    players=command.players, results=(), disciplinary_zeros=context.disciplinary_zeros,
                ),
                bootstrap=True,
            )
        else:
            if command.tournaments and awards is None:
                raise ValueError("Tournament ingestion requires an award service")
            sources = OfficialRankingResultStore(session)
            for binding in sorted(command.tournaments, key=lambda t: t.edition_id):
                ingest_tournament_ranking_sources(awards, sources, binding)
            for correction in sorted(
                command.corrections,
                key=lambda v: (v.result.edition_id, v.result.player_id),
            ):
                sources.append(correction)
            snapshot = stage_official_ranking_from_history(candidates, sources, context)
        manifest = RankingInputManifest(
            zeros_from_history=stored_zeros,
            disciplinary_zeros=tuple(sorted(context.disciplinary_zeros, key=lambda z: z.zero_id)),
            players=tuple(sorted(context.players, key=lambda p: p.player_id)),
            results=() if isinstance(command, RankingBootstrapCommand) else sources.resolve(
                run_id=context.run_id, branch_id=context.branch_id, week=context.target_week,
            ),
        )
        previous = next((s for s in history if s.fingerprint == snapshot.previous_fingerprint), None)
        manifest.verify(snapshot, previous)
        session.add(
            OfficialRankingCommandModel(
                run_id=context.run_id,
                branch_id=context.branch_id,
                command_id=command.command_id,
                request_fingerprint=command.fingerprint,
                target_ordinal=context.target_week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                input_manifest_version=1,
                input_manifest_json=manifest.model_dump_json(),
            )
        )
        session.flush()
        return snapshot


def _validated_command(
    command: RankingWeekCommand | RankingBootstrapCommand,
) -> RankingWeekCommand | RankingBootstrapCommand:
    model = RankingBootstrapCommand if isinstance(command, RankingBootstrapCommand) else RankingWeekCommand
    return model.model_validate_json(command.model_dump_json())


def verify_ranking_command_inputs(receipt, snapshot, history) -> RankingInputManifest | None:
    """Legacy receipts remain readable; versioned manifests must verify fully."""
    if receipt.input_manifest_version is None and receipt.input_manifest_json is None:
        return
    if receipt.input_manifest_version != 1 or receipt.input_manifest_json is None:
        raise ValueError("Missing or unsupported ranking input manifest")
    manifest = RankingInputManifest.model_validate_json(receipt.input_manifest_json)
    previous = next((s for s in history if s.fingerprint == snapshot.previous_fingerprint), None)
    manifest.verify(snapshot, previous)
    return manifest
