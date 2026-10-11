"""Read-only canonical Viewer tournament history boundary."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_tournament_history_read_model import (
    ViewerTournamentHistory,
    resolve_viewer_tournament_history,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)


router = APIRouter(tags=["viewer-tournament-history"])


@router.get(
    "/viewer/runs/{product_run_id:path}/tournaments",
    response_model=ViewerTournamentHistory,
)
def get_viewer_tournament_history(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerTournamentHistory:
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=product_run_id
        )
        return resolve_viewer_tournament_history(
            run_package_state=snapshot.run_package_state,
            ranking=snapshot.ranking,
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
            detail={"code": "viewer_tournament_history_unavailable", "message": str(exc)},
        ) from exc
