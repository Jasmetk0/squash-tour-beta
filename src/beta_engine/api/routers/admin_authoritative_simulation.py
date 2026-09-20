"""Explicit Admin HTTP boundary for the authoritative Run simulation driver."""

import json
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
    AuthoritativeWalkoverCommand,
    FinalSeasonTransitionCommand,
    OrdinarySeasonTransitionCommand,
)
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.prospect_bridge_inspection import inspect_prospect_bridge
from beta_engine.domain.players.sporting import PlayerDevelopmentPolicy
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.domain.simulation_slots import WeekSimulationSchedule

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation",
    tags=["admin-authoritative-simulation"],
)


def _driver(runtime, matches, awards):
    return AuthoritativeRunSimulationDriver(
        runtime.repository._session_factory, matches, awards
    )


@router.post("/season-transition/configuration/preview")
def preview_season_transition_configuration(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        ranking_payload = payload.get("target_ranking_policy")
        development_payload = payload.get("target_development_policy")
        target_ranking_policy = (
            OfficialRankingPolicy.model_validate(ranking_payload)
            if ranking_payload is not None
            else None
        )
        target_development_policy = (
            PlayerDevelopmentPolicy.model_validate(development_payload)
            if development_payload is not None
            else None
        )
        with runtime.repository._session_factory() as session:
            configuration = resolve_season_transition_configuration(
                session,
                run_id=run_id,
                branch_id=branch_id,
                target_ranking_policy=target_ranking_policy,
                target_development_policy=target_development_policy,
            )
        return {
            "configuration": configuration,
            "configuration_fingerprint": configuration.fingerprint,
            "ranking_policy_inherited": configuration.ranking_policy_inherited,
            "development_policy_inherited": (
                configuration.development_policy_inherited
            ),
            "reset_component_ids": list(
                configuration.reset_catalog.component_ids
            ),
        }
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "season_transition_configuration_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/prospect-bridge")
def prospect_bridge(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        with runtime.repository._session_factory() as session:
            return inspect_prospect_bridge(
                session,
                run_id=run_id,
                branch_id=branch_id,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "prospect_bridge_inspection_conflict", "message": str(exc)},
        ) from exc


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


@router.get("/season-transition/preflight")
def season_transition_preflight(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).season_transition_preflight(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "season_transition_preflight_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/season-transition/advance", status_code=201)
def advance_ordinary_season(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        command = OrdinarySeasonTransitionCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).advance_ordinary_season(command)
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ordinary_season_transition_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/season-transition/finalize", status_code=201)
def finalize_final_season(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        command = FinalSeasonTransitionCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).finalize_final_season(command)
    except (KeyError, ValueError, ValidationError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "final_season_transition_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/week-schedule/proposal")
def propose_week_schedule(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).propose_topological_schedule(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "topological_schedule_proposal_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/week-schedule/adopt-proposal", status_code=201)
def adopt_topological_week_schedule_proposal(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).adopt_topological_schedule_proposal(
            run_id=run_id,
            branch_id=branch_id,
            request_id=payload["request_id"],
            expected_week=RankingWeek.model_validate(payload["expected_week"]),
            expected_schedule_fingerprint=payload["expected_schedule_fingerprint"],
            expected_position_fingerprint=payload["expected_position_fingerprint"],
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "topological_schedule_adoption_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/week-schedule")
def inspect_week_schedule(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_schedule(
            run_id=run_id, branch_id=branch_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/week-schedule", status_code=201)
def adopt_week_schedule(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        schedule = WeekSimulationSchedule.model_validate_json(
            json.dumps(payload["schedule"])
        )
        if (schedule.run_id, schedule.branch_id) != (run_id, branch_id):
            raise ValueError("week schedule request scope mismatch")
        return _driver(runtime, matches, awards).adopt_schedule(
            schedule,
            request_id=payload["request_id"],
            expected_position_fingerprint=payload["expected_position_fingerprint"],
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/week-schedule/preview")
def preview_week_schedule(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        schedule = WeekSimulationSchedule.model_validate_json(
            json.dumps(payload["schedule"])
        )
        if (schedule.run_id, schedule.branch_id) != (run_id, branch_id):
            raise ValueError("week schedule request scope mismatch")
        return _driver(runtime, matches, awards).preview_schedule(schedule)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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


@router.post("/post-cutoff-walkover")
def post_cutoff_walkover(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        command = AuthoritativeWalkoverCommand.model_validate(payload)
        if (command.run_id, command.branch_id) != (run_id, branch_id):
            raise ValueError("authoritative W/O request scope mismatch")
        return _driver(runtime, matches, awards).commit_post_cutoff_walkover(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_walkover_conflict", "message": str(exc)},
        ) from exc


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
