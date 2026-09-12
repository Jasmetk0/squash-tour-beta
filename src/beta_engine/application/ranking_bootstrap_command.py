"""Explicit initial candidate preparation from a resolved roster and policy."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator, model_serializer

from beta_engine.domain.rankings.zero_history import RankingZeroVersion
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.application.ranking_zero_batch import validate_zero_batch, canonicalize_zero_batch

from beta_engine.domain.rankings.official import (
    WithDisciplinaryZeros,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    RankingWeek,
)


class RankingBootstrapCommand(WithDisciplinaryZeros):
    kind: Literal["initial_ranking.v1"] = "initial_ranking.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    target_week: RankingWeek = RankingWeek(season_index=0, week=1)
    policy: OfficialRankingPolicy
    players: tuple[OfficialRankingPlayer, ...]
    discipline: Literal["none", "resolved_zeros", "stored_zeros"]

    zero_versions: tuple[RankingZeroVersion, ...] = ()
    audit: RankingCommandAudit | None = None

    @model_serializer(mode="wrap")
    def serialize_command(self, handler):
        payload = handler(self)
        if self.audit is None:
            payload.pop("audit", None)
        if not self.zero_versions:
            payload.pop("zero_versions", None)
        if not self.disciplinary_zeros:
            payload.pop("disciplinary_zeros", None)
        return payload

    @model_validator(mode="after")
    def acknowledge_discipline(self):
        validate_zero_batch(self.zero_versions, self)
        if self.disciplinary_zeros and self.discipline != "resolved_zeros":
            raise ValueError("Disciplinary zeros require explicit resolved_zeros mode")
        return self


    @model_validator(mode="after")
    def require_initial_week(self):
        if self.target_week.ordinal != 0:
            raise ValueError("Initial ranking command requires the Run's first week")
        return self

    @property
    def canonical_request_json(self) -> str:
        payload = self.model_dump(mode="json")
        canonicalize_zero_batch(payload)
        if "disciplinary_zeros" in payload:
            payload["disciplinary_zeros"].sort(key=lambda z: z["zero_id"])
        payload["players"].sort(key=lambda p: p["player_id"])
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_request_json.encode()).hexdigest()
