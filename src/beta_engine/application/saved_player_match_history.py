"""Canonical, read-only played tournament match history for one saved player.

Only the selected Run/Branch immutable Saved Revision is queried. Legacy careers,
Viewer selection, live slots, unclosed tournaments and future-only matches are
never merged into this timeline. BYEs do not count as played matches; recorded
walkovers appear separately from on-court wins/losses.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.run_home_player_identity import SavedHomePlayerIdentities
from beta_engine.application.run_home_activity_read_model import _season_index
from beta_engine.application.viewer_tournament_history_read_model import resolve_viewer_tournament_history
from beta_engine.application.viewer_tournament_result_read_model import resolve_viewer_tournament_result
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState


class SavedPlayerMatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    season_index: int = Field(ge=0, le=49)
    season: str
    week: int = Field(ge=1, le=61)
    draw_type: Literal["qualification", "main", "group", "knockout"]
    round_number: int = Field(ge=1)
    opponent_player_id: str = Field(min_length=1)
    outcome: Literal["win", "loss"]
    completion: Literal["played", "walkover"]
    scoreline: str = Field(min_length=1)


class SavedPlayerMatchHistory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["saved_player_match_history.v1"] = "saved_player_match_history.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    player_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    status: Literal["identity_unavailable", "ready"]
    season_index: int | None = Field(default=None, ge=0, le=49)
    available_seasons: tuple[int, ...]
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=20)
    # Total scope is the requested season, or the entire saved career when absent.
    total_results: int = Field(ge=0)
    played_wins: int = Field(ge=0)
    played_losses: int = Field(ge=0)
    walkovers: int = Field(ge=0)
    # These all-time counters never change when the season filter changes.
    career_played_wins: int = Field(ge=0)
    career_played_losses: int = Field(ge=0)
    career_walkovers: int = Field(ge=0)
    has_more: bool
    matches: tuple[SavedPlayerMatch, ...]


def _is_walkover(scoreline: str) -> bool:
    value = scoreline.strip().upper().replace(" ", "")
    return any(marker in value for marker in ("W/O", "WALKOVER", "W.O.", "WO.")) or value == "WO"


def resolve_saved_player_match_history(
    *, run_id: str, branch_id: str, saved_revision_id: str,
    player_id: str, identities: SavedHomePlayerIdentities,
    ranking: RankingRevisionState | None, packages: RunPackageState | None,
    season_index: int | None = None, offset: int = 0, limit: int = 20,
) -> SavedPlayerMatchHistory:
    if not player_id or len(player_id) > 128 or player_id.strip() != player_id:
        raise ValueError("Invalid saved player ID")
    if season_index is not None and not 0 <= season_index <= 49:
        raise ValueError("Season index outside 50-season Run")
    if offset < 0 or not 1 <= limit <= 20:
        raise ValueError("Invalid match history page")
    if (identities.run_id, identities.branch_id, identities.saved_revision_id,
        identities.requested_ids) != (run_id, branch_id, saved_revision_id, (player_id,)):
        raise ValueError("Player identity differs from selected Saved Branch HEAD")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
        raise ValueError("Saved ranking differs from selected Run/Branch")
    if packages is not None and (packages.run_id, packages.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Calendar differs from selected Run/Branch")
    base = dict(run_id=run_id, branch_id=branch_id,
                saved_revision_id=saved_revision_id, player_id=player_id,
                season_index=season_index, offset=offset, limit=limit)
    if not any(row.player_id == player_id for row in identities.players):
        if identities.unresolved_ids != (player_id,):
            raise ValueError("Missing identity is inconsistent with Saved Revision")
        return SavedPlayerMatchHistory(
            **base, status="identity_unavailable", available_seasons=(),
            total_results=0, played_wins=0, played_losses=0, walkovers=0,
            career_played_wins=0, career_played_losses=0, career_walkovers=0,
            has_more=False, matches=(),
        )

    if packages is None:
        if ranking is not None and ranking.tournament_sources:
            raise ValueError("Saved tournament evidence has no saved Calendar")
        calendar_events = ()
    else:
        try:
            history = resolve_viewer_tournament_history(
                run_package_state=packages, ranking=ranking,
                run_id=run_id, branch_id=branch_id,
            )
            if (history.product_run_id, history.viewer_branch_id) != (run_id, branch_id):
                raise ValueError("Tournament Calendar belongs to a different Branch")
            calendar_events = history.tournaments
        except KeyError as exc:
            if "no applied Calendar Package" not in str(exc):
                raise
            if ranking is not None and ranking.tournament_sources:
                raise ValueError("Saved tournament evidence has no applied Calendar") from exc
            calendar_events = ()

    results: list[tuple[tuple[int, int, str, int, int, str], SavedPlayerMatch]] = []
    seen: set[tuple[str, str]] = set()
    for event in calendar_events:
        if not event.result_published:
            continue
        result = resolve_viewer_tournament_result(
            ranking, run_id=run_id, branch_id=branch_id, event_id=event.event_id,
        )
        index = _season_index(event.season)
        if (result.product_run_id, result.viewer_branch_id, result.event_id,
            result.completed_season_index, result.completed_week) != (
                run_id, branch_id, event.event_id, index, event.season_week,
            ):
            raise ValueError("Saved Tournament Result differs from Calendar timing or scope")
        for match in result.matches:
            key = (event.event_id, match.match_id)
            if key in seen:
                raise ValueError("Saved tournament repeats a match identity")
            seen.add(key)
            if match.winner_player_id == match.loser_player_id:
                raise ValueError("Saved match plays a player against themselves")
            # A BYE/no-opponent node is not an actual played or walkover match.
            if match.loser_player_id is None:
                continue
            if player_id not in (match.winner_player_id, match.loser_player_id):
                continue
            opponent = (match.loser_player_id if match.winner_player_id == player_id
                        else match.winner_player_id)
            score = match.scoreline.strip()
            if not score or not opponent:
                raise ValueError("Saved match result is missing score or opponent")
            projected = SavedPlayerMatch(
                event_id=event.event_id, event_name=event.event_name,
                match_id=match.match_id, season_index=index, season=event.season,
                week=event.season_week, draw_type=match.draw_type,
                round_number=match.round_number, opponent_player_id=opponent,
                outcome="win" if match.winner_player_id == player_id else "loss",
                completion="walkover" if _is_walkover(score) else "played",
                scoreline=score,
            )
            results.append(((index, event.season_week, event.event_id,
                             match.round_number, match.bracket_position, match.match_id), projected))
    results.sort(key=lambda item: item[0], reverse=True)
    all_rows = tuple(row for _, row in results)
    filtered = tuple(row for row in all_rows if season_index is None or row.season_index == season_index)
    counts = lambda rows: (
        sum(row.completion == "played" and row.outcome == "win" for row in rows),
        sum(row.completion == "played" and row.outcome == "loss" for row in rows),
        sum(row.completion == "walkover" for row in rows),
    )
    wins, losses, walkovers = counts(filtered)
    career_wins, career_losses, career_walkovers = counts(all_rows)
    return SavedPlayerMatchHistory(
        **base, status="ready",
        available_seasons=tuple(sorted({row.season_index for row in all_rows})),
        total_results=len(filtered), played_wins=wins, played_losses=losses,
        walkovers=walkovers, career_played_wins=career_wins,
        career_played_losses=career_losses, career_walkovers=career_walkovers,
        has_more=offset + limit < len(filtered),
        matches=filtered[offset:offset + limit],
    )
