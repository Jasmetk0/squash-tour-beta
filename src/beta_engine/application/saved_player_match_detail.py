"""Read-only canonical saved player match detail and bounded archived rally replay.

The tournament outcome comes from the selected Branch's frozen canonical result.
Replay is offered only when a matching restore-grade-validated Saved Simulation Slot
group proves its exact Run/Branch/Week/Event/Match and participants. No RNG and no
live SQLite fallback; absent historical rally evidence is explicitly unavailable.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.run_home_activity_read_model import _season_index
from beta_engine.application.run_home_player_identity import SavedHomePlayerIdentities
from beta_engine.application.saved_player_match_history import SavedPlayerMatch, _is_walkover
from beta_engine.application.viewer_tournament_history_read_model import resolve_viewer_tournament_history
from beta_engine.application.viewer_tournament_result_read_model import resolve_viewer_tournament_result
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.authoritative_group_state import AuthoritativeGroupResult, load_authoritative_group


class SavedMatchRallyFrame(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rally_index: int = Field(ge=1)
    set_number: int = Field(ge=1)
    server_player_id: str
    winner_player_id: str | None
    score_a_before: int = Field(ge=0)
    score_b_before: int = Field(ge=0)
    score_a_after: int = Field(ge=0)
    score_b_after: int = Field(ge=0)
    sets_a_after: int = Field(ge=0)
    sets_b_after: int = Field(ge=0)
    set_complete: bool
    match_complete: bool


class SavedPlayerMatchDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["saved_player_match_detail.v1"] = "saved_player_match_detail.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    player_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    match: SavedPlayerMatch
    winner_player_id: str
    loser_player_id: str
    replay_status: Literal["available", "unavailable"]
    player_a_id: str | None = None
    player_b_id: str | None = None
    # Cursor is bounded, and no hidden inputs/seed/fingerprints are exported.
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=25)
    total_rallies: int = Field(ge=0)
    has_more: bool
    rallies: tuple[SavedMatchRallyFrame, ...]


def resolve_saved_player_match_detail(
    *, run_id: str, branch_id: str, saved_revision_id: str,
    player_id: str, event_id: str, match_id: str,
    identities: SavedHomePlayerIdentities,
    ranking: RankingRevisionState | None, packages: RunPackageState | None,
    saved_slots: dict | None,
    offset: int = 0, limit: int = 25,
) -> SavedPlayerMatchDetail:
    if not all(value and value.strip() == value and len(value) <= 128
               for value in (player_id, event_id, match_id)):
        raise ValueError("Invalid player/event/match ID")
    if offset < 0 or not 1 <= limit <= 25:
        raise ValueError("Invalid saved replay cursor")
    if (identities.run_id, identities.branch_id, identities.saved_revision_id,
        identities.requested_ids) != (run_id, branch_id, saved_revision_id, (player_id,)):
        raise ValueError("Saved identity differs from selected Branch HEAD")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
        raise ValueError("Ranking belongs to a foreign Branch")
    if packages is not None and (packages.run_id, packages.branch_id) != (run_id, branch_id):
        raise ValueError("Calendar belongs to a foreign Branch")
    if not any(item.player_id == player_id for item in identities.players):
        raise KeyError("Player is not present in selected Saved Revision")
    if packages is None or ranking is None:
        raise KeyError("Selected Saved Revision has no canonical Tournament Result")
    history = resolve_viewer_tournament_history(
        run_package_state=packages, ranking=ranking, run_id=run_id, branch_id=branch_id,
    )
    if (history.product_run_id, history.viewer_branch_id) != (run_id, branch_id):
        raise ValueError("Saved Tournament history belongs to another Branch")
    events = [item for item in history.tournaments if item.event_id == event_id]
    if len(events) != 1 or not events[0].result_published:
        raise KeyError("Requested event has no published canonical result")
    event = events[0]
    result = resolve_viewer_tournament_result(
        ranking, run_id=run_id, branch_id=branch_id, event_id=event_id,
    )
    season = _season_index(event.season)
    if (result.product_run_id, result.viewer_branch_id, result.event_id,
        result.completed_season_index, result.completed_week) != (
            run_id, branch_id, event_id, season, event.season_week,
        ):
        raise ValueError("Canonical result differs from saved Calendar scope or week")
    matches = [item for item in result.matches if item.match_id == match_id]
    if len(matches) != 1 or matches[0].loser_player_id is None:
        raise KeyError("Requested played match does not exist in canonical result")
    game = matches[0]
    if player_id not in (game.winner_player_id, game.loser_player_id):
        raise KeyError("Player did not participate in the requested match")
    if game.winner_player_id == game.loser_player_id:
        raise ValueError("Match winner and loser are the same identity")

    match = SavedPlayerMatch(
        event_id=event_id, event_name=event.event_name, match_id=match_id,
        season_index=season, season=event.season, week=event.season_week,
        draw_type=game.draw_type, round_number=game.round_number,
        opponent_player_id=(game.loser_player_id if game.winner_player_id == player_id
                            else game.winner_player_id),
        outcome="win" if game.winner_player_id == player_id else "loss",
        completion="walkover" if _is_walkover(game.scoreline) else "played",
        scoreline=game.scoreline,
    )
    base = dict(
        run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id,
        player_id=player_id, match=match, winner_player_id=game.winner_player_id,
        loser_player_id=game.loser_player_id, offset=offset, limit=limit,
    )
    candidates = []
    for row in (saved_slots or {}).get("groups", ()):
        if row["match_id"] != match_id or row["week_ordinal"] != season * 61 + event.season_week - 1:
            continue
        # An identical match ID may occur in different events or weeks. Only
        # the selected canonical Event is a valid replay authority.
        group = load_authoritative_group(SimpleNamespace(**row))
        if not isinstance(group, AuthoritativeGroupResult):
            continue
        if group.authoritative_input.event_id == event_id:
            candidates.append(group)
    if len(candidates) > 1:
        raise ValueError("Multiple saved competitive groups claim this canonical match")
    if match.completion == "walkover" or not candidates:
        return SavedPlayerMatchDetail(
            **base, replay_status="unavailable", total_rallies=0, has_more=False, rallies=(),
        )
    stored = candidates[0]
    authority, played = stored.authoritative_input, stored.result
    if (
        authority.run_id != run_id or authority.branch_id != branch_id
        or authority.week.ordinal != season * 61 + event.season_week - 1
        or authority.event_id != event_id or authority.match_id != match_id
        or played.match_id != match_id
        or played.winner_player_id != game.winner_player_id
        or played.loser_player_id != game.loser_player_id
        or {played.player_a_id, played.player_b_id}
           != {game.winner_player_id, game.loser_player_id}
    ):
        raise ValueError("Saved match replay contradicts canonical Tournament Result")
    log = played.rally_log
    if log is None:
        return SavedPlayerMatchDetail(
            **base, replay_status="unavailable", total_rallies=0, has_more=False, rallies=(),
        )
    if log.match_id != match_id or log.total_rallies != len(log.events):
        raise ValueError("Saved rally log does not match completed match identity")
    frames = tuple(SavedMatchRallyFrame(
        rally_index=r.rally_index, set_number=r.set_number,
        server_player_id=r.serving_player_id, winner_player_id=r.winner_player_id,
        score_a_before=r.score_before.points_a, score_b_before=r.score_before.points_b,
        score_a_after=r.score_after.points_a, score_b_after=r.score_after.points_b,
        sets_a_after=r.score_after.sets_a, sets_b_after=r.score_after.sets_b,
        set_complete=r.post_rally_state.set_complete,
        match_complete=r.post_rally_state.match_complete,
    ) for r in log.events[offset:offset + limit])
    return SavedPlayerMatchDetail(
        **base, replay_status="available", player_a_id=played.player_a_id,
        player_b_id=played.player_b_id, total_rallies=log.total_rallies,
        has_more=offset + limit < log.total_rallies, rallies=frames,
    )
