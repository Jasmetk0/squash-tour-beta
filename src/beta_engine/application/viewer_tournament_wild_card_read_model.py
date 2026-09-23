"""Read-only Viewer projection of definitive canonical WC/RWC assignments."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.infrastructure.db.definitive_wild_card_assignments import (
    DefinitiveWildCardAssignmentStore,
)


class ViewerTournamentWildCardAssignment(BaseModel):
    wildcard_index: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    source: Literal["original_wc", "reserve_wc"]
    reserve_ordinal: int | None = Field(default=None, ge=1)


class ViewerTournamentWildCards(BaseModel):
    schema_version: Literal["viewer_tournament_wild_cards.v1"] = (
        "viewer_tournament_wild_cards.v1"
    )
    product_run_id: str
    viewer_branch_id: str
    event_id: str
    assignment_count: int = Field(ge=0)
    assignments: tuple[ViewerTournamentWildCardAssignment, ...]


def resolve_viewer_tournament_wild_cards(
    store: DefinitiveWildCardAssignmentStore,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentWildCards:
    assignments = tuple(
        assignment
        for assignment in store.list(run_id=run_id, branch_id=branch_id)
        if assignment.event_id == event_id
    )
    return ViewerTournamentWildCards(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        event_id=event_id,
        assignment_count=len(assignments),
        assignments=tuple(
            ViewerTournamentWildCardAssignment(
                wildcard_index=assignment.wildcard_index,
                player_id=assignment.player_id,
                source=assignment.assignment_source,
                reserve_ordinal=assignment.reserve_ordinal,
            )
            for assignment in sorted(assignments, key=lambda item: item.wildcard_index)
        ),
    )
