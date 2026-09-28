"""Admin boundary for season-versioned group rules and Tournament Format/Topology."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentFormatKind,
    TournamentGroupCrossingMatch,
    TournamentGroupMatchBestOf,
    TournamentGroupRulesPolicy,
    TournamentGroupSeedPlacement,
)
from beta_engine.domain.tournaments.topology_authority import (
    TournamentTopologyAuthority,
)
from beta_engine.infrastructure.db.tournament_format_authority import (
    TournamentFormatAuthorityConflict,
    TournamentFormatAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_rules_policy import (
    TournamentGroupRulesPolicyConflict,
    TournamentGroupRulesPolicyStore,
)
from beta_engine.infrastructure.db.tournament_topology_authority import (
    TournamentTopologyAuthorityConflict,
    TournamentTopologyAuthorityStore,
)


router = APIRouter(tags=["admin-tournament-format-authority"])


class TournamentGroupRulesAdoptRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    effective_from_season_index: int = Field(ge=0, le=49)
    default_match_best_of: TournamentGroupMatchBestOf


class TournamentGroupRulesPolicyResponse(TournamentGroupRulesPolicy):
    """Admin projection with the immutable policy identity made explicit."""

    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_policy(
        cls, policy: TournamentGroupRulesPolicy
    ) -> "TournamentGroupRulesPolicyResponse":
        return cls.model_validate(
            {
                **policy.model_dump(mode="json"),
                "authority_fingerprint": policy.fingerprint,
            }
        )


class TournamentGroupRulesState(BaseModel):
    schema_version: Literal["tournament_group_rules_state.v1"] = (
        "tournament_group_rules_state.v1"
    )
    run_id: str
    branch_id: str
    target_season_index: int = Field(ge=0, le=49)
    effective: TournamentGroupRulesPolicyResponse | None
    versions: tuple[TournamentGroupRulesPolicyResponse, ...]


class TournamentFormatConfigureRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    format_kind: TournamentFormatKind
    group_count: int | None = Field(default=None, ge=1, le=64)
    group_size: int | None = Field(default=None, ge=2, le=128)
    seeded_slots_per_group: int = Field(default=0, ge=0, le=128)
    group_seed_placements: tuple[TournamentGroupSeedPlacement, ...] = ()
    match_best_of_override: TournamentGroupMatchBestOf | None = None
    advancing_per_group: int = Field(default=0, ge=0, le=128)
    knockout_crossings: tuple[TournamentGroupCrossingMatch, ...] = ()


class TournamentTopologyGenerateRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    topology_seed: int | None = None


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournament-group-rules",
    response_model=TournamentGroupRulesState,
)
def inspect_group_rules(
    run_id: str,
    branch_id: str,
    target_season_index: Annotated[int, Query(ge=0, le=49)],
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupRulesState:
    try:
        with runtime.repository._session_factory() as session:
            store = TournamentGroupRulesPolicyStore(session)
            versions = store.list_versions(run_id=run_id, branch_id=branch_id)
            effective = store.resolve(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
            )
            return TournamentGroupRulesState(
                run_id=run_id,
                branch_id=branch_id,
                target_season_index=target_season_index,
                effective=(
                    TournamentGroupRulesPolicyResponse.from_policy(effective)
                    if effective is not None
                    else None
                ),
                versions=tuple(
                    TournamentGroupRulesPolicyResponse.from_policy(value)
                    for value in versions
                ),
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_group_rules_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournament-group-rules/versions",
    response_model=TournamentGroupRulesPolicyResponse,
    status_code=201,
)
def adopt_group_rules(
    run_id: str,
    branch_id: str,
    payload: TournamentGroupRulesAdoptRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupRulesPolicyResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            policy = TournamentGroupRulesPolicyStore(session).adopt(
                run_id=run_id,
                branch_id=branch_id,
                effective_from_season_index=payload.effective_from_season_index,
                command_id=payload.command_id,
                default_match_best_of=payload.default_match_best_of,
            )
            return TournamentGroupRulesPolicyResponse.from_policy(policy)
    except (TournamentGroupRulesPolicyConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_group_rules_conflict", "message": str(exc)},
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format",
    response_model=TournamentFormatAuthority,
)
def inspect_format(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentFormatAuthority:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentFormatAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(status_code=404, detail="Tournament Format authority not found")
            return value
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_format_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format/configure",
    response_model=TournamentFormatAuthority,
    status_code=201,
)
def configure_format(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentFormatConfigureRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentFormatAuthority:
    try:
        with runtime.repository._session_factory.begin() as session:
            return TournamentFormatAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
                format_kind=payload.format_kind,
                group_count=payload.group_count,
                group_size=payload.group_size,
                seeded_slots_per_group=payload.seeded_slots_per_group,
                group_seed_placements=payload.group_seed_placements,
                match_best_of_override=payload.match_best_of_override,
                advancing_per_group=payload.advancing_per_group,
                knockout_crossings=payload.knockout_crossings,
            )
    except (TournamentFormatAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_format_conflict", "message": str(exc)},
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format/topology",
    response_model=TournamentTopologyAuthority,
)
def inspect_topology(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentTopologyAuthority:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentTopologyAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(status_code=404, detail="Tournament Topology authority not found")
            return value
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_topology_conflict", "message": str(exc)},
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format/topology/generate",
    response_model=TournamentTopologyAuthority,
    status_code=201,
)
def generate_topology(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentTopologyGenerateRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentTopologyAuthority:
    try:
        with runtime.repository._session_factory.begin() as session:
            return TournamentTopologyAuthorityStore(session).generate(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
                topology_seed=payload.topology_seed,
            )
    except (TournamentTopologyAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "tournament_topology_conflict", "message": str(exc)},
        ) from exc
