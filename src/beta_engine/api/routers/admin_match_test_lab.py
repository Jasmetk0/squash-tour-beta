from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_match_test_lab_service
from beta_engine.application.match_test_lab_service import (
    BuiltInMatchLabScenario,
    MatchLabRequest,
    MatchLabResult,
    MatchLabSavedRevisionPlayerImportRequest,
    MatchLabSession,
    MatchLabSessionCreateRequest,
    MatchLabSessionRunRequest,
    MatchLabSessionUpdateRequest,
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



@router.get("/scenarios", response_model=list[BuiltInMatchLabScenario])
def list_match_lab_built_in_scenarios(
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> list[BuiltInMatchLabScenario]:
    return list(service.list_built_in_scenarios())


@router.get("/sessions", response_model=list[MatchLabSession])
def list_match_lab_sessions(
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> list[MatchLabSession]:
    return list(service.list_sessions())


@router.get("/sessions/{session_id}", response_model=MatchLabSession)
def get_match_lab_session(
    session_id: str,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabSession:
    try:
        return service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions", response_model=MatchLabSession, status_code=201)
def create_match_lab_session(
    request: MatchLabSessionCreateRequest,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabSession:
    try:
        return service.create_session(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/sessions/{session_id}", response_model=MatchLabSession)
def update_match_lab_session(
    session_id: str,
    request: MatchLabSessionUpdateRequest,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabSession:
    try:
        return service.update_session(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/run", response_model=MatchLabResult)
def run_match_lab_session(
    session_id: str,
    request: MatchLabSessionRunRequest,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabResult:
    try:
        return service.run_session(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc



@router.post("/sessions/{session_id}/import-saved-revision-player", response_model=MatchLabSession)
def import_match_lab_saved_revision_player(
    session_id: str,
    request: MatchLabSavedRevisionPlayerImportRequest,
    service: MatchTestLabService = Depends(get_match_test_lab_service),
) -> MatchLabSession:
    try:
        return service.import_saved_revision_player(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
