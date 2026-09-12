"""Admin ranking inspection and explicit preparation Save; no publication."""

from typing import Annotated
import json
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
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






def _prepare(runtime, run_id, branch_id, payload, model):
    try:
        # Strict domain tuples validate in JSON mode; arrays are their wire form.
        command = model.model_validate_json(json.dumps(payload))
        if command.audit is None:
            raise ValueError("Admin audit is required")
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_ranking_command",
                            "message": "A valid ranking command with audit label and reason is required."}) from exc
    try:
        snapshot = runtime.repository.prepare_official_ranking(run_id=run_id, branch_id=branch_id, command=command)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "ranking_preparation_conflict",
                            "message": "Ranking preparation was rejected; verify scope, history and input dependencies."}) from exc
    return RankingCandidateDetail(snapshot=snapshot, fingerprint=snapshot.fingerprint, command_ids=(command.command_id,))


@router.post("/prepare/initial", response_model=RankingCandidateDetail, status_code=201)
def prepare_initial(run_id: str, branch_id: str, payload: dict,
                    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    return _prepare(runtime, run_id, branch_id, payload, RankingBootstrapCommand)


@router.post("/prepare/week", response_model=RankingCandidateDetail, status_code=201)
def prepare_week(run_id: str, branch_id: str, payload: dict,
                 runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    return _prepare(runtime, run_id, branch_id, payload, RankingWeekCommand)


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
