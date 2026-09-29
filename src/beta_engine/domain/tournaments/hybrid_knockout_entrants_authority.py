"""Immutable hybrid knockout entrants resolved only from final group positions."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.format_authority import TournamentGroupCrossingSource
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsAuthority,
)
from beta_engine.domain.tournaments.topology_authority import TournamentTopologyAuthority


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridKnockoutMatchEntrants(FrozenInput):
    match_id: str = Field(min_length=1)
    match_index: int = Field(ge=1, le=64)
    top_source: TournamentGroupCrossingSource
    top_player_id: str = Field(min_length=1)
    bottom_source: TournamentGroupCrossingSource
    bottom_player_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_match(self) -> "TournamentHybridKnockoutMatchEntrants":
        if self.top_source == self.bottom_source:
            raise ValueError("Hybrid knockout match cannot reuse one group-position source")
        if self.top_player_id == self.bottom_player_id:
            raise ValueError("Hybrid knockout match cannot pair one player with itself")
        return self


class TournamentHybridKnockoutEntrantsAuthority(FrozenInput):
    """Frozen first-round hybrid field; never re-seeded from Ranking/Race."""

    schema_version: Literal["tournament_hybrid_knockout_entrants_authority.v1"] = (
        "tournament_hybrid_knockout_entrants_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    topology_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_standings_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_policy_id: Literal["configured_group_crossings_no_reseed.v1"] = (
        "configured_group_crossings_no_reseed.v1"
    )
    first_round_matches: tuple[TournamentHybridKnockoutMatchEntrants, ...] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_authority(self) -> "TournamentHybridKnockoutEntrantsAuthority":
        indexes = tuple(match.match_index for match in self.first_round_matches)
        if indexes != tuple(range(1, len(indexes) + 1)):
            raise ValueError("Hybrid knockout match indexes must be contiguous from one")
        sources = [
            (source.group_index, source.finishing_position)
            for match in self.first_round_matches
            for source in (match.top_source, match.bottom_source)
        ]
        if len(sources) != len(set(sources)):
            raise ValueError("Hybrid knockout entrants cannot reuse a group position")
        players = [
            player_id
            for match in self.first_round_matches
            for player_id in (match.top_player_id, match.bottom_player_id)
        ]
        if len(players) != len(set(players)):
            raise ValueError("Hybrid knockout entrants cannot reuse a player")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentHybridKnockoutEntrantsBuilder:
    @staticmethod
    def build(
        *,
        topology: TournamentTopologyAuthority,
        standings: TournamentGroupStandingsAuthority,
        command_id: str,
    ) -> TournamentHybridKnockoutEntrantsAuthority:
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Hybrid Knockout Entrants requires a valid command ID")
        if topology.format_kind != "groups_knockout":
            raise ValueError("Hybrid Knockout Entrants requires groups+knockout topology")
        if not topology.hybrid_first_round_crossings:
            raise ValueError("Hybrid Knockout Entrants requires configured crossings")
        if (
            standings.run_id,
            standings.branch_id,
            standings.event_id,
        ) != (
            topology.run_id,
            topology.branch_id,
            topology.event_id,
        ):
            raise ValueError("Hybrid entrants standings/topology scope mismatch")

        by_position = {
            (group.group_index, row.position): row.player_id
            for group in standings.groups
            for row in group.rows
        }
        matches = []
        for crossing in sorted(
            topology.hybrid_first_round_crossings,
            key=lambda value: value.match_index,
        ):
            top_key = (
                crossing.top.group_index,
                crossing.top.finishing_position,
            )
            bottom_key = (
                crossing.bottom.group_index,
                crossing.bottom.finishing_position,
            )
            try:
                top_player = by_position[top_key]
                bottom_player = by_position[bottom_key]
            except KeyError as exc:
                raise ValueError(
                    "Hybrid crossing references a missing final group position"
                ) from exc
            matches.append(
                TournamentHybridKnockoutMatchEntrants(
                    match_id=(
                        f"{topology.event_id}:hybrid:knockout:first:"
                        f"M{crossing.match_index}"
                    ),
                    match_index=crossing.match_index,
                    top_source=crossing.top,
                    top_player_id=top_player,
                    bottom_source=crossing.bottom,
                    bottom_player_id=bottom_player,
                )
            )

        return TournamentHybridKnockoutEntrantsAuthority(
            run_id=topology.run_id,
            branch_id=topology.branch_id,
            event_id=topology.event_id,
            generated_by_command_id=command_id,
            topology_authority_fingerprint=topology.fingerprint,
            group_standings_authority_fingerprint=standings.fingerprint,
            first_round_matches=tuple(matches),
        )
