"""Read-only Viewer projection of the selected Branch's effective canonical Tournament Draw."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority, TournamentDrawBracket
from beta_engine.domain.tournaments.draw_revision_authority import TournamentDrawRevision


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
    component: dict | None,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentDraw:
    if component is None:
        raise KeyError("Viewer Saved Revision has no Tournament Draw component")
    initial_rows = [row for row in component.get("draw_authorities", ()) if row["event_id"] == event_id]
    if len(initial_rows) != 1:
        raise KeyError(f"Tournament Draw {event_id!r} is not present in Viewer Saved Revision")
    authority = TournamentDrawAuthority.model_validate_json(initial_rows[0]["payload_json"])
    revision_rows = sorted(
        (row for row in component.get("draw_revisions", ()) if row["event_id"] == event_id),
        key=lambda row: row["sequence"],
    )
    revisions = [TournamentDrawRevision.model_validate_json(row["payload_json"]) for row in revision_rows]
    effective = revisions[-1].successor_draw if revisions else authority
    return ViewerTournamentDraw(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        event_id=event_id,
        revision_count=len(revisions),
        main=_project_bracket(effective.main),
        qualification_sections=tuple(
            _project_bracket(bracket)
            for bracket in effective.qualification_brackets
        ),
    )
