from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from beta_engine.api.deps import get_run_cross_saved_comparison_service
from beta_engine.application.run_cross_saved_comparison import (
    RunCrossSavedComparisonService,
    CrossSavedRevisionComparison,
    CrossSavedRevisionComparisonSource
)
from beta_engine.infrastructure.db.repositories import (
    SavedRevisionHistoryNotFoundError,
    SavedRevisionHistoryConflictError,
)

router = APIRouter(prefix="/admin", tags=["admin", "runs"])


class CrossSavedRevisionHistoryEntryResponse(BaseModel):
    revision_id: str
    revision_branch_id: str
    sequence: int
    parent_revision_id: str | None
    is_branch_head: bool
    content_hash_algorithm: str
    content_hash: str


class CrossSavedRevisionComparisonSourceResponse(BaseModel):
    run_id: str
    branch_id: str
    saved_head_revision_id: str
    revision: CrossSavedRevisionHistoryEntryResponse


class CrossSavedRevisionComponentComparisonResponse(BaseModel):
    component_key: str
    status: str
    before_fingerprint: str | None
    after_fingerprint: str | None


class CrossSavedRevisionComparisonResponse(BaseModel):
    from_source: CrossSavedRevisionComparisonSourceResponse
    to_source: CrossSavedRevisionComparisonSourceResponse
    run_changes: dict[str, dict[str, object | None]]
    branch_changes: dict[str, dict[str, object | None]]
    components: list[CrossSavedRevisionComponentComparisonResponse] = Field(
        default_factory=list
    )


def _map_source(source: CrossSavedRevisionComparisonSource) -> CrossSavedRevisionComparisonSourceResponse:
    return CrossSavedRevisionComparisonSourceResponse(
        run_id=source.run_id,
        branch_id=source.branch_id,
        saved_head_revision_id=source.saved_head_revision_id,
        revision=CrossSavedRevisionHistoryEntryResponse(
            revision_id=source.revision.revision_id,
            revision_branch_id=source.revision.branch_id,
            sequence=source.revision.sequence,
            parent_revision_id=source.revision.parent_revision_id,
            is_branch_head=source.revision.revision_id == source.saved_head_revision_id,
            content_hash_algorithm=source.revision.content_hash_algorithm,
            content_hash=source.revision.content_hash,
        ),
    )


def _map_response(
    comparison: CrossSavedRevisionComparison,
) -> CrossSavedRevisionComparisonResponse:
    return CrossSavedRevisionComparisonResponse(
        from_source=_map_source(comparison.from_source),
        to_source=_map_source(comparison.to_source),
        run_changes=comparison.run_changes,
        branch_changes=comparison.branch_changes,
        components=[
            CrossSavedRevisionComponentComparisonResponse(
                component_key=c.component_key,
                status=c.status,
                before_fingerprint=c.before_fingerprint,
                after_fingerprint=c.after_fingerprint,
            )
            for c in comparison.components
        ],
    )


@router.get(
    "/cross-run-compare",
    response_model=CrossSavedRevisionComparisonResponse,
)
def compare_cross_saved_revisions(
    run_a_id: str = Query(..., min_length=1, max_length=128),
    branch_a_id: str = Query(..., min_length=1, max_length=128),
    revision_a_id: str = Query(..., min_length=1, max_length=128),
    run_b_id: str = Query(..., min_length=1, max_length=128),
    branch_b_id: str = Query(..., min_length=1, max_length=128),
    revision_b_id: str = Query(..., min_length=1, max_length=128),
    service: RunCrossSavedComparisonService = Depends(
        get_run_cross_saved_comparison_service
    ),
) -> CrossSavedRevisionComparisonResponse:
    try:
        return _map_response(
            service.compare(
                run_a_id=run_a_id,
                branch_a_id=branch_a_id,
                revision_a_id=revision_a_id,
                run_b_id=run_b_id,
                branch_b_id=branch_b_id,
                revision_b_id=revision_b_id,
            )
        )
    except SavedRevisionHistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except SavedRevisionHistoryConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
