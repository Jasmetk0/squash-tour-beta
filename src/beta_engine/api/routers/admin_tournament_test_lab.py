"""Global Tournament Test Lab API."""

from fastapi import APIRouter, Depends, HTTPException

from beta_engine.api.deps import get_tournament_test_lab_service
from beta_engine.application.tournament_test_lab_service import (
    BuiltInTournamentLabScenario,
    TournamentLabCompatibility,
    TournamentLabRequest,
    TournamentLabRunDraftApplyRequest,
    TournamentLabRunDraftApplyResult,
    TournamentLabRunDraftPreview,
    TournamentLabRunDraftPreviewRequest,
    TournamentLabSavedRevisionCopyRequest,
    TournamentLabResult,
    TournamentLabScenario,
    TournamentLabSession,
    TournamentLabSessionCreateRequest,
    TournamentLabSessionExport,
    TournamentLabSessionImportRequest,
    TournamentLabSessionRunRequest,
    TournamentLabSessionUpdateRequest,
    TournamentTestLabService,
)

router = APIRouter(prefix="/admin/labs/tournament", tags=["admin-labs"])


@router.get("/scenarios", response_model=list[BuiltInTournamentLabScenario])
def list_tournament_lab_scenarios(
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> list[BuiltInTournamentLabScenario]:
    return list(service.list_built_in_scenarios())


@router.post("/inspect", response_model=TournamentLabCompatibility)
def inspect_tournament_lab_scenario(
    scenario: TournamentLabScenario,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabCompatibility:
    return service.inspect(scenario)


@router.post("/run", response_model=TournamentLabResult)
def run_tournament_lab(
    request: TournamentLabRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabResult:
    return service.run(request)



@router.get("/sessions", response_model=list[TournamentLabSession])
def list_tournament_lab_sessions(
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> list[TournamentLabSession]:
    return list(service.list_sessions())


@router.post("/sessions/copy-saved-revision", response_model=TournamentLabSession, status_code=201)
def copy_saved_revision_tournament_to_lab(
    request: TournamentLabSavedRevisionCopyRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSession:
    try:
        return service.copy_saved_revision_tournament(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/run-draft-preview",
    response_model=TournamentLabRunDraftPreview,
)
def preview_tournament_lab_run_draft(
    session_id: str,
    request: TournamentLabRunDraftPreviewRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabRunDraftPreview:
    try:
        return service.preview_run_draft(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/run-draft-apply",
    response_model=TournamentLabRunDraftApplyResult,
    status_code=201,
)
def apply_tournament_lab_run_draft(
    session_id: str,
    request: TournamentLabRunDraftApplyRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabRunDraftApplyResult:
    try:
        return service.apply_run_draft(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", response_model=TournamentLabSession)
def get_tournament_lab_session(
    session_id: str,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSession:
    try:
        return service.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions", response_model=TournamentLabSession, status_code=201)
def create_tournament_lab_session(
    request: TournamentLabSessionCreateRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSession:
    try:
        return service.create_session(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/sessions/{session_id}", response_model=TournamentLabSession)
def update_tournament_lab_session(
    session_id: str,
    request: TournamentLabSessionUpdateRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSession:
    try:
        return service.update_session(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/export", response_model=TournamentLabSessionExport)
def export_tournament_lab_session(
    session_id: str,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSessionExport:
    try:
        return service.export_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions/import", response_model=TournamentLabSession, status_code=201)
def import_tournament_lab_session(
    request: TournamentLabSessionImportRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabSession:
    try:
        return service.import_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/run", response_model=TournamentLabResult)
def run_tournament_lab_session(
    session_id: str,
    request: TournamentLabSessionRunRequest,
    service: TournamentTestLabService = Depends(get_tournament_test_lab_service),
) -> TournamentLabResult:
    try:
        return service.run_session(session_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
