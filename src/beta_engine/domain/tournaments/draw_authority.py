"""Immutable Run/Branch-owned canonical tournament bracket authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)


TournamentDrawType = Literal["qualification", "main"]
TournamentDrawEntrantKind = Literal["player", "qualifier_placeholder", "bye"]


class TournamentDrawSlot(FrozenInput):
    """One immutable first-round bracket position."""

    slot_index: int = Field(ge=1)
    entrant_kind: TournamentDrawEntrantKind
    player_id: str | None = None
    placeholder_id: str | None = None
    seed_number: int | None = Field(default=None, ge=1)
    is_seed_protected: bool = False

    @model_validator(mode="after")
    def validate_identity(self) -> "TournamentDrawSlot":
        if self.entrant_kind == "player":
            if not self.player_id or self.placeholder_id is not None:
                raise ValueError("Player draw slot requires exactly one player identity")
        elif self.entrant_kind == "qualifier_placeholder":
            if not self.placeholder_id or self.player_id is not None:
                raise ValueError(
                    "Qualifier-placeholder draw slot requires exactly one placeholder identity"
                )
            if self.seed_number is not None or self.is_seed_protected:
                raise ValueError("Qualifier placeholder cannot be seeded")
        else:
            if self.player_id is not None or self.placeholder_id is not None:
                raise ValueError("BYE draw slot cannot carry an entrant identity")
            if self.seed_number is not None or self.is_seed_protected:
                raise ValueError("BYE draw slot cannot be seeded")
        if self.seed_number is not None and not self.is_seed_protected:
            raise ValueError("Seed number requires protected seed placement")
        if self.is_seed_protected and self.seed_number is None:
            raise ValueError("Protected seed placement requires seed number")
        return self


class TournamentDrawNode(FrozenInput):
    """One immutable bracket match node and its deterministic feeder sources."""

    node_id: str = Field(min_length=1)
    round_number: int = Field(ge=1)
    round_sequence: int = Field(ge=1)
    source_top: str = Field(min_length=1)
    source_bottom: str = Field(min_length=1)


class TournamentDrawBracket(FrozenInput):
    """One complete binary bracket generated from committed draw inputs."""

    draw_type: TournamentDrawType
    bracket_size: int = Field(ge=2)
    seed_positions: tuple[tuple[int, int], ...]
    slots: tuple[TournamentDrawSlot, ...]
    nodes: tuple[TournamentDrawNode, ...]
    bye_slot_indexes: tuple[int, ...] = ()
    qualifier_placeholder_slots: tuple[tuple[str, int], ...] = ()

    @model_validator(mode="after")
    def validate_bracket(self) -> "TournamentDrawBracket":
        if not _is_power_of_two(self.bracket_size):
            raise ValueError("Tournament bracket size must be a power of two")
        if tuple(slot.slot_index for slot in self.slots) != tuple(
            range(1, self.bracket_size + 1)
        ):
            raise ValueError("Tournament draw slots must be canonical and contiguous")
        if len(self.nodes) != self.bracket_size - 1:
            raise ValueError("Tournament draw node count does not form a complete bracket")

        expected_seed_positions = tuple(
            (slot.seed_number, slot.slot_index)
            for slot in self.slots
            if slot.seed_number is not None
        )
        if tuple(sorted(expected_seed_positions)) != tuple(sorted(self.seed_positions)):
            raise ValueError("Tournament draw seed positions differ from slot payload")

        expected_byes = tuple(
            slot.slot_index for slot in self.slots if slot.entrant_kind == "bye"
        )
        if self.bye_slot_indexes != expected_byes:
            raise ValueError("Tournament draw BYE indexes differ from slot payload")

        expected_placeholders = tuple(
            (slot.placeholder_id, slot.slot_index)
            for slot in self.slots
            if slot.entrant_kind == "qualifier_placeholder"
            and slot.placeholder_id is not None
        )
        if self.qualifier_placeholder_slots != expected_placeholders:
            raise ValueError(
                "Tournament draw qualifier placeholders differ from slot payload"
            )

        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Tournament draw node identities must be unique")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentDrawAuthority(FrozenInput):
    """Immutable canonical bracket package owned by one Run/Branch/Event."""

    schema_version: Literal["tournament_draw_authority.v1"] = (
        "tournament_draw_authority.v1"
    )
    algorithm_version: Literal["protected_seed_shuffle.v1"] = (
        "protected_seed_shuffle.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification: TournamentDrawBracket | None = None
    main: TournamentDrawBracket

    @model_validator(mode="after")
    def validate_scope(self) -> "TournamentDrawAuthority":
        if self.main.draw_type != "main":
            raise ValueError("Tournament Main bracket has wrong draw type")
        if self.qualification is not None and self.qualification.draw_type != "qualification":
            raise ValueError("Tournament Qualification bracket has wrong draw type")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentDrawAuthorityBuilder:
    """Generate replayable brackets only from immutable Draw Input authority."""

    @classmethod
    def build(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        command_id: str,
    ) -> TournamentDrawAuthority:
        capacity = draw_input.capacity
        if capacity.wild_card_slots:
            raise ValueError(
                "Tournament Draw authority requires Wild Card resolution before generation"
            )
        if capacity.main_draw_size < 2 or not _is_power_of_two(capacity.main_draw_size):
            raise ValueError(
                "Canonical Run-owned Main Draw currently supports complete binary brackets"
            )
        if capacity.qualification_draw_size not in (0, 1) and not _is_power_of_two(
            capacity.qualification_draw_size
        ):
            raise ValueError(
                "Canonical Run-owned Qualification Draw currently supports complete binary brackets"
            )
        if capacity.qualification_draw_size == 1:
            raise ValueError(
                "One-position Qualification Draw requires an explicit auto-qualification policy"
            )

        expected_main_occupants = (
            len(draw_input.direct_main_player_ids)
            + len(draw_input.qualifier_placeholder_ids)
            + capacity.bye_slots
        )
        if expected_main_occupants != capacity.main_draw_size:
            raise ValueError(
                "Canonical Run-owned Main Draw requires a fully resolved field including explicit BYEs"
            )
        if len(draw_input.qualification_player_ids) != capacity.qualification_draw_size:
            raise ValueError(
                "Canonical Run-owned Qualification Draw requires a fully resolved field"
            )

        qualification = None
        if capacity.qualification_draw_size:
            qualification = cls._build_bracket(
                draw_input=draw_input,
                draw_type="qualification",
                bracket_size=capacity.qualification_draw_size,
                player_ids=draw_input.qualification_player_ids,
                seed_player_ids=draw_input.qualification_seed_player_ids,
                placeholder_ids=(),
                explicit_byes=0,
            )

        main = cls._build_bracket(
            draw_input=draw_input,
            draw_type="main",
            bracket_size=capacity.main_draw_size,
            player_ids=draw_input.direct_main_player_ids,
            seed_player_ids=draw_input.main_seed_player_ids,
            placeholder_ids=draw_input.qualifier_placeholder_ids,
            explicit_byes=capacity.bye_slots,
        )
        return TournamentDrawAuthority(
            run_id=draw_input.run_id,
            branch_id=draw_input.branch_id,
            event_id=draw_input.event_id,
            generated_by_command_id=command_id,
            draw_input_fingerprint=draw_input.fingerprint,
            qualification=qualification,
            main=main,
        )

    @classmethod
    def _build_bracket(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        draw_type: TournamentDrawType,
        bracket_size: int,
        player_ids: tuple[str, ...],
        seed_player_ids: tuple[str, ...],
        placeholder_ids: tuple[str, ...],
        explicit_byes: int,
    ) -> TournamentDrawBracket:
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Tournament draw contains duplicate player identities")
        if tuple(player_ids[: len(seed_player_ids)]) != seed_player_ids:
            raise ValueError(
                "Tournament draw seeds must follow the frozen ranking-derived field order"
            )

        seed_positions = _seed_positions(bracket_size, len(seed_player_ids))
        slots: dict[int, TournamentDrawSlot | None] = {
            index: None for index in range(1, bracket_size + 1)
        }
        for seed_number, player_id in enumerate(seed_player_ids, start=1):
            position = seed_positions[seed_number]
            slots[position] = TournamentDrawSlot(
                slot_index=position,
                entrant_kind="player",
                player_id=player_id,
                seed_number=seed_number,
                is_seed_protected=True,
            )

        bye_positions = _choose_bye_positions(
            bracket_size=bracket_size,
            explicit_byes=explicit_byes,
            seed_positions=seed_positions,
            occupied_positions={index for index, slot in slots.items() if slot is not None},
        )
        for position in bye_positions:
            slots[position] = TournamentDrawSlot(
                slot_index=position,
                entrant_kind="bye",
            )

        open_positions = [
            index for index in range(1, bracket_size + 1) if slots[index] is None
        ]
        rng = DeterministicRng(
            _draw_subseed(
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                draw_type=draw_type,
            )
        )
        rng.shuffle(open_positions)

        remaining_players = player_ids[len(seed_player_ids) :]
        entrants: tuple[tuple[str, str], ...] = tuple(
            ("player", player_id) for player_id in remaining_players
        ) + tuple(("qualifier_placeholder", value) for value in placeholder_ids)
        if len(entrants) != len(open_positions):
            raise ValueError(
                "Tournament draw entrant count differs from available bracket positions"
            )

        for position, (kind, identity) in zip(open_positions, entrants, strict=True):
            if kind == "player":
                slots[position] = TournamentDrawSlot(
                    slot_index=position,
                    entrant_kind="player",
                    player_id=identity,
                )
            else:
                slots[position] = TournamentDrawSlot(
                    slot_index=position,
                    entrant_kind="qualifier_placeholder",
                    placeholder_id=identity,
                )

        final_slots = tuple(slots[index] for index in range(1, bracket_size + 1))
        if any(slot is None for slot in final_slots):
            raise ValueError("Tournament draw generation left unresolved bracket slots")
        typed_slots = tuple(slot for slot in final_slots if slot is not None)
        qualifier_slots = tuple(
            (slot.placeholder_id, slot.slot_index)
            for slot in typed_slots
            if slot.entrant_kind == "qualifier_placeholder"
            and slot.placeholder_id is not None
        )
        return TournamentDrawBracket(
            draw_type=draw_type,
            bracket_size=bracket_size,
            seed_positions=tuple(sorted(seed_positions.items())),
            slots=typed_slots,
            nodes=_build_nodes(draw_input.event_id, draw_type, bracket_size),
            bye_slot_indexes=tuple(
                slot.slot_index for slot in typed_slots if slot.entrant_kind == "bye"
            ),
            qualifier_placeholder_slots=qualifier_slots,
        )


def _draw_subseed(
    *, draw_seed: int, event_id: str, draw_type: TournamentDrawType
) -> int:
    material = (
        f"tournament_draw_authority.v1|{draw_seed}|{event_id}|{draw_type}"
    ).encode()
    return int.from_bytes(
        hashlib.blake2b(material, digest_size=16).digest(),
        byteorder="big",
        signed=False,
    )


def _is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def _paired_slot(slot_index: int) -> int:
    return slot_index + 1 if slot_index % 2 else slot_index - 1


def _choose_bye_positions(
    *,
    bracket_size: int,
    explicit_byes: int,
    seed_positions: dict[int, int],
    occupied_positions: set[int],
) -> tuple[int, ...]:
    if explicit_byes < 0:
        raise ValueError("Tournament draw BYE count cannot be negative")
    bye_positions: list[int] = []
    for seed_number in sorted(seed_positions):
        if len(bye_positions) >= explicit_byes:
            break
        opponent = _paired_slot(seed_positions[seed_number])
        if opponent not in occupied_positions and opponent not in bye_positions:
            bye_positions.append(opponent)
    for position in range(1, bracket_size + 1):
        if len(bye_positions) >= explicit_byes:
            break
        if position not in occupied_positions and position not in bye_positions:
            bye_positions.append(position)
    if len(bye_positions) != explicit_byes:
        raise ValueError("Tournament draw cannot place all explicit BYEs")
    return tuple(sorted(bye_positions))


def _seed_positions(bracket_size: int, seeds_count: int) -> dict[int, int]:
    if seeds_count < 0 or seeds_count > bracket_size:
        raise ValueError("Tournament draw seed count exceeds bracket size")
    if not seeds_count:
        return {}
    placement_order = _seed_placement_order(bracket_size)
    return {
        seed_number: placement_order[seed_number - 1]
        for seed_number in range(1, seeds_count + 1)
    }


def _seed_placement_order(bracket_size: int) -> tuple[int, ...]:
    if bracket_size < 2 or not _is_power_of_two(bracket_size):
        raise ValueError("Tournament bracket size must be a power of two >= 2")
    positions = [1, 2]
    size = 2
    while size < bracket_size:
        size *= 2
        expanded: list[int] = []
        for slot in positions:
            expanded.extend((slot, size + 1 - slot))
        positions = expanded
    return tuple(positions)


def _build_nodes(
    event_id: str,
    draw_type: TournamentDrawType,
    bracket_size: int,
) -> tuple[TournamentDrawNode, ...]:
    prior_sources = [f"slot:{index}" for index in range(1, bracket_size + 1)]
    nodes: list[TournamentDrawNode] = []
    rounds = bracket_size.bit_length() - 1
    for round_number in range(1, rounds + 1):
        current_sources: list[str] = []
        node_count = bracket_size // (2**round_number)
        for sequence in range(1, node_count + 1):
            node_id = (
                f"{event_id}:{draw_type}:R{round_number}-N{sequence}"
            )
            nodes.append(
                TournamentDrawNode(
                    node_id=node_id,
                    round_number=round_number,
                    round_sequence=sequence,
                    source_top=prior_sources[(sequence - 1) * 2],
                    source_bottom=prior_sources[(sequence - 1) * 2 + 1],
                )
            )
            current_sources.append(f"winner:{node_id}")
        prior_sources = current_sources
    return tuple(nodes)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
