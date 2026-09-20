"""SQLite transaction owner for tournament ingestion and candidate preparation."""

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.application.official_ranking_transition import (
    stage_official_ranking_from_history,
)
from beta_engine.application.ranking_tournament_ingestion import (
    ingest_canonical_tournament_ranking_sources,
    ingest_frozen_tournament_ranking_sources,
    prepare_tournament_ranking_sources,
)
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.official import (
    OfficialRankingSnapshot,
    calculate_official_ranking,
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
from beta_engine.infrastructure.db.owned_tournament_sources import (
    OwnedTournamentRankingSourceStore,
)
from beta_engine.domain.rankings.tournament_source import OwnedTournamentRankingSource
from beta_engine.infrastructure.db.models import RunBranchModel, RunContainerModel
from beta_engine.infrastructure.db.models import BranchWorkingDraftModel
from beta_engine.infrastructure.db.ranking_transition_authority import (
    RankingTransitionAuthorityStore,
    authority_carried_to_saved_head,
)
from sqlalchemy import select


class RankingWeekCommandRunner:
    """One owned transaction; never advances the simulation clock or Viewer.

    The future full Week Transition must incorporate this work in its own unit
    of work, not call this committing runner halfway through a transition.
    """

    def __init__(
        self,
        factory: sessionmaker[Session],
        awards: SeasonPointAwardsService | None = None,
    ):
        self.factory = factory
        self.awards = awards

    def execute(
        self,
        command: RankingWeekCommand | RankingBootstrapCommand,
        *,
        expected_snapshot_fingerprint: str | None = None,
    ) -> OfficialRankingSnapshot:
        command = _validated_command(command)
        with self.factory.begin() as session:
            # Lock before reading the head/receipt: competing SQLite commands
            # cannot both decide that a request is new and then stage different data.
            session.execute(text("BEGIN IMMEDIATE"))
            snapshot = stage_ranking_week_command(session, self.awards, command)
            if (
                expected_snapshot_fingerprint is not None
                and snapshot.fingerprint != expected_snapshot_fingerprint
            ):
                raise ValueError("Ranking inputs changed since preview")
            return snapshot

    def preview(
        self, command: RankingWeekCommand | RankingBootstrapCommand
    ) -> OfficialRankingSnapshot:
        """Exercise the real preparation transaction, then unconditionally roll it back."""
        command = _validated_command(command)
        with self.factory() as session:
            try:
                session.execute(text("BEGIN IMMEDIATE"))
                return stage_ranking_week_command(session, self.awards, command)
            finally:
                session.rollback()


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
    context = (
        command if isinstance(command, RankingBootstrapCommand) else command.context
    )
    with session.begin_nested():
        if (
            isinstance(command, RankingBootstrapCommand)
            and command.initial_world_fingerprint is not None
        ):
            from beta_engine.infrastructure.db.initial_world_state import (
                get_initial_world,
            )
            from beta_engine.application.initial_world import (
                derive_initial_ranking_inputs,
            )

            world = get_initial_world(
                session, run_id=command.run_id, branch_id=command.branch_id
            )
            if world is None or world.fingerprint != command.initial_world_fingerprint:
                raise ValueError(
                    "Initial-world source changed since ranking preparation"
                )
            policy, players = derive_initial_ranking_inputs(world)
            if command.policy != policy or command.players != players:
                raise ValueError("Ranking inputs differ from the owned initial world")
        candidates = OfficialRankingCandidateStore(session)
        history = candidates.history(run_id=context.run_id, branch_id=context.branch_id)
        key = (context.run_id, context.branch_id, command.command_id)
        receipt = session.get(OfficialRankingCommandModel, key)
        if (
            isinstance(command, RankingWeekCommand)
            and command.authority_fingerprint is not None
        ):
            authority = RankingTransitionAuthorityStore(session).get(
                run_id=context.run_id,
                branch_id=context.branch_id,
                target_ordinal=context.target_week.ordinal,
            )
            if (
                authority is None
                or authority.fingerprint != command.authority_fingerprint
            ):
                raise ValueError("Authoritative ranking transition inputs changed")
            from beta_engine.infrastructure.db.player_lifecycle_state import (
                advance_lifecycle_with_prospects,
                get_lifecycle,
            )

            predecessor_lifecycle = get_lifecycle(
                session,
                run_id=context.run_id,
                branch_id=context.branch_id,
                week=context.completed_week,
            )
            if predecessor_lifecycle is None:
                raise ValueError(
                    "Authoritative predecessor player lifecycle snapshot is missing"
                )
            derived_players = advance_lifecycle_with_prospects(
                session,
                predecessor=predecessor_lifecycle,
                target=context.target_week,
            ).ranking_roster()
            authority_identity = tuple(
                (p.player_id, p.tie_break_token, p.tour_entry_week)
                for p in authority.players
            )
            derived_identity = tuple(
                (p.player_id, p.tie_break_token, p.tour_entry_week)
                for p in derived_players
            )
            if (
                (authority.completed_week, authority.target_week, authority.policy)
                != (context.completed_week, context.target_week, context.policy)
                or authority_identity != derived_identity
                or context.players != derived_players
            ):
                raise ValueError(
                    "Resolved ranking context differs from stored authority"
                )
            draft = session.scalar(
                select(BranchWorkingDraftModel).where(
                    BranchWorkingDraftModel.branch_id == context.branch_id
                )
            )
            branch = session.get(RunBranchModel, context.branch_id)
            if (
                draft is None
                or branch is None
                or (
                    receipt is None
                    and not authority_carried_to_saved_head(
                        session, authority, branch, draft
                    )
                )
            ):
                raise ValueError(
                    "Authoritative ranking transition source revision is stale"
                )
        if receipt is not None:
            if (
                receipt.request_fingerprint != command.fingerprint
                or receipt.target_ordinal != context.target_week.ordinal
            ):
                raise ValueError("Ranking command ID already has a different request")
            snapshot = next((s for s in history if s.week == context.target_week), None)
            if snapshot is None or snapshot.fingerprint != receipt.snapshot_fingerprint:
                raise ValueError(
                    "Ranking command receipt has missing or corrupt snapshot"
                )
            verify_ranking_command_inputs(receipt, snapshot, history)
            return snapshot
        if any(s.week == context.target_week for s in history):
            raise ValueError(
                "Ranking target already staged by another command or pathway"
            )
        stored_zeros = context.discipline == "stored_zeros"
        zeros = OfficialRankingZeroStore(session)
        for version in sorted(command.zero_versions, key=lambda v: v.zero.zero_id):
            zeros.append(version)
        zero_history = zeros.history(run_id=context.run_id, branch_id=context.branch_id)
        if zero_history and not stored_zeros:
            raise ValueError("Persisted zero history requires stored_zeros mode")
        if stored_zeros:
            context = context.model_copy(
                update={
                    "discipline": "resolved_zeros",
                    "disciplinary_zeros": resolve_zero_versions(
                        zero_history, context.target_week
                    ),
                }
            )
        if isinstance(command, RankingBootstrapCommand):
            snapshot = candidates.append(
                calculate_official_ranking(
                    run_id=command.run_id,
                    branch_id=command.branch_id,
                    week=command.target_week,
                    policy=command.policy,
                    players=command.players,
                    results=(),
                    disciplinary_zeros=context.disciplinary_zeros,
                ),
                bootstrap=True,
            )
        else:
            sources = OfficialRankingResultStore(session)
            owned = OwnedTournamentRankingSourceStore(session)
            for binding in sorted(command.tournaments, key=lambda t: t.edition_id):
                frozen = owned.get(
                    run_id=context.run_id,
                    branch_id=context.branch_id,
                    edition_id=binding.edition_id,
                )
                if frozen is None:
                    if awards is None:
                        raise ValueError(
                            "Legacy tournament adoption requires an award service"
                        )
                    run = session.get(RunContainerModel, context.run_id)
                    branch = session.get(RunBranchModel, context.branch_id)
                    if run is None or branch is None or branch.run_id != context.run_id:
                        raise ValueError(
                            "Tournament adoption Run/Branch scope not found"
                        )
                    if run.read_only or branch.read_only or branch.status != "active":
                        raise ValueError(
                            "Tournament adoption requires a writable active Run/Branch"
                        )
                    result = awards.result_service.get_event_result(
                        event_id=binding.event_id
                    ).result_package
                    award_package = awards.get_event_point_awards(
                        event_id=binding.event_id
                    ).award_package
                    if result is None or award_package is None:
                        raise ValueError(
                            "Persisted tournament results and awards are required"
                        )
                    # Complete validation deliberately precedes the first adoption write.
                    prepare_tournament_ranking_sources(binding, result, award_package)
                    frozen = owned.append(
                        OwnedTournamentRankingSource(
                            binding=binding,
                            result=result,
                            awards=award_package,
                            adopted_by_command_id=command.command_id,
                        )
                    )
                elif frozen.binding != binding:
                    raise ValueError(
                        "Tournament binding conflicts with its owned frozen source"
                    )
                if frozen.schema_version in {
                    "owned_tournament_ranking_source.v3",
                    "owned_tournament_ranking_source.v4",
                    "owned_tournament_ranking_source.v5",
                }:
                    if (
                        frozen.canonical_result is None
                        or frozen.canonical_awards is None
                    ):
                        raise ValueError(
                            "Canonical owned tournament source is incomplete"
                        )
                    ingest_canonical_tournament_ranking_sources(
                        sources,
                        binding,
                        frozen.canonical_result,
                        frozen.canonical_awards,
                    )
                else:
                    if frozen.result is None or frozen.awards is None:
                        raise ValueError(
                            "Historical owned tournament source is incomplete"
                        )
                    ingest_frozen_tournament_ranking_sources(
                        sources, binding, frozen.result, frozen.awards
                    )
            for correction in sorted(
                command.corrections,
                key=lambda v: (v.result.edition_id, v.result.player_id),
            ):
                sources.append(correction)
            snapshot = stage_official_ranking_from_history(candidates, sources, context)
        manifest = RankingInputManifest(
            command_request_fingerprint=command.fingerprint,
            zeros_from_history=stored_zeros,
            disciplinary_zeros=tuple(
                sorted(context.disciplinary_zeros, key=lambda z: z.zero_id)
            ),
            players=tuple(sorted(context.players, key=lambda p: p.player_id)),
            results=()
            if isinstance(command, RankingBootstrapCommand)
            else sources.resolve(
                run_id=context.run_id,
                branch_id=context.branch_id,
                week=context.target_week,
            ),
        )
        previous = next(
            (s for s in history if s.fingerprint == snapshot.previous_fingerprint), None
        )
        manifest.verify(snapshot, previous)
        session.add(
            OfficialRankingCommandModel(
                run_id=context.run_id,
                branch_id=context.branch_id,
                command_id=command.command_id,
                request_fingerprint=command.fingerprint,
                request_payload_json=command.canonical_request_json,
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
    model = (
        RankingBootstrapCommand
        if isinstance(command, RankingBootstrapCommand)
        else RankingWeekCommand
    )
    return model.model_validate_json(command.model_dump_json())


def verify_ranking_command_inputs(
    receipt, snapshot, history
) -> RankingInputManifest | None:
    """Legacy receipts remain readable; versioned manifests must verify fully."""
    from beta_engine.domain.rankings.command_audit import verify_request_payload

    verify_request_payload(
        receipt.request_payload_json,
        request_fingerprint=receipt.request_fingerprint,
        command_id=receipt.command_id,
        snapshot=snapshot,
    )
    if receipt.input_manifest_version is None and receipt.input_manifest_json is None:
        return
    if receipt.input_manifest_version != 1 or receipt.input_manifest_json is None:
        raise ValueError("Missing or unsupported ranking input manifest")
    manifest = RankingInputManifest.model_validate_json(receipt.input_manifest_json)
    if manifest.command_request_fingerprint is not None and (
        receipt.request_payload_json is None
        or manifest.command_request_fingerprint != receipt.request_fingerprint
    ):
        raise ValueError("Ranking manifest requires its original command payload")
    previous = next(
        (s for s in history if s.fingerprint == snapshot.previous_fingerprint), None
    )
    manifest.verify(snapshot, previous)
    return manifest
