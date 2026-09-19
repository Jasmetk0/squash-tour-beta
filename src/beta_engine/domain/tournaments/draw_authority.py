"""Immutable Run/Branch-owned canonical tournament bracket authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.bracket_diagnostics import (
    TournamentBracketDiagnostic,
    main_bracket_diagnostics,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)


TournamentDrawType = Literal["qualification", "main"]
TournamentDrawEntrantKind = Literal[
    "player",
    "qualifier_placeholder",
    "lucky_loser_placeholder",
    "bye",
]
TournamentDrawAlgorithmVersion = Literal[
    "protected_seed_shuffle.v1",
    "idealized_seed_tiers.v2",
]


class TournamentDrawSlot(FrozenInput):
    """One immutable first-round bracket position."""

    slot_index: int = Field(ge=1)
    idealized_slot_number: int | None = Field(
        default=None,
        ge=1,
        exclude_if=lambda value: value is None,
    )
    entrant_kind: TournamentDrawEntrantKind
    player_id: str | None = None
    placeholder_id: str | None = None
    seed_number: int | None = Field(default=None, ge=1)
    is_seed_protected: bool = False
    entry_status: Literal["wild_card", "lucky_loser"] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    lucky_loser_placeholder_id: str | None = Field(
        default=None,
        pattern=r"^LL[1-9][0-9]*$",
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_identity(self) -> "TournamentDrawSlot":
        if self.entrant_kind == "player":
            if not self.player_id or self.placeholder_id is not None:
                raise ValueError("Player draw slot requires exactly one player identity")
            if self.entry_status == "lucky_loser":
                if self.lucky_loser_placeholder_id is None:
                    raise ValueError("Lucky Loser player slot requires LL identity")
                if self.seed_number is not None or self.is_seed_protected:
                    raise ValueError("Lucky Loser replacement cannot inherit seed status")
            elif self.lucky_loser_placeholder_id is not None:
                raise ValueError("Only Lucky Loser player slot can carry LL identity")
        elif self.entrant_kind in {
            "qualifier_placeholder",
            "lucky_loser_placeholder",
        }:
            if not self.placeholder_id or self.player_id is not None:
                raise ValueError(
                    "Placeholder draw slot requires exactly one placeholder identity"
                )
            if self.seed_number is not None or self.is_seed_protected:
                raise ValueError("Placeholder draw slot cannot be seeded")
            if self.lucky_loser_placeholder_id is not None:
                raise ValueError("Placeholder draw slot cannot carry filled LL identity")
            if (
                self.entrant_kind == "qualifier_placeholder"
                and not self.placeholder_id.startswith("Q")
            ):
                raise ValueError("Qualifier placeholder must use Q identity")
            if (
                self.entrant_kind == "lucky_loser_placeholder"
                and not self.placeholder_id.startswith("LL")
            ):
                raise ValueError("Lucky Loser placeholder must use LL identity")
        else:
            if (
                self.player_id is not None
                or self.placeholder_id is not None
                or self.lucky_loser_placeholder_id is not None
            ):
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
    lucky_loser_placeholder_slots: tuple[tuple[str, int], ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )

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
        idealized = tuple(
            slot.idealized_slot_number
            for slot in self.slots
            if slot.idealized_slot_number is not None
        )
        if idealized:
            if len(idealized) != self.bracket_size:
                raise ValueError(
                    "Idealized slot numbering must cover the complete bracket"
                )
            if set(idealized) != set(range(1, self.bracket_size + 1)):
                raise ValueError(
                    "Idealized slot numbering must be a permutation of bracket capacity"
                )

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

        expected_lucky_losers = tuple(
            (slot.placeholder_id, slot.slot_index)
            for slot in self.slots
            if slot.entrant_kind == "lucky_loser_placeholder"
            and slot.placeholder_id is not None
        )
        if self.lucky_loser_placeholder_slots != expected_lucky_losers:
            raise ValueError(
                "Tournament draw Lucky Loser placeholders differ from slot payload"
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
    algorithm_version: TournamentDrawAlgorithmVersion = "protected_seed_shuffle.v1"
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
    def main_bracket_diagnostics(self) -> tuple[TournamentBracketDiagnostic, ...]:
        """Derived Admin diagnostics; excluded from persisted authority/fingerprint."""

        slots = tuple(sorted(self.main.slots, key=lambda slot: slot.slot_index))
        first_round_bye_matches = sum(
            any(slot.entrant_kind == "bye" for slot in slots[index : index + 2])
            for index in range(0, len(slots), 2)
        )
        return main_bracket_diagnostics(
            entrant_count=self.main.bracket_size - len(self.main.bye_slot_indexes),
            bracket_capacity=self.main.bracket_size,
            bye_count=len(self.main.bye_slot_indexes),
            first_round_bye_match_count=first_round_bye_matches,
        )

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
        algorithm_version: TournamentDrawAlgorithmVersion = "idealized_seed_tiers.v2",
        draw_seed_override: int | None = None,
    ) -> TournamentDrawAuthority:
        source_draw_input = draw_input
        effective_draw_input = (
            draw_input.model_copy(update={"draw_seed": draw_seed_override})
            if draw_seed_override is not None
            else draw_input
        )
        draw_input = effective_draw_input
        capacity = draw_input.capacity
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
        if (
            capacity.qualifier_spots > 0
            and len(draw_input.qualification_player_ids) < capacity.qualifier_spots
        ):
            raise ValueError(
                "Qualification requires at least one real player per Q section"
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

        if algorithm_version == "idealized_seed_tiers.v2":
            expected_main_seed_count = _master_seed_count(
                bracket_size=capacity.main_draw_size,
                actual_player_count=(
                    len(draw_input.direct_main_player_ids)
                    + len(draw_input.wild_card_player_ids)
                ),
            )
            if draw_input.main_seed_count != expected_main_seed_count:
                raise ValueError(
                    "Main seed count differs from the Master bracket seed formula"
                )
            if capacity.qualification_draw_size and capacity.qualifier_spots == 1:
                expected_q_seed_count = _master_seed_count(
                    bracket_size=capacity.qualification_draw_size,
                    actual_player_count=len(draw_input.qualification_player_ids),
                )
                if draw_input.qualification_seed_count != expected_q_seed_count:
                    raise ValueError(
                        "Qualification seed count differs from the Master bracket seed formula"
                    )

        expected_main_occupants = (
            len(draw_input.direct_main_player_ids)
            + len(draw_input.wild_card_player_ids)
            + len(draw_input.qualifier_placeholder_ids)
            + capacity.bye_slots
        )
        if expected_main_occupants != capacity.main_draw_size:
            raise ValueError(
                "Canonical Run-owned Main Draw requires a fully resolved field including explicit BYEs"
            )
        if len(draw_input.qualification_player_ids) > capacity.qualification_draw_size:
            raise ValueError(
                "Canonical Run-owned Qualification field exceeds configured capacity"
            )
        qualification_bye_count = (
            capacity.qualification_draw_size
            - len(draw_input.qualification_player_ids)
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
                    explicit_byes=qualification_bye_count,
                    algorithm_version=algorithm_version,
                )
            else:
                qualification_sections = cls._build_qualification_sections(
                    draw_input=draw_input,
                    algorithm_version=algorithm_version,
                )

        main_pool = (
            *draw_input.direct_main_player_ids,
            *draw_input.wild_card_player_ids,
        )
        main_seed_set = set(draw_input.main_seed_player_ids)
        main_player_ids = (
            *draw_input.main_seed_player_ids,
            *(player_id for player_id in main_pool if player_id not in main_seed_set),
        )
        main = cls._build_bracket(
            draw_input=draw_input,
            draw_type="main",
            bracket_size=capacity.main_draw_size,
            player_ids=main_player_ids,
            seed_player_ids=draw_input.main_seed_player_ids,
            placeholder_ids=draw_input.qualifier_placeholder_ids,
            explicit_byes=capacity.bye_slots,
            algorithm_version=algorithm_version,
            wild_card_player_ids=set(draw_input.wild_card_player_ids),
        )
        return TournamentDrawAuthority(
            schema_version=(
                "tournament_draw_authority.v2"
                if qualification_sections
                else "tournament_draw_authority.v1"
            ),
            algorithm_version=algorithm_version,
            run_id=draw_input.run_id,
            branch_id=draw_input.branch_id,
            event_id=draw_input.event_id,
            generated_by_command_id=command_id,
            draw_input_fingerprint=source_draw_input.fingerprint,
            qualification=qualification,
            qualification_sections=qualification_sections,
            main=main,
        )

    @classmethod
    def _build_qualification_sections(
        cls,
        *,
        draw_input: TournamentDrawInputAuthority,
        algorithm_version: TournamentDrawAlgorithmVersion,
    ) -> tuple[TournamentDrawBracket, ...]:
        capacity = draw_input.capacity
        section_count = capacity.qualifier_spots
        section_size = capacity.qualification_draw_size // section_count
        total_byes = (
            capacity.qualification_draw_size
            - len(draw_input.qualification_player_ids)
        )
        bye_counts = _qualification_byes_by_section(
            section_count=section_count,
            section_size=section_size,
            total_byes=total_byes,
            draw_seed=draw_input.draw_seed,
            event_id=draw_input.event_id,
        )

        expected_seed_count = _master_qualification_seed_count(
            section_count=section_count,
            section_size=section_size,
            actual_player_count=len(draw_input.qualification_player_ids),
        )
        if draw_input.qualification_seed_count != expected_seed_count:
            raise ValueError(
                "Qualification seed count must match the Master seed formula across Q sections"
            )

        global_seeds = draw_input.qualification_seed_player_ids
        section_seeds: list[list[tuple[int, str]]] = [
            [] for _ in range(section_count)
        ]

        seed_cursor = 0
        layer = 0
        while seed_cursor < len(global_seeds):
            layer += 1
            layer_players = list(
                global_seeds[seed_cursor : seed_cursor + section_count]
            )
            section_order = list(range(section_count))
            if layer > 1:
                rng = DeterministicRng(
                    _draw_named_subseed(
                        draw_seed=draw_input.draw_seed,
                        event_id=draw_input.event_id,
                        key=f"qualification:seed-layer:{layer}",
                    )
                )
                rng.shuffle(section_order)
            for offset, player_id in enumerate(layer_players):
                section_index = section_order[offset]
                global_seed_number = seed_cursor + offset + 1
                section_seeds[section_index].append(
                    (global_seed_number, player_id)
                )
            seed_cursor += len(layer_players)

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

        sections = []
        cursor = 0
        for section_index in range(section_count):
            section_id = f"Q{section_index + 1}"
            seed_pairs = tuple(section_seeds[section_index])
            seeds = tuple(player_id for _, player_id in seed_pairs)
            seed_numbers = tuple(number for number, _ in seed_pairs)
            available_player_slots = (
                section_size
                - bye_counts[section_index]
                - len(seeds)
            )
            if available_player_slots < 0:
                raise ValueError(
                    "Qualification BYE layering conflicts with protected seed capacity"
                )
            extras = tuple(
                unseeded[cursor : cursor + available_player_slots]
            )
            cursor += available_player_slots
            sections.append(
                cls._build_bracket(
                    draw_input=draw_input,
                    draw_type="qualification",
                    bracket_size=section_size,
                    player_ids=(*seeds, *extras),
                    seed_player_ids=seeds,
                    seed_numbers=seed_numbers,
                    placeholder_ids=(),
                    explicit_byes=bye_counts[section_index],
                    section_id=section_id,
                    section_ordinal=section_index,
                    section_count=section_count,
                    algorithm_version=algorithm_version,
                )
            )
        if cursor != len(unseeded):
            raise ValueError(
                "Qualification player distribution did not fill all non-BYE Q slots exactly"
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
        algorithm_version: TournamentDrawAlgorithmVersion,
        wild_card_player_ids: set[str] | None = None,
    ) -> TournamentDrawBracket:
        wild_card_player_ids = wild_card_player_ids or set()
        if not wild_card_player_ids.issubset(set(player_ids)):
            raise ValueError("WC provenance references player outside bracket field")
        if len(set(player_ids)) != len(player_ids):
            raise ValueError("Tournament draw contains duplicate player identities")
        if tuple(player_ids[: len(seed_player_ids)]) != seed_player_ids:
            raise ValueError(
                "Tournament draw seeds must follow the frozen ranking-derived field order"
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

        draw_scope = draw_type if section_id is None else f"{draw_type}:{section_id}"
        idealized_by_position = (
            _idealized_slot_order(bracket_size)
            if algorithm_version == "idealized_seed_tiers.v2"
            else ()
        )
        local_seed_positions = (
            _master_seed_positions(
                bracket_size=bracket_size,
                seed_count=len(seed_player_ids),
                draw_seed=draw_input.draw_seed,
                event_id=draw_input.event_id,
                draw_scope=draw_scope,
            )
            if algorithm_version == "idealized_seed_tiers.v2"
            else _seed_positions(bracket_size, len(seed_player_ids))
        )

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
                idealized_slot_number=(
                    idealized_by_position[position - 1]
                    if idealized_by_position
                    else None
                ),
                entrant_kind="player",
                player_id=player_id,
                seed_number=seed_number,
                is_seed_protected=True,
                entry_status=(
                    "wild_card" if player_id in wild_card_player_ids else None
                ),
            )

        bye_positions = (
            _choose_master_bye_positions(
                bracket_size=bracket_size,
                explicit_byes=explicit_byes,
                occupied_positions={
                    index for index, slot in slots.items() if slot is not None
                },
            )
            if algorithm_version == "idealized_seed_tiers.v2"
            else _choose_bye_positions(
                bracket_size=bracket_size,
                explicit_byes=explicit_byes,
                seed_positions=seed_positions,
                occupied_positions={
                    index for index, slot in slots.items() if slot is not None
                },
            )
        )
        for position in bye_positions:
            slots[position] = TournamentDrawSlot(
                slot_index=position,
                idealized_slot_number=(
                    idealized_by_position[position - 1]
                    if idealized_by_position
                    else None
                ),
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
                    idealized_slot_number=(
                        idealized_by_position[position - 1]
                        if idealized_by_position
                        else None
                    ),
                    entrant_kind="player",
                    player_id=identity,
                    entry_status=(
                        "wild_card" if identity in wild_card_player_ids else None
                    ),
                )
            else:
                slots[position] = TournamentDrawSlot(
                    slot_index=position,
                    idealized_slot_number=(
                        idealized_by_position[position - 1]
                        if idealized_by_position
                        else None
                    ),
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


def _master_seed_count(*, bracket_size: int, actual_player_count: int) -> int:
    if actual_player_count < 0:
        raise ValueError("Actual player count cannot be negative")
    if actual_player_count == 0:
        return 0
    return min(actual_player_count, max(1, bracket_size // 4))


def _idealized_slot_order(bracket_size: int) -> tuple[int, ...]:
    if bracket_size < 2 or not _is_power_of_two(bracket_size):
        raise ValueError("Tournament bracket size must be a power of two >= 2")
    order = [1]
    size = 1
    while size < bracket_size:
        next_size = size * 2
        expanded: list[int] = []
        for index, value in enumerate(order):
            pair = (value, next_size + 1 - value)
            expanded.extend(pair if index % 2 == 0 else reversed(pair))
        order = expanded
        size = next_size
    return tuple(order)


def _master_seed_positions(
    *,
    bracket_size: int,
    seed_count: int,
    draw_seed: int,
    event_id: str,
    draw_scope: str,
) -> dict[int, int]:
    if seed_count < 0 or seed_count > bracket_size:
        raise ValueError("Tournament draw seed count exceeds bracket size")
    if seed_count == 0:
        return {}
    idealized_by_position = _idealized_slot_order(bracket_size)
    physical_by_idealized = {
        idealized: position
        for position, idealized in enumerate(idealized_by_position, start=1)
    }
    assigned_idealized: dict[int, int] = {1: 1}
    if seed_count >= 2:
        assigned_idealized[2] = 2
    tier_start = 3
    while tier_start <= seed_count:
        tier_capacity_end = min(bracket_size, 2 * (tier_start - 1))
        actual_seed_end = min(seed_count, tier_capacity_end)
        idealized_slots = list(range(tier_start, tier_capacity_end + 1))
        rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_seed,
                event_id=event_id,
                key=(
                    f"{draw_scope}:seed-tier:"
                    f"{tier_start}-{tier_capacity_end}"
                ),
            )
        )
        rng.shuffle(idealized_slots)
        actual_seed_numbers = list(range(tier_start, actual_seed_end + 1))
        for seed_number, idealized_slot in zip(
            actual_seed_numbers,
            idealized_slots[: len(actual_seed_numbers)],
            strict=True,
        ):
            assigned_idealized[seed_number] = idealized_slot
        tier_start = tier_capacity_end + 1
    return {
        seed_number: physical_by_idealized[idealized_slot]
        for seed_number, idealized_slot in assigned_idealized.items()
    }


def _choose_master_bye_positions(
    *,
    bracket_size: int,
    explicit_byes: int,
    occupied_positions: set[int],
) -> tuple[int, ...]:
    if explicit_byes < 0:
        raise ValueError("Tournament draw BYE count cannot be negative")
    idealized_by_position = _idealized_slot_order(bracket_size)
    physical_by_idealized = {
        idealized: position
        for position, idealized in enumerate(idealized_by_position, start=1)
    }
    positions = []
    for idealized_slot in range(
        bracket_size, bracket_size - explicit_byes, -1
    ):
        position = physical_by_idealized[idealized_slot]
        if position in occupied_positions:
            raise ValueError(
                "Master BYE idealized slot conflicts with a protected seed position"
            )
        positions.append(position)
    return tuple(sorted(positions))


def _master_qualification_seed_count(
    *,
    section_count: int,
    section_size: int,
    actual_player_count: int,
) -> int:
    if actual_player_count < 0:
        raise ValueError("Actual Qualification player count cannot be negative")
    maximum_seed_pool = section_count * max(1, section_size // 4)
    return min(actual_player_count, maximum_seed_pool)


def _qualification_byes_by_section(
    *,
    section_count: int,
    section_size: int,
    total_byes: int,
    draw_seed: int,
    event_id: str,
) -> tuple[int, ...]:
    if total_byes < 0 or total_byes > section_count * section_size:
        raise ValueError("Qualification BYE count is outside configured capacity")
    full_layers, remainder = divmod(total_byes, section_count)
    if full_layers > section_size:
        raise ValueError("Qualification BYE layers exceed section capacity")

    counts = [full_layers for _ in range(section_count)]
    if remainder:
        section_order = list(range(section_count))
        rng = DeterministicRng(
            _draw_named_subseed(
                draw_seed=draw_seed,
                event_id=event_id,
                key=f"qualification:bye-layer:{full_layers + 1}",
            )
        )
        rng.shuffle(section_order)
        for section_index in section_order[:remainder]:
            counts[section_index] += 1
    return tuple(counts)


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