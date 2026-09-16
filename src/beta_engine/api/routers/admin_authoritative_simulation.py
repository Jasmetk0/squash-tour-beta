"""Explicit Admin HTTP boundary for the authoritative Run simulation driver."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import (
    ApiRuntime,
    get_runtime,
    get_season_match_service,
    get_season_point_awards_service,
    get_run_working_draft_service,
)
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    AuthoritativeSimulationCommand,
)
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation",
    tags=["admin-authoritative-simulation"],
)


def _driver(runtime, matches, awards):
    return AuthoritativeRunSimulationDriver(
        runtime.repository._session_factory, matches, awards
    )


@router.get("/position")
def position(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).position(
            run_id=run_id, branch_id=branch_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_simulation_conflict", "message": str(exc)},
        ) from exc


def _mutate(run_id, branch_id, payload, runtime, matches, awards, *, slot):
    try:
        command = AuthoritativeSimulationCommand.model_validate(payload)
        if (command.run_id, command.branch_id) != (run_id, branch_id):
            raise ValueError("authoritative simulation request scope mismatch")
        driver = _driver(runtime, matches, awards)
        return (
            driver.simulate_next_slot(command)
            if slot
            else driver.simulate_next_match(command)
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_simulation_conflict", "message": str(exc)},
        ) from exc


@router.post("/simulate-next-match")
def simulate_next_match(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    return _mutate(run_id, branch_id, payload, runtime, matches, awards, slot=False)


@router.post("/simulate-next-slot")
def simulate_next_slot(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    return _mutate(run_id, branch_id, payload, runtime, matches, awards, slot=True)


@router.get("/save/preview")
def preview_save(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    try:
        return runtime.repository.preview_simulation_save(
            run_id=run_id, branch_id=branch_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/save", status_code=201)
def save(
    run_id: str,
    branch_id: str,
    payload: dict,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        return service.save_simulation(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=payload["expected_draft_version"],
            expected_simulation_fingerprint=payload["expected_simulation_fingerprint"],
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
