"""Global Player Test Lab API."""

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from beta_engine.api.deps import (
    get_initial_population_comparison_service,
    get_player_test_lab_service,
    get_runtime,
)
from beta_engine.application.initial_population_comparison_service import (
    InitialPopulationComparisonService,
    PopulationComparisonRequest,
)
from beta_engine.application.player_lab_sessions import (
    PlayerLabHistoricalRequest,
    PlayerLabSaveRequest,
    PlayerLabSession,
    PlayerLabSessionService,
)
from beta_engine.application.player_test_lab_service import (
    BuiltInPlayerLabScenario,
    PlayerLabRequest,
    PlayerLabResult,
    PlayerLabScenario,
    PlayerLabScenarioV2,
    PlayerTestLabService,
)

router = APIRouter(prefix="/admin/labs/player", tags=["admin-labs"])


@router.get("/scenarios", response_model=list[BuiltInPlayerLabScenario])
def list_player_lab_built_in_scenarios(
    service: Annotated[PlayerTestLabService, Depends(get_player_test_lab_service)],
) -> list[BuiltInPlayerLabScenario]:
    return list(service.list_built_in_scenarios())


@router.post("/run", response_model=PlayerLabResult)
def run_player_lab(
    request: PlayerLabRequest,
    service: Annotated[PlayerTestLabService, Depends(get_player_test_lab_service)],
) -> PlayerLabResult:
    try:
        return service.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Initial populations are a separate operation in the existing global Player Lab.
PopulationService = Annotated[
    InitialPopulationComparisonService,
    Depends(get_initial_population_comparison_service),
]


@router.post("/population-comparisons", status_code=201)
def generate_population_comparison(
    request: PopulationComparisonRequest,
    service: PopulationService,
):
    try:
        result, cached = service.run(request)
        return service.overview(result, cached=cached)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/population-comparisons")
def list_population_comparisons(service: PopulationService):
    try:
        return service.list_sessions()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/population-comparisons/{session_id}")
def read_population_comparison(session_id: str, service: PopulationService):
    try:
        return service.overview(service.load(session_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/population-comparisons/{session_id}/players/{world_id}/{seed}")
def read_population_players(
    session_id: str, world_id: str, seed: int, service: PopulationService
):
    try:
        data = service.load(session_id)
        runs = [
            r for r in data["runs"] if r["world_id"] == world_id and r["seed"] == seed
        ]
        if len(runs) != 1:
            raise KeyError("Population is not part of this saved comparison")
        return {
            "session_id": session_id,
            "world_id": world_id,
            "seed": seed,
            "gameplay_fingerprint": runs[0]["gameplay_fingerprint"],
            "players": runs[0]["players"],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/population-comparisons/{session_id}/export")
def export_population_comparison(
    session_id: str, service: PopulationService, format: Literal["json", "csv"] = "json"
):
    try:
        if format == "csv":
            content = service.csv_export(session_id)
            media_type = "text/csv"
        elif format == "json":
            content = json.dumps(service.load(session_id), ensure_ascii=False)
            media_type = "application/json"
        else:
            raise ValueError("Export format must be json or csv")
        return Response(
            content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{session_id}.{format}"'
            },
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def session_service(request: Request):
    return PlayerLabSessionService(get_runtime(request).repository)


@router.get("/sessions", response_model=list[PlayerLabSession])
def list_player_sessions(
    service: Annotated[PlayerLabSessionService, Depends(session_service)],
):
    try:
        return service.list_sessions()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/sessions", response_model=PlayerLabSession, status_code=201)
def create_player_session(
    request: PlayerLabSaveRequest,
    service: Annotated[PlayerLabSessionService, Depends(session_service)],
):
    return service.save(request)


@router.put("/sessions/{session_id}", response_model=PlayerLabSession)
def update_player_session(
    session_id: str,
    request: PlayerLabSaveRequest,
    service: Annotated[PlayerLabSessionService, Depends(session_service)],
):
    try:
        return service.save(request, session_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post(
    "/import-saved-revision-player",
    response_model=PlayerLabScenario | PlayerLabScenarioV2,
)
def import_player_history(
    request: PlayerLabHistoricalRequest,
    service: Annotated[PlayerLabSessionService, Depends(session_service)],
):
    try:
        return service.import_player(request)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


class PlayerLabSessionRunRequest(BaseModel):
    model_config = {"extra": "forbid"}
    expected_session_fingerprint: str


@router.post("/sessions/{session_id}/run", response_model=PlayerLabResult)
def run_player_session(
    session_id: str,
    request: PlayerLabSessionRunRequest,
    service: Annotated[PlayerLabSessionService, Depends(session_service)],
):
    try:
        item = service.get(session_id)
        if item.session_fingerprint != request.expected_session_fingerprint:
            raise ValueError("Player Lab session changed since it was reviewed")
        return PlayerTestLabService().run(PlayerLabRequest(scenario=item.scenario))
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
