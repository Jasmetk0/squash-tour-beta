"""Immutable, scoped authority for the ranking part of a Week Transition."""

import hashlib
import json
from pydantic import Field, model_validator

from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingPlayer, OfficialRankingPolicy, RankingWeek


class RankingTransitionAuthority(FrozenInput):
    schema_version: str = "ranking_transition_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    base_revision_id: str = Field(min_length=1)
    completed_week: RankingWeek
    target_week: RankingWeek
    players: tuple[OfficialRankingPlayer, ...]
    policy: OfficialRankingPolicy
    provenance: str = Field(min_length=1, max_length=2000)
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    audit: RankingCommandAudit

    @model_validator(mode="after")
    def validate_boundary(self):
        if self.target_week.ordinal != self.completed_week.ordinal + 1:
            raise ValueError("Authority requires a consecutive completed/target boundary")
        ids = [player.player_id for player in self.players]
        tokens = [player.tie_break_token for player in self.players]
        if ids != sorted(set(ids)) or len(set(tokens)) != len(tokens):
            raise ValueError("Authority requires a complete canonical roster with unique identities")
        if any(player.tour_entry_week.ordinal > self.target_week.ordinal for player in self.players):
            raise ValueError("Authority roster contains a future Tour entrant")
        return self

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()
