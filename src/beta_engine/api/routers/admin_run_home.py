"""Narrow, read-only Run Home projection from the selected Branch Saved Revision."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.saved_player_match_detail import (SavedPlayerMatchDetail, resolve_saved_player_match_detail)
from beta_engine.infrastructure.db.simulation_slot_state import load_saved_simulation_slot_component
from beta_engine.application.saved_player_profile import (SavedPlayerProfile, resolve_saved_player_profile)
from beta_engine.application.saved_players_inventory import (SavedPlayersInventory, resolve_saved_players_inventory)
from beta_engine.application.saved_player_match_history import (SavedPlayerMatchHistory, resolve_saved_player_match_history)
from beta_engine.application.run_home_player_identity import (
    SavedHomePlayerIdentities,
    resolve_saved_home_player_identities,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source
from beta_engine.application.run_home_ranking_changes import (
    RunHomeRankingChanges,
    resolve_run_home_ranking_changes,
)
from beta_engine.application.run_home_activity_read_model import (
    RunHomeActivity,
    resolve_run_home_activity,
)
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.infrastructure.db.saved_revision_rankings import load_saved_ranking_component


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}",
    tags=["admin-run-home"],
)


@router.get("/home-activity", response_model=RunHomeActivity)
def inspect_run_home_activity(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> RunHomeActivity:
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if state.run_id != run_id or state.branch_id != branch_id:
            raise ValueError("Saved Revision state has wrong Run / Branch identity")
        # A shared pre-fork ancestor may be readable history, but it cannot be
        # relabelled as current Branch-owned sporting evidence without remapping.
        if revision.run_id != run_id or revision.branch_id != branch_id:
            raise ValueError("Saved Revision is not yet Branch-owned for this Home view")
        if branch.saved_head_revision_id != revision.revision_id:
            raise ValueError("Saved Revision HEAD changed during Run Home inspection")
        packages = load_saved_run_package_state(
            revision.payload, run_id=run_id, branch_id=branch_id,
        )
        ranking = load_saved_ranking_component(
            revision.payload, run_id=run_id, branch_id=branch_id,
        )
        location = repository.get_branch_state(branch_id=branch_id)
        if location is not None and location.run_id != run_id:
            raise ValueError("Branch time locator belongs to a different Run")
        return resolve_run_home_activity(
            run_id=run_id,
            branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            packages=packages,
            ranking=ranking,
            current_season=location.current_season if location else None,
            current_week=location.current_week if location else None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "run_home_activity_unavailable", "message": str(exc)},
        ) from exc


@router.get("/home-ranking-changes", response_model=RunHomeRankingChanges)
def inspect_run_home_ranking_changes(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> RunHomeRankingChanges:
    """Read only the selected Branch's *saved* HEAD, never live ranking state."""
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ):
            raise ValueError("Saved ranking revision belongs to a different Run / Branch")
        if branch.saved_head_revision_id != revision.revision_id:
            raise ValueError("Saved ranking HEAD differs from the selected Branch")
        ranking = load_saved_ranking_component(
            revision.payload, run_id=run_id, branch_id=branch_id,
        )
        return resolve_run_home_ranking_changes(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id, ranking=ranking,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "run_home_ranking_unavailable", "message": str(exc)},
        ) from exc





@router.get("/player-profiles/{player_id}/matches/{event_id}/{match_id}", response_model=SavedPlayerMatchDetail)
def get_saved_player_match_detail(
    run_id: str,
    branch_id: str,
    player_id: str,
    event_id: str,
    match_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=25),
) -> SavedPlayerMatchDetail:
    """Read published result; replay only from verified matching Saved Slot group."""
    if any(not item or len(item) > 128 or item.strip() != item
           for item in (player_id, event_id, match_id)):
        raise HTTPException(status_code=422, detail="Invalid match detail identifiers")
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ) or revision.revision_id != branch.saved_head_revision_id:
            raise ValueError("Saved match detail HEAD belongs to another Run/Branch")
        identities = resolve_saved_home_player_identities(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id, requested_ids=(player_id,),
            initial_world=load_saved_initial_world(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            prospect_source=load_saved_run_prospect_source(
                revision.payload, run_id=run_id,
            ),
        )
        return resolve_saved_player_match_detail(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            player_id=player_id, event_id=event_id, match_id=match_id,
            identities=identities,
            ranking=load_saved_ranking_component(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            packages=load_saved_run_package_state(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            saved_slots=load_saved_simulation_slot_component(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            offset=offset, limit=limit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "saved_match_detail_unavailable", "message": str(exc)},
        ) from exc


@router.get("/player-profiles/{player_id}/matches", response_model=SavedPlayerMatchHistory)
def get_saved_player_matches(
    run_id: str,
    branch_id: str,
    player_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    season_index: int | None = Query(default=None, ge=0, le=49),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=20),
) -> SavedPlayerMatchHistory:
    """Only verified Saved HEAD and canonical completed tournament results."""
    if not player_id or len(player_id) > 128 or player_id.strip() != player_id:
        raise HTTPException(status_code=422, detail="Invalid player identifier")
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ) or revision.revision_id != branch.saved_head_revision_id:
            raise ValueError("Saved match history belongs to another Run/Branch HEAD")
        identities = resolve_saved_home_player_identities(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id, requested_ids=(player_id,),
            initial_world=load_saved_initial_world(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            prospect_source=load_saved_run_prospect_source(
                revision.payload, run_id=run_id,
            ),
        )
        return resolve_saved_player_match_history(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id, player_id=player_id,
            identities=identities,
            ranking=load_saved_ranking_component(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            packages=load_saved_run_package_state(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            season_index=season_index, offset=offset, limit=limit,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "saved_player_match_history_unavailable", "message": str(exc)},
        ) from exc


@router.get("/saved-players", response_model=SavedPlayersInventory)
def get_saved_players_inventory(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    search: str = Query(default="", max_length=120),
    country_code: str = Query(default="", max_length=3),
    status_filter: str = Query(default="", max_length=80),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> SavedPlayersInventory:
    """Server-paged canonical present-time roster from the exact Saved HEAD."""
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ) or revision.revision_id != branch.saved_head_revision_id:
            raise ValueError("Saved Players HEAD belongs to another Run / Branch")
        return resolve_saved_players_inventory(
            run_id=run_id, branch_id=branch_id, saved_revision_id=revision.revision_id,
            initial_world=load_saved_initial_world(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            prospect_source=load_saved_run_prospect_source(
                revision.payload, run_id=run_id,
            ),
            ranking=load_saved_ranking_component(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            search=search, country_code=country_code, status_filter=status_filter,
            offset=offset, limit=limit,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "saved_players_inventory_unavailable", "message": str(exc)},
        ) from exc


@router.get("/player-profiles/{player_id}", response_model=SavedPlayerProfile)
def get_saved_player_profile(
    run_id: str,
    branch_id: str,
    player_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> SavedPlayerProfile:
    """Only the selected Branch's verified immutable present-time Saved HEAD."""
    if not player_id or len(player_id) > 128 or player_id.strip() != player_id:
        raise HTTPException(status_code=422, detail="Invalid player identifier")
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ) or revision.revision_id != branch.saved_head_revision_id:
            raise ValueError("Saved player profile HEAD belongs to another Run/Branch")
        identities = resolve_saved_home_player_identities(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            requested_ids=(player_id,),
            initial_world=load_saved_initial_world(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            prospect_source=load_saved_run_prospect_source(
                revision.payload, run_id=run_id,
            ),
        )
        return resolve_saved_player_profile(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            player_id=player_id, identities=identities,
            ranking=load_saved_ranking_component(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
            packages=load_saved_run_package_state(
                revision.payload, run_id=run_id, branch_id=branch_id,
            ),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "saved_player_profile_unavailable", "message": str(exc)},
        ) from exc


@router.get("/home-player-identities", response_model=SavedHomePlayerIdentities)
def get_saved_home_player_identities(
    run_id: str,
    branch_id: str,
    player_ids: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> SavedHomePlayerIdentities:
    """Bounded player IDs with immutable source provenance, including empty/missing."""
    if len(player_ids) > 3200:
        raise HTTPException(status_code=422, detail="Player identity request exceeds limit")
    ids = tuple(player_ids.split(","))
    if (
        not 1 <= len(ids) <= 25
        or len(ids) != len(set(ids))
        or any(not item or len(item) > 128 or item.strip() != item for item in ids)
    ):
        raise HTTPException(status_code=422, detail="Expected 1–25 distinct player IDs")
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if run is None or branch is None or branch.run_id != run_id:
        raise HTTPException(status_code=404, detail="Product Run / Branch was not found")
    try:
        state = repository.get_branch_revision_state(branch_id=branch_id)
        revision = state.saved_revision
        if (state.run_id, state.branch_id, revision.run_id, revision.branch_id) != (
            run_id, branch_id, run_id, branch_id
        ) or revision.revision_id != branch.saved_head_revision_id:
            raise ValueError("Saved player identity HEAD belongs to another Run/Branch")
        initial_world = load_saved_initial_world(
            revision.payload, run_id=run_id, branch_id=branch_id
        )
        prospect_source = load_saved_run_prospect_source(
            revision.payload, run_id=run_id
        )
        return resolve_saved_home_player_identities(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            requested_ids=ids, initial_world=initial_world,
            prospect_source=prospect_source,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "run_home_player_identity_unavailable", "message": str(exc)},
        ) from exc
