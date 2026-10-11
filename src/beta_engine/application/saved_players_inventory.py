"""Canonical present-time player inventory from one immutable Branch Saved Revision.

No joins against the legacy Run player explorer, live Run prospects, the Viewer
Branch or future-only records. Pagination takes place after verified identity
deduplication and filtering. Unsupported OVR/age are explicitly unavailable.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.viewer_official_ranking_read_model import resolve_viewer_official_ranking
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class SavedInventoryPlayer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    country_code: str = Field(min_length=3, max_length=3)
    identity_source: Literal["initial_world", "run_prospect"]
    status: str | None
    age: int | None = Field(default=None, ge=0)
    ovr: int | None = Field(default=None, ge=0, le=200)
    potential_ovr: int | None = Field(default=None, ge=0, le=200)
    ranking_status: Literal["unpublished", "ranked", "unranked"]
    rank: int | None = Field(default=None, ge=1)


class SavedPlayersInventory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["saved_players_inventory.v1"] = "saved_players_inventory.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    time_context: Literal["present"] = "present"
    ranking_week_ordinal: int | None = Field(default=None, ge=0, le=3049)
    search: str
    country_code: str
    status_filter: str
    include_prepared: bool = False
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    has_more: bool
    players: tuple[SavedInventoryPlayer, ...]


def resolve_saved_players_inventory(
    *, run_id: str, branch_id: str, saved_revision_id: str,
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
    ranking: RankingRevisionState | None,
    search: str = "", country_code: str = "", status_filter: str = "",
    include_prepared: bool = False,
    offset: int = 0, limit: int = 50,
) -> SavedPlayersInventory:
    if not 0 <= offset or not 1 <= limit <= 100:
        raise ValueError("Invalid inventory page")
    if len(search) > 120 or len(status_filter) > 80 or (
        country_code and (len(country_code) != 3 or not country_code.isalpha())
    ):
        raise ValueError("Invalid inventory filters")
    if initial_world is not None and (initial_world.run_id, initial_world.branch_id) != (run_id, branch_id):
        raise ValueError("Initial World belongs to another Branch")
    if prospect_source is not None and prospect_source.run_id != run_id:
        raise ValueError("Prospect snapshot belongs to another Run")
    if ranking is not None and (ranking.run_id, ranking.branch_id) != (run_id, branch_id):
        raise ValueError("Ranking snapshot belongs to another Branch")

    # A player's 1–99 legacy abilities are NOT canonical 0–200 OVR. The
    # stored initial season age is likewise not the player's present-time age.
    # Expose neither as a guessed current value.
    players: dict[str, SavedInventoryPlayer] = {}
    ranked: dict[str, int] = {}
    week_ordinal: int | None = None
    if ranking is not None and ranking.authoritative_transition_state is not None:
        transition = ranking.authoritative_transition_state
        if transition.get("world") is not None:
            published = resolve_viewer_official_ranking(ranking)
            if (published.product_run_id, published.viewer_branch_id) != (run_id, branch_id):
                raise ValueError("Ranking publication belongs to another Branch")
            week_ordinal = published.week_ordinal
            for row in published.rows:
                if row.player_id in ranked:
                    raise ValueError("Duplicate Official Ranking player")
                ranked[row.player_id] = row.rank
        elif transition.get("publications"):
            raise ValueError("Ranking publications lack a saved public HEAD")

    def identity(*, player_id: str, name: str, country: str,
                 source: Literal["initial_world", "run_prospect"],
                 status: str | None) -> None:
        if not isinstance(player_id, str) or not player_id or len(player_id) > 128 or player_id.strip() != player_id:
            raise ValueError("Invalid Saved player identity")
        if player_id in players:
            raise ValueError("Duplicate initial-world/prospect player ID")
        if not isinstance(name, str) or not name.strip() or not isinstance(country, str) or len(country.strip()) != 3 or not country.strip().isalpha():
            raise ValueError("Saved player has an invalid display identity")
        if status is not None and (not isinstance(status, str) or not status.strip()):
            raise ValueError("Saved player status is malformed")
        players[player_id] = SavedInventoryPlayer(
            player_id=player_id, display_name=name.strip(), country_code=country.strip().upper(),
            identity_source=source, status=status,
            ranking_status="unpublished" if week_ordinal is None else
                           "ranked" if player_id in ranked else "unranked",
            rank=ranked.get(player_id) if week_ordinal is not None else None,
        )

    if initial_world is not None:
        for player in initial_world.players:
            identity(player_id=player.player_id, name=player.name, country=player.country_code,
                     source="initial_world", status=player.active_status)
    # Existing saved prospect sources can include pre-reveal/future cohorts.
    # Admin must opt in before enumerating them; default inventory is present-safe.
    if prospect_source is not None and include_prepared:
        for record in prospect_source.records:
            identity(player_id=record.get("prospect_id"), name=record.get("display_name"),
                     country=record.get("country_code"), source="run_prospect",
                     status=record.get("status"))

    needle, country, wanted_status = search.casefold().strip(), country_code.upper(), status_filter.casefold().strip()
    matching = sorted((
        item for item in players.values()
        if (not needle or needle in item.display_name.casefold() or needle in item.player_id.casefold())
        and (not country or item.country_code == country)
        and (not wanted_status or (item.status or "").casefold() == wanted_status)
    ), key=lambda item: (item.display_name.casefold(), item.player_id))
    return SavedPlayersInventory(
        run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id,
        search=search, country_code=country_code, status_filter=status_filter,
        include_prepared=include_prepared, offset=offset, limit=limit, total=len(matching),
        has_more=offset + limit < len(matching),
        ranking_week_ordinal=week_ordinal, players=tuple(matching[offset:offset + limit]),
    )
