from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from beta_engine.api.deps import get_season_entry_list_service
from beta_engine.application.season_entry_list_service import EntryListGenerateRequest, SeasonEntryListService, SeasonEventEntryListResult

router = APIRouter(prefix="/admin/entries", tags=["admin-entries"])


@router.get("/{event_id}", response_model=SeasonEventEntryListResult)
def get_event_entry_list(
    event_id: str,
    service: SeasonEntryListService = Depends(get_season_entry_list_service),
) -> SeasonEventEntryListResult:
    return service.get_entry_list(event_id=event_id)


@router.post("/{event_id}/generate", response_model=SeasonEventEntryListResult)
def generate_event_entry_list(
    event_id: str,
    payload: EntryListGenerateRequest,
    service: SeasonEntryListService = Depends(get_season_entry_list_service),
) -> SeasonEventEntryListResult:
    try:
        return service.generate_entry_list(event_id=event_id, request=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
