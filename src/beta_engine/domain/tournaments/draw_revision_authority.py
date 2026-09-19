"""Append-only canonical Tournament Draw revisions for phase-aware full redraw."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
    TournamentDrawBracket,
    TournamentDrawSlot,
    TournamentDrawType,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryField
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
)


TournamentDrawRevisionRepairKind = Literal["full_redraw", "seed_cascade_phase"]
TournamentDrawComponentRepairAction = Literal["seed_cascade", "direct_slot_fill"]


class TournamentDrawRevision(FrozenInput):
    schema_version: Literal[
        "tournament_draw_revision.v2",
        "tournament_draw_revision.v3",
    ] = "tournament_draw_revision.v2"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    command_id: str = Field(min_length=1, max_length=128)
    repair_kind: TournamentDrawRevisionRepairKind
    affected_draw_types: tuple[TournamentDrawType, ...]
    main_process_window_ordinal: int | None = Field(default=None, ge=1)
    qualification_process_window_ordinal: int | None = Field(default=None, ge=1)
    repair_draw_seed: int | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    main_repair_action: TournamentDrawComponentRepairAction | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    qualification_repair_action: TournamentDrawComponentRepairAction | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    withdrawn_player_ids: tuple[str, ...]
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    process_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_field: TournamentEntryField
    successor_draw_input: TournamentDrawInputAuthority
    successor_draw: TournamentDrawAuthority

    @model_validator(mode="after")
    def validate_scope(self):
        scope = (self.run_id, self.branch_id, self.event_id)
        if (
            self.successor_draw.run_id,
            self.successor_draw.branch_id,
            self.successor_draw.event_id,
        ) != scope:
            raise ValueError("Draw revision successor scope mismatch")
        if (
            self.successor_draw_input.run_id,
            self.successor_draw_input.branch_id,
            self.successor_draw_input.event_id,
        ) != scope:
            raise ValueError("Draw revision successor input scope mismatch")
        if self.successor_draw_input.entry_field_fingerprint != self.successor_field.fingerprint:
            raise ValueError("Draw revision successor Input/Field binding mismatch")
        if (
            self.successor_draw.draw_input_fingerprint
            != self.successor_draw_input.fingerprint
        ):
            raise ValueError("Draw revision successor Draw/Input binding mismatch")
        if self.successor_draw.fingerprint == self.predecessor_draw_fingerprint:
            raise ValueError("Draw repair must produce a new Draw fingerprint")
        if not self.affected_draw_types:
            raise ValueError("Draw revision must affect at least one draw component")
        if len(set(self.affected_draw_types)) != len(self.affected_draw_types):
            raise ValueError("Draw revision affected draw types must be unique")
        if "main" in self.affected_draw_types and self.main_process_window_ordinal is None:
            raise ValueError("Main redraw requires Main process-window evidence")
        if (
            "qualification" in self.affected_draw_types
            and self.qualification_process_window_ordinal is None
        ):
            raise ValueError(
                "Qualification Draw repair requires Qualification process-window evidence"
            )

        if self.repair_kind == "full_redraw":
            if self.repair_draw_seed is None:
                raise ValueError("Full redraw requires a repair draw seed")
            if (
                self.main_repair_action is not None
                or self.qualification_repair_action is not None
            ):
                raise ValueError(
                    "Historical full redraw revision cannot carry cascade actions"
                )
        else:
            if self.schema_version != "tournament_draw_revision.v3":
                raise ValueError(
                    "Seed-cascade phase repair requires revision schema v3"
                )
            if self.repair_draw_seed is not None:
                raise ValueError(
                    "Seed-cascade phase repair cannot introduce a new draw seed"
                )
            if "main" in self.affected_draw_types:
                if self.main_repair_action is None:
                    raise ValueError(
                        "Main seed-cascade phase repair lacks repair action"
                    )
            elif self.main_repair_action is not None:
                raise ValueError("Unchanged Main Draw cannot carry a repair action")
            if "qualification" in self.affected_draw_types:
                if self.qualification_repair_action is None:
                    raise ValueError(
                        "Qualification seed-cascade phase repair lacks repair action"
                    )
            elif self.qualification_repair_action is not None:
                raise ValueError(
                    "Unchanged Qualification Draw cannot carry a repair action"
                )
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentDrawRevisionBuilder:
    @staticmethod
    def build_full_redraw(
        *,
        predecessor: TournamentDrawAuthority,
        successor_field: TournamentEntryField,
        successor_draw_input: TournamentDrawInputAuthority,
        process_authority: TournamentDrawProcessAuthority,
        affected_draw_types: tuple[TournamentDrawType, ...],
        main_process_window_ordinal: int | None,
        qualification_process_window_ordinal: int | None,
        repair_draw_seed: int,
        withdrawn_player_ids: tuple[str, ...],
        sequence: int,
        command_id: str,
    ) -> TournamentDrawRevision:
        if not affected_draw_types:
            raise ValueError("Full redraw requires at least one affected draw component")
        if "main" in affected_draw_types:
            if main_process_window_ordinal is None:
                raise ValueError("Main redraw requires Main process-window evidence")
            if process_authority.phase_for(
                draw_type="main",
                process_window_ordinal=main_process_window_ordinal,
            ) != "full_redraw":
                raise ValueError("Main full redraw is only legal before Redraw Cutoff")
        if "qualification" in affected_draw_types:
            if qualification_process_window_ordinal is None:
                raise ValueError(
                    "Qualification redraw requires Qualification process-window evidence"
                )
            if process_authority.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            ) != "full_redraw":
                raise ValueError(
                    "Qualification full redraw is only legal before Redraw Cutoff"
                )

        regenerated = TournamentDrawAuthorityBuilder.build(
            draw_input=successor_draw_input,
            command_id=command_id,
            algorithm_version=predecessor.algorithm_version,
            draw_seed_override=repair_draw_seed,
        )

        successor = regenerated
        if "main" not in affected_draw_types:
            successor = successor.model_copy(update={"main": predecessor.main})
        if "qualification" not in affected_draw_types:
            successor = successor.model_copy(
                update={
                    "qualification": predecessor.qualification,
                    "qualification_sections": predecessor.qualification_sections,
                }
            )

        if "qualification" in affected_draw_types:
            before_ids = tuple(
                bracket.section_id for bracket in predecessor.qualification_brackets
            )
            after_ids = tuple(
                bracket.section_id for bracket in successor.qualification_brackets
            )
            if before_ids != after_ids:
                raise ValueError("Qualification redraw changed Q1..Qn linkage identities")
        if "main" in affected_draw_types:
            before_q_ids = {
                placeholder_id
                for placeholder_id, _ in predecessor.main.qualifier_placeholder_slots
            }
            after_q_ids = {
                placeholder_id
                for placeholder_id, _ in successor.main.qualifier_placeholder_slots
            }
            if before_q_ids != after_q_ids:
                raise ValueError("Main redraw changed Q placeholder identities")

        return TournamentDrawRevision(
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            event_id=predecessor.event_id,
            sequence=sequence,
            command_id=command_id,
            repair_kind="full_redraw",
            affected_draw_types=affected_draw_types,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=qualification_process_window_ordinal,
            repair_draw_seed=repair_draw_seed,
            withdrawn_player_ids=withdrawn_player_ids,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            process_authority_fingerprint=process_authority.fingerprint,
            successor_field=successor_field,
            successor_draw_input=successor_draw_input,
            successor_draw=successor,
        )

    @staticmethod
    def build_seed_cascade_phase(
        *,
        predecessor: TournamentDrawAuthority,
        successor_field: TournamentEntryField,
        successor_draw_input: TournamentDrawInputAuthority,
        process_authority: TournamentDrawProcessAuthority,
        affected_draw_types: tuple[TournamentDrawType, ...],
        main_process_window_ordinal: int | None,
        qualification_process_window_ordinal: int | None,
        withdrawn_player_ids: tuple[str, ...],
        sequence: int,
        command_id: str,
    ) -> TournamentDrawRevision:
        if not affected_draw_types:
            raise ValueError(
                "Seed-cascade phase repair requires at least one affected draw component"
            )
        if "main" in affected_draw_types:
            if main_process_window_ordinal is None:
                raise ValueError("Main repair requires Main process-window evidence")
            if process_authority.phase_for(
                draw_type="main",
                process_window_ordinal=main_process_window_ordinal,
            ) != "seed_cascade":
                raise ValueError(
                    "Main seed-cascade phase repair is only legal from "
                    "Redraw Cutoff to Draw Freeze"
                )
        if "qualification" in affected_draw_types:
            if qualification_process_window_ordinal is None:
                raise ValueError(
                    "Qualification repair requires Qualification process-window evidence"
                )
            if process_authority.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            ) != "seed_cascade":
                raise ValueError(
                    "Qualification seed-cascade phase repair is only legal from "
                    "Redraw Cutoff to Draw Freeze"
                )

        main = predecessor.main
        main_action = None
        if "main" in affected_draw_types:
            repaired, main_action = _repair_bracket_family(
                brackets=(predecessor.main,),
                target_player_ids=(
                    *successor_draw_input.direct_main_player_ids,
                    *successor_draw_input.wild_card_player_ids,
                ),
                draw_type="main",
                qualification_section_count=1,
            )
            main = repaired[0]

        qualification = predecessor.qualification
        qualification_sections = predecessor.qualification_sections
        qualification_action = None
        if "qualification" in affected_draw_types:
            original_q = predecessor.qualification_brackets
            if not original_q:
                raise ValueError(
                    "Qualification repair requested for tournament without Q Draw"
                )
            repaired_q, qualification_action = _repair_bracket_family(
                brackets=original_q,
                target_player_ids=successor_draw_input.qualification_player_ids,
                draw_type="qualification",
                qualification_section_count=len(original_q),
            )
            if predecessor.qualification_sections:
                qualification = None
                qualification_sections = repaired_q
            else:
                qualification = repaired_q[0]
                qualification_sections = ()

        successor = TournamentDrawAuthority(
            schema_version=predecessor.schema_version,
            algorithm_version=predecessor.algorithm_version,
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            event_id=predecessor.event_id,
            generated_by_command_id=command_id,
            draw_input_fingerprint=successor_draw_input.fingerprint,
            qualification=qualification,
            qualification_sections=qualification_sections,
            main=main,
        )

        before_q_ids = {
            placeholder_id
            for placeholder_id, _ in predecessor.main.qualifier_placeholder_slots
        }
        after_q_ids = {
            placeholder_id
            for placeholder_id, _ in successor.main.qualifier_placeholder_slots
        }
        if before_q_ids != after_q_ids:
            raise ValueError(
                "Seed-cascade phase repair changed Q placeholder identities"
            )
        if tuple(
            bracket.section_id for bracket in predecessor.qualification_brackets
        ) != tuple(
            bracket.section_id for bracket in successor.qualification_brackets
        ):
            raise ValueError(
                "Seed-cascade phase repair changed Q1..Qn linkage identities"
            )

        return TournamentDrawRevision(
            schema_version="tournament_draw_revision.v3",
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            event_id=predecessor.event_id,
            sequence=sequence,
            command_id=command_id,
            repair_kind="seed_cascade_phase",
            affected_draw_types=affected_draw_types,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=(
                qualification_process_window_ordinal
            ),
            main_repair_action=main_action,
            qualification_repair_action=qualification_action,
            withdrawn_player_ids=withdrawn_player_ids,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            process_authority_fingerprint=process_authority.fingerprint,
            successor_field=successor_field,
            successor_draw_input=successor_draw_input,
            successor_draw=successor,
        )


def _repair_bracket_family(
    *,
    brackets: tuple[TournamentDrawBracket, ...],
    target_player_ids: tuple[str, ...],
    draw_type: TournamentDrawType,
    qualification_section_count: int,
) -> tuple[
    tuple[TournamentDrawBracket, ...],
    TournamentDrawComponentRepairAction,
]:
    templates: dict[tuple[int, int], TournamentDrawSlot] = {}
    mutable: dict[tuple[int, int], TournamentDrawSlot | None] = {}
    player_ref: dict[str, tuple[int, int]] = {}
    for bracket_index, bracket in enumerate(brackets):
        for slot in bracket.slots:
            ref = (bracket_index, slot.slot_index)
            templates[ref] = slot
            mutable[ref] = slot
            if slot.player_id is not None:
                if slot.player_id in player_ref:
                    raise ValueError(
                        "Draw repair contains duplicate predecessor player"
                    )
                player_ref[slot.player_id] = ref

    predecessor_players = set(player_ref)
    target_set = set(target_player_ids)
    if len(target_set) != len(target_player_ids):
        raise ValueError("Draw repair target contains duplicate players")
    removed = predecessor_players - target_set
    incoming = tuple(
        player_id
        for player_id in target_player_ids
        if player_id not in predecessor_players
    )
    if not removed:
        raise ValueError("Draw repair component has no removed predecessor player")
    if len(removed) != len(incoming):
        raise ValueError(
            "Seed-cascade phase repair currently requires "
            "replacement-backed field parity"
        )

    removed_refs = {player_ref[player_id] for player_id in removed}
    seeded_removed_refs = {
        ref for ref in removed_refs if templates[ref].seed_number is not None
    }
    ordinary_vacancies = [
        ref for ref in removed_refs if templates[ref].seed_number is None
    ]
    for ref in removed_refs:
        mutable[ref] = None

    final_seed_vacancies: list[tuple[int, int]] = []
    if seeded_removed_refs:
        for bracket_index, bracket in enumerate(brackets):
            seeded_refs = [
                (bracket_index, slot.slot_index)
                for slot in bracket.slots
                if slot.seed_number is not None
            ]
            if not any(ref in seeded_removed_refs for ref in seeded_refs):
                continue
            tiers: dict[int, list[tuple[int, int]]] = {}
            for ref in seeded_refs:
                seed_number = templates[ref].seed_number
                assert seed_number is not None
                tier = _seed_tier(
                    seed_number=seed_number,
                    draw_type=draw_type,
                    qualification_section_count=qualification_section_count,
                )
                tiers.setdefault(tier, []).append(ref)

            carry: list[tuple[int, int]] = []
            for tier in sorted(tiers):
                refs = sorted(
                    tiers[tier],
                    key=lambda ref: (
                        templates[ref].seed_number or 10**9,
                        templates[ref].slot_index,
                    ),
                )
                own_vacancies = [
                    ref for ref in refs if ref in seeded_removed_refs
                ]
                candidates = [
                    ref
                    for ref in refs
                    if ref not in seeded_removed_refs
                    and mutable[ref] is not None
                ]
                destinations = sorted(
                    carry,
                    key=lambda ref: _vacancy_priority(ref, templates),
                )
                movers = candidates[: len(destinations)]
                for destination, source in zip(
                    destinations, movers, strict=True
                ):
                    source_slot = mutable[source]
                    if source_slot is None:
                        raise ValueError(
                            "Seed cascade source unexpectedly vacant"
                        )
                    mutable[destination] = _move_slot(
                        source_slot=source_slot,
                        destination=templates[destination],
                    )
                    mutable[source] = None
                carry = [
                    *destinations[len(movers) :],
                    *own_vacancies,
                    *movers,
                ]
            final_seed_vacancies.extend(carry)

        unseeded_candidates = [
            player_id
            for player_id in target_player_ids
            if player_id in predecessor_players
            and templates[player_ref[player_id]].seed_number is None
            and player_ref[player_id] not in ordinary_vacancies
        ]
        ordered_seed_vacancies = sorted(
            final_seed_vacancies,
            key=lambda ref: _vacancy_priority(ref, templates),
        )
        if len(unseeded_candidates) < len(ordered_seed_vacancies):
            raise ValueError(
                "Seed cascade lacks enough surviving unseeded players "
                "to close seed structure"
            )
        for destination, player_id in zip(
            ordered_seed_vacancies,
            unseeded_candidates[: len(ordered_seed_vacancies)],
            strict=True,
        ):
            source = player_ref[player_id]
            source_slot = mutable[source]
            if source_slot is None:
                raise ValueError(
                    "Seed cascade unseeded source unexpectedly vacant"
                )
            mutable[destination] = _move_slot(
                source_slot=source_slot,
                destination=templates[destination],
            )
            mutable[source] = None
            ordinary_vacancies.append(source)

    ordered_ordinary = sorted(
        set(ordinary_vacancies),
        key=lambda ref: _ordinary_vacancy_priority(ref, templates),
    )
    if len(ordered_ordinary) != len(incoming):
        raise ValueError(
            "Draw repair replacement count differs from physical vacancies"
        )
    for destination, player_id in zip(
        ordered_ordinary, incoming, strict=True
    ):
        template = templates[destination]
        mutable[destination] = TournamentDrawSlot(
            slot_index=template.slot_index,
            idealized_slot_number=template.idealized_slot_number,
            entrant_kind="player",
            player_id=player_id,
        )

    rebuilt = []
    for bracket_index, bracket in enumerate(brackets):
        slots = tuple(
            mutable[(bracket_index, index)]
            for index in range(1, bracket.bracket_size + 1)
        )
        if any(slot is None for slot in slots):
            raise ValueError("Draw repair left an unresolved physical slot")
        typed_slots = tuple(slot for slot in slots if slot is not None)
        players = {
            slot.player_id
            for slot in typed_slots
            if slot.player_id is not None
        }
        rebuilt.append(
            TournamentDrawBracket(
                draw_type=bracket.draw_type,
                section_id=bracket.section_id,
                bracket_size=bracket.bracket_size,
                seed_positions=tuple(
                    sorted(
                        (slot.seed_number, slot.slot_index)
                        for slot in typed_slots
                        if slot.seed_number is not None
                    )
                ),
                slots=typed_slots,
                nodes=bracket.nodes,
                bye_slot_indexes=tuple(
                    slot.slot_index
                    for slot in typed_slots
                    if slot.entrant_kind == "bye"
                ),
                qualifier_placeholder_slots=tuple(
                    (slot.placeholder_id, slot.slot_index)
                    for slot in typed_slots
                    if slot.entrant_kind == "qualifier_placeholder"
                    and slot.placeholder_id is not None
                ),
            )
        )
        if not players <= target_set:
            raise ValueError(
                "Draw repair retained a player outside successor field"
            )

    actual_players = {
        slot.player_id
        for bracket in rebuilt
        for slot in bracket.slots
        if slot.player_id is not None
    }
    if actual_players != target_set:
        raise ValueError(
            "Draw repair physical player set differs from successor field"
        )

    return tuple(rebuilt), (
        "seed_cascade" if seeded_removed_refs else "direct_slot_fill"
    )


def _seed_tier(
    *,
    seed_number: int,
    draw_type: TournamentDrawType,
    qualification_section_count: int,
) -> int:
    if draw_type == "qualification" and qualification_section_count > 1:
        return (seed_number - 1) // qualification_section_count
    return max(0, (seed_number - 1).bit_length() - 1)


def _move_slot(
    *,
    source_slot: TournamentDrawSlot,
    destination: TournamentDrawSlot,
) -> TournamentDrawSlot:
    return TournamentDrawSlot(
        slot_index=destination.slot_index,
        idealized_slot_number=destination.idealized_slot_number,
        entrant_kind="player",
        player_id=source_slot.player_id,
        seed_number=source_slot.seed_number,
        is_seed_protected=source_slot.is_seed_protected,
        entry_status=source_slot.entry_status,
    )


def _vacancy_priority(
    ref: tuple[int, int],
    templates: dict[tuple[int, int], TournamentDrawSlot],
) -> tuple[int, int, int, int]:
    bracket_index, slot_index = ref
    slot = templates[ref]
    return (
        slot.seed_number or 10**9,
        bracket_index,
        slot.idealized_slot_number or 10**9,
        slot_index,
    )


def _ordinary_vacancy_priority(
    ref: tuple[int, int],
    templates: dict[tuple[int, int], TournamentDrawSlot],
) -> tuple[int, int, int]:
    bracket_index, slot_index = ref
    slot = templates[ref]
    return (
        bracket_index,
        slot.idealized_slot_number or 10**9,
        slot_index,
    )

