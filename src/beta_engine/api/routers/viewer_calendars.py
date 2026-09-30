"""Read-only Viewer Run Calendar boundary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_calendar_read_model import (
    ViewerRunCalendar,
    resolve_viewer_run_calendar,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state


router = APIRouter(tags=["viewer-calendar"])


@router.get(
    "/viewer/runs/{product_run_id:path}/calendar",
    response_model=ViewerRunCalendar,
)
def get_viewer_run_calendar(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerRunCalendar:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        package_state = load_saved_run_package_state(
            snapshot.revision.payload,
            run_id=product_run_id,
            branch_id=snapshot.context.official_branch_id,
        )
        return resolve_viewer_run_calendar(
            package_state,
            snapshot.ranking,
            run_id=product_run_id,
            branch_id=snapshot.context.official_branch_id,
        )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_calendar_unavailable", "message": str(exc)},
        ) from exc
