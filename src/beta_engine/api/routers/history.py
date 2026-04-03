from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    RunActivityResponse,
    RunActivityItemResponse,
    WildcardAssignRequest,
    PreDrawWithdrawalRequest,
    WildcardStateApiResponse,
    WildcardActionHistoryApiResponse,
    PreDrawWithdrawalStateApiResponse,
    PreDrawWithdrawalResultApiResponse,
    PreDrawWithdrawalActionHistoryApiResponse,
    EventListResponse,
    EventRecordResponse,
    FinalsQualificationResponse,
    FinalsResultResponse,
    FinalsSummaryApiResponse,
    WildcardCandidatesApiResponse,
    NextSeasonPlayersResponse,
    PlayerTransitionsResponse,
    RaceSnapshotListResponse,
    RaceSnapshotRecordResponse,
    RankingSnapshotListResponse,
    RankingSnapshotRecordResponse,
    RunSummaryResponse,
    SeasonRolloverExecutionResponse,
    SeasonRolloverSummaryApiResponse,
    RunLineageApiResponse,
    RunSourceApiResponse,
)
from beta_engine.application.api_services import SimulationApiService, WildcardAssignment

router = APIRouter(prefix="/runs/{run_id}", tags=["history"])


@router.get("/activity", response_model=RunActivityResponse)
def get_run_activity(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunActivityResponse:
    try:
        activity = service.get_run_activity_feed(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RunActivityResponse(
        run_id=activity.run_id,
        items=[RunActivityItemResponse.model_validate(item.__dict__) for item in activity.items],
    )


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


@router.get("/events/{event_id}/wildcards", response_model=WildcardStateApiResponse)
def get_event_wildcard_state(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> WildcardStateApiResponse:
    try:
        state = service.get_wildcard_state(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WildcardStateApiResponse.model_validate(state, from_attributes=True)


@router.post("/events/{event_id}/wildcards", response_model=WildcardStateApiResponse)
def assign_event_wildcards(
    run_id: str,
    event_id: str,
    payload: WildcardAssignRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> WildcardStateApiResponse:
    try:
        state = service.assign_wildcards(
            run_id=run_id,
            event_id=event_id,
            assignments=[
                WildcardAssignment(slot_index=assignment.slot_index, player_id=assignment.player_id)
                for assignment in payload.assignments
            ],
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WildcardStateApiResponse.model_validate(state, from_attributes=True)


@router.get("/events/{event_id}/wildcard-candidates", response_model=WildcardCandidatesApiResponse)
def list_event_wildcard_candidates(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> WildcardCandidatesApiResponse:
    try:
        candidates = service.get_wildcard_candidates(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WildcardCandidatesApiResponse.model_validate(candidates, from_attributes=True)


@router.get("/events/{event_id}/wildcard-actions", response_model=WildcardActionHistoryApiResponse)
def list_event_wildcard_actions(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> WildcardActionHistoryApiResponse:
    try:
        history = service.get_wildcard_action_history(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return WildcardActionHistoryApiResponse.model_validate(history, from_attributes=True)


@router.get("/events/{event_id}/pre-draw-withdrawal", response_model=PreDrawWithdrawalStateApiResponse)
def get_event_pre_draw_withdrawal_state(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PreDrawWithdrawalStateApiResponse:
    try:
        state = service.get_pre_draw_withdrawal_state(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PreDrawWithdrawalStateApiResponse.model_validate(state, from_attributes=True)


@router.post("/events/{event_id}/pre-draw-withdrawal", response_model=PreDrawWithdrawalResultApiResponse)
def apply_event_pre_draw_withdrawal(
    run_id: str,
    event_id: str,
    payload: PreDrawWithdrawalRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PreDrawWithdrawalResultApiResponse:
    try:
        result = service.apply_pre_draw_withdrawal_replacement(
            run_id=run_id,
            event_id=event_id,
            withdrawn_player_id=payload.withdrawn_player_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PreDrawWithdrawalResultApiResponse.model_validate(result, from_attributes=True)


@router.get("/events/{event_id}/pre-draw-withdrawal-actions", response_model=PreDrawWithdrawalActionHistoryApiResponse)
def list_event_pre_draw_withdrawal_actions(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PreDrawWithdrawalActionHistoryApiResponse:
    try:
        history = service.get_pre_draw_withdrawal_action_history(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PreDrawWithdrawalActionHistoryApiResponse.model_validate(history, from_attributes=True)


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


@router.get("/snapshots/ranking/{snapshot_sequence}", response_model=RankingSnapshotRecordResponse)
def get_ranking_snapshot(
    run_id: str,
    snapshot_sequence: int,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RankingSnapshotRecordResponse:
    try:
        service.get_run_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    snapshot = service.get_ranking_snapshot(run_id=run_id, snapshot_sequence=snapshot_sequence)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ranking snapshot sequence {snapshot_sequence} was not found",
        )
    sequence, kind, source_event_id, payload = snapshot
    return RankingSnapshotRecordResponse(
        snapshot_sequence=sequence,
        snapshot_kind=kind,
        source_event_id=source_event_id,
        payload=payload,
    )


@router.get("/snapshots/race/{snapshot_sequence}", response_model=RaceSnapshotRecordResponse)
def get_race_snapshot(
    run_id: str,
    snapshot_sequence: int,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RaceSnapshotRecordResponse:
    try:
        service.get_run_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    snapshot = service.get_race_snapshot(run_id=run_id, snapshot_sequence=snapshot_sequence)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"race snapshot sequence {snapshot_sequence} was not found",
        )
    sequence, kind, source_event_id, payload = snapshot
    return RaceSnapshotRecordResponse(
        snapshot_sequence=sequence,
        snapshot_kind=kind,
        source_event_id=source_event_id,
        payload=payload,
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


@router.get("/lineage", response_model=RunLineageApiResponse)
def get_run_lineage(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunLineageApiResponse:
    try:
        lineage = service.get_run_lineage(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RunLineageApiResponse(lineage=lineage)


@router.get("/source", response_model=RunSourceApiResponse)
def get_run_source(run_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> RunSourceApiResponse:
    try:
        source = service.get_run_source(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RunSourceApiResponse(source=source)
