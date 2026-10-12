"""Per-country player standings from immutable published tournament and match evidence.

No invented ranking points or title weight. Ranking priority is titles, total
final appearances, played wins, then fewest played losses and stable player ID.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_country_records_read_model import resolve_run_country_records
from beta_engine.application.country_saved_match_records import collect_country_saved_match_records
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class CountryPlayerStanding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    position: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    player_name: str = Field(min_length=1)
    country_code: str
    titles: int = Field(ge=0)
    runner_up_finishes: int = Field(ge=0)
    final_appearances: int = Field(ge=0)
    played_wins: int = Field(ge=0)
    played_losses: int = Field(ge=0)
    walkover_wins: int = Field(ge=0)
    walkover_losses: int = Field(ge=0)


class CountryPlayerStandings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["country_player_standings.v1"] = "country_player_standings.v1"
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    country_code: str
    calendar_status: Literal["empty", "ready"]
    published_event_count: int = Field(ge=0)
    country_titles: int = Field(ge=0)
    country_runner_up_finishes: int = Field(ge=0)
    country_played_wins: int = Field(ge=0)
    country_played_losses: int = Field(ge=0)
    country_walkover_wins: int = Field(ge=0)
    country_walkover_losses: int = Field(ge=0)
    total_players: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    has_more: bool
    players: tuple[CountryPlayerStanding, ...]


def resolve_country_player_standings(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, country_code: str,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
    offset: int = 0, limit: int = 25,
) -> CountryPlayerStandings:
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError("Invalid country player standings page")
    params = dict(
        run_id=run_id, selected_branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        country_code=country_code, packages=packages, ranking=ranking,
        initial_world=initial_world, prospect_source=prospect_source,
    )
    tournaments = resolve_run_country_records(**params)
    matches, all_country_matches = collect_country_saved_match_records(
        **params, offset=0, limit=25,
    )
    if (
        tournaments.published_result_count != matches.published_event_count
        or tournaments.calendar_status != matches.calendar_status
        or len(all_country_matches) != matches.country_match_count
        or tournaments.revision_branch_id != matches.revision_branch_id
    ):
        raise ValueError("Country player standing sources contradict the Saved Revision")
    players: dict[str, dict] = {}

    def get_player(player_id: str, name: str, nationality: str) -> dict:
        if nationality != country_code:
            raise ValueError("Country player standing participant nationality differs")
        if not player_id or not name.strip():
            raise ValueError("Country player standing participant identity missing")
        if player_id not in players:
            players[player_id] = dict(player_id=player_id, player_name=name,
                country_code=nationality, titles=0, runner_up_finishes=0,
                played_wins=0, played_losses=0, walkover_wins=0, walkover_losses=0)
        elif players[player_id]["player_name"] != name:
            raise ValueError("Country player standing identity name differs across Saved evidence")
        return players[player_id]

    for event in tournaments.player_results:
        if event.champion_country == country_code:
            get_player(event.champion_player_id, event.champion_name,
                event.champion_country)["titles"] += 1
        if event.finalist_country == country_code:
            get_player(event.finalist_player_id, event.finalist_name,
                event.finalist_country)["runner_up_finishes"] += 1
    for match in all_country_matches:
        key = "played" if match.completion == "played" else "walkover"
        if match.winner_country == country_code:
            get_player(match.winner_player_id, match.winner_name,
                match.winner_country)[key + "_wins"] += 1
        if match.loser_country == country_code:
            get_player(match.loser_player_id, match.loser_name,
                match.loser_country)[key + "_losses"] += 1

    ordered = sorted(players.values(), key=lambda p: (
        -p["titles"], -(p["titles"] + p["runner_up_finishes"]),
        -p["played_wins"], p["played_losses"], p["player_id"],
    ))
    # These reconciliation checks cover all players and all results, not the
    # returned page; no truncated 25-match view is used to rank athletes.
    if (
        sum(p["titles"] for p in ordered) != tournaments.country_titles
        or sum(p["runner_up_finishes"] for p in ordered) != tournaments.country_finalists
        or sum(p["played_wins"] for p in ordered) != matches.country_played_wins
        or sum(p["played_losses"] for p in ordered) != matches.country_played_losses
        or sum(p["walkover_wins"] for p in ordered) != matches.country_walkover_wins
        or sum(p["walkover_losses"] for p in ordered) != matches.country_walkover_losses
    ):
        raise ValueError("Country player totals contradict published canonical evidence")
    ranked = tuple(CountryPlayerStanding(
        position=i + 1, **row,
        final_appearances=row["titles"] + row["runner_up_finishes"],
    ) for i, row in enumerate(ordered))
    return CountryPlayerStandings(
        run_id=run_id, branch_id=selected_branch_id,
        revision_branch_id=revision_branch_id, saved_revision_id=saved_revision_id,
        country_code=country_code, calendar_status=tournaments.calendar_status,
        published_event_count=tournaments.published_result_count,
        country_titles=tournaments.country_titles,
        country_runner_up_finishes=tournaments.country_finalists,
        country_played_wins=matches.country_played_wins,
        country_played_losses=matches.country_played_losses,
        country_walkover_wins=matches.country_walkover_wins,
        country_walkover_losses=matches.country_walkover_losses,
        total_players=len(ranked), offset=offset, limit=limit,
        has_more=offset+limit<len(ranked),
        players=ranked[offset:offset+limit],
    )
