"""Deterministic draw generation for qualification and main-draw structures."""

from __future__ import annotations

from dataclasses import dataclass

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.draws.models import (
    DrawEntrantType,
    DrawNode,
    DrawSlot,
    DrawType,
    GeneratedDraw,
    LuckyLoserHook,
)
from beta_engine.domain.entries.models import AcceptanceList, AcceptanceStatus, TournamentEntry
from beta_engine.domain.tournaments.models import TournamentTemplate


@dataclass(slots=True)
class DrawEngine:
    rng: DeterministicRng

    def generate_qualification_draw(
        self,
        *,
        acceptance_list: AcceptanceList,
        template: TournamentTemplate,
    ) -> GeneratedDraw:
        accepted = [
            entry
            for entry in acceptance_list.qualification_entries
            if entry.status == AcceptanceStatus.QUALIFICATION_ACCEPTANCE
        ]
        bracket_size = _next_power_of_two(max(1, template.qualification_draw_size))
        byes = max(0, bracket_size - template.qualification_draw_size)
        return self._generate_draw(
            event_id=acceptance_list.event_id,
            draw_type=DrawType.QUALIFICATION,
            season=acceptance_list.season,
            week=acceptance_list.week,
            target_draw_size=template.qualification_draw_size,
            bracket_size=bracket_size,
            seeds_count=min(template.seeds_count, template.qualification_draw_size),
            entrant_entries=accepted,
            explicit_byes=byes,
            lucky_loser_hook=None,
        )

    def generate_main_draw(
        self,
        *,
        acceptance_list: AcceptanceList,
        template: TournamentTemplate,
    ) -> GeneratedDraw:
        accepted_statuses = {
            AcceptanceStatus.DIRECT_ACCEPTANCE,
            AcceptanceStatus.QUALIFIER_PLACEHOLDER,
            AcceptanceStatus.WILD_CARD_PLACEHOLDER,
            AcceptanceStatus.WITHDRAWAL_PLACEHOLDER,
            AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER,
        }
        accepted = [
            entry
            for entry in acceptance_list.main_draw_entries
            if entry.status in accepted_statuses
        ]
        bracket_size = template.main_draw_size + template.byes
        if bracket_size <= 0 or (bracket_size & (bracket_size - 1)) != 0:
            raise ValueError(
                "main_draw_size + byes must resolve to a power-of-two bracket for deterministic placement"
            )

        return self._generate_draw(
            event_id=acceptance_list.event_id,
            draw_type=DrawType.MAIN,
            season=acceptance_list.season,
            week=acceptance_list.week,
            target_draw_size=template.main_draw_size,
            bracket_size=bracket_size,
            seeds_count=min(template.seeds_count, template.main_draw_size),
            entrant_entries=accepted,
            explicit_byes=template.byes,
            lucky_loser_hook=LuckyLoserHook(
                enabled=template.lucky_loser_rules.enabled,
                replacement_window=template.lucky_loser_rules.replacement_window,
                max_spots=template.lucky_loser_rules.max_spots,
            ),
        )

    def _generate_draw(
        self,
        *,
        event_id: str,
        draw_type: DrawType,
        season: int,
        week: int,
        target_draw_size: int,
        bracket_size: int,
        seeds_count: int,
        entrant_entries: list[TournamentEntry],
        explicit_byes: int,
        lucky_loser_hook: LuckyLoserHook | None,
    ) -> GeneratedDraw:
        draw_rng = self.rng.branch(SeedScope.WEEK, season, week, event_id, draw_type.value)
        seed_positions = _seed_positions(bracket_size, seeds_count)

        ranked_entries = sorted(
            entrant_entries,
            key=lambda entry: (
                10_000 if entry.ranking_priority is None else entry.ranking_priority,
                "" if entry.player_id is None else entry.player_id,
                entry.entry_id,
            ),
        )
        seeded_entries = [entry for entry in ranked_entries if entry.player_id is not None][:seeds_count]
        remaining_entries = [entry for entry in ranked_entries if entry not in seeded_entries]

        slot_by_index: dict[int, DrawSlot] = {
            i: DrawSlot(slot_index=i, entrant_type=DrawEntrantType.TBD) for i in range(1, bracket_size + 1)
        }

        for seed_number, entry in enumerate(seeded_entries, start=1):
            position = seed_positions[seed_number]
            slot_by_index[position] = self._slot_from_entry(
                slot_index=position,
                entry=entry,
                seed_number=seed_number,
                is_seed_protected=True,
            )

        bye_positions = self._choose_bye_positions(
            bracket_size=bracket_size,
            explicit_byes=explicit_byes,
            seed_positions=seed_positions,
            occupied_positions=set(pos for pos in seed_positions.values() if slot_by_index[pos].entry_id is not None),
        )
        for bye_position in bye_positions:
            slot_by_index[bye_position] = DrawSlot(slot_index=bye_position, entrant_type=DrawEntrantType.BYE)

        open_positions = [
            idx
            for idx in range(1, bracket_size + 1)
            if slot_by_index[idx].entrant_type == DrawEntrantType.TBD
        ]
        draw_rng.shuffle(open_positions)

        for position, entry in zip(open_positions, remaining_entries, strict=False):
            slot_by_index[position] = self._slot_from_entry(slot_index=position, entry=entry)

        slots = [slot_by_index[i] for i in range(1, bracket_size + 1)]
        qualifier_slots = [slot.slot_index for slot in slots if slot.entrant_type == DrawEntrantType.QUALIFIER_PLACEHOLDER]
        wild_card_slots = [slot.slot_index for slot in slots if slot.entrant_type == DrawEntrantType.WILD_CARD_PLACEHOLDER]
        bye_slots = [slot.slot_index for slot in slots if slot.entrant_type == DrawEntrantType.BYE]

        if lucky_loser_hook is not None:
            lucky_loser_hook = lucky_loser_hook.model_copy(update={"candidate_slot_indexes": self._ll_candidate_slots(slots)})

        return GeneratedDraw(
            event_id=event_id,
            draw_type=draw_type,
            bracket_size=bracket_size,
            target_draw_size=target_draw_size,
            seeds_count=seeds_count,
            seed_positions=seed_positions,
            slots=slots,
            nodes=_build_nodes(bracket_size),
            qualifier_slot_indexes=qualifier_slots,
            wild_card_slot_indexes=wild_card_slots,
            bye_slot_indexes=bye_slots,
            lucky_loser_hook=lucky_loser_hook,
        )

    @staticmethod
    def _slot_from_entry(
        *,
        slot_index: int,
        entry: TournamentEntry,
        seed_number: int | None = None,
        is_seed_protected: bool = False,
    ) -> DrawSlot:
        entrant_type = _entrant_type_for_status(entry.status, entry.player_id)
        return DrawSlot(
            slot_index=slot_index,
            seed_number=seed_number,
            entrant_type=entrant_type,
            entry_id=entry.entry_id,
            player_id=entry.player_id,
            acceptance_status=entry.status,
            is_seed_protected=is_seed_protected,
            metadata={"placeholder_reason": entry.placeholder_reason or ""},
        )

    @staticmethod
    def _choose_bye_positions(
        *,
        bracket_size: int,
        explicit_byes: int,
        seed_positions: dict[int, int],
        occupied_positions: set[int],
    ) -> list[int]:
        if explicit_byes <= 0:
            return []

        bye_positions: list[int] = []
        for seed_number in sorted(seed_positions):
            if len(bye_positions) >= explicit_byes:
                break
            seed_slot = seed_positions[seed_number]
            opponent = _paired_slot(seed_slot)
            if opponent not in occupied_positions and opponent not in bye_positions:
                bye_positions.append(opponent)

        candidate_positions = [idx for idx in range(1, bracket_size + 1) if idx not in occupied_positions and idx not in bye_positions]
        for position in candidate_positions:
            if len(bye_positions) >= explicit_byes:
                break
            bye_positions.append(position)
        return sorted(bye_positions)

    @staticmethod
    def _ll_candidate_slots(slots: list[DrawSlot]) -> list[int]:
        return [
            slot.slot_index
            for slot in slots
            if slot.acceptance_status in {AcceptanceStatus.WITHDRAWAL_PLACEHOLDER, AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER}
        ]


def _entrant_type_for_status(status: AcceptanceStatus, player_id: str | None) -> DrawEntrantType:
    if player_id is not None:
        return DrawEntrantType.PLAYER
    mapping = {
        AcceptanceStatus.QUALIFIER_PLACEHOLDER: DrawEntrantType.QUALIFIER_PLACEHOLDER,
        AcceptanceStatus.WILD_CARD_PLACEHOLDER: DrawEntrantType.WILD_CARD_PLACEHOLDER,
        AcceptanceStatus.WITHDRAWAL_PLACEHOLDER: DrawEntrantType.WITHDRAWAL_PLACEHOLDER,
        AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER: DrawEntrantType.LATE_REPLACEMENT_PLACEHOLDER,
    }
    return mapping.get(status, DrawEntrantType.TBD)


def _paired_slot(slot_index: int) -> int:
    return slot_index + 1 if slot_index % 2 == 1 else slot_index - 1


def _next_power_of_two(value: int) -> int:
    size = 1
    while size < value:
        size *= 2
    return size


def _seed_positions(bracket_size: int, seeds_count: int) -> dict[int, int]:
    if seeds_count <= 0:
        return {}

    placements = _seed_placement_order(bracket_size)
    return {seed: placements[seed - 1] for seed in range(1, seeds_count + 1)}


def _seed_placement_order(bracket_size: int) -> list[int]:
    if bracket_size <= 1 or (bracket_size & (bracket_size - 1)) != 0:
        raise ValueError("bracket_size must be a power of two")

    positions = [1, 2]
    size = 2
    while size < bracket_size:
        size *= 2
        expanded: list[int] = []
        for slot in positions:
            expanded.extend([slot, size + 1 - slot])
        positions = expanded
    return positions


def _build_nodes(bracket_size: int) -> list[DrawNode]:
    rounds = bracket_size.bit_length() - 1
    nodes: list[DrawNode] = []

    prior_round_ids = [f"SLOT:{idx}" for idx in range(1, bracket_size + 1)]
    for round_number in range(1, rounds + 1):
        current_round_ids: list[str] = []
        node_count = bracket_size // (2**round_number)
        for sequence in range(1, node_count + 1):
            top = prior_round_ids[(sequence - 1) * 2]
            bottom = prior_round_ids[(sequence - 1) * 2 + 1]
            node_id = f"R{round_number}-N{sequence}"
            nodes.append(
                DrawNode(
                    node_id=node_id,
                    round_number=round_number,
                    round_sequence=sequence,
                    source_top=top,
                    source_bottom=bottom,
                )
            )
            current_round_ids.append(node_id)
        prior_round_ids = current_round_ids

    return nodes
