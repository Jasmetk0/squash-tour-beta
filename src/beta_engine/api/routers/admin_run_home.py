"""Narrow, read-only Run Home projection from the selected Branch Saved Revision."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.application.run_home_player_identity_read_model import (
    HomePlayerIdentities, resolve_run_home_player_identities,
)
from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
from beta_engine.infrastructure.db.run_prospect_source_state import (
    load_saved_run_prospect_source,
)
from beta_engine.api.deps import ApiRuntime, get_runtime
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


@router.get("/home-player-identities", response_model=HomePlayerIdentities)
def inspect_run_home_player_identities(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    player_id: Annotated[list[str] | None, Query()] = None,
) -> HomePlayerIdentities:
    """Names for explicitly requested IDs in the selected Branch *saved* HEAD."""
    ids = tuple(player_id or ())
    if len(ids) > 30 or any(not value.strip() or len(value) > 128 for value in ids):
        raise HTTPException(status_code=422, detail="Request up to 30 nonempty player IDs")
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
        ) or branch.saved_head_revision_id != revision.revision_id:
            raise ValueError("Saved player identity HEAD differs from selected Run / Branch")
        initial_world = load_saved_initial_world(
            revision.payload, run_id=run_id, branch_id=branch_id,
        )
        prospects = load_saved_run_prospect_source(revision.payload, run_id=run_id)
        return resolve_run_home_player_identities(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=revision.revision_id,
            initial_world=initial_world, prospects=prospects, player_ids=ids,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "run_home_player_identity_unavailable", "message": str(exc)},
        ) from exc
