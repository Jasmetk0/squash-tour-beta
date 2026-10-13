"""Immutable Saved Edition match detail with optional *archived* rally replay.

Unlike the present-time Saved Player profile endpoint, this contract is scoped
to an explicitly reachable Saved Revision, including shared pre-fork ancestors.
A canonical published result is necessary for a match detail; replay additionally
requires a matching saved competitive group, never live/Official Viewer state.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.run_saved_tour_read_model import RunSavedTourEdition
from beta_engine.application.saved_player_match_detail import SavedMatchRallyFrame
from beta_engine.application.saved_player_match_history import _is_walkover
from beta_engine.application.viewer_tournament_result_read_model import ViewerTournamentResultMatch
from beta_engine.infrastructure.db.authoritative_group_state import (
    AuthoritativeGroupResult, load_authoritative_group,
)


class RunSavedTourMatchDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_saved_tour_match_detail.v1"] = (
        "run_saved_tour_match_detail.v1"
    )
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    season_index: int = Field(ge=0, le=49)
    event_id: str
    match_id: str
    match: ViewerTournamentResultMatch
    replay_status: Literal["available", "unavailable"]
    player_a_id: str | None = None
    player_b_id: str | None = None
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=25)
    total_rallies: int = Field(ge=0)
    has_more: bool
    rallies: tuple[SavedMatchRallyFrame, ...]


def resolve_run_saved_tour_match_detail(
    edition: RunSavedTourEdition, *, match_id: str,
    saved_slots: dict | None, offset: int = 0, limit: int = 25,
) -> RunSavedTourMatchDetail:
    if not match_id or len(match_id) > 128 or match_id.strip() != match_id:
        raise ValueError("Invalid Saved Edition match ID")
    if offset < 0 or not 1 <= limit <= 25:
        raise ValueError("Invalid Saved Edition rally cursor")
    if edition.published_result is None:
        raise KeyError("Saved Edition has no published canonical result")
    result = edition.published_result
    if (result.product_run_id, result.viewer_branch_id, result.event_id,
        result.completed_season_index, result.completed_week) != (
        edition.run_id, edition.revision_branch_id, edition.edition.event_id,
        edition.season_index, edition.edition.season_week,
    ):
        raise ValueError("Saved Edition canonical match source context differs")
    matches = [item for item in result.matches if item.match_id == match_id]
    if not matches:
        raise KeyError("Match is not in the requested historical Edition")
    if len(matches) != 1:
        raise ValueError("Canonical Saved Edition match identity is ambiguous")
    match = matches[0]
    if match.loser_player_id is None:
        raise KeyError("No played match detail exists for BYE/non-played entry")
    if match.winner_player_id == match.loser_player_id:
        raise ValueError("Canonical match has identical winner and loser")

    base = dict(
        run_id=edition.run_id, branch_id=edition.branch_id,
        revision_branch_id=edition.revision_branch_id,
        saved_revision_id=edition.saved_revision_id,
        season_index=edition.season_index, event_id=edition.edition.event_id,
        match_id=match_id, match=match, offset=offset, limit=limit,
    )

    candidates = []
    week_ordinal = edition.season_index * 61 + edition.edition.season_week - 1
    for row in (saved_slots or {}).get("groups", ()):
        if row.get("match_id") != match_id or row.get("week_ordinal") != week_ordinal:
            continue
        # The owning Run/Branch identity must NOT be relabelled to the selected
        # post-fork Branch. A conflicting apparent replay is corruption.
        group = load_authoritative_group(SimpleNamespace(**row))
        if not isinstance(group, AuthoritativeGroupResult):
            continue
        if group.authoritative_input.event_id != edition.edition.event_id:
            continue
        if (row.get("run_id"), row.get("branch_id")) != (
            edition.run_id, edition.revision_branch_id,
        ):
            raise ValueError("Archived match group belongs to a foreign Run/Branch")
        candidates.append(group)
    if len(candidates) > 1:
        raise ValueError("Ambiguous archived competitive group for Saved Edition match")

    unavailable = RunSavedTourMatchDetail(
        **base, replay_status="unavailable", total_rallies=0,
        has_more=False, rallies=(),
    )
    if _is_walkover(match.scoreline) or not candidates:
        return unavailable

    archived = candidates[0]
    authority, played = archived.authoritative_input, archived.result
    if (
        (authority.run_id, authority.branch_id, authority.week.ordinal,
         authority.event_id, authority.match_id)
        != (edition.run_id, edition.revision_branch_id, week_ordinal,
            edition.edition.event_id, match_id)
        or played.match_id != match_id
        or (played.winner_player_id, played.loser_player_id) != (
            match.winner_player_id, match.loser_player_id,
        )
        or {played.player_a_id, played.player_b_id} != {
            match.winner_player_id, match.loser_player_id,
        }
    ):
        raise ValueError("Saved rally replay contradicts canonical Edition result")
    log = played.rally_log
    if log is None:
        return unavailable
    if log.match_id != match_id or log.total_rallies != len(log.events):
        raise ValueError("Saved rally log has corrupt match identity or length")
    frames = tuple(SavedMatchRallyFrame(
        rally_index=r.rally_index, set_number=r.set_number,
        server_player_id=r.serving_player_id, winner_player_id=r.winner_player_id,
        score_a_before=r.score_before.points_a,
        score_b_before=r.score_before.points_b,
        score_a_after=r.score_after.points_a,
        score_b_after=r.score_after.points_b,
        sets_a_after=r.score_after.sets_a,
        sets_b_after=r.score_after.sets_b,
        set_complete=r.post_rally_state.set_complete,
        match_complete=r.post_rally_state.match_complete,
    ) for r in log.events[offset:offset + limit])
    return RunSavedTourMatchDetail(
        **base, replay_status="available", player_a_id=played.player_a_id,
        player_b_id=played.player_b_id, total_rallies=log.total_rallies,
        has_more=offset + limit < log.total_rallies, rallies=frames,
    )
