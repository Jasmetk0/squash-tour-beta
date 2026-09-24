"""Read-only Viewer Tournament Draw boundary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_tournament_draw_read_model import (
    ViewerTournamentDraw,
    resolve_viewer_tournament_draw,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)


router = APIRouter(tags=["viewer-tournament-draws"])


@router.get(
    "/viewer/runs/{product_run_id:path}/tournaments/{event_id}/draw",
    response_model=ViewerTournamentDraw,
)
def get_viewer_tournament_draw(
    product_run_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerTournamentDraw:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        return resolve_viewer_tournament_draw(
            snapshot.simulation_slot_component,
            run_id=product_run_id,
            branch_id=snapshot.context.official_branch_id,
            event_id=event_id,
        )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_tournament_draw_unavailable", "message": str(exc)},
        ) from exc
