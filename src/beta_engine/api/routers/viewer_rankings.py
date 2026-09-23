"""Read-only canonical Viewer Official Ranking surface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_official_ranking_read_model import (
    ViewerOfficialRanking,
    resolve_viewer_official_ranking,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)

router = APIRouter(tags=["viewer-rankings"])


@router.get(
    "/viewer/runs/{product_run_id:path}/rankings/current",
    response_model=ViewerOfficialRanking,
)
def get_viewer_current_official_ranking(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerOfficialRanking:
    try:
        context = runtime.repository.get_viewer_official_run_context(
            product_run_id=product_run_id
        )
        with runtime.repository._session_factory() as session:
            return resolve_viewer_official_ranking(
                session,
                run_id=product_run_id,
                branch_id=context.official_branch_id,
            )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_official_ranking_unavailable", "message": str(exc)},
        ) from exc
