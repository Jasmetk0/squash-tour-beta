"""Historically filtered native Tour publication from the Viewer Saved revision."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.infrastructure.db import (
    ViewerOfficialRunContextConflictError,
    ViewerOfficialRunContextNotFoundError,
)
from beta_engine.infrastructure.db.calendar_tour import saved_tour

router = APIRouter(tags=["viewer-calendar-tour"])


@router.get("/viewer/runs/{run_id}/calendar-tour/records")
def read_signed_career_records(
    run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    as_of_season_index: int | None = Query(default=None, ge=0),
    from_season_index: int = Query(default=0, ge=0),
    country_code: str | None = Query(default=None),
    leaderboard_limit: int = Query(default=20, ge=1, le=100),
):
    from beta_engine.application.calendar_tour_signed_records import (
        signed_tour_records,
    )
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )

    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=run_id,
        )
        payload = snapshot.revision.payload
        state = saved_tour(
            payload, run_id=run_id, branch_id=snapshot.revision.branch_id,
        )
        if state is None:
            raise ValueError("Signed career records need a Saved native Tour")
        world = load_saved_initial_world(
            payload, run_id=run_id, branch_id=state.branch_id,
        )
        return {
            **signed_tour_records(
                state, world, as_of_season_index=as_of_season_index,
                from_season_index=from_season_index,
                country_code=country_code, leaderboard_limit=leaderboard_limit,
            ),
            "schema_version": "calendar_tour_signed_records_response.v1",
            "saved_head_revision_id": snapshot.revision.revision_id,
        }
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (KeyError, ValueError, TypeError, ViewerOfficialRunContextConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/viewer/runs/{run_id}/calendar-tour/seasons/{season_index}")
def read_signed_season_summary(
    run_id: str,
    season_index: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    compare_to: int | None = Query(default=None, ge=0),
):
    from beta_engine.application.calendar_tour_season_summary import (
        compare_completed_seasons,
    )
    from beta_engine.infrastructure.db.initial_world_state import (
        load_saved_initial_world,
    )

    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=run_id,
        )
        payload = snapshot.revision.payload
        state = saved_tour(
            payload, run_id=run_id, branch_id=snapshot.revision.branch_id,
        )
        if state is None:
            raise ValueError("Saved native Tour publication is unavailable")
        world = load_saved_initial_world(
            payload, run_id=run_id, branch_id=state.branch_id,
        )
        return {
            "schema_version": "calendar_tour_season_comparison.v1",
            "run_id": run_id,
            "branch_id": state.branch_id,
            "saved_head_revision_id": snapshot.revision.revision_id,
            **compare_completed_seasons(state, world, season_index, compare_to),
        }
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (KeyError, ValueError, TypeError, ViewerOfficialRunContextConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/viewer/runs/{run_id}/calendar-tour")
def read_saved_tour(
    run_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    week_ordinal: int | None = Query(default=None, ge=0),
):
    try:
        snapshot = runtime.repository.get_viewer_saved_revision_snapshot(
            product_run_id=run_id
        )
        state = saved_tour(
            snapshot.revision.payload,
            run_id=run_id,
            branch_id=snapshot.revision.branch_id,
        )
        if state is None:
            raise ValueError("Saved native Tour publication is unavailable")
        ordinal = state.week.ordinal if week_ordinal is None else week_ordinal
        if ordinal > state.week.ordinal:
            raise ValueError("Future native week is unavailable")
        rankings = tuple(
            r
            for r in state.rankings
            if state.week.calendar.ordinal(r.week.season_index, r.week.week) <= ordinal
        )
        if not rankings:
            raise ValueError(
                "No generated native ranking exists at this historical week"
            )
        return {
            "schema_version": "viewer_calendar_tour.v1",
            "run_id": run_id,
            "branch_id": state.branch_id,
            "saved_revision_id": snapshot.revision.revision_id,
            "week_ordinal": ordinal,
            "official_ranking": rankings[-1].model_dump(mode="json"),
            "editions": [
                {
                    "edition_id": a.edition.edition_id,
                    "name": a.edition.name,
                    "week": a.edition.week.model_dump(mode="json"),
                    "point_table": a.edition.point_table,
                    "completed": bool(
                        a.result_confirmed and a.edition.week.ordinal <= ordinal
                    ),
                }
                for a in state.editions
                if a.edition.announcement_week.ordinal <= ordinal
                and any(
                    a.edition.edition_id
                    in t.public_event.get("announced_edition_ids", [])
                    for t in state.transitions
                    if t.target_week.ordinal <= ordinal
                )
            ],
            "public_events": [
                t.public_event
                for t in state.transitions
                if t.target_week.ordinal <= ordinal
            ],
        }
    except ViewerOfficialRunContextNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, ViewerOfficialRunContextConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
