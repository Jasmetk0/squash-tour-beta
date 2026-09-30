"""Read-only canonical Viewer players and countries boundaries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.viewer_people_read_model import (
    ViewerCountries,
    ViewerPlayers,
    resolve_viewer_countries,
    resolve_viewer_players,
)
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.player_lifecycle_state import load_saved_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import load_saved_sporting
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)


router = APIRouter(tags=["viewer-people"])


def _resolve_people(
    *,
    product_run_id: str,
    runtime: ApiRuntime,
) -> ViewerPlayers:
    snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
        product_run_id=product_run_id
    )
    branch_id = snapshot.context.official_branch_id
    payload = snapshot.revision.payload
    return resolve_viewer_players(
        initial_world=load_saved_initial_world(
            payload,
            run_id=product_run_id,
            branch_id=branch_id,
        ),
        lifecycle_states=load_saved_lifecycle(
            payload,
            run_id=product_run_id,
            branch_id=branch_id,
        ),
        sporting_states=load_saved_sporting(
            payload,
            run_id=product_run_id,
            branch_id=branch_id,
        ),
        prospect_source=load_saved_run_prospect_source(
            payload,
            run_id=product_run_id,
        ),
        run_id=product_run_id,
        branch_id=branch_id,
    )


@router.get(
    "/viewer/runs/{product_run_id:path}/players",
    response_model=ViewerPlayers,
)
def get_viewer_players(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerPlayers:
    try:
        return _resolve_people(product_run_id=product_run_id, runtime=runtime)
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_players_unavailable", "message": str(exc)},
        ) from exc


@router.get(
    "/viewer/runs/{product_run_id:path}/countries",
    response_model=ViewerCountries,
)
def get_viewer_countries(
    product_run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> ViewerCountries:
    try:
        return resolve_viewer_countries(
            _resolve_people(product_run_id=product_run_id, runtime=runtime)
        )
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (ViewerOfficialRunContextConflictError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "viewer_countries_unavailable", "message": str(exc)},
        ) from exc
