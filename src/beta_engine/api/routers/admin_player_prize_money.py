"""Read-only Admin boundary for canonical player prize-money history."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import ApiRuntime, get_runtime
from beta_engine.application.player_prize_money_history import (
    PlayerPrizeMoneyHistory,
    PlayerPrizeMoneyHistoryService,
)


router = APIRouter(
    prefix="/admin/runs/{run_id}/branches/{branch_id}/players/{player_id}/prize-money",
    tags=["admin-player-prize-money"],
)


@router.get("", response_model=PlayerPrizeMoneyHistory)
def get_player_prize_money_history(
    run_id: str,
    branch_id: str,
    player_id: str,
    runtime: Annotated[ApiRuntime, Depends(get_runtime)],
) -> PlayerPrizeMoneyHistory:
    service = PlayerPrizeMoneyHistoryService(
        runtime.repository._session_factory
    )
    try:
        return service.inspect(
            run_id=run_id,
            branch_id=branch_id,
            player_id=player_id,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "player_prize_money_history_conflict",
                "message": str(exc),
            },
        ) from exc
