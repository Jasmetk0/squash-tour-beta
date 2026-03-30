from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    EventListResponse,
    EventRecordResponse,
    FinalsQualificationResponse,
    FinalsResultResponse,
    FinalsSummaryApiResponse,
    NextSeasonPlayersResponse,
    PlayerTransitionsResponse,
    RaceSnapshotListResponse,
    RaceSnapshotRecordResponse,
    RankingSnapshotListResponse,
    RankingSnapshotRecordResponse,
    RunSummaryResponse,
    SeasonRolloverExecutionResponse,
    SeasonRolloverSummaryApiResponse,
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


@router.get("/finals/qualification", response_model=FinalsQualificationResponse)
def get_finals_qualification(
    run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)
) -> FinalsQualificationResponse:
    try:
        qualification = service.get_finals_qualification(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FinalsQualificationResponse.model_validate(qualification.model_dump())


@router.get("/finals/result", response_model=FinalsResultResponse)
def get_finals_result(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> FinalsResultResponse:
    try:
        result = service.get_finals_result(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World Tour Finals result not found for run")
    return FinalsResultResponse.model_validate(result.model_dump())


@router.get("/finals/summary", response_model=FinalsSummaryApiResponse)
def get_finals_summary(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> FinalsSummaryApiResponse:
    try:
        summary = service.get_finals_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FinalsSummaryApiResponse(
        run_id=summary.run_id,
        season=summary.season,
        qualification=(
            FinalsQualificationResponse.model_validate(summary.qualification.model_dump())
            if summary.qualification is not None
            else None
        ),
        result=(FinalsResultResponse.model_validate(summary.result.model_dump()) if summary.result is not None else None),
    )


@router.post("/rollover/next-season", response_model=SeasonRolloverExecutionResponse)
def rollover_next_season(
    run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)
) -> SeasonRolloverExecutionResponse:
    try:
        rollover = service.rollover_to_next_season(run_id=run_id)
        run = service.get_run_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SeasonRolloverExecutionResponse(
        run=RunSummaryResponse.model_validate(run.__dict__),
        rollover=rollover,
    )


@router.get("/rollover/latest", response_model=SeasonRolloverSummaryApiResponse)
def get_latest_rollover(
    run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)
) -> SeasonRolloverSummaryApiResponse:
    try:
        rollover = service.get_latest_rollover(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if rollover is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No rollover found for run")
    return SeasonRolloverSummaryApiResponse(rollover=rollover)


@router.get("/rollover/{to_season}", response_model=SeasonRolloverSummaryApiResponse)
def get_rollover_by_season(
    run_id: str, to_season: int, service: SimulationApiService = Depends(get_simulation_api_service)
) -> SeasonRolloverSummaryApiResponse:
    try:
        rollover = service.get_rollover(run_id=run_id, to_season=to_season)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if rollover is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No rollover found for season {to_season}")
    return SeasonRolloverSummaryApiResponse(rollover=rollover)


@router.get("/players/next-season/{to_season}", response_model=NextSeasonPlayersResponse)
def get_next_season_players(
    run_id: str, to_season: int, service: SimulationApiService = Depends(get_simulation_api_service)
) -> NextSeasonPlayersResponse:
    try:
        players = service.list_next_season_players(run_id=run_id, to_season=to_season)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NextSeasonPlayersResponse(run_id=run_id, to_season=to_season, players=players)


@router.get("/players/transitions/{to_season}", response_model=PlayerTransitionsResponse)
def get_player_transitions(
    run_id: str, to_season: int, service: SimulationApiService = Depends(get_simulation_api_service)
) -> PlayerTransitionsResponse:
    try:
        transitions = service.list_player_transitions(run_id=run_id, to_season=to_season)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PlayerTransitionsResponse(run_id=run_id, to_season=to_season, transitions=transitions)
