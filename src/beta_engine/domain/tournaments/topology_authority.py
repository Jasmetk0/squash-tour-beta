"""Immutable tournament topology derived from Format + Entry authorities."""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.entry_field import TournamentEntryField
from beta_engine.domain.tournaments.format_authority import (
    TournamentFormatAuthority,
    TournamentGroupCrossingMatch,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentGroupTopologySlot(FrozenInput):
    group_index: int = Field(ge=1, le=64)
    slot_index: int = Field(ge=1, le=128)
    player_id: str = Field(min_length=1)
    seed_number: int | None = Field(default=None, ge=1, le=128)


class TournamentGroupTopologyMatch(FrozenInput):
    """One round-robin pairing; chronology is intentionally not implied."""

    match_id: str = Field(min_length=1)
    group_index: int = Field(ge=1, le=64)
    match_index: int = Field(ge=1)
    top_slot_index: int = Field(ge=1)
    bottom_slot_index: int = Field(ge=1)
    top_player_id: str = Field(min_length=1)
    bottom_player_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_pair(self) -> "TournamentGroupTopologyMatch":
        if self.top_slot_index >= self.bottom_slot_index:
            raise ValueError(
                "Group topology match slots must use canonical ascending pair order"
            )
        if self.top_player_id == self.bottom_player_id:
            raise ValueError("Group topology match cannot pair one player with itself")
        return self


class TournamentTopologyAuthority(FrozenInput):
    """Immutable structural topology for one configured Tournament Edition.

    For classic knockout this is a provenance wrapper over the existing canonical
    Draw authority. For group-based formats it owns immutable group assignment and
    round-robin pairing topology; hybrid knockout entrants remain group-position
    sources until group results resolve them.
    """

    schema_version: Literal["tournament_topology_authority.v1"] = (
        "tournament_topology_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    format_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    format_kind: Literal["knockout", "groups", "groups_knockout"]
    topology_seed: int | None = None
    participant_order_player_ids: tuple[str, ...] = ()
    group_slots: tuple[TournamentGroupTopologySlot, ...] = ()
    group_matches: tuple[TournamentGroupTopologyMatch, ...] = ()
    knockout_draw_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    hybrid_first_round_crossings: tuple[TournamentGroupCrossingMatch, ...] = ()

    @model_validator(mode="after")
    def validate_topology(self) -> "TournamentTopologyAuthority":
        if len(self.participant_order_player_ids) != len(
            set(self.participant_order_player_ids)
        ):
            raise ValueError("Tournament topology participant order contains duplicates")

        if self.format_kind == "knockout":
            if self.knockout_draw_fingerprint is None:
                raise ValueError(
                    "Knockout topology requires canonical Draw authority fingerprint"
                )
            if (
                self.topology_seed is not None
                or self.group_slots
                or self.group_matches
                or self.hybrid_first_round_crossings
            ):
                raise ValueError(
                    "Knockout topology cannot carry group topology payload"
                )
            return self

        if self.knockout_draw_fingerprint is not None:
            raise ValueError(
                "Group topology cannot pretend an unresolved group-dependent knockout is already drawn"
            )
        if self.topology_seed is None:
            raise ValueError("Group topology requires frozen deterministic topology seed")
        if not self.group_slots or not self.group_matches:
            raise ValueError("Group topology requires slots and round-robin pairings")
        slot_players = tuple(slot.player_id for slot in self.group_slots)
        if set(slot_players) != set(self.participant_order_player_ids):
            raise ValueError(
                "Group topology slots must contain the complete participant field exactly once"
            )
        if len(slot_players) != len(set(slot_players)):
            raise ValueError("Group topology cannot place one player twice")
        if self.format_kind == "groups" and self.hybrid_first_round_crossings:
            raise ValueError("Groups-only topology cannot carry knockout crossings")
        if self.format_kind == "groups_knockout" and not self.hybrid_first_round_crossings:
            raise ValueError("Hybrid topology requires explicit first-round crossings")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentTopologyAuthorityBuilder:
    """Build topology only from frozen Format/Entry and resolved participant order."""

    @staticmethod
    def build_knockout_reference(
        *,
        format_authority: TournamentFormatAuthority,
        entry_field: TournamentEntryField,
        draw_fingerprint: str,
        command_id: str,
        participant_order_player_ids: tuple[str, ...],
    ) -> TournamentTopologyAuthority:
        if format_authority.format_kind != "knockout":
            raise ValueError("Knockout topology requires knockout Format authority")
        TournamentTopologyAuthorityBuilder._validate_scope_and_field(
            format_authority=format_authority,
            entry_field=entry_field,
        )
        return TournamentTopologyAuthority(
            run_id=format_authority.run_id,
            branch_id=format_authority.branch_id,
            event_id=format_authority.event_id,
            generated_by_command_id=command_id,
            format_authority_fingerprint=format_authority.fingerprint,
            entry_field_fingerprint=entry_field.fingerprint,
            format_kind="knockout",
            participant_order_player_ids=participant_order_player_ids,
            knockout_draw_fingerprint=draw_fingerprint,
        )

    @staticmethod
    def build_groups(
        *,
        format_authority: TournamentFormatAuthority,
        entry_field: TournamentEntryField,
        participant_order_player_ids: tuple[str, ...],
        command_id: str,
        topology_seed: int,
    ) -> TournamentTopologyAuthority:
        if format_authority.format_kind not in {"groups", "groups_knockout"}:
            raise ValueError("Group topology requires group-based Format authority")
        TournamentTopologyAuthorityBuilder._validate_scope_and_field(
            format_authority=format_authority,
            entry_field=entry_field,
        )
        group = format_authority.group_configuration
        assert group is not None

        if len(participant_order_player_ids) != group.participant_capacity:
            raise ValueError(
                "Group topology participant count must exactly fill equal configured groups"
            )
        if len(participant_order_player_ids) != len(
            set(participant_order_player_ids)
        ):
            raise ValueError("Group topology participant order contains duplicates")

        active_players = TournamentTopologyAuthorityBuilder._active_group_players(
            entry_field
        )
        if set(participant_order_player_ids) != set(active_players):
            raise ValueError(
                "Group topology participant order differs from active Entry Field"
            )

        slots: dict[tuple[int, int], TournamentGroupTopologySlot] = {}
        seeded_count = group.group_count * group.seeded_slots_per_group
        for placement in group.group_seed_placements:
            player_id = participant_order_player_ids[placement.seed_number - 1]
            key = (placement.group_index, placement.slot_index)
            slots[key] = TournamentGroupTopologySlot(
                group_index=placement.group_index,
                slot_index=placement.slot_index,
                player_id=player_id,
                seed_number=placement.seed_number,
            )

        unseeded_players = list(participant_order_player_ids[seeded_count:])
        rng = DeterministicRng(
            TournamentTopologyAuthorityBuilder._subseed(
                topology_seed=topology_seed,
                event_id=format_authority.event_id,
                key="groups:unseeded",
            )
        )
        rng.shuffle(unseeded_players)

        open_slots = [
            (group_index, slot_index)
            for group_index in range(1, group.group_count + 1)
            for slot_index in range(1, group.group_size + 1)
            if (group_index, slot_index) not in slots
        ]
        if len(open_slots) != len(unseeded_players):
            raise ValueError("Group topology open-slot count differs from unseeded field")
        for key, player_id in zip(open_slots, unseeded_players, strict=True):
            slots[key] = TournamentGroupTopologySlot(
                group_index=key[0],
                slot_index=key[1],
                player_id=player_id,
            )

        ordered_slots = tuple(
            slots[(group_index, slot_index)]
            for group_index in range(1, group.group_count + 1)
            for slot_index in range(1, group.group_size + 1)
        )
        matches: list[TournamentGroupTopologyMatch] = []
        for group_index in range(1, group.group_count + 1):
            group_slots = [
                slots[(group_index, slot_index)]
                for slot_index in range(1, group.group_size + 1)
            ]
            for match_index, (top, bottom) in enumerate(
                combinations(group_slots, 2),
                start=1,
            ):
                matches.append(
                    TournamentGroupTopologyMatch(
                        match_id=(
                            f"{format_authority.event_id}:group:{group_index}:"
                            f"M{match_index}"
                        ),
                        group_index=group_index,
                        match_index=match_index,
                        top_slot_index=top.slot_index,
                        bottom_slot_index=bottom.slot_index,
                        top_player_id=top.player_id,
                        bottom_player_id=bottom.player_id,
                    )
                )

        return TournamentTopologyAuthority(
            run_id=format_authority.run_id,
            branch_id=format_authority.branch_id,
            event_id=format_authority.event_id,
            generated_by_command_id=command_id,
            format_authority_fingerprint=format_authority.fingerprint,
            entry_field_fingerprint=entry_field.fingerprint,
            format_kind=format_authority.format_kind,
            topology_seed=topology_seed,
            participant_order_player_ids=participant_order_player_ids,
            group_slots=ordered_slots,
            group_matches=tuple(matches),
            hybrid_first_round_crossings=(
                group.knockout_crossings
                if format_authority.format_kind == "groups_knockout"
                else ()
            ),
        )

    @staticmethod
    def _active_group_players(
        entry_field: TournamentEntryField,
    ) -> tuple[str, ...]:
        if (
            entry_field.qualification_player_ids
            or entry_field.capacity.qualifier_spots
            or entry_field.capacity.wild_card_slots
            or entry_field.capacity.bye_slots
        ):
            raise ValueError(
                "Group topology currently requires one fully resolved participant field without Qualification/WC/BYE reservations"
            )
        return entry_field.direct_main_player_ids

    @staticmethod
    def _validate_scope_and_field(
        *,
        format_authority: TournamentFormatAuthority,
        entry_field: TournamentEntryField,
    ) -> None:
        if (
            entry_field.run_id,
            entry_field.branch_id,
            entry_field.event_id,
            entry_field.fingerprint,
        ) != (
            format_authority.run_id,
            format_authority.branch_id,
            format_authority.event_id,
            format_authority.entry_field_fingerprint,
        ):
            raise ValueError(
                "Tournament Format authority is stale for current Entry Field"
            )

    @staticmethod
    def _subseed(*, topology_seed: int, event_id: str, key: str) -> int:
        material = (
            f"tournament_topology_authority.v1|{topology_seed}|{event_id}|{key}"
        ).encode()
        return int.from_bytes(
            hashlib.blake2b(material, digest_size=16).digest(),
            byteorder="big",
            signed=False,
        )
