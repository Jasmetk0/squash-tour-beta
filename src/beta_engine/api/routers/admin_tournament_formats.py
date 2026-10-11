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
from beta_engine.domain.tournaments.group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthority,
)
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
    TournamentGroupStandingsTieCase,
)
from beta_engine.domain.tournaments.group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthority,
)
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
)
from beta_engine.domain.tournaments.hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthority,
)
from beta_engine.domain.tournaments.hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthority,
)
from beta_engine.domain.tournaments.pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthority,
)
from beta_engine.application.pure_groups_tournament_closure import (
    TournamentPureGroupsClosureConflict,
    TournamentPureGroupsClosureService,
)
from beta_engine.application.hybrid_tournament_closure import (
    TournamentHybridClosureConflict,
    TournamentHybridClosureService,
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
from beta_engine.infrastructure.db.tournament_group_match_schedule_authority import (
    TournamentGroupMatchScheduleAuthorityConflict,
    TournamentGroupMatchScheduleAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityConflict,
    TournamentGroupStandingsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthorityConflict,
    TournamentGroupTieResolutionAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthorityConflict,
    TournamentHybridKnockoutEntrantsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_hybrid_knockout_bracket_authority import (
    TournamentHybridKnockoutBracketAuthorityConflict,
    TournamentHybridKnockoutBracketAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_hybrid_ranking_policy_authority import (
    TournamentHybridRankingPolicyAuthorityConflict,
    TournamentHybridRankingPolicyAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_pure_groups_ranking_policy_authority import (
    TournamentPureGroupsRankingPolicyAuthorityConflict,
    TournamentPureGroupsRankingPolicyAuthorityStore,
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


class TournamentGroupMatchScheduleGenerateRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentGroupStandingsGenerateRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentGroupTieResolveRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    case_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    ordered_player_ids: tuple[str, ...] = Field(min_length=2)
    admin_reason: str = Field(min_length=1, max_length=1000)


class TournamentHybridKnockoutEntrantsGenerateRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentHybridKnockoutBracketGenerateRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentHybridRankingPolicyConfigureRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    played_group_win_points: int = Field(ge=0)
    knockout_stage_points: tuple[tuple[str, int], ...] = Field(min_length=2)


class TournamentHybridCloseRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentPureGroupsRankingPolicyConfigureRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    played_group_win_points: int = Field(ge=0)


class TournamentPureGroupsCloseRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)


class TournamentGroupMatchScheduleResponse(
    TournamentGroupMatchScheduleAuthority
):
    """Admin projection exposing immutable Match Schedule identity."""

    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentGroupMatchScheduleAuthority
    ) -> "TournamentGroupMatchScheduleResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentGroupStandingsResponse(TournamentGroupStandingsAuthority):
    """Admin projection exposing immutable final group-table identity."""

    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentGroupStandingsAuthority
    ) -> "TournamentGroupStandingsResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentGroupTieResolutionResponse(
    TournamentGroupTieResolutionAuthority
):
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentGroupTieResolutionAuthority
    ) -> "TournamentGroupTieResolutionResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentGroupTieResolutionState(BaseModel):
    schema_version: Literal["tournament_group_tie_resolution_state.v1"] = (
        "tournament_group_tie_resolution_state.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    unresolved_case: TournamentGroupStandingsTieCase | None
    resolutions: tuple[TournamentGroupTieResolutionResponse, ...]


class TournamentHybridKnockoutEntrantsResponse(
    TournamentHybridKnockoutEntrantsAuthority
):
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentHybridKnockoutEntrantsAuthority
    ) -> "TournamentHybridKnockoutEntrantsResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentHybridKnockoutBracketResponse(
    TournamentHybridKnockoutBracketAuthority
):
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentHybridKnockoutBracketAuthority
    ) -> "TournamentHybridKnockoutBracketResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentHybridRankingPolicyResponse(
    TournamentHybridRankingPolicyAuthority
):
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentHybridRankingPolicyAuthority
    ) -> "TournamentHybridRankingPolicyResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


class TournamentHybridClosureResponse(BaseModel):
    schema_version: Literal["tournament_hybrid_closure_response.v1"] = (
        "tournament_hybrid_closure_response.v1"
    )
    run_id: str
    branch_id: str
    event_id: str
    source_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prize_award_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    prize_configuration_status: str
    total_ranking_points: int = Field(ge=0)


class TournamentPureGroupsRankingPolicyResponse(
    TournamentPureGroupsRankingPolicyAuthority
):
    authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_authority(
        cls, authority: TournamentPureGroupsRankingPolicyAuthority
    ) -> "TournamentPureGroupsRankingPolicyResponse":
        return cls.model_validate(
            {
                **authority.model_dump(mode="python"),
                "authority_fingerprint": authority.fingerprint,
            }
        )


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


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format/group-match-schedule",
    response_model=TournamentGroupMatchScheduleResponse,
)
def inspect_group_match_schedule(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupMatchScheduleResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentGroupMatchScheduleAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Group Match Schedule authority not found",
                )
            return TournamentGroupMatchScheduleResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_match_schedule_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/format/group-match-schedule/generate",
    response_model=TournamentGroupMatchScheduleResponse,
    status_code=201,
)
def generate_group_match_schedule(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentGroupMatchScheduleGenerateRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupMatchScheduleResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            authority = TournamentGroupMatchScheduleAuthorityStore(session).generate(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            return TournamentGroupMatchScheduleResponse.from_authority(authority)
    except (TournamentGroupMatchScheduleAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_match_schedule_conflict",
                "message": str(exc),
            },
        ) from exc



@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/group-standings",
    response_model=TournamentGroupStandingsResponse,
)
def inspect_group_standings(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupStandingsResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentGroupStandingsAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Group Standings authority not found",
                )
            return TournamentGroupStandingsResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_standings_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/group-standings/generate",
    response_model=TournamentGroupStandingsResponse,
    status_code=201,
)
def generate_group_standings(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentGroupStandingsGenerateRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupStandingsResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            authority = TournamentGroupStandingsAuthorityStore(session).generate(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            return TournamentGroupStandingsResponse.from_authority(authority)
    except (TournamentGroupStandingsAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_standings_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/group-standings/tie-resolution",
    response_model=TournamentGroupTieResolutionState,
)
def inspect_group_tie_resolution(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupTieResolutionState:
    try:
        with runtime.repository._session_factory() as session:
            store = TournamentGroupTieResolutionAuthorityStore(session)
            resolutions = store.list_authorities(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            unresolved = store.current_unresolved_case(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            return TournamentGroupTieResolutionState(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                unresolved_case=unresolved,
                resolutions=tuple(
                    TournamentGroupTieResolutionResponse.from_authority(value)
                    for value in resolutions
                ),
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_tie_resolution_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/group-standings/tie-resolution",
    response_model=TournamentGroupTieResolutionResponse,
    status_code=201,
)
def resolve_group_standings_tie(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentGroupTieResolveRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentGroupTieResolutionResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            value = TournamentGroupTieResolutionAuthorityStore(session).resolve(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
                case_fingerprint=payload.case_fingerprint,
                ordered_player_ids=payload.ordered_player_ids,
                admin_reason=payload.admin_reason,
            )
            return TournamentGroupTieResolutionResponse.from_authority(value)
    except (TournamentGroupTieResolutionAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_group_tie_resolution_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-knockout-entrants",
    response_model=TournamentHybridKnockoutEntrantsResponse,
)
def inspect_hybrid_knockout_entrants(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridKnockoutEntrantsResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentHybridKnockoutEntrantsAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Hybrid Knockout Entrants authority not found",
                )
            return TournamentHybridKnockoutEntrantsResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_knockout_entrants_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-knockout-entrants/generate",
    response_model=TournamentHybridKnockoutEntrantsResponse,
    status_code=201,
)
def generate_hybrid_knockout_entrants(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentHybridKnockoutEntrantsGenerateRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridKnockoutEntrantsResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            value = TournamentHybridKnockoutEntrantsAuthorityStore(session).generate(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            return TournamentHybridKnockoutEntrantsResponse.from_authority(value)
    except (TournamentHybridKnockoutEntrantsAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_knockout_entrants_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-knockout-bracket",
    response_model=TournamentHybridKnockoutBracketResponse,
)
def inspect_hybrid_knockout_bracket(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridKnockoutBracketResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentHybridKnockoutBracketAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Hybrid Knockout Bracket authority not found",
                )
            return TournamentHybridKnockoutBracketResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_knockout_bracket_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-knockout-bracket/generate",
    response_model=TournamentHybridKnockoutBracketResponse,
    status_code=201,
)
def generate_hybrid_knockout_bracket(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentHybridKnockoutBracketGenerateRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridKnockoutBracketResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            value = TournamentHybridKnockoutBracketAuthorityStore(session).generate(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            return TournamentHybridKnockoutBracketResponse.from_authority(value)
    except (TournamentHybridKnockoutBracketAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_knockout_bracket_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-ranking-policy",
    response_model=TournamentHybridRankingPolicyResponse,
)
def inspect_hybrid_ranking_policy(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridRankingPolicyResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentHybridRankingPolicyAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Hybrid Ranking Policy authority not found",
                )
            return TournamentHybridRankingPolicyResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_ranking_policy_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-ranking-policy/configure",
    response_model=TournamentHybridRankingPolicyResponse,
    status_code=201,
)
def configure_hybrid_ranking_policy(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentHybridRankingPolicyConfigureRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridRankingPolicyResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            value = TournamentHybridRankingPolicyAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
                played_group_win_points=payload.played_group_win_points,
                knockout_stage_points=payload.knockout_stage_points,
            )
            return TournamentHybridRankingPolicyResponse.from_authority(value)
    except (TournamentHybridRankingPolicyAuthorityConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_ranking_policy_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/hybrid-ranking-close",
    response_model=TournamentHybridClosureResponse,
    status_code=201,
)
def close_hybrid_tournament_ranking_source(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentHybridCloseRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridClosureResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            source = TournamentHybridClosureService(session).close_from_current_receipts(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            if (
                source.canonical_result is None
                or source.canonical_awards is None
                or source.canonical_prize_awards is None
            ):
                raise ValueError("Hybrid Tournament closure produced incomplete source")
            return TournamentHybridClosureResponse(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                source_fingerprint=source.fingerprint,
                result_fingerprint=source.canonical_result.fingerprint,
                award_fingerprint=source.canonical_awards.fingerprint,
                prize_award_fingerprint=source.canonical_prize_awards.fingerprint,
                prize_configuration_status=(
                    source.canonical_prize_awards.configuration_status
                ),
                total_ranking_points=source.canonical_awards.total_ranking_points,
            )
    except (TournamentHybridClosureConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_hybrid_closure_conflict",
                "message": str(exc),
            },
        ) from exc


@router.get(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/pure-groups-ranking-policy",
    response_model=TournamentPureGroupsRankingPolicyResponse,
)
def inspect_pure_groups_ranking_policy(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentPureGroupsRankingPolicyResponse:
    try:
        with runtime.repository._session_factory() as session:
            value = TournamentPureGroupsRankingPolicyAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if value is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tournament Pure Groups Ranking Policy authority not found",
                )
            return TournamentPureGroupsRankingPolicyResponse.from_authority(value)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_pure_groups_ranking_policy_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/pure-groups-ranking-policy/configure",
    response_model=TournamentPureGroupsRankingPolicyResponse,
    status_code=201,
)
def configure_pure_groups_ranking_policy(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentPureGroupsRankingPolicyConfigureRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentPureGroupsRankingPolicyResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            value = TournamentPureGroupsRankingPolicyAuthorityStore(session).configure(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
                played_group_win_points=payload.played_group_win_points,
            )
            return TournamentPureGroupsRankingPolicyResponse.from_authority(value)
    except (
        TournamentPureGroupsRankingPolicyAuthorityConflict,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_pure_groups_ranking_policy_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post(
    "/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/pure-groups-ranking-close",
    response_model=TournamentHybridClosureResponse,
    status_code=201,
)
def close_pure_groups_tournament_ranking_source(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: TournamentPureGroupsCloseRequest,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentHybridClosureResponse:
    try:
        with runtime.repository._session_factory.begin() as session:
            source = TournamentPureGroupsClosureService(session).close_from_current_receipts(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                command_id=payload.command_id,
            )
            if (
                source.canonical_result is None
                or source.canonical_awards is None
                or source.canonical_prize_awards is None
            ):
                raise ValueError("Pure-groups Tournament closure produced incomplete source")
            return TournamentHybridClosureResponse(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                source_fingerprint=source.fingerprint,
                result_fingerprint=source.canonical_result.fingerprint,
                award_fingerprint=source.canonical_awards.fingerprint,
                prize_award_fingerprint=source.canonical_prize_awards.fingerprint,
                prize_configuration_status=(
                    source.canonical_prize_awards.configuration_status
                ),
                total_ranking_points=source.canonical_awards.total_ranking_points,
            )
    except (TournamentPureGroupsClosureConflict, ValueError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_pure_groups_closure_conflict",
                "message": str(exc),
            },
        ) from exc
