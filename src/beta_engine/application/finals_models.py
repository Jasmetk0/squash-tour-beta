"""Application DTOs for World Tour Finals orchestration/persistence/API mapping."""

from __future__ import annotations

from pydantic import BaseModel
from beta_engine.domain.finals import FinalsQualificationResult, FinalsResult


class PersistedFinalsQualification(BaseModel):
    run_id: str
    season: int
    source_as_of_season: int
    source_as_of_week: int
    qualification: FinalsQualificationResult


class PersistedFinalsResult(BaseModel):
    run_id: str
    season: int
    event_id: str
    source_as_of_season: int
    source_as_of_week: int
    result: FinalsResult


class FinalsSimulationResult(BaseModel):
    run_id: str
    season: int
    event_id: str
    qualification: PersistedFinalsQualification
    result: PersistedFinalsResult
    already_simulated: bool


class FinalsSummaryResponse(BaseModel):
    run_id: str
    season: int
    qualification: PersistedFinalsQualification | None
    result: PersistedFinalsResult | None
