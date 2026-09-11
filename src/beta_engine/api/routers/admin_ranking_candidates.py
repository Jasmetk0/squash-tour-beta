"""Admin ranking inspection and explicit preparation Save; no publication."""

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field
from beta_engine.application.run_working_draft_service import RunWorkingDraftService

from fastapi import APIRouter, Depends, HTTPException, Path

from beta_engine.api.deps import ApiRuntime, get_runtime, get_run_working_draft_service
from beta_engine.application.ranking_inspection import (
    RankingCandidateDetail,
    RankingCandidateHistory,
    RankingCandidateSources,
    RankingCandidateInputs,
)

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates",
    tags=["admin-rankings"],
)


def _history(
    runtime: ApiRuntime, run_id: str, branch_id: str
) -> RankingCandidateHistory:
    try:
        return runtime.repository.inspect_official_ranking_history(
            run_id=run_id, branch_id=branch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Ranking Run/Branch scope not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_history_unavailable", "message": str(exc)},
        ) from exc


@router.get("", response_model=RankingCandidateHistory)
def get_history(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    return _history(runtime, run_id, branch_id)






class RankingSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_draft_version: int = Field(ge=0)
    expected_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/save/preview")
def preview_save(run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return runtime.repository.preview_ranking_save(run_id=run_id, branch_id=branch_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={"code": "ranking_save_unavailable", "message": str(exc)}) from exc


@router.post("/save", status_code=201)
def save_ranking(
    run_id: str, branch_id: str, payload: RankingSaveRequest,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        return service.save_ranking(run_id=run_id, branch_id=branch_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "ranking_save_conflict", "message": str(exc)}) from exc


@router.get("/{season_index}/{week}", response_model=RankingCandidateDetail)
def get_candidate(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    history = _history(runtime, run_id, branch_id)
    for candidate in history.candidates:
        if (candidate.snapshot.week.season_index, candidate.snapshot.week.week) == (
            season_index,
            week,
        ):
            return candidate
    raise HTTPException(status_code=404, detail="Ranking candidate week not found")


@router.get("/{season_index}/{week}/sources", response_model=RankingCandidateSources)
def get_sources(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    from beta_engine.domain.rankings.official import RankingWeek

    try:
        return runtime.repository.inspect_official_ranking_sources(
            run_id=run_id, branch_id=branch_id,
            week=RankingWeek(season_index=season_index, week=week),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Ranking scope or candidate week not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={
            "code": "ranking_sources_unavailable",
            "message": "Stored ranking sources could not be verified.",
        }) from exc


@router.get("/{season_index}/{week}/inputs", response_model=RankingCandidateInputs)
def get_inputs(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    from beta_engine.domain.rankings.official import RankingWeek

    try:
        return runtime.repository.inspect_official_ranking_inputs(
            run_id=run_id, branch_id=branch_id,
            week=RankingWeek(season_index=season_index, week=week),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Ranking scope or candidate week not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={
            "code": "ranking_inputs_unavailable",
            "message": "Stored ranking inputs could not be verified.",
        }) from exc
