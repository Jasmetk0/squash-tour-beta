"""Command contract for the first atomic canonical Week Transition slice."""

from __future__ import annotations

import hashlib
import json

from pydantic import Field, model_validator

from beta_engine.application.ranking_tournament_ingestion import TournamentRankingBinding
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.result_history import RankingResultVersion
from beta_engine.domain.rankings.zero_history import RankingZeroVersion


class AuthoritativeWeekTransitionCommand(FrozenInput):
    """Frozen confirmation input; unresolved lifecycle mechanics are not defaulted."""

    kind: str = "authoritative_week_transition.v1"
    command_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    base_revision_id: str = Field(min_length=1)
    completed_week: RankingWeek
    target_week: RankingWeek
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    tournaments: tuple[TournamentRankingBinding, ...] = ()
    corrections: tuple[RankingResultVersion, ...] = ()
    zero_versions: tuple[RankingZeroVersion, ...] = ()
    audit: RankingCommandAudit

    @model_validator(mode="after")
    def validate_boundary(self):
        if self.target_week.ordinal != self.completed_week.ordinal + 1:
            raise ValueError("Week Transition requires a consecutive boundary")
        return self

    @property
    def canonical_request_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_request_json.encode()).hexdigest()


class AuthoritativeWeekTransitionResult(FrozenInput):
    run_id: str
    branch_id: str
    command_id: str
    completed_week: RankingWeek
    target_week: RankingWeek
    official_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_event_kind: str = "week_transition_completed"
