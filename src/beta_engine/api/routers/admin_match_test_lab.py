from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_match_test_lab_service
from beta_engine.application.match_test_lab_service import (
    MatchLabRequest,
    MatchLabResult,
    MatchTestLabService,
)

router = APIRouter(prefix="/admin/labs/match", tags=["admin-labs"])


@router.post("/run", response_model=MatchLabResult)
def run_match_lab(
    request: MatchLabRequest,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabResult:
    try:
        return service.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
