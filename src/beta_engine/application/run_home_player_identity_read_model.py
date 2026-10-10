"""Strict read model for player names in a selected Branch's immutable Saved Revision.

Initial World and frozen Run Prospect source are the sole identity authorities.
This is NOT a Viewer Branch lookup, current live Run query, or historical replay.
"""

from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class HomePlayerIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    country_code: str = Field(min_length=3, max_length=3)
    identity_source: Literal["initial_world", "run_prospect"]


class HomePlayerIdentities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["run_home_player_identities.v1"] = "run_home_player_identities.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    players: tuple[HomePlayerIdentity, ...]
    unresolved_ids: tuple[str, ...]


def resolve_run_home_player_identities(
    *,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    initial_world: InitialWorldState | None,
    prospects: RunProspectSourceSnapshot | None,
    player_ids: tuple[str, ...],
) -> HomePlayerIdentities:
    if len(player_ids) > 30 or any(not item.strip() for item in player_ids):
        raise ValueError("Home player identity request requires at most 30 nonempty IDs")
    if initial_world is not None and (
        initial_world.run_id, initial_world.branch_id
    ) != (run_id, branch_id):
        raise ValueError("Saved Initial World has wrong Run / Branch scope")
    if prospects is not None and prospects.run_id != run_id:
        raise ValueError("Saved prospect source has wrong Run scope")

    by_id: dict[str, HomePlayerIdentity] = {}
    if initial_world is not None:
        for player in initial_world.players:
            if player.player_id in by_id:
                raise ValueError("Saved Initial World repeats player identity")
            by_id[player.player_id] = HomePlayerIdentity(
                player_id=player.player_id, name=player.name,
                country_code=player.country_code.strip().upper(),
                identity_source="initial_world",
            )
    if prospects is not None:
        for record in prospects.records:
            player_id = record.get("prospect_id")
            name = record.get("display_name")
            country_code = record.get("country_code")
            if (
                not isinstance(player_id, str) or not player_id or
                not isinstance(name, str) or not name.strip() or
                not isinstance(country_code, str) or len(country_code.strip()) != 3
            ):
                raise ValueError("Saved prospect source contains invalid identity")
            if player_id in by_id:
                raise ValueError("Saved Initial World and prospects overlap identities")
            by_id[player_id] = HomePlayerIdentity(
                player_id=player_id, name=name.strip(),
                country_code=country_code.strip().upper(),
                identity_source="run_prospect",
            )

    unique = tuple(dict.fromkeys(player_ids))
    return HomePlayerIdentities(
        run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id,
        players=tuple(by_id[player_id] for player_id in unique if player_id in by_id),
        unresolved_ids=tuple(player_id for player_id in unique if player_id not in by_id),
    )
