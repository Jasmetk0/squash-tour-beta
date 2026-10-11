"""Immutable tournament binding to one published Official Ranking snapshot."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingSnapshot,
    RankingWeek,
)


class TournamentRankingSnapshotAuthority(FrozenInput):
    """One event-scoped ranking snapshot used across its Entry/Draw process."""

    schema_version: Literal["tournament_ranking_snapshot_authority.v1"] = (
        "tournament_ranking_snapshot_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    ranking_week: RankingWeek
    ranking_snapshot: OfficialRankingSnapshot
    adopted_by_command_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def validate_scope_and_week(self) -> "TournamentRankingSnapshotAuthority":
        if (
            self.ranking_snapshot.run_id,
            self.ranking_snapshot.branch_id,
            self.ranking_snapshot.week,
        ) != (self.run_id, self.branch_id, self.ranking_week):
            raise ValueError(
                "Tournament Ranking Snapshot authority scope/week differs from "
                "the published Official Ranking snapshot"
            )
        return self

    @property
    def ranking_snapshot_fingerprint(self) -> str:
        return self.ranking_snapshot.fingerprint

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
