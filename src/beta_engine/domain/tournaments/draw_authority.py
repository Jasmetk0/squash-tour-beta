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
    section_id: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
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

    schema_version: Literal[
        "tournament_draw_authority.v1",
        "tournament_draw_authority.v2",
    ] = "tournament_draw_authority.v1"
    algorithm_version: Literal["protected_seed_shuffle.v1"] = (
        "protected_seed_shuffle.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification: TournamentDrawBracket | None = None
    qualification_sections: tuple[TournamentDrawBracket, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )
    main: TournamentDrawBracket

    @model_validator(mode="after")
    def validate_scope(self) -> "TournamentDrawAuthority":
        if self.main.draw_type != "main":
            raise ValueError("Tournament Main bracket has wrong draw type")
        if self.qualification is not None and self.qualification.draw_type != "qualification":
            raise ValueError("Tournament Qualification bracket has wrong draw type")
        if any(section.draw_type != "qualification" for section in self.qualification_sections):
            raise ValueError("Tournament Qualification section has wrong draw type")
        if self.schema_version == "tournament_draw_authority.v1":
            if self.qualification_sections:
                raise ValueError("Historical Draw authority v1 cannot contain Qualification sections")
        else:
            if self.qualification is not None:
                raise ValueError("Draw authority v2 uses Qualification sections, not the v1 bracket")
            expected_section_ids = tuple(
                f"Q{index}" for index in range(1, len(self.qualification_sections) + 1)
            )
            actual_section_ids = tuple(section.section_id for section in self.qualification_sections)
            if actual_section_ids != expected_section_ids:
                raise ValueError("Qualification section identities must be canonical Q1..Qn")
        return self

    @property
    def qualification_brackets(self) -> tuple[TournamentDrawBracket, ...]:
        if self.qualification_sections:
            return self.qualification_sections
        return (self.qualification,) if self.qualification is not None else ()

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
        if capacity.qualification_draw_size == 0 and capacity.qualifier_spots != 0:
            raise ValueError(
                "Qualification slots require a non-empty Qualification Draw"
            )
        if capacity.qualification_draw_size > 0 and capacity.qualifier_spots <= 0:
            raise ValueError(
                "Qualification Draw requires at least one qualifier spot"
            )
        if capacity.qualification_draw_size == 1:
            raise ValueError(
                "One-position Qualification Draw requires an explicit auto-qualification policy"
            )
        if capacity.qualifier_spots > 0:
            if capacity.qualification_draw_size % capacity.qualifier_spots:
                raise ValueError(
                    "Qualification field must split evenly across equal Q sections"
                )
            qualification_section_size = (
                capacity.qualification_draw_size // capacity.qualifier_spots
            )
            if qualification_section_size < 2 or not _is_power_of_two(
                qualification_section_size
            ):
                raise ValueError(
                    "Each canonical Qualification section must be a complete binary bracket"
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
        qualification_sections: tuple[TournamentDrawBracket, ...] = ()
        if capacity.qualification_draw_size:
            if capacity.qualifier_spots == 1:
                qualification = cls._build_bracket(
                    draw_input=draw_input,
                    draw_type="qualification",
                    bracket_size=capacity.qualification_draw_size,
                    player_ids=draw_input.qualification_player_ids,
                    seed_player_ids=draw_input.qualification_seed_player_ids,
                    placeholder_ids=(),
                    explicit_byes=0,
                )
            else:
                qualification_sections = cls._build_qualification_sections(
                    draw_input=draw_input,
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
            schema_version=(
                "tournament_draw_authority.v2"
                if qualification_sections
                else "tournament_draw_authority.v1"
            ),
            run_id=draw_input.run_id,
            branch_id=draw_input.branch_id,
            event_id=draw_input.event_id,
            generated_by_command_id=command_id,
            draw_input_fingerprint=draw_input.fingerprint,
            qualification=qualification,
            qualification_sections=qualification_sections,
            main=main,
        )

    @classmethod
    def _build_qualification_sections(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
    ) -> tuple[TournamentDrawBracket, ...]:
        capacity = draw_input.capacity
        section_count = capacity.qualifier_spots
        section_size = capacity.qualification_draw_size // section_count
        seeds_per_section = min(section_size, max(1, section_size // 4))
        expected_seed_count = section_count * seeds_per_section
        if draw_input.qualification_seed_count != expected_seed_count:
            raise ValueError(
                "Qualification seed count must match the Master seed formula for all Q sections"
            )

        global_seeds = draw_input.qualification_seed_player_ids
        section_seeds: list[list[tuple[int, str]]] = [
            [] for _ in range(section_count)
        ]
        for layer in range(seeds_per_section):
            layer_players = list(
                global_seeds[layer * section_count : (layer + 1) * section_count]
            )
            section_order = list(range(section_count))
            if layer > 0:
                rng = DeterministicRng(
                    _draw_named_subseed(
                        draw_seed=draw_input.draw_seed,
                        event_id=draw_input.event_id,
                        key=f"qualification:seed-layer:{layer + 1}",
                    )
                )
                rng.shuffle(section_order)
            for offset, (player_id, section_index) in enumerate(
                zip(layer_players, section_order, strict=True)
            ):
                global_seed_number = layer * section_count + offset + 1
                section_seeds[section_index].append(
                    (global_seed_number, player_id)
                )

        unseeded = list(
            draw_input.qualification_player_ids[draw_input.qualification_seed_count :]
        )
        unseeded_rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                key="qualification:unseeded-distribution",
            )
        )
        unseeded_rng.shuffle(unseeded)

        unseeded_per_section = section_size - seeds_per_section
        sections = []
        cursor = 0
        for section_index in range(section_count):
            section_id = f"Q{section_index + 1}"
            extras = unseeded[cursor : cursor + unseeded_per_section]
            cursor += unseeded_per_section
            seed_pairs = tuple(section_seeds[section_index])
            seeds = tuple(player_id for _, player_id in seed_pairs)
            seed_numbers = tuple(number for number, _ in seed_pairs)
            sections.append(
                cls._build_bracket(
                    draw_input=draw_input,
                    draw_type="qualification",
                    bracket_size=section_size,
                    player_ids=(*seeds, *extras),
                    seed_player_ids=seeds,
                    seed_numbers=seed_numbers,
                    placeholder_ids=(),
                    explicit_byes=0,
                    section_id=section_id,
                    section_ordinal=section_index,
                    section_count=section_count,
                )
            )
        if cursor != len(unseeded):
            raise ValueError(
                "Qualification player distribution did not fill all Q sections exactly"
            )
        return tuple(sections)

    @classmethod
    def _build_bracket(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        draw_type: TournamentDrawType,
        bracket_size: int,
        player_ids: tuple[str, ...],
        seed_player_ids: tuple[str, ...],
        seed_numbers: tuple[int, ...] | None = None,
        placeholder_ids: tuple[str, ...],
        explicit_byes: int,
        section_id: str | None = None,
        section_ordinal: int = 0,
        section_count: int = 1,
    ) -> TournamentDrawBracket:
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Tournament draw contains duplicate player identities")
        if tuple(player_ids[: len(seed_player_ids)]) != seed_player_ids:
            raise ValueError(
                "Tournament draw seeds must follow the frozen ranking-derived field order"
            )

        local_seed_positions = _seed_positions(
            bracket_size, len(seed_player_ids)
        )
        effective_seed_numbers = (
            seed_numbers
            if seed_numbers is not None
            else tuple(range(1, len(seed_player_ids) + 1))
        )
        if len(effective_seed_numbers) != len(seed_player_ids):
            raise ValueError("Tournament draw seed identity count differs from seed players")
        if len(set(effective_seed_numbers)) != len(effective_seed_numbers):
            raise ValueError("Tournament draw seed identities must be unique")

        seed_positions: dict[int, int] = {}
        slots: dict[int, TournamentDrawSlot | None] = {
            index: None for index in range(1, bracket_size + 1)
        }
        for local_seed_number, (seed_number, player_id) in enumerate(
            zip(effective_seed_numbers, seed_player_ids, strict=True),
            start=1,
        ):
            position = local_seed_positions[local_seed_number]
            seed_positions[seed_number] = position
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
                draw_type=(
                    draw_type if section_id is None else f"{draw_type}:{section_id}"
                ),
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
            section_id=section_id,
            bracket_size=bracket_size,
            seed_positions=tuple(sorted(seed_positions.items())),
            slots=typed_slots,
            nodes=_build_nodes(
                draw_input.event_id,
                draw_type,
                bracket_size,
                section_id=section_id,
                section_ordinal=section_ordinal,
                section_count=section_count,
            ),
            bye_slot_indexes=tuple(
                slot.slot_index for slot in typed_slots if slot.entrant_kind == "bye"
            ),
            qualifier_placeholder_slots=qualifier_slots,
        )


def _draw_subseed(
    *, draw_seed: int, event_id: str, draw_type: str
) -> int:
    material = (
        f"tournament_draw_authority.v1|{draw_seed}|{event_id}|{draw_type}"
    ).encode()
    return int.from_bytes(
        hashlib.blake2b(material, digest_size=16).digest(),
        byteorder="big",
        signed=False,
    )


def _draw_named_subseed(*, draw_seed: int, event_id: str, key: str) -> int:
    return _draw_subseed(draw_seed=draw_seed, event_id=event_id, draw_type=key)


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
    *,
    section_id: str | None = None,
    section_ordinal: int = 0,
    section_count: int = 1,
) -> tuple[TournamentDrawNode, ...]:
    prior_sources = [f"slot:{index}" for index in range(1, bracket_size + 1)]
    nodes: list[TournamentDrawNode] = []
    rounds = bracket_size.bit_length() - 1
    for round_number in range(1, rounds + 1):
        current_sources: list[str] = []
        node_count = bracket_size // (2**round_number)
        for local_sequence in range(1, node_count + 1):
            sequence = section_ordinal * node_count + local_sequence
            scope = draw_type if section_id is None else f"{draw_type}:{section_id}"
            node_id = f"{event_id}:{scope}:R{round_number}-N{local_sequence}"
            nodes.append(
                TournamentDrawNode(
                    node_id=node_id,
                    round_number=round_number,
                    round_sequence=sequence,
                    source_top=prior_sources[(local_sequence - 1) * 2],
                    source_bottom=prior_sources[(local_sequence - 1) * 2 + 1],
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