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
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.official import OfficialRankingSnapshot
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
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
        self, factory: sessionmaker[Session], awards: SeasonPointAwardsService
    ):
        self.factory = factory
        self.awards = awards

    def execute(self, command: RankingWeekCommand) -> OfficialRankingSnapshot:
        command = RankingWeekCommand.model_validate_json(command.model_dump_json())
        context = command.context
        with self.factory.begin() as session:
            # Lock before reading the head/receipt: competing SQLite commands
            # cannot both decide that a request is new and then stage different data.
            session.execute(text("BEGIN IMMEDIATE"))
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
                return snapshot
            if any(s.week == context.target_week for s in history):
                raise ValueError("Ranking target already staged by another command or pathway")
            sources = OfficialRankingResultStore(session)
            for binding in sorted(command.tournaments, key=lambda t: t.edition_id):
                ingest_tournament_ranking_sources(self.awards, sources, binding)
            snapshot = stage_official_ranking_from_history(candidates, sources, context)
            session.add(
                OfficialRankingCommandModel(
                    run_id=context.run_id,
                    branch_id=context.branch_id,
                    command_id=command.command_id,
                    request_fingerprint=command.fingerprint,
                    target_ordinal=context.target_week.ordinal,
                    snapshot_fingerprint=snapshot.fingerprint,
                )
            )
            session.flush()
            return snapshot
