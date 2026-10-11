"""Branch-scoped, immutable weekly ranking movement projection for Admin Run Home.

Only two consecutive *published* ranking snapshots in the verified Saved Revision
are compared; live candidates, future publications and legacy ranking are excluded.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.viewer_official_ranking_read_model import (
    resolve_viewer_official_ranking,
    resolve_viewer_official_ranking_at,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState


class RunHomeRankingChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str = Field(min_length=1)
    movement: Literal["up", "down", "entered", "exited", "points_only"]
    previous_rank: int | None = Field(default=None, ge=1)
    current_rank: int | None = Field(default=None, ge=1)
    previous_points: int | None = Field(default=None, ge=0)
    current_points: int | None = Field(default=None, ge=0)
    points_delta: int | None = None
    rank_delta: int | None = None


class RunHomeRankingChanges(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["run_home_ranking_changes.v1"] = "run_home_ranking_changes.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    status: Literal["unpublished", "first_publication", "ready"]
    previous_week_ordinal: int | None = Field(default=None, ge=0, le=3049)
    current_week_ordinal: int | None = Field(default=None, ge=0, le=3049)
    current_row_count: int | None = Field(default=None, ge=0)
    total_change_count: int = Field(ge=0)
    moved_count: int = Field(ge=0)
    entered_count: int = Field(ge=0)
    exited_count: int = Field(ge=0)
    points_only_count: int = Field(ge=0)
    changes: tuple[RunHomeRankingChange, ...]


def resolve_run_home_ranking_changes(
    *,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    ranking: RankingRevisionState | None,
) -> RunHomeRankingChanges:
    base = dict(run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id)
    empty_counts = dict(total_change_count=0, moved_count=0, entered_count=0,
                        exited_count=0, points_only_count=0, changes=())
    if ranking is None:
        return RunHomeRankingChanges(status="unpublished", **base, **empty_counts)
    if (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
        raise ValueError("Saved ranking belongs to another Run / Branch")

    transition = ranking.authoritative_transition_state
    if transition is None:
        return RunHomeRankingChanges(status="unpublished", **base, **empty_counts)
    world = transition["world"]
    publications = transition["publications"]
    if world is None:
        if publications:
            raise ValueError("Ranking publications exist without a saved public world HEAD")
        return RunHomeRankingChanges(status="unpublished", **base, **empty_counts)
    # Resolves and validates the actual published head, including snapshot fingerprint.
    current = resolve_viewer_official_ranking(ranking)
    if (current.product_run_id, current.viewer_branch_id) != (run_id, branch_id):
        raise ValueError("Current ranking projection differs from selected Branch")
    visible = [item["week_ordinal"] for item in publications
               if item["week_ordinal"] <= current.week_ordinal]
    if not visible or visible[-1] != current.week_ordinal:
        raise ValueError("Saved ranking HEAD has no matching publication")
    if len(visible) == 1:
        return RunHomeRankingChanges(
            status="first_publication",
            current_week_ordinal=current.week_ordinal,
            current_row_count=current.row_count,
            **base, **empty_counts,
        )

    previous_ordinal = visible[-2]
    if previous_ordinal != current.week_ordinal - 1:
        raise ValueError("Cannot compare nonconsecutive weekly rankings")
    previous = resolve_viewer_official_ranking_at(ranking, week_ordinal=previous_ordinal)
    if (previous.product_run_id, previous.viewer_branch_id) != (run_id, branch_id):
        raise ValueError("Previous ranking belongs to another Run / Branch")
    before = {row.player_id: row for row in previous.rows}
    after = {row.player_id: row for row in current.rows}
    if len(before) != len(previous.rows) or len(after) != len(current.rows):
        raise ValueError("Published ranking contains duplicate player identity")
    changes = []
    for player_id in before.keys() | after.keys():
        old, new = before.get(player_id), after.get(player_id)
        old_rank, new_rank = (old.rank if old else None), (new.rank if new else None)
        if old is None:
            movement = "entered"
        elif new is None:
            movement = "exited"
        elif old_rank != new_rank:
            movement = "up" if new_rank < old_rank else "down"
        elif old.points != new.points:
            movement = "points_only"
        else:
            continue
        changes.append(RunHomeRankingChange(
            player_id=player_id,
            movement=movement,
            previous_rank=old_rank, current_rank=new_rank,
            previous_points=old.points if old else None,
            current_points=new.points if new else None,
            points_delta=new.points - old.points if old and new else None,
            rank_delta=old_rank - new_rank if old and new else None,
        ))
    counts = {name: sum(row.movement == name for row in changes)
              for name in ("up", "down", "entered", "exited", "points_only")}
    # Deterministic, significant rank movement first; 'entered'/'exited' are never
    # represented as an arbitrary climb/drop from a made-up previous ranking.
    order = {"up": 0, "down": 1, "entered": 2, "exited": 3, "points_only": 4}
    changes.sort(key=lambda row: (
        order[row.movement], -(abs(row.rank_delta or 0)),
        row.current_rank or row.previous_rank or 0, row.player_id,
    ))
    return RunHomeRankingChanges(
        status="ready", previous_week_ordinal=previous_ordinal,
        current_week_ordinal=current.week_ordinal, current_row_count=current.row_count,
        total_change_count=len(changes),
        moved_count=counts["up"] + counts["down"],
        entered_count=counts["entered"], exited_count=counts["exited"],
        points_only_count=counts["points_only"],
        changes=tuple(changes[:10]),
        **base,
    )
