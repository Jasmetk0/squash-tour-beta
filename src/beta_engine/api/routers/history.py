from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import (
    RunActivityResponse,
    RunActivityItemResponse,
    WildcardAssignRequest,
    PreDrawWithdrawalRequest,
    LateReplacementRequest,
    WildcardStateApiResponse,
    WildcardActionHistoryApiResponse,
    PreDrawWithdrawalStateApiResponse,
    PreDrawWithdrawalResultApiResponse,
    PreDrawWithdrawalActionHistoryApiResponse,
    LateReplacementStateApiResponse,
    LateReplacementCandidatesApiResponse,
    LateReplacementResultApiResponse,
    LateReplacementActionHistoryApiResponse,
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
    RunTalentPlanSummaryResponse,
    GeneratedPlayerProvenanceListResponse,
    GeneratedPlayerProvenanceResponse,
    RunPlayerDetailResponse,
    PlayerCareerHistoryResponse,
    PlayerCareerPerformanceResponse,
    PlayerTournamentResultsTimelineResponse,
    RunPlayersListResponse,
    RunNationsSummaryResponse,
    RunNationDetailResponse,
    RunWorldStatusResponse,
)
from beta_engine.application.api_services import (
    GeneratedPlayerProvenance,
    RunNationDetail,
    RunNationsSummaryResponse as RunNationsSummaryServiceResponse,
    RunPlayerDetail,
    PlayerCareerHistoryResponse as PlayerCareerHistoryServiceResponse,
    PlayerCareerPerformanceResponse as PlayerCareerPerformanceServiceResponse,
    PlayerTournamentResultsTimelineResponse as PlayerTournamentResultsTimelineServiceResponse,
    RunPlayerListResponse,
    RunTalentPlanSummary,
    RunWorldStatus,
    SimulationApiService,
    WildcardAssignment,
)

router = APIRouter(prefix="/runs/{run_id}", tags=["history"])


def _to_run_talent_plan_summary(summary: RunTalentPlanSummary) -> RunTalentPlanSummaryResponse:
    return RunTalentPlanSummaryResponse.model_validate(summary, from_attributes=True)


def _to_player_provenance(record: GeneratedPlayerProvenance) -> GeneratedPlayerProvenanceResponse:
    return GeneratedPlayerProvenanceResponse.model_validate(record, from_attributes=True)


def _to_run_players_response(response: RunPlayerListResponse) -> RunPlayersListResponse:
    return RunPlayersListResponse.model_validate(response, from_attributes=True)


def _to_run_player_detail(response: RunPlayerDetail) -> RunPlayerDetailResponse:
    return RunPlayerDetailResponse.model_validate(response, from_attributes=True)


def _to_player_career_history_response(response: PlayerCareerHistoryServiceResponse) -> PlayerCareerHistoryResponse:
    return PlayerCareerHistoryResponse.model_validate(response, from_attributes=True)


def _to_player_career_performance_response(response: PlayerCareerPerformanceServiceResponse) -> PlayerCareerPerformanceResponse:
    return PlayerCareerPerformanceResponse.model_validate(response, from_attributes=True)


def _to_player_tournament_results_timeline_response(
    response: PlayerTournamentResultsTimelineServiceResponse,
) -> PlayerTournamentResultsTimelineResponse:
    return PlayerTournamentResultsTimelineResponse.model_validate(response, from_attributes=True)


def _to_run_nations_response(response: RunNationsSummaryServiceResponse) -> RunNationsSummaryResponse:
    return RunNationsSummaryResponse.model_validate(response, from_attributes=True)


def _to_run_nation_detail(response: RunNationDetail) -> RunNationDetailResponse:
    return RunNationDetailResponse.model_validate(response, from_attributes=True)


def _to_run_world_status(response: RunWorldStatus) -> RunWorldStatusResponse:
    return RunWorldStatusResponse.model_validate(response, from_attributes=True)


@router.get("/world/talent-plan", response_model=RunTalentPlanSummaryResponse)
def get_run_talent_plan(
    run_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunTalentPlanSummaryResponse:
    try:
        summary = service.get_run_talent_plan_summary(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_talent_plan_summary(summary)


@router.get("/world/generated-players", response_model=GeneratedPlayerProvenanceListResponse)
def list_generated_players_provenance(
    run_id: str,
    country_code: str | None = None,
    quality_band: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> GeneratedPlayerProvenanceListResponse:
    try:
        players = service.list_generated_player_provenance(
            run_id=run_id,
            country_code=country_code,
            quality_band=quality_band,
            limit=limit,
            offset=offset,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return GeneratedPlayerProvenanceListResponse(run_id=run_id, players=[_to_player_provenance(player) for player in players])


@router.get("/world/generated-players/{player_id}", response_model=GeneratedPlayerProvenanceResponse)
def get_generated_player_provenance(
    run_id: str,
    player_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> GeneratedPlayerProvenanceResponse:
    try:
        record = service.get_generated_player_provenance(run_id=run_id, player_id=player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_player_provenance(record)


@router.get("/world-status", response_model=RunWorldStatusResponse)
def get_run_world_status(
    run_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunWorldStatusResponse:
    try:
        status_payload = service.get_run_world_status(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_world_status(status_payload)


@router.post("/rebuild-world", response_model=RunWorldStatusResponse)
def rebuild_run_world(
    run_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunWorldStatusResponse:
    try:
        status_payload = service.rebuild_run_world(run_id=run_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_run_world_status(status_payload)


@router.get("/players", response_model=RunPlayersListResponse)
def list_run_players(
    run_id: str,
    country_code: str | None = None,
    source_type: str | None = None,
    min_age: int | None = Query(default=None, ge=15, le=60),
    max_age: int | None = Query(default=None, ge=15, le=60),
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort: str = "name_asc",
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunPlayersListResponse:
    try:
        players = service.list_run_players(
            run_id=run_id,
            country_code=country_code,
            source_type=source_type,
            min_age=min_age,
            max_age=max_age,
            search=search,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_players_response(players)


@router.get("/players/{player_id}", response_model=RunPlayerDetailResponse)
def get_run_player_detail(
    run_id: str,
    player_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunPlayerDetailResponse:
    try:
        player = service.get_run_player_detail(run_id=run_id, player_id=player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_player_detail(player)


@router.get("/players/{player_id}/career", response_model=PlayerCareerHistoryResponse)
def get_run_player_career_history(
    run_id: str,
    player_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PlayerCareerHistoryResponse:
    try:
        history = service.get_player_career_history(run_id=run_id, player_id=player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_player_career_history_response(history)


@router.get("/players/{player_id}/career/performance", response_model=PlayerCareerPerformanceResponse)
def get_run_player_career_performance(
    run_id: str,
    player_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PlayerCareerPerformanceResponse:
    try:
        performance = service.get_player_career_performance(run_id=run_id, player_id=player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_player_career_performance_response(performance)


@router.get("/players/{player_id}/career/results", response_model=PlayerTournamentResultsTimelineResponse)
def get_run_player_tournament_results_timeline(
    run_id: str,
    player_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> PlayerTournamentResultsTimelineResponse:
    try:
        timeline = service.get_player_tournament_results_timeline(run_id=run_id, player_id=player_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_player_tournament_results_timeline_response(timeline)


@router.get("/nations", response_model=RunNationsSummaryResponse)
def list_run_nations(
    run_id: str,
    search: str | None = None,
    sort: str = "total_players_desc",
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunNationsSummaryResponse:
    try:
        nations = service.list_run_nations(run_id=run_id, search=search, sort=sort, limit=limit, offset=offset)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_nations_response(nations)


@router.get("/nations/{country_code}", response_model=RunNationDetailResponse)
def get_run_nation_detail(
    run_id: str,
    country_code: str,
    top_limit: int = Query(default=10, ge=1, le=100),
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> RunNationDetailResponse:
    try:
        nation = service.get_run_nation_detail(run_id=run_id, country_code=country_code, top_limit=top_limit)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_run_nation_detail(nation)


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


@router.get("/events/{event_id}/late-replacement", response_model=LateReplacementStateApiResponse)
def get_event_late_replacement_state(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> LateReplacementStateApiResponse:
    try:
        state = service.get_late_replacement_state(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LateReplacementStateApiResponse.model_validate(state, from_attributes=True)


@router.get("/events/{event_id}/late-replacement-candidates", response_model=LateReplacementCandidatesApiResponse)
def list_event_late_replacement_candidates(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> LateReplacementCandidatesApiResponse:
    try:
        candidates = service.get_late_replacement_candidates(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LateReplacementCandidatesApiResponse.model_validate(candidates, from_attributes=True)


@router.post("/events/{event_id}/late-replacement", response_model=LateReplacementResultApiResponse)
def apply_event_late_replacement(
    run_id: str,
    event_id: str,
    payload: LateReplacementRequest,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> LateReplacementResultApiResponse:
    try:
        result = service.apply_late_replacement(
            run_id=run_id,
            event_id=event_id,
            withdrawn_player_id=payload.withdrawn_player_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LateReplacementResultApiResponse.model_validate(result, from_attributes=True)


@router.get("/events/{event_id}/late-replacement-actions", response_model=LateReplacementActionHistoryApiResponse)
def list_event_late_replacement_actions(
    run_id: str,
    event_id: str,
    service: SimulationApiService = Depends(get_simulation_api_service),
) -> LateReplacementActionHistoryApiResponse:
    try:
        history = service.get_late_replacement_action_history(run_id=run_id, event_id=event_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return LateReplacementActionHistoryApiResponse.model_validate(history, from_attributes=True)


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
