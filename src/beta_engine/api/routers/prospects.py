"""Read-only Admin and Viewer prospect visibility surfaces."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.visible_prospect_read_model import (
    VisiblePreTourProspects,
    resolve_visible_pre_tour_prospects,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)

router = APIRouter(tags=["prospects"])


def _requested_week(
    *,
    season_index: int | None,
    week: int | None,
) -> RankingWeek | None:
    if season_index is None and week is None:
        return None
    if season_index is None or week is None:
        raise ValueError("season_index and week must be supplied together")
    return RankingWeek(season_index=season_index, week=week)


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/prospects/visible",
    response_model=VisiblePreTourProspects,
)
def get_admin_visible_prospects(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    season_index: int | None = Query(default=None, ge=0, le=49),
    week: int | None = Query(default=None, ge=1, le=61),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> VisiblePreTourProspects:
    try:
        target = _requested_week(season_index=season_index, week=week)
        with runtime.repository._session_factory() as session:
            return resolve_visible_pre_tour_prospects(
                session,
                run_id=run_id,
                branch_id=branch_id,
                week=target,
                limit=limit,
                offset=offset,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "prospect_read_model_unavailable", "message": str(exc)},
        ) from exc


@router.get(
    "/viewer/runs/{product_run_id:path}/prospects/next-gen",
    response_model=VisiblePreTourProspects,
)
def get_viewer_visible_prospects(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> VisiblePreTourProspects:
    try:
        context = runtime.repository.get_viewer_official_run_context(
            product_run_id=product_run_id
        )
        with runtime.repository._session_factory() as session:
            return resolve_visible_pre_tour_prospects(
                session,
                run_id=product_run_id,
                branch_id=context.official_branch_id,
                limit=limit,
                offset=offset,
            )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (ViewerOfficialRunContextConflictError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "prospect_read_model_unavailable", "message": str(exc)},
        ) from exc
