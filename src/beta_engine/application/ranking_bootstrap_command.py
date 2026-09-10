"""Explicit initial candidate preparation from a resolved roster and policy."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import (
    FrozenInput,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
)


class RankingBootstrapCommand(FrozenInput):
    kind: Literal["initial_ranking.v1"] = "initial_ranking.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_week: RankingWeek = RankingWeek(season_index=0, week=1)
    policy: OfficialRankingPolicy
    players: tuple[OfficialRankingPlayer, ...]
    discipline: Literal["none"]

    @model_validator(mode="after")
    def require_initial_week(self):
        if self.target_week.ordinal != 0:
            raise ValueError("Initial ranking command requires the Run's first week")
        return self

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        payload["players"].sort(key=lambda p: p["player_id"])
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
