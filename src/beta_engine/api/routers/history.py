from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    EventListResponse,
    EventRecordResponse,
    RaceSnapshotListResponse,
    RaceSnapshotRecordResponse,
    RankingSnapshotListResponse,
    RankingSnapshotRecordResponse,
)
from beta_engine.application.api_services import SimulationApiService

router = APIRouter(prefix="/runs/{run_id}", tags=["history"])


@router.get("/events", response_model=EventListResponse)
def list_completed_events(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> EventListResponse:
    try:
        service.get_run_summary(run_id=run_id)
        events = service.list_events(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return EventListResponse(
        run_id=run_id,
        events=[EventRecordResponse.model_validate(event.__dict__) for event in events],
    )


@router.get("/events/{event_id}", response_model=EventRecordResponse)
def get_completed_event(run_id: str, event_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> EventRecordResponse:
    try:
        service.get_run_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    event = service.get_event(run_id=run_id, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"event_id {event_id} was not found")
    return EventRecordResponse.model_validate(event.__dict__)


@router.get("/snapshots/ranking", response_model=RankingSnapshotListResponse)
def list_ranking_snapshots(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RankingSnapshotListResponse:
    try:
        service.get_run_summary(run_id=run_id)
        snapshots = service.list_ranking_snapshots(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RankingSnapshotListResponse(
        run_id=run_id,
        snapshots=[
            RankingSnapshotRecordResponse(
                snapshot_sequence=sequence,
                snapshot_kind=kind,
                source_event_id=source_event_id,
                payload=payload,
            )
            for sequence, kind, source_event_id, payload in snapshots
        ],
    )


@router.get("/snapshots/race", response_model=RaceSnapshotListResponse)
def list_race_snapshots(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RaceSnapshotListResponse:
    try:
        service.get_run_summary(run_id=run_id)
        snapshots = service.list_race_snapshots(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RaceSnapshotListResponse(
        run_id=run_id,
        snapshots=[
            RaceSnapshotRecordResponse(
                snapshot_sequence=sequence,
                snapshot_kind=kind,
                source_event_id=source_event_id,
                payload=payload,
            )
            for sequence, kind, source_event_id, payload in snapshots
        ],
    )
