"""Canonical Viewer World Tour Finals Race projection from Saved Revision evidence."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.domain.finals.participant_selection import (
    WorldTourFinalsParticipantSelectionSnapshot,
)
from beta_engine.domain.finals.race import WorldTourFinalsRaceSnapshot
from beta_engine.domain.finals.race_replacement import (
    WorldTourFinalsEffectiveParticipantState,
)


class ViewerFinalsRaceCountedResult(BaseModel):
    event_id: str = Field(min_length=1)
    completed_season_index: int = Field(ge=0, le=49)
    completed_week: int = Field(ge=1, le=61)
    race_points: int = Field(ge=0)


class ViewerFinalsRaceRow(BaseModel):
    rank: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    race_points: int = Field(ge=0)
    tournaments_counted: int = Field(ge=0)
    finals_selected: bool | None
    finals_seed: int | None = Field(default=None, ge=1)
    qualification_source: Literal["direct_entry", "race"] | None = None
    counted_results: tuple[ViewerFinalsRaceCountedResult, ...]


class ViewerFinalsRacePublication(BaseModel):
    schema_version: Literal["viewer_finals_race_publication.v1"] = (
        "viewer_finals_race_publication.v1"
    )
    product_run_id: str
    viewer_branch_id: str
    target_season_index: int = Field(ge=0, le=49)
    cutoff_season_index: int = Field(ge=0, le=49)
    cutoff_week: int = Field(ge=1, le=61)
    best_n: int = Field(ge=1)
    selection_published: bool
    finals_event_id: str | None
    rows: tuple[ViewerFinalsRaceRow, ...]


class ViewerFinalsRaceHistory(BaseModel):
    schema_version: Literal["viewer_finals_race_history.v1"] = (
        "viewer_finals_race_history.v1"
    )
    product_run_id: str
    viewer_branch_id: str
    latest_target_season_index: int | None
    publications: tuple[ViewerFinalsRacePublication, ...]


def _component_rows(
    component: dict[str, object] | None,
    key: str,
) -> tuple[dict[str, object], ...]:
    if component is None:
        return ()
    raw = component.get(key, [])
    if not isinstance(raw, list):
        raise ValueError(f"Saved Finals Race component {key!r} is corrupt")
    rows: list[dict[str, object]] = []
    for value in raw:
        if not isinstance(value, dict):
            raise ValueError(f"Saved Finals Race component {key!r} has a corrupt row")
        rows.append(value)
    return tuple(rows)


def _payload(row: dict[str, object], *, label: str) -> dict[str, object]:
    raw = row.get("payload_json")
    if not isinstance(raw, str):
        raise ValueError(f"Saved {label} payload is missing")
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Saved {label} payload is corrupt") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Saved {label} payload must be an object")
    return value


def _race_snapshots(
    component: dict[str, object] | None,
    *,
    run_id: str,
    branch_id: str,
) -> tuple[WorldTourFinalsRaceSnapshot, ...]:
    values: list[WorldTourFinalsRaceSnapshot] = []
    seen_seasons: set[int] = set()
    for row in _component_rows(component, "finals_race_snapshots"):
        snapshot = WorldTourFinalsRaceSnapshot.model_validate(
            _payload(row, label="Finals Race snapshot")
        )
        if (snapshot.run_id, snapshot.branch_id) != (run_id, branch_id):
            raise ValueError("Saved Finals Race snapshot belongs to another Viewer Branch")
        if row.get("run_id") != run_id or row.get("branch_id") != branch_id:
            raise ValueError("Saved Finals Race row scope differs from its payload")
        if row.get("target_season_index") != snapshot.target_season_index:
            raise ValueError("Saved Finals Race row season differs from its payload")
        if row.get("snapshot_fingerprint") != snapshot.fingerprint:
            raise ValueError("Saved Finals Race snapshot fingerprint is corrupt")
        if row.get("input_fingerprint") != snapshot.input_fingerprint:
            raise ValueError("Saved Finals Race input fingerprint is corrupt")
        if row.get("cutoff_week_ordinal") != snapshot.cutoff_week.ordinal:
            raise ValueError("Saved Finals Race cutoff ordinal is corrupt")
        if snapshot.target_season_index in seen_seasons:
            raise ValueError("Viewer Saved Revision has duplicate Finals Race seasons")
        seen_seasons.add(snapshot.target_season_index)
        values.append(snapshot)
    return tuple(sorted(values, key=lambda value: value.target_season_index))


def _participant_selections(
    component: dict[str, object] | None,
    *,
    run_id: str,
    branch_id: str,
) -> dict[int, WorldTourFinalsParticipantSelectionSnapshot]:
    result: dict[int, WorldTourFinalsParticipantSelectionSnapshot] = {}
    for row in _component_rows(component, "finals_participant_snapshots"):
        snapshot = WorldTourFinalsParticipantSelectionSnapshot.model_validate(
            _payload(row, label="Finals participant selection")
        )
        if (snapshot.run_id, snapshot.branch_id) != (run_id, branch_id):
            raise ValueError(
                "Saved Finals participant selection belongs to another Viewer Branch"
            )
        if row.get("run_id") != run_id or row.get("branch_id") != branch_id:
            raise ValueError("Saved Finals participant row scope differs from its payload")
        if row.get("target_season_index") != snapshot.target_season_index:
            raise ValueError("Saved Finals participant row season differs from its payload")
        if row.get("snapshot_fingerprint") != snapshot.fingerprint:
            raise ValueError("Saved Finals participant snapshot fingerprint is corrupt")
        if snapshot.target_season_index in result:
            raise ValueError("Viewer Saved Revision has duplicate Finals participant seasons")
        result[snapshot.target_season_index] = snapshot
    return result


def _effective_states(
    component: dict[str, object] | None,
    *,
    run_id: str,
    branch_id: str,
) -> dict[int, WorldTourFinalsEffectiveParticipantState]:
    latest: dict[int, tuple[int, WorldTourFinalsEffectiveParticipantState]] = {}
    for row in _component_rows(component, "finals_effective_states"):
        state = WorldTourFinalsEffectiveParticipantState.model_validate(
            _payload(row, label="Finals effective participant state")
        )
        if (state.run_id, state.branch_id) != (run_id, branch_id):
            raise ValueError(
                "Saved Finals effective participant state belongs to another Viewer Branch"
            )
        if row.get("run_id") != run_id or row.get("branch_id") != branch_id:
            raise ValueError("Saved Finals effective-state row scope differs from payload")
        if row.get("target_season_index") != state.target_season_index:
            raise ValueError("Saved Finals effective-state season differs from payload")
        if row.get("state_fingerprint") != state.fingerprint:
            raise ValueError("Saved Finals effective-state fingerprint is corrupt")
        sequence = row.get("sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise ValueError("Saved Finals effective-state sequence is corrupt")
        current = latest.get(state.target_season_index)
        if current is None or sequence > current[0]:
            latest[state.target_season_index] = (sequence, state)
        elif sequence == current[0]:
            raise ValueError("Viewer Saved Revision has duplicate Finals effective-state sequence")
    return {season: value[1] for season, value in latest.items()}


def resolve_viewer_finals_race_history(
    component: dict[str, object] | None,
    *,
    run_id: str,
    branch_id: str,
) -> ViewerFinalsRaceHistory:
    races = _race_snapshots(component, run_id=run_id, branch_id=branch_id)
    selections = _participant_selections(component, run_id=run_id, branch_id=branch_id)
    effective = _effective_states(component, run_id=run_id, branch_id=branch_id)

    publications: list[ViewerFinalsRacePublication] = []
    for race in races:
        selection = selections.get(race.target_season_index)
        if (
            selection is not None
            and selection.race_snapshot_fingerprint != race.fingerprint
        ):
            raise ValueError("Finals participant selection references another Race snapshot")

        effective_state = effective.get(race.target_season_index)
        if effective_state is not None:
            if selection is None:
                raise ValueError(
                    "Finals effective participant state exists without published selection"
                )
            if effective_state.initial_selection_fingerprint != selection.fingerprint:
                raise ValueError(
                    "Finals effective participant state references another selection"
                )
            if effective_state.race_snapshot_fingerprint != race.fingerprint:
                raise ValueError(
                    "Finals effective participant state references another Race snapshot"
                )
            public_participants = effective_state.participants
        else:
            public_participants = selection.participants if selection is not None else ()

        selected_by_player = {player.player_id: player for player in public_participants}
        selection_published = selection is not None
        publications.append(
            ViewerFinalsRacePublication(
                product_run_id=run_id,
                viewer_branch_id=branch_id,
                target_season_index=race.target_season_index,
                cutoff_season_index=race.cutoff_week.season_index,
                cutoff_week=race.cutoff_week.week,
                best_n=race.best_n,
                selection_published=selection_published,
                finals_event_id=selection.finals_event_id if selection is not None else None,
                rows=tuple(
                    ViewerFinalsRaceRow(
                        rank=row.rank,
                        player_id=row.player_id,
                        race_points=row.race_points,
                        tournaments_counted=len(row.counted_results),
                        finals_selected=(
                            row.player_id in selected_by_player
                            if selection_published
                            else None
                        ),
                        finals_seed=(
                            selected_by_player[row.player_id].seed
                            if row.player_id in selected_by_player
                            else None
                        ),
                        qualification_source=(
                            selected_by_player[row.player_id].qualification_source
                            if row.player_id in selected_by_player
                            else None
                        ),
                        counted_results=tuple(
                            ViewerFinalsRaceCountedResult(
                                event_id=result.event_id,
                                completed_season_index=result.completed_week.season_index,
                                completed_week=result.completed_week.week,
                                race_points=result.race_points,
                            )
                            for result in row.counted_results
                        ),
                    )
                    for row in race.rows
                ),
            )
        )

    return ViewerFinalsRaceHistory(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        latest_target_season_index=(
            publications[-1].target_season_index if publications else None
        ),
        publications=tuple(publications),
    )
