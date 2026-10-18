"""Read-only inspection endpoints for mutable branch-head metadata."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from beta_engine.api.deps import get_simulation_api_service
from beta_engine.api.schemas import BranchStateListResponse, BranchStateResponse
from beta_engine.application.api_services import SimulationApiService
from beta_engine.infrastructure.db import RunBranchStateRecord

router = APIRouter(prefix="/branch-states", tags=["branch-states"])


def _response(record: RunBranchStateRecord) -> BranchStateResponse:
    return BranchStateResponse.model_validate({**record.__dict__, "metadata_json": record.metadata})


@router.get("", response_model=BranchStateListResponse)
def list_branch_states(run_id: str | None = Query(None), service: SimulationApiService = Depends(get_simulation_api_service)) -> BranchStateListResponse:
    return BranchStateListResponse(branch_states=[_response(item) for item in service.repository.list_branch_states(run_id=run_id)])


@router.get("/{branch_id}", response_model=BranchStateResponse)
def get_branch_state(branch_id: str, service: SimulationApiService = Depends(get_simulation_api_service)) -> BranchStateResponse:
    from beta_engine.application.calendar_tour_service import CalendarTourService
    from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel
    with service.repository._session_factory() as session:
        native=session.query(CalendarTourAuthorityModel).filter_by(branch_id=branch_id).one_or_none()
        run_id=native.run_id if native else None
    if run_id is not None:
        try:
            view=CalendarTourService(service.repository).inspect(run_id=run_id,branch_id=branch_id)
            week=view['state']['week']
            return BranchStateResponse(branch_id=branch_id,run_id=run_id,
                current_season=week['calendar']['start_year']+week['season_index'],current_week=week['week'],
                state_schema_version='calendar_tour_branch_state.v1',status='active',
                metadata_json={'source':'native_tour_working_authority','saved':view['saved'],
                    'saved_revision_id':view['saved_head_revision_id'],'run_calendar':week['calendar']})
        except (ValueError,KeyError) as exc:
            raise HTTPException(status_code=409,detail=str(exc)) from exc
    record = service.repository.get_branch_state(branch_id=branch_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"branch state {branch_id} was not found")
    return _response(record)
