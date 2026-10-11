"""Read-only Viewer projection of the selected Branch's canonical Tournament Result."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.tournaments.result_authority import TournamentResultAuthority


class ViewerTournamentResultPlayer(BaseModel):
    player_id: str = Field(min_length=1)
    draw_type: Literal["qualification", "main", "both", "hybrid", "group"]
    seed_number: int | None = Field(default=None, ge=1)
    qualifier: bool
    main_entry_status: Literal["direct", "wild_card", "lucky_loser"] | None = None
    reached_stage: str = Field(min_length=1)
    final_round_number: int | None = Field(default=None, ge=1)
    eliminated_by_player_id: str | None = None
    last_match_id: str | None = None
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    byes_received: int = Field(ge=0)
    walkovers_received: int = Field(ge=0)
    retired_or_walkover_loss: bool
    group_index: int | None = Field(default=None, ge=1)
    group_position: int | None = Field(default=None, ge=1)
    played_group_wins: int | None = Field(default=None, ge=0)
    group_walkovers_received: int | None = Field(default=None, ge=0)
    knockout_reached_stage: str | None = None


class ViewerTournamentResultMatch(BaseModel):
    match_id: str = Field(min_length=1)
    draw_type: Literal["qualification", "main", "group", "knockout"]
    round_number: int = Field(ge=1)
    bracket_position: int = Field(ge=1)
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str | None = None
    scoreline: str = Field(min_length=1)


class ViewerTournamentResult(BaseModel):
    schema_version: Literal["viewer_tournament_result.v1"] = "viewer_tournament_result.v1"
    product_run_id: str
    viewer_branch_id: str
    event_id: str
    completed_season_index: int = Field(ge=0)
    completed_week: int = Field(ge=1, le=61)
    champion_player_id: str = Field(min_length=1)
    finalist_player_id: str = Field(min_length=1)
    qualification_winner_ids: tuple[str, ...]
    players: tuple[ViewerTournamentResultPlayer, ...]
    matches: tuple[ViewerTournamentResultMatch, ...]


def _project_result(
    result: TournamentResultAuthority,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentResult:
    if (result.run_id, result.branch_id, result.event_id) != (
        run_id,
        branch_id,
        event_id,
    ):
        raise ValueError("Canonical Tournament Result scope differs from Viewer Branch")

    return ViewerTournamentResult(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        event_id=event_id,
        completed_season_index=result.completed_week.season_index,
        completed_week=result.completed_week.week,
        champion_player_id=result.champion_player_id,
        finalist_player_id=result.finalist_player_id,
        qualification_winner_ids=result.qualification_winner_ids,
        players=tuple(
            ViewerTournamentResultPlayer(
                player_id=player.player_id,
                draw_type=player.draw_type,
                seed_number=player.seed_number,
                qualifier=player.qualifier,
                main_entry_status=player.main_entry_status,
                reached_stage=player.reached_stage,
                final_round_number=player.final_round_number,
                eliminated_by_player_id=player.eliminated_by_player_id,
                last_match_id=player.last_match_id,
                wins=player.wins,
                losses=player.losses,
                byes_received=player.byes_received,
                walkovers_received=player.walkovers_received,
                retired_or_walkover_loss=player.retired_or_walkover_loss,
                group_index=player.group_index,
                group_position=player.group_position,
                played_group_wins=player.played_group_wins,
                group_walkovers_received=player.group_walkovers_received,
                knockout_reached_stage=player.knockout_reached_stage,
            )
            for player in result.players
        ),
        matches=tuple(
            ViewerTournamentResultMatch(
                match_id=match.match_id,
                draw_type=match.draw_type,
                round_number=match.round_number,
                bracket_position=match.bracket_position,
                winner_player_id=match.winner_player_id,
                loser_player_id=match.loser_player_id,
                scoreline=match.scoreline,
            )
            for match in result.matches
        ),
    )


def resolve_viewer_tournament_result(
    ranking: RankingRevisionState | None,
    *,
    run_id: str,
    branch_id: str,
    event_id: str,
) -> ViewerTournamentResult:
    if ranking is None:
        raise KeyError("Viewer Saved Revision has no Ranking component")

    sources = tuple(
        source
        for source in ranking.tournament_sources
        if source.binding.event_id == event_id
    )
    if not sources:
        raise KeyError(
            f"Tournament Result {event_id!r} is not present in Viewer Saved Revision"
        )
    if len(sources) != 1:
        raise ValueError("Viewer Tournament Result source identity is ambiguous")

    source = sources[0]
    if (
        source.binding.run_id,
        source.binding.branch_id,
        source.binding.event_id,
    ) != (run_id, branch_id, event_id):
        raise ValueError("Owned Tournament Result source scope differs from Viewer Branch")
    if source.canonical_result is None:
        raise ValueError("Viewer Tournament Result requires canonical result authority")

    return _project_result(
        source.canonical_result,
        run_id=run_id,
        branch_id=branch_id,
        event_id=event_id,
    )
