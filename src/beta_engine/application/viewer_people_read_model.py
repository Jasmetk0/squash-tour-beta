"""Canonical Saved-Revision Viewer player and country read models."""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.players.sporting import PlayerSportingWeekState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class ViewerPlayer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    player_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    country_code: str = Field(min_length=3, max_length=3)
    age: int = Field(ge=0, le=120)
    status: Literal["active", "retired"]
    tour_entry_season_index: int | None = Field(default=None, ge=0)
    tour_entry_week: int | None = Field(default=None, ge=1, le=61)
    current_ovr: int | None = Field(default=None, ge=0, le=200)
    potential_ovr: int | None = Field(default=None, ge=0, le=200)
    current_form: int | None = Field(default=None, ge=0, le=200)
    match_sharpness: int | None = Field(default=None, ge=0, le=100)
    long_term_fatigue: int | None = Field(default=None, ge=0, le=100)
    identity_source: Literal["initial_world", "run_prospect"]


class ViewerPlayers(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["viewer_players.v1"] = "viewer_players.v1"
    product_run_id: str
    viewer_branch_id: str
    season_index: int = Field(ge=0)
    week: int = Field(ge=1, le=61)
    player_count: int = Field(ge=0)
    active_player_count: int = Field(ge=0)
    retired_player_count: int = Field(ge=0)
    players: tuple[ViewerPlayer, ...]


class ViewerCountry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    country_code: str = Field(min_length=3, max_length=3)
    player_count: int = Field(ge=0)
    active_player_count: int = Field(ge=0)
    retired_player_count: int = Field(ge=0)
    average_current_ovr: float | None = None
    top_player_id: str | None = None
    top_player_name: str | None = None
    top_player_current_ovr: int | None = Field(default=None, ge=0, le=200)


class ViewerCountries(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["viewer_countries.v1"] = "viewer_countries.v1"
    product_run_id: str
    viewer_branch_id: str
    season_index: int = Field(ge=0)
    week: int = Field(ge=1, le=61)
    country_count: int = Field(ge=0)
    countries: tuple[ViewerCountry, ...]


def _prospect_identity(
    snapshot: RunProspectSourceSnapshot | None,
) -> dict[str, tuple[str, str]]:
    if snapshot is None:
        return {}
    result: dict[str, tuple[str, str]] = {}
    for record in snapshot.records:
        player_id = record.get("prospect_id")
        name = record.get("display_name")
        country_code = record.get("country_code")
        if not isinstance(player_id, str) or not player_id:
            raise ValueError("Saved prospect source contains invalid player identity")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Saved prospect {player_id!r} has no display name")
        if not isinstance(country_code, str) or len(country_code.strip()) != 3:
            raise ValueError(f"Saved prospect {player_id!r} has invalid country code")
        if player_id in result:
            raise ValueError("Saved prospect source contains duplicate player identity")
        result[player_id] = (name, country_code.strip().upper())
    return result


def resolve_viewer_players(
    *,
    initial_world: InitialWorldState | None,
    lifecycle_states: tuple[PlayerLifecycleWeekState, ...] | None,
    sporting_states: tuple[PlayerSportingWeekState, ...] | None,
    prospect_source: RunProspectSourceSnapshot | None,
    run_id: str,
    branch_id: str,
) -> ViewerPlayers:
    if initial_world is None:
        raise KeyError("Viewer Saved Revision has no Initial World")
    if lifecycle_states is None or not lifecycle_states:
        raise KeyError("Viewer Saved Revision has no player lifecycle state")
    if sporting_states is None or not sporting_states:
        raise KeyError("Viewer Saved Revision has no player sporting state")

    if (initial_world.run_id, initial_world.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Initial World scope differs from Viewer Branch")

    lifecycle = lifecycle_states[-1]
    sporting = sporting_states[-1]
    if (lifecycle.run_id, lifecycle.branch_id) != (run_id, branch_id):
        raise ValueError("Saved player lifecycle scope differs from Viewer Branch")
    if (sporting.run_id, sporting.branch_id) != (run_id, branch_id):
        raise ValueError("Saved player sporting scope differs from Viewer Branch")
    if lifecycle.week != sporting.week:
        raise ValueError("Saved lifecycle and sporting public weeks differ")

    initial_identity = {
        player.player_id: (player.name, player.country_code.strip().upper())
        for player in initial_world.players
    }
    prospect_identity = _prospect_identity(prospect_source)
    overlap = set(initial_identity) & set(prospect_identity)
    if overlap:
        raise ValueError("Initial World and prospect source duplicate player identity")

    sporting_by_id = {player.player_id: player for player in sporting.players}
    if len(sporting_by_id) != len(sporting.players):
        raise ValueError("Saved sporting state contains duplicate player identity")

    players: list[ViewerPlayer] = []
    for life in lifecycle.players:
        identity = initial_identity.get(life.player_id)
        identity_source: Literal["initial_world", "run_prospect"]
        if identity is not None:
            identity_source = "initial_world"
        else:
            identity = prospect_identity.get(life.player_id)
            identity_source = "run_prospect"
        if identity is None:
            raise ValueError(
                f"Saved player identity metadata is missing for {life.player_id!r}"
            )

        sporting_player = sporting_by_id.get(life.player_id)
        if life.status == "active" and sporting_player is None:
            raise ValueError(
                f"Active player {life.player_id!r} has no saved sporting state"
            )

        players.append(
            ViewerPlayer(
                player_id=life.player_id,
                name=identity[0],
                country_code=identity[1],
                age=life.age,
                status=life.status,
                tour_entry_season_index=(
                    life.tour_entry_week.season_index
                    if life.tour_entry_week is not None
                    else None
                ),
                tour_entry_week=(
                    life.tour_entry_week.week if life.tour_entry_week is not None else None
                ),
                current_ovr=(
                    sporting_player.ovr if sporting_player is not None else None
                ),
                potential_ovr=(
                    sporting_player.potential_ovr
                    if sporting_player is not None
                    else None
                ),
                current_form=(
                    sporting_player.current_form
                    if sporting_player is not None
                    else None
                ),
                match_sharpness=(
                    sporting_player.match_sharpness
                    if sporting_player is not None
                    else None
                ),
                long_term_fatigue=(
                    sporting_player.long_term_fatigue
                    if sporting_player is not None
                    else None
                ),
                identity_source=identity_source,
            )
        )

    ordered = tuple(sorted(players, key=lambda player: player.player_id))
    return ViewerPlayers(
        product_run_id=run_id,
        viewer_branch_id=branch_id,
        season_index=lifecycle.week.season_index,
        week=lifecycle.week.week,
        player_count=len(ordered),
        active_player_count=sum(player.status == "active" for player in ordered),
        retired_player_count=sum(player.status == "retired" for player in ordered),
        players=ordered,
    )


def resolve_viewer_countries(players: ViewerPlayers) -> ViewerCountries:
    grouped: dict[str, list[ViewerPlayer]] = defaultdict(list)
    for player in players.players:
        grouped[player.country_code].append(player)

    countries: list[ViewerCountry] = []
    for country_code, roster in grouped.items():
        ovr_players = [player for player in roster if player.current_ovr is not None]
        top = (
            min(
                ovr_players,
                key=lambda player: (-int(player.current_ovr or 0), player.player_id),
            )
            if ovr_players
            else None
        )
        countries.append(
            ViewerCountry(
                country_code=country_code,
                player_count=len(roster),
                active_player_count=sum(player.status == "active" for player in roster),
                retired_player_count=sum(player.status == "retired" for player in roster),
                average_current_ovr=(
                    round(
                        sum(int(player.current_ovr or 0) for player in ovr_players)
                        / len(ovr_players),
                        2,
                    )
                    if ovr_players
                    else None
                ),
                top_player_id=top.player_id if top is not None else None,
                top_player_name=top.name if top is not None else None,
                top_player_current_ovr=top.current_ovr if top is not None else None,
            )
        )

    ordered = tuple(sorted(countries, key=lambda country: country.country_code))
    return ViewerCountries(
        product_run_id=players.product_run_id,
        viewer_branch_id=players.viewer_branch_id,
        season_index=players.season_index,
        week=players.week,
        country_count=len(ordered),
        countries=ordered,
    )
