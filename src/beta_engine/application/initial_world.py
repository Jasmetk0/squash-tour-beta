"""Immutable Run/Branch-owned initial player and ranking-policy state."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.rankings.official import OfficialRankingPlayer, RankingWeek


class InitialWorldState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["initial_world_state.v1"] = "initial_world_state.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    season: Literal["2000/2001"] = "2000/2001"
    players: tuple[SeasonActivePlayer, ...]
    policies: tuple[OfficialRankingPolicy, ...] = ()
    source_kind: Literal["production_initial_pool.v1"]
    source_season: str = Field(min_length=1)
    source_fingerprint: str = Field(min_length=1)
    bootstrap_seed: int
    bootstrap_fingerprint: str = Field(min_length=1)
    adopted_by_command_id: str = Field(min_length=1, max_length=128)
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    adoption_request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_complete_state(self) -> "InitialWorldState":
        ids = [player.player_id for player in self.players]
        if not ids:
            raise ValueError("Initial player source is empty")
        if ids != sorted(set(ids)):
            raise ValueError("Initial players must have unique canonical player IDs")
        if any(
            player.season != self.season or player.active_status != "active"
            for player in self.players
        ):
            raise ValueError(
                "Initial world requires active players for its first season"
            )
        policy_ids = [policy.policy_id for policy in self.policies]
        if policy_ids != sorted(set(policy_ids)):
            raise ValueError("Ranking policies must have unique canonical identities")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()


class InitialWorldAdoptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    command_id: str = Field(min_length=1, max_length=128)
    source_season: Literal["2000/2001"] = "2000/2001"
    bootstrap_seed: int
    audit_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    official_run: bool = False
    best_n: int | None = Field(default=None, ge=1)
    automatic_retirement_age: int | None = Field(default=None, ge=16, le=120)

    @model_validator(mode="after")
    def policy_is_explicit(self) -> "InitialWorldAdoptionRequest":
        if self.official_run and self.best_n not in (None, 15):
            raise ValueError("Official Run first-season policy is Best 15")
        if not self.official_run and self.best_n is None:
            raise ValueError("Custom Run requires an explicit first-season Best N")
        if self.official_run and self.automatic_retirement_age not in (None, 46):
            raise ValueError("Official Run automatic retirement age is 46")
        return self

    def fingerprint_for_scope(self, *, run_id: str, branch_id: str) -> str:
        request = self.model_dump(mode="json")
        if request["automatic_retirement_age"] is None:
            request.pop("automatic_retirement_age")
        payload = {"run_id": run_id, "branch_id": branch_id, **request}
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def derive_initial_ranking_inputs(
    state: InitialWorldState,
) -> tuple[OfficialRankingPolicy, tuple[OfficialRankingPlayer, ...]]:
    """Derive the only world-backed initial ranking inputs from owned state."""
    if len(state.policies) != 1:
        raise ValueError("Exactly one first-season ranking policy is required")
    players = []
    for player in state.players:
        identity = json.dumps(
            {
                "player_id": player.player_id,
                "birth_year": player.birth_year,
                "birth_year_week": player.birth_year_week,
                "source": player.source_generation_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        players.append(
            OfficialRankingPlayer(
                player_id=player.player_id,
                tie_break_token=hashlib.sha256(identity.encode()).hexdigest(),
                tour_entry_week=RankingWeek(season_index=0, week=1),
                retired=False,
            )
        )
    return state.policies[0], tuple(players)
