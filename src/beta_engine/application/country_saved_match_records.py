"""Read-only country match records from actual canonical played Saved results.

Counters are PLAYER outcomes, not "country events": an intra-country match
increments one win and one loss. BYEs are excluded and walkovers tracked apart
from on-court play. All source components are one exact reachable Saved Revision.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.run_home_activity_read_model import _season_index
from beta_engine.application.run_home_player_identity import resolve_saved_home_player_identities
from beta_engine.application.saved_player_match_history import _is_walkover
from beta_engine.application.viewer_tournament_history_read_model import resolve_viewer_tournament_history
from beta_engine.application.viewer_tournament_result_read_model import resolve_viewer_tournament_result
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class CountrySavedMatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    event_name: str
    season: str
    season_week: int = Field(ge=1, le=61)
    match_id: str
    draw_type: Literal["qualification", "main", "group", "knockout"]
    round_number: int = Field(ge=1)
    winner_player_id: str
    winner_name: str
    winner_country: str
    loser_player_id: str
    loser_name: str
    loser_country: str
    host_country: str
    completion: Literal["played", "walkover"]
    scoreline: str


class CountrySavedMatchRecords(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["country_saved_match_records.v1"] = "country_saved_match_records.v1"
    run_id: str
    branch_id: str
    revision_branch_id: str
    saved_revision_id: str
    country_code: str
    source: Literal["reachable_saved_revision"] = "reachable_saved_revision"
    calendar_status: Literal["empty", "ready"]
    published_event_count: int = Field(ge=0)
    total_played_matches: int = Field(ge=0)
    total_walkovers: int = Field(ge=0)
    country_played_wins: int = Field(ge=0)
    country_played_losses: int = Field(ge=0)
    country_walkover_wins: int = Field(ge=0)
    country_walkover_losses: int = Field(ge=0)
    hosted_played_matches: int = Field(ge=0)
    hosted_walkovers: int = Field(ge=0)
    country_match_count: int = Field(ge=0)
    # Filters are applied server-side AFTER every canonical result is validated,
    # and BEFORE paging; lifetime totals above are always unfiltered.
    available_seasons: tuple[int, ...]
    season_index: int | None = Field(default=None, ge=0, le=49)
    result_kind: Literal["all", "played", "walkover"] = "all"
    outcome: Literal["all", "win", "loss"] = "all"
    filtered_match_count: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=50)
    has_more: bool
    matches: tuple[CountrySavedMatch, ...]


def resolve_country_saved_match_records(
    *, run_id: str, selected_branch_id: str, revision_branch_id: str,
    saved_revision_id: str, country_code: str,
    packages: RunPackageState | None, ranking: RankingRevisionState | None,
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
    offset: int = 0, limit: int = 25,
    season_index: int | None = None,
    result_kind: Literal["all", "played", "walkover"] = "all",
    outcome: Literal["all", "win", "loss"] = "all",
) -> CountrySavedMatchRecords:
    if len(country_code) != 3 or not country_code.isalpha() or country_code != country_code.upper():
        raise ValueError("Country match records requires uppercase ISO-like country code")
    if not all((run_id, selected_branch_id, revision_branch_id, saved_revision_id)):
        raise ValueError("Country match records requires exact Run/Branch/Revision")
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError("Country match records cursor is invalid")
    if season_index is not None and (not isinstance(season_index, int) or not 0 <= season_index <= 49):
        raise ValueError("Country match records season filter is invalid")
    if result_kind not in ("all", "played", "walkover") or outcome not in ("all", "win", "loss"):
        raise ValueError("Country match records result filter is invalid")
    if packages is not None and (packages.run_id, packages.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Calendar belongs to a foreign Run/Branch")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Ranking belongs to a foreign Run/Branch")
    if initial_world is not None and (initial_world.run_id, initial_world.branch_id) != (run_id, revision_branch_id):
        raise ValueError("Saved Initial World belongs to a foreign Run/Branch")
    if prospect_source is not None and prospect_source.run_id != run_id:
        raise ValueError("Saved prospects belong to a foreign Run")

    events = ()
    if packages is None:
        if ranking is not None and ranking.tournament_sources:
            raise ValueError("Published matches have no Saved Calendar")
    else:
        try:
            history = resolve_viewer_tournament_history(
                run_package_state=packages, ranking=ranking,
                run_id=run_id, branch_id=revision_branch_id,
            )
        except KeyError as exc:
            if "no applied Calendar Package" not in str(exc) or (
                ranking is not None and ranking.tournament_sources
            ):
                raise
        else:
            events = history.tournaments

    published = [event for event in events if event.result_published]
    raw_matches: list[tuple[object, object]] = []
    ids: set[str] = set()
    for event in published:
        result = resolve_viewer_tournament_result(
            ranking, run_id=run_id, branch_id=revision_branch_id, event_id=event.event_id,
        )
        if (result.product_run_id, result.viewer_branch_id, result.event_id,
            result.completed_season_index, result.completed_week) != (
            run_id, revision_branch_id, event.event_id,
            _season_index(event.season), event.season_week,
        ):
            raise ValueError("Published match Result does not match Saved Calendar time/scope")
        seen: set[str] = set()
        for match in result.matches:
            if match.match_id in seen:
                raise ValueError("Duplicate canonical Saved match ID")
            seen.add(match.match_id)
            if match.loser_player_id is None:
                # Genuine BYE is not an actual match.
                continue
            if match.winner_player_id == match.loser_player_id:
                raise ValueError("Saved match plays a player against themselves")
            if not match.scoreline or not match.scoreline.strip():
                raise ValueError("Saved match has no canonical scoreline")
            ids.update((match.winner_player_id, match.loser_player_id))
            raw_matches.append((event, match))

    identities = {}
    sorted_ids = sorted(ids)
    for start in range(0, len(sorted_ids), 25):
        batch = tuple(sorted_ids[start:start + 25])
        result = resolve_saved_home_player_identities(
            run_id=run_id, branch_id=revision_branch_id,
            saved_revision_id=saved_revision_id, requested_ids=batch,
            initial_world=initial_world, prospect_source=prospect_source,
        )
        if result.status != "ready" or result.unresolved_ids:
            raise ValueError("Saved match participant has no verified nationality")
        for player in result.players:
            if player.player_id in identities:
                raise ValueError("Duplicate participant national identity")
            identities[player.player_id] = player

    matches: list[CountrySavedMatch] = []
    for event, match in raw_matches:
        winner = identities[match.winner_player_id]
        loser = identities[match.loser_player_id]
        matches.append(CountrySavedMatch(
            event_id=event.event_id, event_name=event.event_name or event.event_id,
            season=event.season, season_week=event.season_week,
            match_id=match.match_id, draw_type=match.draw_type,
            round_number=match.round_number, winner_player_id=winner.player_id,
            winner_name=winner.display_name, winner_country=winner.country_code,
            loser_player_id=loser.player_id, loser_name=loser.display_name,
            loser_country=loser.country_code, host_country=event.host_country,
            completion="walkover" if _is_walkover(match.scoreline) else "played",
            scoreline=match.scoreline.strip(),
        ))
    matches.sort(key=lambda x: (_season_index(x.season), x.season_week,
        x.event_id, x.round_number, x.match_id), reverse=True)
    own = tuple(row for row in matches if
        row.winner_country == country_code or row.loser_country == country_code)
    # Work with the complete verified result set. Filtering just a 25-row page
    # would silently make season/results searches incomplete.
    filtered = tuple(row for row in own if
        (season_index is None or _season_index(row.season) == season_index)
        and (result_kind == "all" or row.completion == result_kind)
        and (outcome == "all" or (
            row.winner_country == country_code if outcome == "win"
            else row.loser_country == country_code
        )))
    return CountrySavedMatchRecords(
        run_id=run_id, branch_id=selected_branch_id, revision_branch_id=revision_branch_id,
        saved_revision_id=saved_revision_id, country_code=country_code,
        calendar_status="ready" if events else "empty",
        published_event_count=len(published),
        total_played_matches=sum(x.completion == "played" for x in matches),
        total_walkovers=sum(x.completion == "walkover" for x in matches),
        country_played_wins=sum(x.completion == "played" and x.winner_country == country_code for x in own),
        country_played_losses=sum(x.completion == "played" and x.loser_country == country_code for x in own),
        country_walkover_wins=sum(x.completion == "walkover" and x.winner_country == country_code for x in own),
        country_walkover_losses=sum(x.completion == "walkover" and x.loser_country == country_code for x in own),
        hosted_played_matches=sum(x.completion == "played" and x.host_country == country_code for x in matches),
        hosted_walkovers=sum(x.completion == "walkover" and x.host_country == country_code for x in matches),
        country_match_count=len(own),
        available_seasons=tuple(sorted({_season_index(row.season) for row in own})),
        season_index=season_index, result_kind=result_kind, outcome=outcome,
        filtered_match_count=len(filtered), offset=offset, limit=limit,
        has_more=offset + limit < len(filtered),
        matches=filtered[offset:offset + limit],
    )
