"""Explicit Admin HTTP boundary for the authoritative Run simulation driver."""

import json
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from beta_engine.api.deps import (
    ApiRuntime,
    get_run_working_draft_service,
    get_runtime,
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeApplicationValidationCommand,
    AuthoritativeEmptyWeekCompletionCommand,
    AuthoritativeEntryDecisionSlotCommand,
    AuthoritativeExplicitApplicationValidationCommand,
    AuthoritativeExplicitEntryDecisionSlotCommand,
    AuthoritativeFullSimulationAbandonCommand,
    AuthoritativeFullSimulationCommand,
    AuthoritativeFullSimulationControlCommand,
    AuthoritativeFullSimulationPreviewRequest,
    AuthoritativeFullSimulationRetargetCommand,
    AuthoritativeLiveConfirmCommand,
    AuthoritativeLiveRangeCommand,
    AuthoritativeLiveReturnCommand,
    AuthoritativeMatchDayCommand,
    AuthoritativeMatchReconstructionCommitCommand,
    AuthoritativeMatchReconstructionPreviewRequest,
    AuthoritativeNextRallyCommand,
    AuthoritativeRoundCommand,
    AuthoritativeRunSimulationDriver,
    AuthoritativeSeasonCommand,
    AuthoritativeSeasonPreviewRequest,
    AuthoritativeSimulationCommand,
    AuthoritativeTournamentCommand,
    AuthoritativeWalkoverCommand,
    AuthoritativeWeekCommand,
    AuthoritativeWeekExtensionApproval,
    AuthoritativeWeekPreviewRequest,
    AuthoritativeWeekTournamentLockCommitCommand,
    AuthoritativeWeekTournamentLockPreviewRequest,
    FinalSeasonTransitionCommand,
    OrdinarySeasonTransitionCommand,
)
from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationCommand,
    CalendarContinuationService,
)
from beta_engine.application.calendar_knockout_award_service import (
    CalendarAwardApplyCommand,
    CalendarAwardProposal,
    CalendarKnockoutAwardService,
)
from beta_engine.application.calendar_opening_knockout_service import (
    CalendarCanonicalPreviewCommand,
    CalendarOpeningKnockoutCommand,
    CalendarOpeningKnockoutService,
)
from beta_engine.application.calendar_signed_knockout_standings import (
    CalendarSignedKnockoutStandingsService,
)
from beta_engine.application.calendar_standalone_match_service import (
    CalendarStandaloneMatchCommand,
    CalendarStandaloneMatchService,
)
from beta_engine.application.full_simulation_tasks import inspect_tasks
from beta_engine.application.native_full_simulation import (
    OPERATION_SCHEMA,
    NativeFullSimulationCommand,
    NativeFullSimulationDriver,
    NativeFullSimulationPreview,
    parse_full_simulation_command,
)
from beta_engine.application.pre_alpha_fax_acceptance_profile import (
    PreAlphaFaxAcceptanceProfile,
    PreAlphaFaxAcceptanceProfileService,
)
from beta_engine.application.pre_alpha_fax_current_entry_decisions import (
    PreAlphaFaxCurrentEntryDecisionApplyRequest,
    PreAlphaFaxCurrentEntryDecisionApplyResult,
    PreAlphaFaxCurrentEntryDecisionPreview,
    PreAlphaFaxCurrentEntryDecisionService,
)
from beta_engine.application.pre_alpha_fax_current_week_ranking_snapshots import (
    PreAlphaFaxCurrentWeekRankingSnapshotApplyRequest,
    PreAlphaFaxCurrentWeekRankingSnapshotApplyResult,
    PreAlphaFaxCurrentWeekRankingSnapshotPreview,
    PreAlphaFaxCurrentWeekRankingSnapshotService,
)
from beta_engine.application.pre_alpha_fax_entry_validation_policy_gate import (
    PreAlphaFaxEntryValidationPolicyGate,
    PreAlphaFaxEntryValidationPolicyGateService,
)
from beta_engine.application.pre_alpha_fax_long_acceptance_probe import (
    PreAlphaFaxLongAcceptanceProbeReport,
    PreAlphaFaxLongAcceptanceProbeRequest,
    PreAlphaFaxLongAcceptanceProbeService,
)
from beta_engine.application.prospect_bridge_inspection import inspect_prospect_bridge
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.season_match_service import SeasonMatchService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.application.season_transition_configuration import (
    resolve_season_transition_configuration,
)
from beta_engine.application.standalone_match_service import (
    StandaloneMatchAddPlayerCommand,
    StandaloneMatchService,
    StandaloneMatchSimulateCommand,
)
from beta_engine.domain.players.sporting import PlayerDevelopmentPolicy
from beta_engine.domain.rankings.official import OfficialRankingPolicy, RankingWeek
from beta_engine.domain.simulation_slots import WeekSimulationSchedule

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/authoritative-simulation",
    tags=["admin-authoritative-simulation"],
)
_logger = logging.getLogger(__name__)


def _safe_simulation_conflict_message(exc: Exception) -> str:
    """Do not disclose unknown exception details to HTTP clients."""
    message = str(exc)
    if "lease ownership was lost" in message:
        return "Full Simulation lease ownership was lost"
    if "global execution lease" in message:
        return "Another operation holds the global execution lease"
    return "Simulation request conflicts with the current Run state"


def _internal_simulation_failure(operation: str) -> HTTPException:
    # Keep implementation details in server logs, never in an HTTP response.
    _logger.exception("Unhandled %s failure", operation)
    return HTTPException(
        status_code=500,
        detail={"code": "internal_simulation_error", "message": "Internal simulation failure"},
    )


@router.get(
    "/pre-alpha/fax-acceptance-profile",
    response_model=PreAlphaFaxAcceptanceProfile,
)
def get_pre_alpha_fax_acceptance_profile(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> PreAlphaFaxAcceptanceProfile:
    try:
        return PreAlphaFaxAcceptanceProfileService(
            runtime.repository._session_factory
        ).inspect(run_id=run_id, branch_id=branch_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_acceptance_profile_conflict",
                "message": str(exc),
            },
        ) from exc


def _driver(runtime, matches, awards):
    return AuthoritativeRunSimulationDriver(
        runtime.repository._session_factory, matches, awards
    )


def _full_driver(runtime, matches, awards, *, command=None, task_id=None, parent_id=None):
    if task_id is not None or parent_id is not None:
        from beta_engine.infrastructure.db.models import (
            AuthoritativeSimulationCommandModel,
            FullSimulationTaskModel,
        )
        with runtime.repository._session_factory() as session:
            if task_id is not None:
                row = session.get(FullSimulationTaskModel, task_id)
                command = parse_full_simulation_command(json.loads(row.payload_json)["command"]) if row else None
            else:
                row = session.get(AuthoritativeSimulationCommandModel, parent_id)
                if row and json.loads(row.result_json).get("schema_version") == OPERATION_SCHEMA:
                    return NativeFullSimulationDriver(runtime.repository)
    return NativeFullSimulationDriver(runtime.repository) if isinstance(command, NativeFullSimulationCommand) else _driver(runtime, matches, awards)


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


@router.get("/entry-roster")
def inspect_entry_roster(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_entry_roster(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "entry_roster_inspection_conflict", "message": str(exc)},
        ) from exc


@router.post("/entry-decision-slot/review", status_code=201)
def review_entry_decision_slot(
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
        command = AuthoritativeExplicitEntryDecisionSlotCommand.model_validate_json(
            json.dumps({**payload, "run_id": run_id, "branch_id": branch_id})
        )
        return _driver(runtime, matches, awards).commit_explicit_entry_decision_slot(
            command
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "explicit_entry_decision_review_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/entry-decision-slot/preview")
def preview_entry_decision_slot(
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
        event_ids = tuple(payload["event_ids"])
        return _driver(runtime, matches, awards).preview_entry_decision_slot(
            run_id=run_id,
            branch_id=branch_id,
            event_ids=event_ids,
            decision_slot_ordinal=payload["decision_slot_ordinal"],
            seed=payload.get("seed", 12345),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "entry_decision_slot_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/entry-decision-slot/{decision_slot_ordinal}")
def inspect_entry_decision_slot(
    run_id: str,
    branch_id: str,
    decision_slot_ordinal: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_entry_decision_slot(
            run_id=run_id,
            branch_id=branch_id,
            decision_slot_ordinal=decision_slot_ordinal,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "entry_decision_slot_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/entry-decision-slot/commit", status_code=201)
def commit_entry_decision_slot(
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
        command = AuthoritativeEntryDecisionSlotCommand.model_validate_json(
            json.dumps({**payload, "run_id": run_id, "branch_id": branch_id})
        )
        return _driver(runtime, matches, awards).commit_entry_decision_slot(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "entry_decision_slot_commit_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/entry-decision-slot/validation/commit", status_code=201)
def commit_application_validation_slot(
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
        command = AuthoritativeApplicationValidationCommand.model_validate_json(
            json.dumps({**payload, "run_id": run_id, "branch_id": branch_id})
        )
        return _driver(runtime, matches, awards).commit_application_validation_slot(
            command
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "application_validation_slot_commit_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/entry-decision-slot/validation/review", status_code=201)
def review_application_validation_slot(
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
        command = AuthoritativeExplicitApplicationValidationCommand.model_validate_json(
            json.dumps({**payload, "run_id": run_id, "branch_id": branch_id})
        )
        return _driver(
            runtime, matches, awards
        ).commit_explicit_application_validation_slot(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "explicit_application_validation_review_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/week-tournament-lock")
def inspect_week_tournament_lock(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_week_tournament_lock(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "week_tournament_lock_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/week-tournament-lock/preview")
def preview_week_tournament_lock(
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
        request = AuthoritativeWeekTournamentLockPreviewRequest.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).preview_week_tournament_lock(
            request
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "week_tournament_lock_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/week-tournament-lock/commit", status_code=201)
def commit_week_tournament_lock(
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
        command = AuthoritativeWeekTournamentLockCommitCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).commit_week_tournament_lock(
            command
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "week_tournament_lock_commit_conflict",
                "message": str(exc),
            },
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


@router.post("/empty-week/complete", status_code=201)
def complete_empty_week(
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
        command = AuthoritativeEmptyWeekCompletionCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).complete_empty_week(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_empty_week_completion_conflict",
                "message": str(exc),
            },
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
        command = OrdinarySeasonTransitionCommand.model_validate_json(
            json.dumps({**payload, "run_id": run_id, "branch_id": branch_id})
        )
        return _driver(runtime, matches, awards).advance_season(command)
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


@router.get("/week-schedule/preflight")
def preflight_week_schedule(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_schedule_preflight(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "week_schedule_preflight_conflict",
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


@router.get("/match-reconstruction/state")
def match_reconstruction_state(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_match_reconstruction(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "match_reconstruction_state_conflict", "message": str(exc)},
        ) from exc


@router.post("/match-reconstruction/preview")
def preview_match_reconstruction(
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
        reconstruction = AuthoritativeMatchReconstructionPreviewRequest.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).preview_match_reconstruction(
            reconstruction
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "match_reconstruction_preview_conflict", "message": str(exc)},
        ) from exc


@router.post("/match-reconstruction/commit", status_code=201)
def commit_match_reconstruction(
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
        command = AuthoritativeMatchReconstructionCommitCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).commit_match_reconstruction(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "match_reconstruction_commit_conflict", "message": str(exc)},
        ) from exc


@router.get("/standalone-match")
def standalone_match_state(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return StandaloneMatchService(runtime.repository._session_factory).inspect(
            run_id=run_id, branch_id=branch_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "standalone_match_state_conflict", "message": str(exc)},
        ) from exc


@router.post("/standalone-match/players")
def add_standalone_match_player(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        command = StandaloneMatchAddPlayerCommand.model_validate(payload)
        return StandaloneMatchService(runtime.repository._session_factory).add_player(
            run_id=run_id, branch_id=branch_id, command=command
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "standalone_match_player_conflict", "message": str(exc)},
        ) from exc


@router.post("/standalone-match/simulate")
def simulate_standalone_match(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        command = StandaloneMatchSimulateCommand.model_validate(payload)
        return StandaloneMatchService(runtime.repository._session_factory).simulate(
            run_id=run_id, branch_id=branch_id, command=command
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "standalone_match_simulation_conflict", "message": str(exc)},
        ) from exc


@router.get("/calendar-standalone-match")
def calendar_standalone_match_state(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarStandaloneMatchService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_match_state_conflict", "message": str(exc)},
        ) from exc


@router.post("/calendar-standalone-match/simulate", status_code=201)
def simulate_calendar_standalone_match(
    run_id: str,
    branch_id: str,
    payload: CalendarStandaloneMatchCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarStandaloneMatchService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_match_simulation_conflict", "message": str(exc)},
        ) from exc


@router.get("/calendar-standalone-match/{match_id}/replay")
def replay_calendar_standalone_match(
    run_id: str,
    branch_id: str,
    match_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarStandaloneMatchService(runtime.repository).replay(
            run_id=run_id, branch_id=branch_id, match_id=match_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_match_replay_conflict", "message": str(exc)},
        ) from exc


@router.get("/calendar-standalone-match/save/preview")
def preview_calendar_standalone_match_save(
    run_id: str, branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return runtime.repository.preview_calendar_match_save(
            run_id=run_id, branch_id=branch_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/calendar-standalone-match/save", status_code=201)
def save_calendar_standalone_match(
    run_id: str, branch_id: str, payload: dict,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        return service.save_calendar_match(
            run_id=run_id, branch_id=branch_id,
            expected_draft_version=payload["expected_draft_version"],
            expected_calendar_match_fingerprint=payload["expected_calendar_match_fingerprint"],
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc



@router.get("/calendar-opening-knockout")
def calendar_opening_knockout_state(
    run_id: str, branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarOpeningKnockoutService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409,
                            detail={"code": "calendar_knockout_state_conflict", "message": str(exc)}) from exc


@router.post("/calendar-opening-knockout/canonical-preview")
def preview_calendar_canonical_knockout(
    run_id: str, branch_id: str, payload: CalendarCanonicalPreviewCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarOpeningKnockoutService(runtime.repository).canonical_preview(
            run_id=run_id, branch_id=branch_id, command=payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/calendar-opening-knockout/sporting-checkpoint/players/{player_id}")
def calendar_sporting_checkpoint_player(
    run_id: str, branch_id: str, player_id: str,
    expected_saved_head: str, expected_checkpoint_fingerprint: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarOpeningKnockoutService(runtime.repository).checkpoint_player(
            run_id=run_id, branch_id=branch_id, player_id=player_id,
            expected_saved_head=expected_saved_head,
            expected_checkpoint_fingerprint=expected_checkpoint_fingerprint)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/calendar-opening-knockout/simulate", status_code=201)
def simulate_calendar_opening_knockout(
    run_id: str, branch_id: str,
    payload: CalendarOpeningKnockoutCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarOpeningKnockoutService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409,
                            detail={"code": "calendar_knockout_execution_conflict", "message": str(exc)}) from exc


@router.get("/calendar-opening-knockout/{match_id}/replay")
def replay_calendar_opening_knockout(
    run_id: str, branch_id: str, match_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarOpeningKnockoutService(runtime.repository).replay(
            run_id=run_id, branch_id=branch_id, match_id=match_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409,
                            detail={"code": "calendar_knockout_replay_conflict", "message": str(exc)}) from exc


# Same immutable calendar sporting component/Save machinery as the v1
# exhibition, so past Saved payloads are never rewritten or silently upgraded.
@router.get("/calendar-opening-knockout/standings")
def calendar_signed_knockout_standings(
    run_id: str, branch_id: str, expected_saved_head: str,
    season_index: int, week: int,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    """Read-only, as-of Signed event standings; not Official Ranking."""
    try:
        return CalendarSignedKnockoutStandingsService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id,
            expected_saved_head=expected_saved_head,
            season_index=season_index, week=week,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_standings_not_eligible", "message": str(exc)},
        ) from exc


@router.post("/calendar-opening-knockout/awards/review")
def review_calendar_knockout_awards(
    run_id: str, branch_id: str, payload: CalendarAwardProposal,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarKnockoutAwardService(runtime.repository).review(
            run_id=run_id, branch_id=branch_id, proposal=payload,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409,
                            detail={"code": "calendar_award_review_conflict", "message": str(exc)}) from exc


@router.post("/calendar-opening-knockout/awards/apply", status_code=201)
def apply_calendar_knockout_awards(
    run_id: str, branch_id: str, payload: CalendarAwardApplyCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarKnockoutAwardService(runtime.repository).apply(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409,
                            detail={"code": "calendar_award_apply_conflict", "message": str(exc)}) from exc


@router.get("/calendar-opening-knockout/save/preview")
def preview_calendar_opening_knockout_save(
    run_id: str, branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        view = CalendarOpeningKnockoutService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id
        )
        if view["knockout"] is None:
            raise ValueError("No opening knockout to save")
        return runtime.repository.preview_calendar_match_save(
            run_id=run_id, branch_id=branch_id
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/calendar-opening-knockout/save", status_code=201)
def save_calendar_opening_knockout(
    run_id: str, branch_id: str, payload: dict,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        view = CalendarOpeningKnockoutService(runtime.repository).inspect(
            run_id=run_id, branch_id=branch_id
        )
        if view["knockout"] is None:
            raise ValueError("No opening knockout to save")
        return service.save_calendar_match(
            run_id=run_id, branch_id=branch_id,
            expected_draft_version=payload["expected_draft_version"],
            expected_calendar_match_fingerprint=payload["expected_calendar_match_fingerprint"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/live-match/confirm")
def confirm_live_match_result(
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
        command = AuthoritativeLiveConfirmCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).confirm_completed_live_match(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_live_confirm_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/live-match/timeline")
def inspect_live_match_timeline(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_live_match_timeline(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_live_match_timeline_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/live-match/restore")
def restore_live_match_return_point(
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
        command = AuthoritativeLiveReturnCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).restore_live_return_point(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_live_return_restore_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/match-replays")
def list_match_replays(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    limit: int = 20,
):
    try:
        return _driver(runtime, matches, awards).list_authoritative_match_replays(
            run_id=run_id,
            branch_id=branch_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_match_replay_list_conflict", "message": str(exc)},
        ) from exc


@router.get("/match-replay")
def get_match_replay(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_replay(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_match_replay_conflict", "message": str(exc)},
        ) from exc


@router.get("/match-replay/context")
def get_match_replay_context(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_replay_context(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_replay_context_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/match-replay/cursor")
def get_match_replay_cursor(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    rally_index: int = 1,
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_replay_cursor(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
            rally_index=rally_index,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_replay_cursor_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/match-replay/frame")
def get_match_replay_frame(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    rally_index: int = 1,
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_replay_frame(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
            rally_index=rally_index,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_replay_frame_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/match-replay/timeline-cursor")
def get_match_replay_timeline_cursor(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    timeline_index: int = 1,
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_timeline_cursor(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
            timeline_index=timeline_index,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_timeline_cursor_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/match-replay/stamina-cursor")
def get_match_replay_stamina_cursor(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    timeline_index: int = 1,
):
    try:
        return _driver(runtime, matches, awards).get_authoritative_match_stamina_cursor(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
            timeline_index=timeline_index,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_stamina_cursor_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/live-match")
def inspect_live_match(
    run_id: str,
    branch_id: str,
    group_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_live_match(
            run_id=run_id,
            branch_id=branch_id,
            group_id=group_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_live_match_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-game")
def simulate_game(
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
        command = AuthoritativeLiveRangeCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_game(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "authoritative_simulate_game_conflict", "message": str(exc)},
        ) from exc


@router.post("/simulate-rest-of-match")
def simulate_rest_of_match(
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
        command = AuthoritativeLiveRangeCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_rest_of_match(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_simulate_rest_of_match_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-rally")
def simulate_next_rally(
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
        command = AuthoritativeNextRallyCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_rally(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_next_rally_conflict",
                "message": str(exc),
            },
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


@router.get("/next-match-day/preview")
def preview_next_match_day(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).preview_next_match_day(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_day_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-match-day", status_code=201)
def simulate_next_match_day(
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
        command = AuthoritativeMatchDayCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_match_day(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_match_day_simulation_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/next-round/preview")
def preview_next_round(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).preview_next_round(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_round_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-round", status_code=201)
def simulate_next_round(
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
        command = AuthoritativeRoundCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_round(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_round_simulation_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/next-tournament/preview")
def preview_next_tournament(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).preview_next_tournament(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_tournament_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-tournament", status_code=201)
def simulate_next_tournament(
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
        command = AuthoritativeTournamentCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_tournament(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_tournament_simulation_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/next-week/extension-approve")
def approve_next_week_extension(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    """Only explicit Admin approval; never resume execution or Save."""
    try:
        command = AuthoritativeWeekExtensionApproval.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).approve_next_week_extension(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "next_week_extension_approval_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/next-week/extension-inspection")
def inspect_next_week_extensions(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    """Read-only diagnostic evidence, not an extension approval."""
    try:
        return _driver(runtime, matches, awards).inspect_next_week_extension_candidates(
            run_id=run_id, branch_id=branch_id
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "next_week_extension_inspection_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/next-week/preview")
def preview_next_week(
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
        request = AuthoritativeWeekPreviewRequest.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).preview_next_week(request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_week_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-week", status_code=201)
def simulate_next_week(
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
        command = AuthoritativeWeekCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_week(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_week_simulation_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/next-season/preview")
def preview_next_season(
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
        request = AuthoritativeSeasonPreviewRequest.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).preview_next_season(request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_season_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-next-season", status_code=201)
def simulate_next_season(
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
        command = AuthoritativeSeasonCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_next_season(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_season_simulation_conflict",
                "message": _safe_simulation_conflict_message(exc),
            },
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_simulation_failure("next-season execution") from exc


@router.get("/full-simulation/parents/{command_id}/summary")
def inspect_full_simulation_terminal_summary(
    run_id: str, branch_id: str, command_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    from beta_engine.application.full_simulation_summary import inspect_terminal_summary
    try:
        return inspect_terminal_summary(runtime.repository._session_factory,
            run_id=run_id, branch_id=branch_id, command_id=command_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={
            "code": "full_simulation_summary_conflict", "message": str(exc),
        }) from exc


@router.get("/full-simulation/parents/{command_id}")
def inspect_full_simulation_parent(
    run_id: str,
    branch_id: str,
    command_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_full_simulation_parent(
            run_id=run_id,
            branch_id=branch_id,
            command_id=command_id,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_parent_detail_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/full-simulation/history")
def inspect_full_simulation_history(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_full_simulation_history(
            run_id=run_id,
            branch_id=branch_id,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_history_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/full-simulation/pending")
def inspect_pending_full_simulations(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        return _driver(runtime, matches, awards).inspect_pending_full_simulations(
            run_id=run_id,
            branch_id=branch_id,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_pending_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get("/full-simulation/target-options")
def inspect_full_simulation_target_options(
    run_id: str, branch_id: str, command_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)],
):
    try:
        return _driver(runtime, matches, awards).inspect_full_simulation_boundary_options(
            run_id=run_id, branch_id=branch_id, command_id=command_id)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=409, detail={"code": "full_simulation_target_review_conflict", "message": _safe_simulation_conflict_message(exc)}) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_simulation_failure("full-simulation boundary inspection") from exc


@router.post("/full-simulation/target")
def retarget_full_simulation(
    run_id: str, branch_id: str, payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)],
):
    try:
        command = AuthoritativeFullSimulationRetargetCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).retarget_full_simulation(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=409, detail={
            "code": "authoritative_full_simulation_target_conflict",
            "message": str(exc)
        }) from exc


@router.post("/full-simulation/control")
def control_full_simulation(
    run_id: str,
    branch_id: str,
    payload: dict,
    request: Request,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    try:
        command = AuthoritativeFullSimulationControlCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        driver = _full_driver(runtime, matches, awards, parent_id=(run_id, branch_id, command.target_command_id))
        result = driver.control(command) if isinstance(driver, NativeFullSimulationDriver) else driver.control_full_simulation(command)
        request.app.state.full_simulation_worker.acknowledge_idle_pause(driver,command)
        return result
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_control_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/full-simulation/abandon")
def abandon_full_simulation(
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
        command = AuthoritativeFullSimulationAbandonCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).abandon_full_simulation(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_abandon_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/pre-alpha/fax-current-entry/preview",
    response_model=PreAlphaFaxCurrentEntryDecisionPreview,
)
def preview_pre_alpha_fax_current_entry(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
) -> PreAlphaFaxCurrentEntryDecisionPreview:
    try:
        return PreAlphaFaxCurrentEntryDecisionService(
            _driver(runtime, matches, awards)
        ).preview(run_id=run_id, branch_id=branch_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_current_entry_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/pre-alpha/fax-current-entry/apply",
    response_model=PreAlphaFaxCurrentEntryDecisionApplyResult,
    status_code=201,
)
def apply_pre_alpha_fax_current_entry(
    run_id: str,
    branch_id: str,
    payload: PreAlphaFaxCurrentEntryDecisionApplyRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
) -> PreAlphaFaxCurrentEntryDecisionApplyResult:
    try:
        return PreAlphaFaxCurrentEntryDecisionService(
            _driver(runtime, matches, awards)
        ).apply(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_current_entry_apply_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/pre-alpha/fax-current-week/ranking-snapshots/preview",
    response_model=PreAlphaFaxCurrentWeekRankingSnapshotPreview,
)
def preview_pre_alpha_fax_current_week_ranking_snapshots(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> PreAlphaFaxCurrentWeekRankingSnapshotPreview:
    try:
        return PreAlphaFaxCurrentWeekRankingSnapshotService(
            runtime.repository._session_factory
        ).preview(run_id=run_id, branch_id=branch_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_current_week_ranking_snapshot_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/pre-alpha/fax-current-week/ranking-snapshots/apply",
    response_model=PreAlphaFaxCurrentWeekRankingSnapshotApplyResult,
    status_code=201,
)
def apply_pre_alpha_fax_current_week_ranking_snapshots(
    run_id: str,
    branch_id: str,
    payload: PreAlphaFaxCurrentWeekRankingSnapshotApplyRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> PreAlphaFaxCurrentWeekRankingSnapshotApplyResult:
    try:
        return PreAlphaFaxCurrentWeekRankingSnapshotService(
            runtime.repository._session_factory
        ).apply(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_current_week_ranking_snapshot_apply_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/pre-alpha/fax-entry-validation-policy-gate",
    response_model=PreAlphaFaxEntryValidationPolicyGate,
)
def inspect_pre_alpha_fax_entry_validation_policy_gate(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
) -> PreAlphaFaxEntryValidationPolicyGate:
    try:
        return PreAlphaFaxEntryValidationPolicyGateService(
            _driver(runtime, matches, awards)
        ).inspect(run_id=run_id, branch_id=branch_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_entry_validation_policy_gate_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/pre-alpha/fax-long-acceptance/probe",
    response_model=PreAlphaFaxLongAcceptanceProbeReport,
    status_code=201,
)
def run_pre_alpha_fax_long_acceptance_probe(
    run_id: str,
    branch_id: str,
    payload: PreAlphaFaxLongAcceptanceProbeRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
) -> PreAlphaFaxLongAcceptanceProbeReport:
    try:
        driver = _driver(runtime, matches, awards)
        return PreAlphaFaxLongAcceptanceProbeService(
            driver=driver,
            profile_service=PreAlphaFaxAcceptanceProfileService(
                runtime.repository._session_factory
            ),
        ).run(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pre_alpha_fax_long_acceptance_probe_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/full-simulation/preview")
def preview_full_simulation(
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
        request = AuthoritativeFullSimulationPreviewRequest.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).preview_full_simulation(request)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_preview_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("/simulate-full-simulation", status_code=201)
def simulate_full_simulation(
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
        command = AuthoritativeFullSimulationCommand.model_validate(
            {**payload, "run_id": run_id, "branch_id": branch_id}
        )
        return _driver(runtime, matches, awards).simulate_full_simulation(command)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "authoritative_full_simulation_conflict",
                "message": _safe_simulation_conflict_message(exc),
            },
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_simulation_failure("full-simulation execution") from exc


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


@router.get("/prospect-source/save/preview")
def preview_run_prospect_source_save(
    run_id: str,
    branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return runtime.repository.preview_run_prospect_source_save(
            run_id=run_id,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/prospect-source/save", status_code=201)
def save_run_prospect_source(
    run_id: str,
    branch_id: str,
    payload: dict,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        return service.save_run_prospect_source(
            run_id=run_id,
            branch_id=branch_id,
            expected_draft_version=payload["expected_draft_version"],
            expected_run_prospect_source_fingerprint=payload[
                "expected_run_prospect_source_fingerprint"
            ],
            expected_saved_head_revision_id=payload.get(
                "expected_saved_head_revision_id"
            ),
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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


# Task mutation envelopes are deliberately strict: scope in an original command
# must agree with the path, and unknown/reused request input fails closed.


class FullSimulationTaskStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=128)
    command: dict

    @field_validator("request_id")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Task request ID must be nonempty")
        return value.strip()


@router.post("/full-simulation/native/preview")
def preview_native_full_simulation(run_id: str, branch_id: str, payload: dict,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        for key, expected in (("run_id", run_id), ("branch_id", branch_id)):
            if key in payload and payload[key] != expected:
                raise ValueError("Native preview scope mismatch")
        command = NativeFullSimulationPreview.model_validate({**payload, "run_id": run_id, "branch_id": branch_id})
        return NativeFullSimulationDriver(runtime.repository).preview(command)
    except ValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


class FullSimulationTaskContinue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=128)
    action: Literal["resume", "recover"]
    expected_revision: int = Field(ge=1, strict=True)
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)

    @field_validator("operator_label", "audit_reason", "request_id")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Audit and request identifiers must be nonempty")
        return value.strip()


class NativeClosureAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=128)
    review_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=128)
    audit_reason: str = Field(min_length=1, max_length=2000)
    explicit_confirmation: Literal[True]

    @field_validator("operator_label", "audit_reason", "request_id")
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or value != value.strip():
            raise ValueError("Closure audit/identity must be nonempty and trimmed")
        return value


def _native_closure_service(runtime, run_id, branch_id, command_id):
    from beta_engine.application.native_full_simulation_closure import NativeFullSimulationClosureService
    from beta_engine.infrastructure.db.models import AuthoritativeSimulationCommandModel
    with runtime.repository._session_factory() as session:
        row = session.get(AuthoritativeSimulationCommandModel, (run_id, branch_id, command_id))
        if row is None:
            raise ValueError("Native task parent is unavailable in this exact scope")
        command = NativeFullSimulationCommand.model_validate(json.loads(row.result_json)["resume_command"])
        if (command.run_id, command.branch_id, command.command_id) != (run_id, branch_id, command_id):
            raise ValueError("Native task parent scope is corrupt")
    return NativeFullSimulationClosureService(runtime.repository), command


@router.get("/full-simulation/native/{command_id}/closure")
def review_native_final_closure(run_id: str, branch_id: str, command_id: str,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        service, command = _native_closure_service(runtime, run_id, branch_id, command_id)
        return service.review(command)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.get("/full-simulation/native/{command_id}/season-transition")
def review_native_task_season_transition(run_id: str, branch_id: str, command_id: str,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        service, command = _native_closure_service(runtime, run_id, branch_id, command_id)
        return service.driver.review_season_transition(command)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/full-simulation/native/{command_id}/season-transition/approve")
def approve_native_task_season_transition(run_id: str, branch_id: str, command_id: str, payload: NativeClosureAction,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        service, command = _native_closure_service(runtime, run_id, branch_id, command_id)
        return service.driver.approve_season_transition(command, payload.model_dump(mode="json"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/full-simulation/native/{command_id}/closure/approve")
def approve_native_final_closure(run_id: str, branch_id: str, command_id: str, payload: NativeClosureAction,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        service, command = _native_closure_service(runtime, run_id, branch_id, command_id)
        return service.approve(command, payload.model_dump(mode="json"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/full-simulation/native/{command_id}/closure/save", status_code=201)
def save_native_final_closure(run_id: str, branch_id: str, command_id: str, payload: NativeClosureAction,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        service, command = _native_closure_service(runtime, run_id, branch_id, command_id)
        return service.save(command, payload.model_dump(mode="json"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.post("/full-simulation/tasks", status_code=202)
def start_full_simulation_task(run_id: str, branch_id: str, payload: FullSimulationTaskStart,
        request: Request, runtime: Annotated[ApiRuntime, Depends(get_runtime)],
        matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
        awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)]):
    try:
        for key, expected in (("run_id",run_id),("branch_id",branch_id)):
            if key in payload.command and payload.command[key] != expected:
                raise ValueError("Task original command scope mismatch")
        command = parse_full_simulation_command({**payload.command,"run_id":run_id,"branch_id":branch_id})
        return request.app.state.full_simulation_worker.start(_full_driver(runtime,matches,awards,command=command),
            run_id=run_id,branch_id=branch_id,request_id=payload.request_id,command=command)
    except ValidationError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(409, detail={"code":"full_simulation_task_conflict","message":str(exc)}) from exc


@router.get("/full-simulation/tasks")
@router.get("/full-simulation/tasks/{task_id}")
def get_full_simulation_tasks(run_id: str, branch_id: str,
        runtime: Annotated[ApiRuntime, Depends(get_runtime)], request: Request, task_id: str | None = None):
    try:
        return inspect_tasks(runtime.repository._session_factory,run_id=run_id,branch_id=branch_id,task_id=task_id,observer_instance=request.app.state.full_simulation_worker.instance)
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(409, detail={"code":"full_simulation_task_conflict","message":str(exc)}) from exc


@router.post("/full-simulation/tasks/{task_id}/continue", status_code=202)
def continue_full_simulation_task(run_id: str, branch_id: str, task_id: str, payload: FullSimulationTaskContinue,
        request: Request, runtime: Annotated[ApiRuntime, Depends(get_runtime)],
        matches: Annotated[SeasonMatchService, Depends(get_season_match_service)],
        awards: Annotated[SeasonPointAwardsService, Depends(get_season_point_awards_service)]):
    try:
        return request.app.state.full_simulation_worker.continue_task(_full_driver(runtime,matches,awards,task_id=task_id),
            run_id=run_id,branch_id=branch_id,task_id=task_id,**payload.model_dump())
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(409, detail={"code":"full_simulation_task_conflict","message":str(exc)}) from exc


# Continued sporting owner: real matches, explicit Save, no week advancement.


@router.get("/calendar-continuation")
def inspect_calendar_continuation(run_id: str, branch_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return CalendarContinuationService(runtime.repository).inspect(run_id=run_id, branch_id=branch_id)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/calendar-continuation/simulate", status_code=201)
def simulate_calendar_continuation(run_id: str, branch_id: str, payload: CalendarContinuationCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return CalendarContinuationService(runtime.repository).simulate(run_id=run_id, branch_id=branch_id, command=payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/calendar-continuation/{match_id}/replay")
def replay_calendar_continuation(run_id: str, branch_id: str, match_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return CalendarContinuationService(runtime.repository).replay(run_id=run_id, branch_id=branch_id, match_id=match_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/calendar-continuation/save", status_code=201)
def save_calendar_continuation(run_id: str, branch_id: str, payload: dict,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        # The authoritative Save below independently verifies the current
        # immutable Saved lineage, exact requested fingerprint and complete
        # 57-attribute/MatchEngine sporting replay before committing.
        # Re-running the full continuation inspection *ahead* of that Save
        # duplicates the expensive seven-match replay in a second transaction.
        # This is only a fast UI precondition guard, never a trust shortcut.
        from sqlalchemy import text

        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            COMPONENT_KEY as SPORTING_COMPONENT_KEY,
        )
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            load_checkpoint,
        )
        from beta_engine.infrastructure.db.models import (
            BranchSavedRevisionModel,
            RunBranchModel,
        )
        with runtime.repository._session_factory() as session:
            session.execute(text('BEGIN'))
            current = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
            branch = session.get(RunBranchModel, branch_id)
            revision = (
                session.get(BranchSavedRevisionModel, branch.saved_head_revision_id)
                if branch is not None and branch.run_id == run_id
                and branch.saved_head_revision_id else None
            )
            if current is None or revision is None or (
                not current.played_continuations and not current.weekly_advances
            ):
                raise ValueError('No unsaved continuation matches')
            saved_fp = json.loads(revision.payload_json).get(
                'content', {},
            ).get(SPORTING_COMPONENT_KEY, {}).get('fingerprint')
            if current.fingerprint == saved_fp:
                raise ValueError('No unsaved continuation matches')
        return service.save_calendar_sporting_checkpoint(run_id=run_id, branch_id=branch_id,
            expected_draft_version=payload['expected_draft_version'],
            expected_calendar_sporting_fingerprint=payload['expected_calendar_sporting_fingerprint'])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# Sporting-only preparation; full Official Week/Season Transition remains guarded.
from beta_engine.application.calendar_sporting_week_service import (
    CalendarSportingWeekCommand,
    CalendarSportingWeekCommit,
    CalendarSportingWeekService,
)


@router.post("/calendar-sporting-week/preview")
def preview_calendar_sporting_week(run_id: str, branch_id: str, payload: CalendarSportingWeekCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return CalendarSportingWeekService(runtime.repository).preview(run_id=run_id,branch_id=branch_id,command=payload)
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc


@router.post("/calendar-sporting-week/commit", status_code=201)
def commit_calendar_sporting_week(run_id: str, branch_id: str, payload: CalendarSportingWeekCommit,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)]):
    try:
        return CalendarSportingWeekService(runtime.repository).commit(run_id=run_id,branch_id=branch_id,request=payload)
    except (KeyError,TypeError,ValueError) as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc


# Full three-match native sporting knockout from a Saved week-2+ checkpoint.
# Results and fatigue are real; Tour points/public Official time are not published.
from beta_engine.application.calendar_followup_knockout_service import (
    CalendarFollowupEightCommand,
    CalendarFollowupEightScoredCommand,
    CalendarFollowupKnockoutCommand,
    CalendarFollowupKnockoutService,
    CalendarFollowupScoredCommand,
)


@router.post("/calendar-continuation/knockouts/simulate", status_code=201)
def simulate_calendar_followup_knockout(
    run_id: str, branch_id: str, payload: CalendarFollowupKnockoutCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarFollowupKnockoutService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_followup_knockout_conflict", "message": str(exc)},
        ) from exc


@router.post("/calendar-continuation/knockouts/simulate-scored", status_code=201)
def simulate_scored_calendar_followup_knockout(
    run_id: str, branch_id: str, payload: CalendarFollowupScoredCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    """Explicit operator-reviewed *prepared* points, never Official publication."""
    try:
        return CalendarFollowupKnockoutService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_followup_scored_knockout_conflict", "message": str(exc)},
        ) from exc


@router.post("/calendar-continuation/knockouts/simulate-eight", status_code=201)
def simulate_eight_calendar_followup_knockout(
    run_id: str, branch_id: str, payload: CalendarFollowupEightCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    """Seven real 57-backed MatchEngine games in one transaction; no Tour publication."""
    try:
        return CalendarFollowupKnockoutService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_followup_eight_knockout_conflict", "message": str(exc)},
        ) from exc


@router.post("/calendar-continuation/knockouts/simulate-eight-scored", status_code=201)
def simulate_eight_scored_calendar_followup_knockout(
    run_id: str, branch_id: str, payload: CalendarFollowupEightScoredCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    """Seven played rounds and eight prepared placements, never Official points."""
    try:
        return CalendarFollowupKnockoutService(runtime.repository).simulate(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "calendar_followup_eight_scored_conflict", "message": str(exc)},
        ) from exc


# Native real-result closure records signed player match counters as a Saved
# sporting fact. It never authenticates Tour Entry or publishes Official Rankings.
from beta_engine.application.calendar_tournament_closure_service import (
    CalendarNativeTournamentClosureCommand,
    CalendarNativeTournamentClosureService,
)


@router.post("/calendar-continuation/knockouts/close-result", status_code=201)
def close_native_tournament_result(
    run_id: str, branch_id: str, payload: CalendarNativeTournamentClosureCommand,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        return CalendarNativeTournamentClosureService(runtime.repository).close(
            run_id=run_id, branch_id=branch_id, command=payload,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail={
            "code": "calendar_native_tournament_closure_conflict",
            "message": str(exc),
        }) from exc
