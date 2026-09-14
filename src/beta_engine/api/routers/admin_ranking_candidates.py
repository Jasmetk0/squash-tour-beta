"""Admin ranking inspection and explicit preparation Save; no publication."""

from typing import Annotated
import json
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from beta_engine.application.ranking_bootstrap_command import RankingBootstrapCommand
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.transition_authority import RankingTransitionAuthority
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.season_point_awards_service import SeasonPointAwardsService
from beta_engine.domain.rankings.command_audit import RankingCommandAudit
from beta_engine.application.initial_world import derive_initial_ranking_inputs

from fastapi import APIRouter, Depends, HTTPException, Path, Header

from beta_engine.api.deps import (
    ApiRuntime,
    get_runtime,
    get_run_working_draft_service,
    get_season_point_awards_service,
)
from beta_engine.application.ranking_inspection import (
    RankingCandidateDetail,
    RankingCandidateHistory,
    RankingCandidateSources,
    RankingCandidateInputs,
    RankingPreparationPreview,
)

router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates",
    tags=["admin-rankings"],
)


def _history(
    runtime: ApiRuntime, run_id: str, branch_id: str
) -> RankingCandidateHistory:
    try:
        return runtime.repository.inspect_official_ranking_history(
            run_id=run_id, branch_id=branch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Ranking Run/Branch scope not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_history_unavailable", "message": str(exc)},
        ) from exc


@router.get("", response_model=RankingCandidateHistory)
def get_history(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    return _history(runtime, run_id, branch_id)


def _prepare(
    runtime,
    run_id,
    branch_id,
    payload,
    model,
    *,
    preview=False,
    expected=None,
    expected_request=None,
    awards=None,
):
    try:
        # Strict domain tuples validate in JSON mode; arrays are their wire form.
        command = model.model_validate_json(json.dumps(payload))
        if command.audit is None:
            raise ValueError("Admin audit is required")
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_ranking_command",
                "message": "A valid ranking command with audit label and reason is required.",
            },
        ) from exc
    try:
        if expected_request is not None and command.fingerprint != expected_request:
            raise ValueError("Ranking command changed since preview")
        snapshot = runtime.repository.prepare_official_ranking(
            run_id=run_id,
            branch_id=branch_id,
            command=command,
            preview=preview,
            expected_snapshot_fingerprint=expected,
            awards=awards,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_preparation_conflict", "message": str(exc)},
        ) from exc
    candidate = RankingCandidateDetail(
        snapshot=snapshot,
        fingerprint=snapshot.fingerprint,
        command_ids=(command.command_id,),
    )
    return (
        RankingPreparationPreview(
            request_fingerprint=command.fingerprint, candidate=candidate
        )
        if preview
        else candidate
    )


@router.post("/prepare/initial", response_model=RankingCandidateDetail, status_code=201)
def prepare_initial(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    expected: Annotated[
        str | None,
        Header(alias="X-Ranking-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"),
    ] = None,
    expected_request: Annotated[
        str | None, Header(alias="X-Ranking-Preview-Request", pattern=r"^[0-9a-f]{64}$")
    ] = None,
):
    return _prepare(
        runtime,
        run_id,
        branch_id,
        payload,
        RankingBootstrapCommand,
        expected=expected,
        expected_request=expected_request,
    )


@router.post("/prepare/week", response_model=RankingCandidateDetail, status_code=201)
def prepare_week(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    expected: Annotated[
        str | None,
        Header(alias="X-Ranking-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"),
    ] = None,
    expected_request: Annotated[
        str | None, Header(alias="X-Ranking-Preview-Request", pattern=r"^[0-9a-f]{64}$")
    ] = None,
):
    return _prepare(
        runtime,
        run_id,
        branch_id,
        payload,
        RankingWeekCommand,
        expected=expected,
        expected_request=expected_request,
        awards=awards,
    )


@router.post("/prepare/initial/preview", response_model=RankingPreparationPreview)
def preview_initial(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    return _prepare(
        runtime, run_id, branch_id, payload, RankingBootstrapCommand, preview=True
    )


class DerivedInitialPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    command_id: str = Field(min_length=1, max_length=128)
    audit: RankingCommandAudit


def _derived_initial(
    runtime: ApiRuntime,
    run_id: str,
    branch_id: str,
    payload: dict,
    *,
    preview: bool,
    expected=None,
    expected_request=None,
):
    try:
        request = DerivedInitialPreparation.model_validate_json(json.dumps(payload))
        world = runtime.repository.get_initial_world(run_id=run_id, branch_id=branch_id)
        if world is None:
            raise ValueError("Run/Branch initial-player snapshot is missing")
        policy, players = derive_initial_ranking_inputs(world)
        command = {
            "kind": "initial_ranking.v1",
            "command_id": request.command_id,
            "run_id": run_id,
            "branch_id": branch_id,
            "target_week": {"season_index": 0, "week": 1},
            "policy": policy.model_dump(mode="json"),
            "players": [p.model_dump(mode="json") for p in players],
            "discipline": "none",
            "initial_world_fingerprint": world.fingerprint,
            "audit": request.audit.model_dump(mode="json"),
        }
        return _prepare(
            runtime,
            run_id,
            branch_id,
            command,
            RankingBootstrapCommand,
            preview=preview,
            expected=expected,
            expected_request=expected_request,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "initial_world_ranking_unavailable", "message": str(exc)},
        ) from exc


@router.post(
    "/prepare/initial/derived/preview", response_model=RankingPreparationPreview
)
def preview_derived_initial(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    return _derived_initial(runtime, run_id, branch_id, payload, preview=True)


@router.post(
    "/prepare/initial/derived", response_model=RankingCandidateDetail, status_code=201
)
def prepare_derived_initial(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    expected: Annotated[
        str | None,
        Header(alias="X-Ranking-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"),
    ] = None,
    expected_request: Annotated[
        str | None, Header(alias="X-Ranking-Preview-Request", pattern=r"^[0-9a-f]{64}$")
    ] = None,
):
    return _derived_initial(
        runtime,
        run_id,
        branch_id,
        payload,
        preview=False,
        expected=expected,
        expected_request=expected_request,
    )


@router.post("/prepare/week/preview", response_model=RankingPreparationPreview)
def preview_week(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    return _prepare(
        runtime,
        run_id,
        branch_id,
        payload,
        RankingWeekCommand,
        preview=True,
        awards=awards,
    )


class RankingSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_draft_version: int = Field(ge=0)
    expected_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.post(
    "/transition-authorities",
    response_model=RankingTransitionAuthority,
    status_code=201,
)
def adopt_transition_authority(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    try:
        authority = RankingTransitionAuthority.model_validate_json(json.dumps(payload))
        if (authority.run_id, authority.branch_id) != (run_id, branch_id):
            raise ValueError("Ranking authority request scope mismatch")
        return runtime.repository.adopt_ranking_transition_authority(authority)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_ranking_authority", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_authority_conflict", "message": str(exc)},
        ) from exc


class AuthoritativeWeekPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    command_id: str = Field(min_length=1, max_length=128)
    target_week: RankingWeek
    tournaments: tuple = ()
    corrections: tuple = ()
    zero_versions: tuple = ()
    audit: dict


def _authoritative_prepare(
    runtime,
    awards,
    run_id,
    branch_id,
    payload,
    *,
    preview,
    expected=None,
    expected_request=None,
):
    try:
        request = AuthoritativeWeekPreparation.model_validate_json(json.dumps(payload))
        authority = runtime.repository.resolve_ranking_transition_authority(
            run_id=run_id,
            branch_id=branch_id,
            target_ordinal=request.target_week.ordinal,
        )
        derived_players = runtime.repository.derive_lifecycle_ranking_roster(
            run_id=run_id,
            branch_id=branch_id,
            completed_week=authority.completed_week,
            target_week=authority.target_week,
        )
        command_payload = request.model_dump(mode="json")
        command_payload.pop("target_week")
        command_payload["authority_fingerprint"] = authority.fingerprint
        command_payload["context"] = {
            "run_id": run_id,
            "branch_id": branch_id,
            "completed_week": authority.completed_week.model_dump(mode="json"),
            "target_week": authority.target_week.model_dump(mode="json"),
            "policy": authority.policy.model_dump(mode="json"),
            "players": [p.model_dump(mode="json") for p in derived_players],
            "discipline": "stored_zeros",
        }
        return _prepare(
            runtime,
            run_id,
            branch_id,
            command_payload,
            RankingWeekCommand,
            preview=preview,
            expected=expected,
            expected_request=expected_request,
            awards=awards,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_authority_unavailable", "message": str(exc)},
        ) from exc


@router.post(
    "/prepare/week/authoritative/preview", response_model=RankingPreparationPreview
)
def preview_authoritative_week(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
):
    return _authoritative_prepare(
        runtime, awards, run_id, branch_id, payload, preview=True
    )


@router.post(
    "/prepare/week/authoritative",
    response_model=RankingCandidateDetail,
    status_code=201,
)
def prepare_authoritative_week(
    run_id: str,
    branch_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
    awards: Annotated[
        SeasonPointAwardsService, Depends(get_season_point_awards_service)
    ],
    expected: Annotated[
        str | None,
        Header(alias="X-Ranking-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"),
    ] = None,
    expected_request: Annotated[
        str | None, Header(alias="X-Ranking-Preview-Request", pattern=r"^[0-9a-f]{64}$")
    ] = None,
):
    return _authoritative_prepare(
        runtime,
        awards,
        run_id,
        branch_id,
        payload,
        preview=False,
        expected=expected,
        expected_request=expected_request,
    )


@router.get("/save/preview")
def preview_save(
    run_id: str, branch_id: str, runtime: Annotated[ApiRuntime, Depends(get_runtime)]
):
    try:
        return runtime.repository.preview_ranking_save(
            run_id=run_id, branch_id=branch_id
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_save_unavailable", "message": str(exc)},
        ) from exc


@router.post("/save", status_code=201)
def save_ranking(
    run_id: str,
    branch_id: str,
    payload: RankingSaveRequest,
    service: Annotated[RunWorkingDraftService, Depends(get_run_working_draft_service)],
):
    try:
        return service.save_ranking(
            run_id=run_id, branch_id=branch_id, **payload.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "ranking_save_conflict", "message": str(exc)},
        ) from exc


@router.get("/{season_index}/{week}", response_model=RankingCandidateDetail)
def get_candidate(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    history = _history(runtime, run_id, branch_id)
    for candidate in history.candidates:
        if (candidate.snapshot.week.season_index, candidate.snapshot.week.week) == (
            season_index,
            week,
        ):
            return candidate
    raise HTTPException(status_code=404, detail="Ranking candidate week not found")


@router.get("/{season_index}/{week}/sources", response_model=RankingCandidateSources)
def get_sources(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    from beta_engine.domain.rankings.official import RankingWeek

    try:
        return runtime.repository.inspect_official_ranking_sources(
            run_id=run_id,
            branch_id=branch_id,
            week=RankingWeek(season_index=season_index, week=week),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Ranking scope or candidate week not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ranking_sources_unavailable",
                "message": "Stored ranking sources could not be verified.",
            },
        ) from exc


@router.get("/{season_index}/{week}/inputs", response_model=RankingCandidateInputs)
def get_inputs(
    run_id: str,
    branch_id: str,
    season_index: Annotated[int, Path(ge=0, le=49)],
    week: Annotated[int, Path(ge=1, le=61)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
):
    from beta_engine.domain.rankings.official import RankingWeek

    try:
        return runtime.repository.inspect_official_ranking_inputs(
            run_id=run_id,
            branch_id=branch_id,
            week=RankingWeek(season_index=season_index, week=week),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, detail="Ranking scope or candidate week not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ranking_inputs_unavailable",
                "message": "Stored ranking inputs could not be verified.",
            },
        ) from exc
