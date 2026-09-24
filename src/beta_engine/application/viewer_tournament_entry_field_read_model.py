"""Read-only Viewer projection of the selected Branch's canonical Tournament Entry Field."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.domain.tournaments.entry_field import TournamentEntryField


class ViewerTournamentEntryField(BaseModel):
    schema_version: Literal["viewer_tournament_entry_field.v1"] = (
        "viewer_tournament_entry_field.v1"
    )
    product_run_id: str
    viewer_branch_id: str
    event_id: str
    field_sequence: int = Field(ge=1)
    mode: Literal["initial", "pre_draw_repair"]
    main_draw_capacity: int = Field(ge=2, le=128)
    active_main_entrant_count: int = Field(ge=0, le=128)
    effective_main_bye_count: int = Field(ge=0, le=128)
    direct_main_player_ids: tuple[str, ...]
    qualification_player_ids: tuple[str, ...]
    alternate_player_ids: tuple[str, ...]
    withdrawn_player_ids: tuple[str, ...]


def resolve_viewer_tournament_entry_field(
    component: dict | None,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentEntryField:
    if component is None:
        raise KeyError("Viewer Saved Revision has no Tournament Entry Field component")
    rows = [row for row in component.get("entry_fields", ()) if row["event_id"] == event_id]
    if not rows:
        raise KeyError(f"Tournament Entry Field {event_id!r} is not present in Viewer Saved Revision")
    row = max(rows, key=lambda item: item["sequence"])
    state = TournamentEntryField.model_validate_json(row["payload_json"])
    return ViewerTournamentEntryField(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        event_id=event_id,
        field_sequence=row["sequence"],
        mode=state.mode,
        main_draw_capacity=state.capacity.main_draw_size,
        active_main_entrant_count=state.active_main_entrant_count,
        effective_main_bye_count=state.effective_main_bye_count,
        direct_main_player_ids=state.direct_main_player_ids,
        qualification_player_ids=state.qualification_player_ids,
        alternate_player_ids=state.below_qualification_cut_player_ids,
        withdrawn_player_ids=state.withdrawn_player_ids,
    )
