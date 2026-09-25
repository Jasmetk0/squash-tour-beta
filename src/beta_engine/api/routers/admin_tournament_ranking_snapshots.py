"""Admin HTTP boundary for Run/Branch tournament ranking snapshot authority."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityConflict,
    TournamentRankingSnapshotAuthorityStore,
)


router = APIRouter(
    prefix=(
        "/admin/runs/{run_id}/branches/{branch_id}"
        "/tournaments/{event_id}/ranking-snapshot-authority"
    ),
    tags=["admin-tournament-ranking-snapshot-authority"],
)


@router.get("", response_model=TournamentRankingSnapshotAuthority)
def inspect_tournament_ranking_snapshot_authority(
    run_id: str,
    branch_id: str,
    event_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentRankingSnapshotAuthority:
    try:
        with runtime.repository._session_factory() as session:
            authority = TournamentRankingSnapshotAuthorityStore(session).get(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
            )
            if authority is None:
                raise KeyError(
                    f"Tournament Ranking Snapshot authority does not exist for event '{event_id}'"
                )
            return authority
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_ranking_snapshot_authority_conflict",
                "message": str(exc),
            },
        ) from exc


@router.post("", status_code=201, response_model=TournamentRankingSnapshotAuthority)
def adopt_tournament_ranking_snapshot_authority(
    run_id: str,
    branch_id: str,
    event_id: str,
    payload: dict,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> TournamentRankingSnapshotAuthority:
    try:
        command_id = payload["command_id"]
        ranking_week = RankingWeek.model_validate(payload["ranking_week"])
        with runtime.repository._session_factory.begin() as session:
            return TournamentRankingSnapshotAuthorityStore(session).adopt(
                run_id=run_id,
                branch_id=branch_id,
                event_id=event_id,
                ranking_week=ranking_week,
                command_id=command_id,
            )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TournamentRankingSnapshotAuthorityConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_ranking_snapshot_authority_conflict",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tournament_ranking_snapshot_authority_conflict",
                "message": str(exc),
            },
        ) from exc
