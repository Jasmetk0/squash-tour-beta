"""Read-only canonical Viewer World Tour Finals Race surface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_finals_race_read_model import (
    ViewerFinalsRaceHistory,
    resolve_viewer_finals_race_history,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)

router = APIRouter(tags=["viewer-finals-race"])


@router.get(
    "/viewer/runs/{product_run_id:path}/race/finals",
    response_model=ViewerFinalsRaceHistory,
)
def get_viewer_finals_race(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerFinalsRaceHistory:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        return resolve_viewer_finals_race_history(
            snapshot.simulation_slot_component,
            run_id=product_run_id,
            branch_id=snapshot.context.official_branch_id,
        )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_finals_race_unavailable", "message": str(exc)},
        ) from exc
