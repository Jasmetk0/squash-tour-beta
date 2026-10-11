"""Selected-Branch Saved Revision player identity, no Viewer or live roster fallback."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot


class SavedHomePlayerIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    player_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    country_code: str = Field(min_length=3, max_length=3)
    identity_source: Literal["initial_world", "run_prospect"]


class SavedHomePlayerIdentities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["run_home_player_identities.v1"] = "run_home_player_identities.v1"
    run_id: str
    branch_id: str
    saved_revision_id: str
    source: Literal["selected_branch_saved_revision"] = "selected_branch_saved_revision"
    status: Literal["unavailable", "partial", "ready"]
    requested_ids: tuple[str, ...]
    players: tuple[SavedHomePlayerIdentity, ...]
    unresolved_ids: tuple[str, ...]


def resolve_saved_home_player_identities(
    *,
    run_id: str,
    branch_id: str,
    saved_revision_id: str,
    requested_ids: tuple[str, ...],
    initial_world: InitialWorldState | None,
    prospect_source: RunProspectSourceSnapshot | None,
) -> SavedHomePlayerIdentities:
    if not 1 <= len(requested_ids) <= 25 or len(requested_ids) != len(set(requested_ids)):
        raise ValueError("Expected 1–25 distinct requested player IDs")
    if any(not item or len(item) > 128 or item.strip() != item for item in requested_ids):
        raise ValueError("Requested player IDs are malformed")
    if initial_world is not None and (initial_world.run_id, initial_world.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Initial World belongs to another Run/Branch")
    if prospect_source is not None and prospect_source.run_id != run_id:
        raise ValueError("Saved prospect source belongs to another Run")
    wanted = set(requested_ids)
    resolved: dict[str, SavedHomePlayerIdentity] = {}
    if initial_world is not None:
        for player in initial_world.players:
            if player.player_id not in wanted:
                continue
            name = player.name.strip()
            country = player.country_code.strip().upper()
            if not name or len(country) != 3:
                raise ValueError("Saved Initial World has invalid identity")
            resolved[player.player_id] = SavedHomePlayerIdentity(
                player_id=player.player_id, display_name=name, country_code=country,
                identity_source="initial_world",
            )
    if prospect_source is not None:
        for record in prospect_source.records:
            player_id = record.get("prospect_id")
            if not isinstance(player_id, str) or not player_id:
                raise ValueError("Saved prospect has invalid player identity")
            if player_id not in wanted:
                continue
            if player_id in resolved:
                raise ValueError("Saved prospect overlaps with Initial World player identity")
            name, country = record.get("display_name"), record.get("country_code")
            if not isinstance(name, str) or not name.strip() or not isinstance(country, str) or len(country.strip()) != 3:
                raise ValueError("Saved prospect has invalid display identity")
            resolved[player_id] = SavedHomePlayerIdentity(
                player_id=player_id, display_name=name.strip(),
                country_code=country.strip().upper(), identity_source="run_prospect",
            )
    players = tuple(resolved[item] for item in requested_ids if item in resolved)
    unresolved = tuple(item for item in requested_ids if item not in resolved)
    return SavedHomePlayerIdentities(
        run_id=run_id, branch_id=branch_id, saved_revision_id=saved_revision_id,
        status="ready" if not unresolved else "unavailable" if not players else "partial",
        requested_ids=requested_ids, players=players, unresolved_ids=unresolved,
    )
