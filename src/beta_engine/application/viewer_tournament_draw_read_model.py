"""Read-only Viewer projection of the selected Branch's effective canonical Tournament Draw."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.authoritative_tournament_draw import (
    CanonicalTournamentDrawService,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawBracket


class ViewerTournamentDrawSlot(BaseModel):
    slot_index: int = Field(ge=1)
    entrant_kind: Literal[
        "player",
        "qualifier_placeholder",
        "lucky_loser_placeholder",
        "bye",
    ]
    player_id: str | None = None
    placeholder_id: str | None = None
    seed_number: int | None = Field(default=None, ge=1)
    entry_status: Literal["wild_card", "lucky_loser"] | None = None


class ViewerTournamentDrawBracket(BaseModel):
    draw_type: Literal["qualification", "main"]
    section_id: str | None = None
    bracket_size: int = Field(ge=2, le=128)
    slots: tuple[ViewerTournamentDrawSlot, ...]


class ViewerTournamentDraw(BaseModel):
    schema_version: Literal["viewer_tournament_draw.v1"] = "viewer_tournament_draw.v1"
    product_run_id: str
    viewer_branch_id: str
    event_id: str
    revision_count: int = Field(ge=0)
    main: ViewerTournamentDrawBracket
    qualification_sections: tuple[ViewerTournamentDrawBracket, ...]


def _project_bracket(bracket: TournamentDrawBracket) -> ViewerTournamentDrawBracket:
    return ViewerTournamentDrawBracket(
        draw_type=bracket.draw_type,
        section_id=bracket.section_id,
        bracket_size=bracket.bracket_size,
        slots=tuple(
            ViewerTournamentDrawSlot(
                slot_index=slot.slot_index,
                entrant_kind=slot.entrant_kind,
                player_id=slot.player_id,
                placeholder_id=slot.placeholder_id,
                seed_number=slot.seed_number,
                entry_status=slot.entry_status,
            )
            for slot in bracket.slots
        ),
    )


def resolve_viewer_tournament_draw(
    service: CanonicalTournamentDrawService,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentDraw:
    authority = service.inspect_effective_authority(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
    revisions = service.inspect_revision_history(
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
    return ViewerTournamentDraw(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        event_id=event_id,
        revision_count=len(revisions.revisions),
        main=_project_bracket(authority.main),
        qualification_sections=tuple(
            _project_bracket(bracket)
            for bracket in authority.qualification_brackets
        ),
    )
