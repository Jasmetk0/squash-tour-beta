"""Admin-only candidate inspection; no Viewer publication or mutation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.ranking_inspection import (
    RankingCandidateDetail,
    RankingCandidateHistory,
    RankingCandidateSources,
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
