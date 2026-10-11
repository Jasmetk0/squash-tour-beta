from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query

from beta_engine.api.deps import (
    get_initial_player_pool_service,
    get_initial_pool_season_bootstrap_service,
    get_runtime,
    get_run_package_service,
    get_run_world_initial_pool_preview_service,
    get_run_world_initial_world_service,
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
from beta_engine.application.run_world_initial_world_service import (
    RunWorldInitialWorldAdoptionRequest,
    RunWorldInitialWorldService,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.application.initial_world import (
    InitialWorldAdoptionRequest,
    InitialWorldState,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from pydantic import BaseModel, ConfigDict, Field, model_validator
from beta_engine.application.run_world_initial_pool_preview_service import RunWorldPreviewFieldLock
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


def _lifecycle_policy(
    payload: InitialWorldAdoptionRequest | RunWorldInitialWorldAdoptionRequest,
) -> PlayerLifecyclePolicy:
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


@router.post(
    "/runs/{run_id}/branches/{branch_id}/initial-world/world-package/preview"
)
def preview_run_world_initial_world(
    run_id: str,
    branch_id: str,
    payload: RunWorldInitialWorldAdoptionRequest,
    service: RunWorldInitialWorldService = Depends(
        get_run_world_initial_world_service
    ),
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        branch = runtime.repository.get_run_branch(branch_id=branch_id)
        if branch is None or branch.run_id != run_id:
            raise KeyError("Initial-world Run/Branch scope not found")
        state = service.preview(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
        return {
            "preview_only": True,
            "state": state,
            "fingerprint": state.fingerprint,
        }
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "run_world_initial_world_unavailable",
                "message": str(exc),
            },
        ) from exc


def _assert_reviewed_generation_context(
    *, runtime: ApiRuntime, package_service: RunPackageService,
    run_id: str, branch_id: str, expected_head: str,
    expected_draft_version: int, expected_package_fingerprint: str,
) -> None:
    """Re-check the exact reviewed source and clean HEAD before any player write.

    A Run-owned World is never allowed to silently swap to dirty/live
    unsaved Package state, even when its identity and seed still match.
    """
    repository = runtime.repository
    run = repository.get_run_container(run_id=run_id)
    branch = repository.get_run_branch(branch_id=branch_id)
    if (run is None or run.storage_kind != "custom_local" or run.read_only or
        branch is None or branch.run_id != run_id or branch.read_only or
        branch.status != "active"):
        raise ValueError("Player generation requires a writable owned Run/Branch")
    revision_state = repository.get_branch_revision_state(branch_id=branch_id)
    saved = revision_state.saved_revision
    draft = revision_state.working_draft
    if (revision_state.run_id != run_id or revision_state.branch_id != branch_id or
        branch.saved_head_revision_id != expected_head or
        saved.revision_id != expected_head or
        saved.run_id != run_id or saved.branch_id != branch_id or
        draft.base_revision_id != expected_head or
        draft.draft_version != expected_draft_version or draft.status != "clean"):
        raise ValueError("Player generation preview is stale: Run/Branch HEAD or Working Draft changed")
    current = package_service.get(run_id=run_id, branch_id=branch_id)
    saved_packages = load_saved_run_package_state(
        saved.payload, run_id=run_id, branch_id=branch_id,
    )
    if (current is None or saved_packages is None or
        current.fingerprint != expected_package_fingerprint or
        saved_packages.fingerprint != expected_package_fingerprint):
        raise ValueError("Player generation preview is stale: Run-owned World Package changed")


class RunWorldGenerationCountryOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: str = Field(min_length=3, max_length=3)
    name: str
    region: str
    travel_region: str


class RunWorldGenerationOptions(BaseModel):
    """Allowed hard conditions from the exact saved Run/Branch World copy."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["run_world_generation_options.v1"] = "run_world_generation_options.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    draft_version: int
    run_package_fingerprint: str
    world_package_id: str
    countries: tuple[RunWorldGenerationCountryOption, ...]
    regions: tuple[str, ...]  # Legacy combined choices for older clients
    geographic_regions: tuple[str, ...]
    travel_regions: tuple[str, ...]


@router.get(
    "/runs/{run_id}/branches/{branch_id}/initial-world/world-package/generation-options",
    response_model=RunWorldGenerationOptions,
)
def get_run_world_generation_options(
    run_id: str,
    branch_id: str,
    world_package_id: str = Query(min_length=1, max_length=128),
    expected_head: str = Query(min_length=1, max_length=128),
    expected_draft_version: int = Query(ge=0),
    expected_package_fingerprint: str = Query(pattern=r"^[0-9a-f]{64}$"),
    package_service: RunPackageService = Depends(get_run_package_service),
    world_adapter: WorldPackageRunAdapter = Depends(get_world_package_run_adapter),
    runtime: ApiRuntime = Depends(get_runtime),
) -> RunWorldGenerationOptions:
    """Read-only versioned country/region choices; no global World fallbacks."""
    try:
        _assert_reviewed_generation_context(
            runtime=runtime, package_service=package_service,
            run_id=run_id, branch_id=branch_id, expected_head=expected_head,
            expected_draft_version=expected_draft_version,
            expected_package_fingerprint=expected_package_fingerprint,
        )
        state = package_service.get(run_id=run_id, branch_id=branch_id)
        projection = world_adapter.project_countries(
            state, package_id=world_package_id,
        )
        countries = tuple(
            RunWorldGenerationCountryOption(
                code=c.code, name=c.name, region=c.region,
                travel_region=c.effective_travel_region,
            )
            for c in projection.countries
        )
        if not countries:
            raise ValueError("Selected saved World has no eligible countries")
        regions = tuple(sorted({
            value for c in countries for value in (c.region, c.travel_region)
            if value
        }))
        return RunWorldGenerationOptions(
            run_id=run_id, branch_id=branch_id,
            saved_revision_id=expected_head,
            draft_version=expected_draft_version,
            run_package_fingerprint=expected_package_fingerprint,
            world_package_id=world_package_id,
            countries=countries, regions=regions,
            geographic_regions=tuple(sorted({c.region for c in countries})),
            travel_regions=tuple(sorted({c.travel_region for c in countries})),
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "run_world_generation_options_unavailable", "message": str(exc)},
        ) from exc


@router.post(
    "/runs/{run_id}/branches/{branch_id}/initial-world/world-package",
    status_code=201,
)
def adopt_run_world_initial_world(
    run_id: str,
    branch_id: str,
    payload: RunWorldInitialWorldAdoptionRequest,
    expected: str = Header(
        alias="X-Initial-World-Preview-Fingerprint", pattern=r"^[0-9a-f]{64}$"
    ),
    service: RunWorldInitialWorldService = Depends(
        get_run_world_initial_world_service
    ),
    package_service: RunPackageService = Depends(get_run_package_service),
    expected_saved_head: str | None = Header(
        default=None, alias="X-Expected-Saved-Revision-Id", max_length=128
    ),
    expected_draft_version: int | None = Header(
        default=None, alias="X-Expected-Draft-Version", ge=0
    ),
    expected_package_fingerprint: str | None = Header(
        default=None, alias="X-Expected-Run-Package-Fingerprint",
        pattern=r"^[0-9a-f]{64}$"
    ),
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        reviewed = (expected_saved_head, expected_draft_version, expected_package_fingerprint)
        if any(item is not None for item in reviewed):
            if any(item is None for item in reviewed):
                raise ValueError("Reviewed generation requires complete HEAD/Draft/World preconditions")
            _assert_reviewed_generation_context(
                runtime=runtime, package_service=package_service,
                run_id=run_id, branch_id=branch_id,
                expected_head=expected_saved_head,
                expected_draft_version=expected_draft_version,
                expected_package_fingerprint=expected_package_fingerprint,
            )
        current = runtime.repository.get_initial_world(
            run_id=run_id, branch_id=branch_id
        )
        request_fingerprint = payload.fingerprint_for_scope(
            run_id=run_id, branch_id=branch_id
        )
        if current is not None:
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

        state = service.preview(
            run_id=run_id,
            branch_id=branch_id,
            request=payload,
        )
        if state.fingerprint != expected:
            raise ValueError(
                "Run-owned generated player pool changed since reviewed preview"
            )
        return runtime.repository.adopt_initial_world(
            state, lifecycle_policy=_lifecycle_policy(payload)
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "run_world_initial_world_conflict",
                "message": str(exc),
            },
        ) from exc


# These are saved *candidate reviews*, not Branch Working Draft state and
# never a way around the authoritative InitialWorld adoption command.
class RunGenerationProposalSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    proposal_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    label: str = Field(min_length=1, max_length=160)
    saved_revision_id: str = Field(min_length=1, max_length=128)
    draft_version: int = Field(ge=0)
    package_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_seed: int
    next_seed: int
    selected_keep_ids: list[str] = Field(default_factory=list, max_length=2000)
    pending_field_locks: list[RunWorldPreviewFieldLock] = Field(default_factory=list, max_length=2000)
    request: RunWorldInitialWorldAdoptionRequest

    @model_validator(mode="after")
    def validate_pending_review(self) -> "RunGenerationProposalSave":
        keep = self.selected_keep_ids
        if keep != sorted(set(keep)) or any(not player_id or len(player_id)>128 for player_id in keep):
            raise ValueError("Saved proposal Keep IDs must be unique and sorted")
        locks = [(lock.player_id, lock.field) for lock in self.pending_field_locks]
        if locks != sorted(set(locks)):
            raise ValueError("Saved proposal field locks must be unique and sorted")
        g = self.request.generation
        first = (g.keep_history[0].keep_from_seed if g.keep_history else
                 g.keep_from_seed if g.keep_from_seed is not None else g.seed)
        if self.source_seed != first:
            raise ValueError("Saved proposal original seed does not match verified replay ancestry")
        return self


def _generation_proposal_storage(runtime: ApiRuntime):
    from beta_engine.infrastructure.db import generation_proposals
    return generation_proposals, runtime.repository._session_factory


def _assert_generator_proposal_owner(runtime: ApiRuntime, run_id: str, branch_id: str) -> None:
    run = runtime.repository.get_run_container(run_id=run_id)
    branch = runtime.repository.get_run_branch(branch_id=branch_id)
    if (run is None or run.storage_kind != "custom_local" or run.read_only
        or branch is None or branch.run_id != run_id
        or branch.read_only or branch.status != "active"):
        raise ValueError("Saved player proposal Run/Branch is missing or read-only")


@router.post(
    "/runs/{run_id}/branches/{branch_id}/initial-world/generation-proposals",
    status_code=201,
)
def save_run_generation_proposal(
    run_id: str, branch_id: str,
    payload: RunGenerationProposalSave,
    package_service: RunPackageService = Depends(get_run_package_service),
    preview_service: RunWorldInitialWorldService = Depends(get_run_world_initial_world_service),
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        _assert_generator_proposal_owner(runtime, run_id, branch_id)
        _assert_reviewed_generation_context(
            runtime=runtime, package_service=package_service,
            run_id=run_id, branch_id=branch_id,
            expected_head=payload.saved_revision_id,
            expected_draft_version=payload.draft_version,
            expected_package_fingerprint=payload.package_fingerprint,
        )
        if runtime.repository.get_initial_world(run_id=run_id, branch_id=branch_id):
            raise ValueError("InitialWorld already exists; proposal editing is closed")
        state = preview_service.preview(
            run_id=run_id, branch_id=branch_id, request=payload.request,
        )
        if state.fingerprint != payload.preview_fingerprint:
            raise ValueError("Saved proposal preview is stale; exact source no longer matches")
        known = {player.player_id for player in state.players}
        if any(player_id not in known for player_id in payload.selected_keep_ids):
            raise ValueError("Saved proposal Keep references players absent from review")
        if any(lock.player_id not in known for lock in payload.pending_field_locks):
            raise ValueError("Saved proposal field edit references players absent from review")
        data = {
            "schema_version": "run_generation_proposal.v1",
            "run_id": run_id, "branch_id": branch_id,
            "proposal_id": payload.proposal_id, "label": payload.label.strip(),
            "saved_revision_id": payload.saved_revision_id,
            "draft_version": payload.draft_version,
            "package_fingerprint": payload.package_fingerprint,
            "preview_fingerprint": state.fingerprint,
            "source_seed": payload.source_seed,
            "next_seed": payload.next_seed,
            "selected_keep_ids": payload.selected_keep_ids,
            "pending_field_locks": [lock.model_dump(mode="json") for lock in payload.pending_field_locks],
            "request": payload.request.model_dump(mode="json"),
            "preview": {
                "preview_only": True,
                "state": state.model_dump(mode="json"),
                "fingerprint": state.fingerprint,
            },
        }
        storage, sessions = _generation_proposal_storage(runtime)
        return storage.save_proposal(sessions, data=data)
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=409, detail={"code": "generation_proposal_conflict", "message": str(exc)},
        ) from exc


@router.get("/runs/{run_id}/branches/{branch_id}/initial-world/generation-proposals")
def list_run_generation_proposals(
    run_id: str, branch_id: str, runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        _assert_generator_proposal_owner(runtime, run_id, branch_id)
        storage, sessions = _generation_proposal_storage(runtime)
        return {"proposals": storage.list_proposals(sessions, run_id=run_id, branch_id=branch_id)}
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runs/{run_id}/branches/{branch_id}/initial-world/generation-proposals/{proposal_id}")
def read_run_generation_proposal(
    run_id: str, branch_id: str, proposal_id: str,
    package_service: RunPackageService = Depends(get_run_package_service),
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        _assert_generator_proposal_owner(runtime, run_id, branch_id)
        storage, sessions = _generation_proposal_storage(runtime)
        data = storage.get_proposal(
            sessions, run_id=run_id, branch_id=branch_id, proposal_id=proposal_id,
        )
        if data is None:
            raise HTTPException(status_code=404, detail="Saved generation proposal not found")
        _assert_reviewed_generation_context(
            runtime=runtime, package_service=package_service,
            run_id=run_id, branch_id=branch_id,
            expected_head=data["saved_revision_id"],
            expected_draft_version=data["draft_version"],
            expected_package_fingerprint=data["package_fingerprint"],
        )
        if runtime.repository.get_initial_world(run_id=run_id, branch_id=branch_id):
            raise ValueError("InitialWorld already exists; saved proposal may not be reopened for adoption")
        from beta_engine.application.initial_world import InitialWorldState
        from beta_engine.domain.run_packages import canonical_hash
        reviewed = InitialWorldState.model_validate(data["preview"]["state"])
        request = RunWorldInitialWorldAdoptionRequest.model_validate(data["request"])
        if (reviewed.fingerprint != data["preview_fingerprint"]
            or reviewed.adopted_by_command_id != request.command_id
            or reviewed.adoption_request_fingerprint != request.fingerprint_for_scope(
                run_id=run_id, branch_id=branch_id,
            ) or reviewed.world_package_id != request.generation.world_package_id):
            raise ValueError("Saved proposal reviewed preview provenance is corrupt")
        return data  # no preview service call / no regeneration on read
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=409, detail={"code": "generation_proposal_stale", "message": str(exc)},
        ) from exc


@router.delete("/runs/{run_id}/branches/{branch_id}/initial-world/generation-proposals/{proposal_id}",
               status_code=204)
def delete_run_generation_proposal(
    run_id: str, branch_id: str, proposal_id: str,
    runtime: ApiRuntime = Depends(get_runtime),
):
    try:
        _assert_generator_proposal_owner(runtime, run_id, branch_id)
        storage, sessions = _generation_proposal_storage(runtime)
        if not storage.delete_proposal(
            sessions, run_id=run_id, branch_id=branch_id, proposal_id=proposal_id,
        ):
            raise HTTPException(status_code=404, detail="Saved generation proposal not found")
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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
