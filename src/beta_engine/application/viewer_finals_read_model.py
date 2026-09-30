"""Canonical Viewer World Tour Finals history from Saved Revision authorities."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.application.viewer_finals_race_read_model import (
    _effective_states,
    _participant_selections,
    resolve_viewer_finals_race_history,
)
from beta_engine.application.viewer_tournament_result_read_model import (
    ViewerTournamentResult,
    resolve_viewer_tournament_result,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState


class ViewerFinalsParticipant(BaseModel):
    player_id: str = Field(min_length=1)
    seed: int = Field(ge=1)
    race_rank: int = Field(ge=1)
    race_points: int = Field(ge=0)
    qualification_source: Literal["direct_entry", "race"]
    direct_entry_event_ids: tuple[str, ...] = ()


class ViewerFinalsSeason(BaseModel):
    schema_version: Literal["viewer_finals_season.v1"] = "viewer_finals_season.v1"
    target_season_index: int = Field(ge=0, le=49)
    race_cutoff_season_index: int = Field(ge=0, le=49)
    race_cutoff_week: int = Field(ge=1, le=61)
    selection_published: bool
    finals_event_id: str | None
    participant_capacity: int | None = Field(default=None, ge=1, le=128)
    participants: tuple[ViewerFinalsParticipant, ...]
    result_published: bool
    result: ViewerTournamentResult | None


class ViewerFinalsHistory(BaseModel):
    schema_version: Literal["viewer_finals_history.v1"] = "viewer_finals_history.v1"
    product_run_id: str
    viewer_branch_id: str
    latest_target_season_index: int | None
    seasons: tuple[ViewerFinalsSeason, ...]


def resolve_viewer_finals_history(
    simulation_component: dict[str, object] | None,
    ranking: RankingRevisionState | None,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerFinalsHistory:
    """Join saved Race/selection/effective field with saved canonical Finals Result."""

    race_history = resolve_viewer_finals_race_history(
        simulation_component,
        run_id=run_id,
        branch_id=branch_id,
    )
    selections = _participant_selections(
        simulation_component,
        run_id=run_id,
        branch_id=branch_id,
    )
    effective = _effective_states(
        simulation_component,
        run_id=run_id,
        branch_id=branch_id,
    )

    seasons: list[ViewerFinalsSeason] = []
    for publication in race_history.publications:
        selection = selections.get(publication.target_season_index)
        if selection is None:
            participants = ()
            participant_capacity = None
            finals_event_id = None
            canonical_result = None
        else:
            finals_event_id = selection.finals_event_id
            participant_capacity = selection.participant_capacity
            effective_state = effective.get(
                (selection.target_season_index, selection.finals_event_id)
            )
            source_participants = (
                effective_state.participants
                if effective_state is not None
                else selection.participants
            )
            participants = tuple(
                ViewerFinalsParticipant(
                    player_id=player.player_id,
                    seed=player.seed,
                    race_rank=player.race_rank,
                    race_points=player.race_points,
                    qualification_source=player.qualification_source,
                    direct_entry_event_ids=player.direct_entry_event_ids,
                )
                for player in source_participants
            )
            canonical_result = None
            if ranking is not None:
                try:
                    canonical_result = resolve_viewer_tournament_result(
                        ranking,
                        run_id=run_id,
                        branch_id=branch_id,
                        event_id=selection.finals_event_id,
                    )
                except KeyError:
                    canonical_result = None

        if selection is None and publication.selection_published:
            raise ValueError(
                "Viewer Finals Race reports published selection without selection authority"
            )
        if selection is not None and not publication.selection_published:
            raise ValueError(
                "Viewer Finals Race omits available participant-selection authority"
            )
        if selection is not None:
            if len(participants) != selection.participant_capacity:
                raise ValueError("Viewer Finals effective field does not preserve capacity")
            if tuple(player.seed for player in participants) != tuple(
                range(1, selection.participant_capacity + 1)
            ):
                raise ValueError("Viewer Finals participant seeds are not canonical")
            race_rows = {row.player_id: row for row in publication.rows}
            for player in participants:
                race_row = race_rows.get(player.player_id)
                if (
                    race_row is None
                    or race_row.rank != player.race_rank
                    or race_row.race_points != player.race_points
                    or race_row.finals_selected is not True
                    or race_row.finals_seed != player.seed
                    or race_row.qualification_source != player.qualification_source
                ):
                    raise ValueError(
                        "Viewer Finals participant field differs from published Race projection"
                    )

        seasons.append(
            ViewerFinalsSeason(
                target_season_index=publication.target_season_index,
                race_cutoff_season_index=publication.cutoff_season_index,
                race_cutoff_week=publication.cutoff_week,
                selection_published=publication.selection_published,
                finals_event_id=finals_event_id,
                participant_capacity=participant_capacity,
                participants=participants,
                result_published=canonical_result is not None,
                result=canonical_result,
            )
        )

    return ViewerFinalsHistory(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        latest_target_season_index=(
            seasons[-1].target_season_index if seasons else None
        ),
        seasons=tuple(seasons),
    )
