"""Explicit publication boundary for the initial Official Ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.rankings.official import RankingWeek, load_official_ranking_snapshot
from beta_engine.infrastructure.db.models import (
    AuthoritativeWorldStateModel,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
)
from beta_engine.infrastructure.db.official_rankings import OfficialRankingCandidateStore


class InitialOfficialRankingPublication(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["initial_official_ranking_publication.v1"] = (
        "initial_official_ranking_publication.v1"
    )
    run_id: str
    branch_id: str
    week: RankingWeek
    ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_retry: bool


@dataclass(slots=True)
class InitialOfficialRankingPublicationService:
    factory: sessionmaker[Session]

    def publish(
        self,
        *,
        run_id: str,
        branch_id: str,
        expected_ranking_fingerprint: str,
    ) -> InitialOfficialRankingPublication:
        with self.factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            run = session.get(RunContainerModel, run_id)
            branch = session.get(RunBranchModel, branch_id)
            if run is None or branch is None or branch.run_id != run_id:
                raise ValueError("Initial ranking publication Run/Branch scope does not exist")
            if run.read_only or branch.read_only or branch.status != "active":
                raise ValueError("Initial ranking publication requires a writable active Run/Branch")

            history = OfficialRankingCandidateStore(session).history(
                run_id=run_id,
                branch_id=branch_id,
            )
            if len(history) != 1 or history[0].week.ordinal != 0:
                raise ValueError(
                    "Initial ranking publication requires exactly one Week-1 bootstrap candidate"
                )
            candidate = history[0]
            if candidate.fingerprint != expected_ranking_fingerprint:
                raise ValueError("Initial ranking candidate changed since publication review")

            publication = session.get(
                PublishedOfficialRankingModel,
                (run_id, branch_id, 0),
            )
            world = session.get(
                AuthoritativeWorldStateModel,
                (run_id, branch_id),
            )
            if publication is not None or world is not None:
                if publication is None or world is None:
                    raise ValueError(
                        "Initial ranking publication/world state is partially persisted"
                    )
                published = load_official_ranking_snapshot(
                    publication.payload_json,
                    expected_fingerprint=publication.snapshot_fingerprint,
                    run_id=run_id,
                    branch_id=branch_id,
                    week=RankingWeek(season_index=0, week=1),
                )
                if (
                    published != candidate
                    or world.current_ordinal != 0
                    or world.ranking_fingerprint != candidate.fingerprint
                ):
                    raise ValueError(
                        "Existing initial ranking publication differs from bootstrap candidate"
                    )
                return InitialOfficialRankingPublication(
                    run_id=run_id,
                    branch_id=branch_id,
                    week=candidate.week,
                    ranking_fingerprint=candidate.fingerprint,
                    exact_retry=True,
                )

            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=0,
                    snapshot_fingerprint=candidate.fingerprint,
                    payload_json=candidate.model_dump_json(),
                )
            )
            session.add(
                AuthoritativeWorldStateModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    current_ordinal=0,
                    ranking_fingerprint=candidate.fingerprint,
                )
            )
            session.flush()
            return InitialOfficialRankingPublication(
                run_id=run_id,
                branch_id=branch_id,
                week=candidate.week,
                ranking_fingerprint=candidate.fingerprint,
                exact_retry=False,
            )
