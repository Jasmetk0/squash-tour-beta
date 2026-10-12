"""Exact Saved Revision Country Match Records, read-only and Branch-reachable."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from beta_engine.api.deps import get_run_saved_revision_history_service
from beta_engine.application.run_saved_revision_history_service import RunSavedRevisionHistoryService
from beta_engine.application.country_player_standings import (
    CountryPlayerStandings, resolve_country_player_standings,
)
from beta_engine.application.country_saved_match_records import (
    CountrySavedMatchRecords, resolve_country_saved_match_records,
)
from beta_engine.infrastructure.db import (
    SavedRevisionHistoryNotFoundError, SavedRevisionHistoryConflictError,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}",
    tags=["admin-country-match-records"],
)


@router.get("/country-match-records/{country_code}", response_model=CountrySavedMatchRecords)
def get_country_match_records(
    run_id: str, branch_id: str, country_code: str,
    service: Annotated[RunSavedRevisionHistoryService, Depends(get_run_saved_revision_history_service)],
    revision_id: str = Query(min_length=1, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=50),
    season_index: int | None = Query(default=None, ge=0, le=49),
    result_kind: Literal["all", "played", "walkover"] = Query(default="all"),
    outcome: Literal["all", "win", "loss"] = Query(default="all"),
) -> CountrySavedMatchRecords:
    if not country_code.isalpha() or not country_code.isupper() or len(country_code) != 3:
        raise HTTPException(status_code=422, detail="Country code must be three uppercase letters")
    try:
        # Get exact selected-Branch-reachable revision. A shared ancestor keeps its
        # ORIGINAL Branch owner; never rebind historical sport source identities.
        detail = service.get_revision(
            run_id=run_id, branch_id=branch_id, revision_id=revision_id,
        )
        saved = detail.saved_revision
        origin = saved.branch_id
        payload = saved.payload
        return resolve_country_saved_match_records(
            run_id=run_id, selected_branch_id=branch_id,
            revision_branch_id=origin, saved_revision_id=saved.revision_id,
            country_code=country_code,
            packages=load_saved_run_package_state(
                payload, run_id=run_id, branch_id=origin,
            ),
            ranking=load_saved_ranking_component(
                payload, run_id=run_id, branch_id=origin,
            ),
            initial_world=load_saved_initial_world(
                payload, run_id=run_id, branch_id=origin,
            ),
            prospect_source=load_saved_run_prospect_source(payload, run_id=run_id),
            offset=offset, limit=limit, season_index=season_index,
            result_kind=result_kind, outcome=outcome,
        )
    except SavedRevisionHistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (SavedRevisionHistoryConflictError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=409, detail={
            "code": "country_match_records_unavailable", "message": str(exc)
        }) from exc


@router.get("/country-player-standings/{country_code}", response_model=CountryPlayerStandings)
def get_country_player_standings(
    run_id: str, branch_id: str, country_code: str,
    service: Annotated[RunSavedRevisionHistoryService, Depends(get_run_saved_revision_history_service)],
    revision_id: str = Query(min_length=1, max_length=128),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=50),
) -> CountryPlayerStandings:
    """Rank published Saved athletes, never mutable snapshots or live standings."""
    if len(country_code) != 3 or not country_code.isalpha() or not country_code.isupper():
        raise HTTPException(status_code=422, detail="Country code must be three uppercase letters")
    try:
        detail = service.get_revision(
            run_id=run_id, branch_id=branch_id, revision_id=revision_id,
        )
        saved = detail.saved_revision
        origin = saved.branch_id
        payload = saved.payload
        return resolve_country_player_standings(
            run_id=run_id, selected_branch_id=branch_id,
            revision_branch_id=origin, saved_revision_id=saved.revision_id,
            country_code=country_code,
            packages=load_saved_run_package_state(
                payload, run_id=run_id, branch_id=origin,
            ),
            ranking=load_saved_ranking_component(
                payload, run_id=run_id, branch_id=origin,
            ),
            initial_world=load_saved_initial_world(
                payload, run_id=run_id, branch_id=origin,
            ),
            prospect_source=load_saved_run_prospect_source(
                payload, run_id=run_id,
            ),
            offset=offset, limit=limit,
        )
    except SavedRevisionHistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (SavedRevisionHistoryConflictError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=409, detail={
            "code": "country_player_standings_unavailable", "message": str(exc)
        }) from exc
