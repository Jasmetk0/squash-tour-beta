"""Application DTOs for deterministic next-season run bootstrapping and lineage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BootstrapNextSeasonRequest(BaseModel):
    child_run_id: str = Field(min_length=1, max_length=128)
    child_seed: int | None = None


class RunSourceSummary(BaseModel):
    source_type: Literal["fresh_seed", "rollover_bootstrap"]
    parent_run_id: str | None = None
    source_rollover_run_id: str | None = None
    source_rollover_from_season: int | None = None
    source_rollover_to_season: int | None = None


class RunLineageRecord(BaseModel):
    run_id: str
    source: RunSourceSummary
    children: list[str] = Field(default_factory=list)


class BootstrapNextSeasonResponse(BaseModel):
    parent_run_id: str
    child_run_id: str
    from_season: int = Field(ge=1900)
    to_season: int = Field(ge=1900)
    child_seed: int
    transitioned_players: int = Field(ge=0)
    source_rollover_run_id: str
    source_rollover_to_season: int = Field(ge=1900)
    already_bootstrapped: bool = False
