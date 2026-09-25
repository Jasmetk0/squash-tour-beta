from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Header

from beta_engine.api.deps import (
    get_initial_player_pool_service,
    get_initial_pool_season_bootstrap_service,
    get_runtime,
    get_run_package_service,
    get_run_world_initial_pool_preview_service,
    get_run_working_draft_service,
    get_world_package_run_adapter,
)
from beta_engine.api.deps import ApiRuntime
from beta_engine.application.season_player_bootstrap_service import (
    InitialPoolSeasonBootstrapService,
)
from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.run_world_initial_pool_preview_service import (
    RunWorldInitialPoolPreviewRequest,
    RunWorldInitialPoolPreviewService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.application.initial_world import (
    InitialWorldAdoptionRequest,
    InitialWorldState,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from pydantic import BaseModel, ConfigDict, Field
from beta_engine.api.schemas import (
    CustomInitialPoolPlayerCreateRequest,
    InitialPoolGenerateRequest,
    InitialPoolPlayerUpdateRequest,
    InitialPoolRegenerateRequest,
)
from beta_engine.application.initial_player_pool_service import InitialPlayerPoolService
from beta_engine.domain.players.initial_pool import (
    InitialPoolAuditList,
    InitialPoolGeneratedPlayer,
    InitialPoolResult,
)

router = APIRouter(prefix="/admin/players", tags=["admin-players"])


def _lifecycle_policy(payload: InitialWorldAdoptionRequest) -> PlayerLifecyclePolicy:
    if payload.automatic_retirement_age is None or payload.official_run:
        return PlayerLifecyclePolicy(
            policy_id="official-fax-lifecycle.v1",
            automatic_retirement_age=46,
            provenance="Official Run default; legacy v1 lifecycle migration",
        )
    return PlayerLifecyclePolicy(
        policy_id="custom-lifecycle.v1",
        automatic_retirement_age=payload.automatic_retirement_age,
        provenance="Explicit custom Initial World adoption policy",
    )


def _resolved_initial_world(
    run_id: str,
    branch_id: str,
    payload: InitialWorldAdoptionRequest,
    bootstrap: InitialPoolSeasonBootstrapService,
    package_service: RunPackageService,
    world_adapter: WorldPackageRunAdapter,
) -> InitialWorldState:
    result = bootstrap.bootstrap_from_initial_pool(
        season="2000/2001",
        source_season=payload.source_season,
        seed=payload.bootstrap_seed,
        dry_run=True,
        overwrite_existing=False,
    )
    best_n = 15 if payload.official_run else payload.best_n
    if best_n is None:  # model validation normally makes this unreachable
        raise ValueError("Custom Run requires an explicit first-season Best N")

    world_country_content_fingerprint = None
    if payload.world_package_id is not None:
        package_state = package_service.get(run_id=run_id, branch_id=branch_id)
        if package_state is None:
            raise ValueError(
                "Initial World requested a World Package, but Run Package state is empty"
            )
        projection = world_adapter.project_countries(
            package_state, package_id=payload.world_package_id
        )
        configured_codes = {country.code for country in projection.countries}
        referenced_codes = {
            code
            for player in result.players
            for code in (player.country_code, player.nationality)
        }
        missing_codes = sorted(referenced_codes - configured_codes)
        if missing_codes:
            raise ValueError(
                "Initial World players reference countries absent from Run World "
                f"Package '{payload.world_package_id}': {', '.join(missing_codes)}"
            )
        world_country_content_fingerprint = projection.content_fingerprint

    return InitialWorldState(
        run_id=run_id,
        branch_id=branch_id,
        players=tuple(sorted(result.players, key=lambda p: p.player_id)),
        policies=(
            OfficialRankingPolicy(policy_id="msa-official-2000-01", best_n=best_n),
        ),
        source_kind="production_initial_pool.v1",
        source_season=payload.source_season,
        source_fingerprint=result.metadata.source_initial_pool_fingerprint,
        world_package_id=payload.world_package_id,
        world_country_content_fingerprint=world_country_content_fingerprint,
        bootstrap_seed=payload.bootstrap_seed,
        bootstrap_fingerprint=result.metadata.bootstrap_fingerprint,
        adopted_by_command_id=payload.command_id,
        audit_label=payload.audit_label,
        audit_reason=payload.audit_reason,
        adoption_request_fingerprint=payload.fingerprint_for_scope(
            run_id=run_id, branch_id=branch_id
        ),
    )


@router.post("/runs/{run_id}/branches/{branch_id}/initial-world/preview")
def preview_initial_world(
    run_id: str,
    branch_id: str,
    payload: InitialWorldAdoptionRequest,
    bootstrap: InitialPoolSeasonBootstrapService = Depends(
        get_initial_pool_season_bootstrap_service
    ),
    package_service: RunPackageService = Depends(get_run_package_service),
    world_adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
    runtime: ApiRuntime = Depends(get_runtime),
):
    # Validate product scope even though preview remains strictly read-only.
    try:
        branch = runtime.repository.get_run_branch(branch_id=branch_id)
        if branch is None or branch.run_id != run_id:
            raise KeyError("Initial-world Run/Branch scope not found")
        state = _resolved_initial_world(
            run_id,
            branch_id,
            payload,
            bootstrap,
            package_service,
            world_adapter,
        )
        return {"preview_only": True, "state": state, "fingerprint": state.fingerprint}
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "initial_world_unavailable", "message": str(exc)},
        ) from exc


@router.post("/runs/{run_id}/branches/{branch_id}/initial-world", status_code=201)
def adopt_initial_world(
    run_id: str,
    branch_id: str,
    payload: InitialWorldAdoptionRequest,
    expected: str = Header(
        alias="X-Initial-World-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"
    ),
    bootstrap: InitialPoolSeasonBootstrapService = Depends(
        get_initial_pool_season_bootstrap_service
    ),
    package_service: RunPackageService = Depends(get_run_package_service),
    world_adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        current = runtime.repository.get_initial_world(
            run_id=run_id, branch_id=branch_id
        )
        if current is not None:
            request_fingerprint = payload.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id
            )
            if (
                current.adopted_by_command_id != payload.command_id
                or current.adoption_request_fingerprint != request_fingerprint
                or current.fingerprint != expected
            ):
                raise ValueError(
                    "Initial-world adoption retry differs from the stored request"
                )
            runtime.repository.ensure_initial_world_lifecycle(
                current, policy=_lifecycle_policy(payload)
            )
            return current
        state = _resolved_initial_world(
            run_id,
            branch_id,
            payload,
            bootstrap,
            package_service,
            world_adapter,
        )
        if state.fingerprint != expected:
            raise ValueError("Production initial-player source changed since preview")
        return runtime.repository.adopt_initial_world(
            state, lifecycle_policy=_lifecycle_policy(payload)
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "initial_world_conflict", "message": str(exc)},
        ) from exc


@router.get("/runs/{run_id}/branches/{branch_id}/initial-world")
def read_initial_world(
    run_id: str, branch_id: str, runtime: ApiRuntime = Depends(get_runtime)
):
    try:
        state = runtime.repository.get_initial_world(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise KeyError("Initial world not found")
        return state
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class InitialWorldSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_draft_version: int = Field(ge=0)
    expected_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.get("/runs/{run_id}/branches/{branch_id}/initial-world/save/preview")
def preview_initial_world_save(
    run_id: str, branch_id: str, runtime: ApiRuntime = Depends(get_runtime)
):
    return runtime.repository.preview_initial_world_save(
        run_id=run_id, branch_id=branch_id
    )


@router.post("/runs/{run_id}/branches/{branch_id}/initial-world/save", status_code=201)
def save_initial_world(
    run_id: str,
    branch_id: str,
    payload: InitialWorldSaveRequest,
    service: RunWorkingDraftService = Depends(get_run_working_draft_service),
):
    try:
        return service.save_initial_world(
            run_id=run_id, branch_id=branch_id, **payload.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "initial_world_save_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/runs/{run_id}/branches/{branch_id}/initial-pool/world-package/preview"
)
def preview_run_world_initial_pool(
    run_id: str,
    branch_id: str,
    payload: RunWorldInitialPoolPreviewRequest,
    service: RunWorldInitialPoolPreviewService = Depends(
        get_run_world_initial_pool_preview_service
    ),
):
    try:
        preview = service.preview(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
        return {
            **preview.model_dump(mode="json"),
            "preview_fingerprint": preview.preview_fingerprint,
        }
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "run_world_initial_pool_preview_unavailable",
                "message": str(exc),
            },
        ) from exc


@router.get("/initial-pool", response_model=InitialPoolResult)
def get_initial_pool(
    season: str = "2000/2001",
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    return service.get_pool(season=season)


@router.post("/initial-pool/generate", response_model=InitialPoolResult)
def generate_initial_pool(
    payload: InitialPoolGenerateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    try:
        return service.generate_pool(
            season=payload.season,
            seed=payload.seed,
            target_pool_size=payload.target_pool_size or 128,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/initial-pool/regenerate-unlocked", response_model=InitialPoolResult)
def regenerate_initial_pool_unlocked(
    payload: InitialPoolRegenerateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolResult:
    try:
        return service.regenerate_unlocked(
            season=payload.season,
            seed=payload.seed,
            target_pool_size=payload.target_pool_size,
            country_code=payload.country_code,
            region=payload.region,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/custom", response_model=InitialPoolGeneratedPlayer)
def create_custom_player(
    payload: CustomInitialPoolPlayerCreateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.create_custom_player(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{player_id}", response_model=InitialPoolGeneratedPlayer)
def update_player(
    player_id: str,
    payload: InitialPoolPlayerUpdateRequest,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.update_player(player_id=player_id, payload=payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/audit", response_model=InitialPoolAuditList)
def get_audit_events(
    season: str | None = None,
    player_id: str | None = None,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolAuditList:
    return service.get_audit_events(season=season, player_id=player_id)


@router.post("/{player_id}/lock", response_model=InitialPoolGeneratedPlayer)
def lock_player(
    player_id: str,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.set_lock(player_id=player_id, locked=True)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/{player_id}/unlock", response_model=InitialPoolGeneratedPlayer)
def unlock_player(
    player_id: str,
    service: InitialPlayerPoolService = Depends(get_initial_player_pool_service),
) -> InitialPoolGeneratedPlayer:
    try:
        return service.set_lock(player_id=player_id, locked=False)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
