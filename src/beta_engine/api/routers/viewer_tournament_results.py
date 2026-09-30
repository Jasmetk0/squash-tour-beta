"""Read-only Viewer Tournament Result boundary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_tournament_result_read_model import (
    ViewerCompletedTournamentCollection,
    ViewerTournamentResult,
    resolve_viewer_completed_tournaments,
    resolve_viewer_tournament_result,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)


router = APIRouter(tags=["viewer-tournament-results"])


@router.get(
    "/viewer/runs/{product_run_id:path}/tournaments/completed",
    response_model=ViewerCompletedTournamentCollection,
)
def list_viewer_completed_tournaments(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerCompletedTournamentCollection:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        return resolve_viewer_completed_tournaments(
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
            detail={"code": "viewer_completed_tournaments_unavailable", "message": str(exc)},
        ) from exc


@router.get(
    "/viewer/runs/{product_run_id:path}/tournaments/{event_id}/result",
    response_model=ViewerTournamentResult,
)
def get_viewer_tournament_result(
    product_run_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerTournamentResult:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        return resolve_viewer_tournament_result(
            snapshot.ranking,
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
            detail={"code": "viewer_tournament_result_unavailable", "message": str(exc)},
        ) from exc
