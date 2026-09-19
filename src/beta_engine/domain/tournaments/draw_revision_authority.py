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
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthority,
)
from beta_engine.domain.tournaments.post_draw_wild_card_repair import (
    TournamentPostDrawWildCardRepairAuthority,
)


TournamentDrawRevisionRepairKind = Literal[
    "full_redraw",
    "seed_cascade_phase",
    "draw_frozen_phase",
    "frozen_wild_card_repair",
]
TournamentDrawComponentRepairAction = Literal[
    "full_redraw",
    "seed_cascade",
    "direct_slot_fill",
    "frozen_slot_fill",
    "frozen_wild_card_fill",
    "frozen_rwc_q_backfill",
]


class TournamentDrawRevision(FrozenInput):
    schema_version: Literal[
        "tournament_draw_revision.v2",
        "tournament_draw_revision.v3",
        "tournament_draw_revision.v4",
        "tournament_draw_revision.v5",
        "tournament_draw_revision.v6",
        "tournament_draw_revision.v7",
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
    replacement_cutoff_authorities: tuple[
        TournamentPlayerReplacementCutoffAuthority, ...
    ] = Field(default=(), exclude_if=lambda value: not value)
    wild_card_repair_authority: TournamentPostDrawWildCardRepairAuthority | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
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

        cutoff_ids = tuple(
            authority.player_id for authority in self.replacement_cutoff_authorities
        )
        if self.schema_version in {
            "tournament_draw_revision.v5",
            "tournament_draw_revision.v6",
            "tournament_draw_revision.v7",
        }:
            if cutoff_ids != tuple(sorted(self.withdrawn_player_ids)):
                raise ValueError(
                    "Cutoff-aware Draw revision must freeze one authority per withdrawal"
                )
            if any(
                (
                    authority.run_id,
                    authority.branch_id,
                    authority.event_id,
                )
                != scope
                for authority in self.replacement_cutoff_authorities
            ):
                raise ValueError("Replacement cutoff authority scope mismatch")
            if any(
                authority.status != "replacement_open"
                for authority in self.replacement_cutoff_authorities
            ):
                raise ValueError(
                    "Successful Draw repair requires every replacement cutoff to remain open"
                )
        elif self.replacement_cutoff_authorities:
            raise ValueError(
                "Historical Draw revision schema cannot carry replacement cutoff authority"
            )

        if self.repair_kind == "full_redraw":
            if self.schema_version not in {
                "tournament_draw_revision.v2",
                "tournament_draw_revision.v5",
            }:
                raise ValueError("Full redraw uses revision schema v2 or cutoff-aware v5")
            if self.repair_draw_seed is None:
                raise ValueError("Full redraw requires a repair draw seed")
            if (
                self.main_repair_action is not None
                or self.qualification_repair_action is not None
            ):
                raise ValueError(
                    "Full redraw revision cannot carry component cascade actions"
                )
        elif self.repair_kind == "seed_cascade_phase":
            if self.schema_version not in {
                "tournament_draw_revision.v3",
                "tournament_draw_revision.v5",
            }:
                raise ValueError(
                    "Seed-cascade phase repair requires revision schema v3 or v5"
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
            actions = {
                action
                for action in (
                    self.main_repair_action,
                    self.qualification_repair_action,
                )
                if action is not None
            }
            if "full_redraw" in actions and self.repair_draw_seed is None:
                raise ValueError(
                    "Mixed pre-freeze repair with full redraw requires repair seed"
                )
            if "full_redraw" not in actions and self.repair_draw_seed is not None:
                raise ValueError(
                    "Pure seed-cascade phase repair cannot introduce a new draw seed"
                )
        elif self.repair_kind == "draw_frozen_phase":
            if self.schema_version not in {
                "tournament_draw_revision.v4",
                "tournament_draw_revision.v5",
            }:
                raise ValueError(
                    "Draw-Freeze phase repair requires revision schema v4 or v5"
                )
            if self.wild_card_repair_authority is not None:
                raise ValueError(
                    "Generic Draw-Freeze repair cannot carry dedicated WC repair authority"
                )
            if "main" in self.affected_draw_types:
                if self.main_repair_action is None:
                    raise ValueError(
                        "Main Draw-Freeze phase repair lacks repair action"
                    )
            elif self.main_repair_action is not None:
                raise ValueError("Unchanged Main Draw cannot carry a repair action")
            if "qualification" in self.affected_draw_types:
                if self.qualification_repair_action is None:
                    raise ValueError(
                        "Qualification Draw-Freeze phase repair lacks repair action"
                    )
            elif self.qualification_repair_action is not None:
                raise ValueError(
                    "Unchanged Qualification Draw cannot carry a repair action"
                )
            actions = {
                action
                for action in (
                    self.main_repair_action,
                    self.qualification_repair_action,
                )
                if action is not None
            }
            if "frozen_slot_fill" not in actions:
                raise ValueError(
                    "Draw-Freeze phase repair requires at least one frozen-slot action"
                )
            if "full_redraw" in actions and self.repair_draw_seed is None:
                raise ValueError(
                    "Mixed Draw-Freeze repair with full redraw requires repair seed"
                )
            if "full_redraw" not in actions and self.repair_draw_seed is not None:
                raise ValueError(
                    "Draw-Freeze repair without full redraw cannot introduce a new draw seed"
                )
        else:
            authority = self.wild_card_repair_authority
            if authority is None:
                raise ValueError("Frozen WC repair lacks dedicated authority")
            if authority.replacement_source == "qualification":
                if self.schema_version != "tournament_draw_revision.v7":
                    raise ValueError(
                        "Frozen cross-draw RWC repair requires revision schema v7"
                    )
                if self.affected_draw_types != ("main", "qualification"):
                    raise ValueError(
                        "Frozen cross-draw RWC repair must affect Main and Qualification"
                    )
                if self.qualification_repair_action != "frozen_rwc_q_backfill":
                    raise ValueError(
                        "Frozen cross-draw RWC repair requires exact Q backfill action"
                    )
            else:
                if self.schema_version != "tournament_draw_revision.v6":
                    raise ValueError(
                        "Frozen external WC repair requires revision schema v6"
                    )
                if self.affected_draw_types != ("main",):
                    raise ValueError(
                        "Frozen external WC repair may affect Main Draw only"
                    )
                if self.qualification_repair_action is not None:
                    raise ValueError(
                        "Frozen external WC repair cannot mutate Qualification"
                    )
            if self.main_repair_action != "frozen_wild_card_fill":
                raise ValueError("Frozen WC repair requires WC physical-slot action")
            if self.repair_draw_seed is not None:
                raise ValueError("Frozen WC repair cannot introduce a draw seed")
            if (
                authority.run_id,
                authority.branch_id,
                authority.event_id,
                authority.command_id,
                authority.predecessor_draw_fingerprint,
            ) != (
                self.run_id,
                self.branch_id,
                self.event_id,
                self.command_id,
                self.predecessor_draw_fingerprint,
            ):
                raise ValueError("Frozen WC repair authority scope mismatch")
            if self.withdrawn_player_ids != (authority.withdrawn_player_id,):
                raise ValueError("Frozen WC repair withdrawal identity mismatch")
            if self.replacement_cutoff_authorities != (
                authority.replacement_cutoff_authority,
            ):
                raise ValueError("Frozen WC repair cutoff evidence mismatch")
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
        replacement_cutoff_authorities: tuple[
            TournamentPlayerReplacementCutoffAuthority, ...
        ] = (),
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
            schema_version=(
                "tournament_draw_revision.v5"
                if replacement_cutoff_authorities
                else "tournament_draw_revision.v2"
            ),
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
            replacement_cutoff_authorities=replacement_cutoff_authorities,
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
        repair_draw_seed: int | None = None,
        replacement_cutoff_authorities: tuple[
            TournamentPlayerReplacementCutoffAuthority, ...
        ] = (),
    ) -> TournamentDrawRevision:
        if not affected_draw_types:
            raise ValueError(
                "Seed-cascade phase repair requires at least one affected draw component"
            )

        phases = {}
        if "main" in affected_draw_types:
            if main_process_window_ordinal is None:
                raise ValueError("Main repair requires Main process-window evidence")
            phases["main"] = process_authority.phase_for(
                draw_type="main",
                process_window_ordinal=main_process_window_ordinal,
            )
        if "qualification" in affected_draw_types:
            if qualification_process_window_ordinal is None:
                raise ValueError(
                    "Qualification repair requires Qualification process-window evidence"
                )
            phases["qualification"] = process_authority.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            )

        if "draw_frozen" in phases.values():
            raise ValueError(
                "Seed-cascade phase repair is not legal after Draw Freeze"
            )
        if "seed_cascade" not in phases.values():
            raise ValueError(
                "This repair path requires at least one affected component "
                "between Redraw Cutoff and Draw Freeze"
            )

        needs_full_redraw = "full_redraw" in phases.values()
        if needs_full_redraw and repair_draw_seed is None:
            raise ValueError(
                "Mixed pre-freeze repair requires a seed for full-redraw components"
            )
        if not needs_full_redraw and repair_draw_seed is not None:
            raise ValueError(
                "Pure seed-cascade phase repair cannot introduce a new draw seed"
            )

        regenerated = None
        if needs_full_redraw:
            regenerated = TournamentDrawAuthorityBuilder.build(
                draw_input=successor_draw_input,
                command_id=command_id,
                algorithm_version=predecessor.algorithm_version,
                draw_seed_override=repair_draw_seed,
            )

        main = predecessor.main
        main_action = None
        if "main" in affected_draw_types:
            if phases["main"] == "full_redraw":
                assert regenerated is not None
                main = regenerated.main
                main_action = "full_redraw"
            else:
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
            if phases["qualification"] == "full_redraw":
                assert regenerated is not None
                qualification = regenerated.qualification
                qualification_sections = regenerated.qualification_sections
                qualification_action = "full_redraw"
            else:
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
            schema_version=(
                "tournament_draw_revision.v5"
                if replacement_cutoff_authorities
                else "tournament_draw_revision.v3"
            ),
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
            repair_draw_seed=repair_draw_seed,
            main_repair_action=main_action,
            qualification_repair_action=qualification_action,
            withdrawn_player_ids=withdrawn_player_ids,
            replacement_cutoff_authorities=replacement_cutoff_authorities,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            process_authority_fingerprint=process_authority.fingerprint,
            successor_field=successor_field,
            successor_draw_input=successor_draw_input,
            successor_draw=successor,
        )

    @staticmethod
    def build_draw_frozen_phase(
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
        repair_draw_seed: int | None = None,
        replacement_cutoff_authorities: tuple[
            TournamentPlayerReplacementCutoffAuthority, ...
        ] = (),
    ) -> TournamentDrawRevision:
        if not affected_draw_types:
            raise ValueError(
                "Draw-Freeze phase repair requires at least one affected draw component"
            )

        phases = {}
        if "main" in affected_draw_types:
            if main_process_window_ordinal is None:
                raise ValueError("Main repair requires Main process-window evidence")
            phases["main"] = process_authority.phase_for(
                draw_type="main",
                process_window_ordinal=main_process_window_ordinal,
            )
        if "qualification" in affected_draw_types:
            if qualification_process_window_ordinal is None:
                raise ValueError(
                    "Qualification repair requires Qualification process-window evidence"
                )
            phases["qualification"] = process_authority.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            )

        if "draw_frozen" not in phases.values():
            raise ValueError(
                "This repair path requires at least one affected component after Draw Freeze"
            )

        needs_full_redraw = "full_redraw" in phases.values()
        if needs_full_redraw and repair_draw_seed is None:
            raise ValueError(
                "Mixed Draw-Freeze repair requires a seed for full-redraw components"
            )
        if not needs_full_redraw and repair_draw_seed is not None:
            raise ValueError(
                "Draw-Freeze repair without full redraw cannot introduce a new draw seed"
            )

        regenerated = None
        if needs_full_redraw:
            regenerated = TournamentDrawAuthorityBuilder.build(
                draw_input=successor_draw_input,
                command_id=command_id,
                algorithm_version=predecessor.algorithm_version,
                draw_seed_override=repair_draw_seed,
            )

        main = predecessor.main
        main_action = None
        if "main" in affected_draw_types:
            phase = phases["main"]
            if phase == "full_redraw":
                assert regenerated is not None
                main = regenerated.main
                main_action = "full_redraw"
            elif phase == "seed_cascade":
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
            else:
                repaired = _repair_frozen_bracket_family(
                    brackets=(predecessor.main,),
                    target_player_ids=(
                        *successor_draw_input.direct_main_player_ids,
                        *successor_draw_input.wild_card_player_ids,
                    ),
                )
                main = repaired[0]
                main_action = "frozen_slot_fill"

        qualification = predecessor.qualification
        qualification_sections = predecessor.qualification_sections
        qualification_action = None
        if "qualification" in affected_draw_types:
            phase = phases["qualification"]
            if phase == "full_redraw":
                assert regenerated is not None
                qualification = regenerated.qualification
                qualification_sections = regenerated.qualification_sections
                qualification_action = "full_redraw"
            else:
                original_q = predecessor.qualification_brackets
                if not original_q:
                    raise ValueError(
                        "Qualification repair requested for tournament without Q Draw"
                    )
                if phase == "seed_cascade":
                    repaired_q, qualification_action = _repair_bracket_family(
                        brackets=original_q,
                        target_player_ids=successor_draw_input.qualification_player_ids,
                        draw_type="qualification",
                        qualification_section_count=len(original_q),
                    )
                else:
                    repaired_q = _repair_frozen_bracket_family(
                        brackets=original_q,
                        target_player_ids=successor_draw_input.qualification_player_ids,
                    )
                    qualification_action = "frozen_slot_fill"
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
                "Draw-Freeze phase repair changed Q placeholder identities"
            )
        if tuple(
            bracket.section_id for bracket in predecessor.qualification_brackets
        ) != tuple(
            bracket.section_id for bracket in successor.qualification_brackets
        ):
            raise ValueError(
                "Draw-Freeze phase repair changed Q1..Qn linkage identities"
            )

        return TournamentDrawRevision(
            schema_version=(
                "tournament_draw_revision.v5"
                if replacement_cutoff_authorities
                else "tournament_draw_revision.v4"
            ),
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            event_id=predecessor.event_id,
            sequence=sequence,
            command_id=command_id,
            repair_kind="draw_frozen_phase",
            affected_draw_types=affected_draw_types,
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=(
                qualification_process_window_ordinal
            ),
            repair_draw_seed=repair_draw_seed,
            main_repair_action=main_action,
            qualification_repair_action=qualification_action,
            withdrawn_player_ids=withdrawn_player_ids,
            replacement_cutoff_authorities=replacement_cutoff_authorities,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            process_authority_fingerprint=process_authority.fingerprint,
            successor_field=successor_field,
            successor_draw_input=successor_draw_input,
            successor_draw=successor,
        )


    @staticmethod
    def build_frozen_wild_card_repair(
        *,
        predecessor: TournamentDrawAuthority,
        successor_field: TournamentEntryField,
        successor_draw_input: TournamentDrawInputAuthority,
        process_authority: TournamentDrawProcessAuthority,
        main_process_window_ordinal: int,
        qualification_process_window_ordinal: int | None = None,
        sequence: int,
        command_id: str,
        wild_card_repair_authority: TournamentPostDrawWildCardRepairAuthority,
    ) -> TournamentDrawRevision:
        if process_authority.phase_for(
            draw_type="main",
            process_window_ordinal=main_process_window_ordinal,
        ) != "draw_frozen":
            raise ValueError("Dedicated RWC physical-slot repair requires Draw Freeze")
        if wild_card_repair_authority.replacement_source == "qualification":
            if qualification_process_window_ordinal is None:
                raise ValueError(
                    "Qualification RWC promotion requires Q process-window evidence"
                )
            if process_authority.phase_for(
                draw_type="qualification",
                process_window_ordinal=qualification_process_window_ordinal,
            ) != "draw_frozen":
                raise ValueError(
                    "Qualification RWC exact-slot backfill requires Q Draw Freeze"
                )
        if (
            wild_card_repair_authority.predecessor_draw_fingerprint
            != predecessor.fingerprint
        ):
            raise ValueError("RWC repair authority predecessor mismatch")
        if (
            wild_card_repair_authority.predecessor_draw_input_fingerprint
            != predecessor.draw_input_fingerprint
        ):
            raise ValueError("RWC repair authority Draw Input mismatch")
        if (
            successor_draw_input.entry_field_fingerprint
            != successor_field.fingerprint
        ):
            raise ValueError("RWC successor Draw Input/Field binding mismatch")
        if (
            successor_draw_input.post_draw_wild_card_repair_fingerprints[-1]
            != wild_card_repair_authority.fingerprint
        ):
            raise ValueError("RWC successor Draw Input lacks repair lineage")

        slots = list(predecessor.main.slots)
        index = wild_card_repair_authority.physical_slot_index - 1
        if index < 0 or index >= len(slots):
            raise ValueError("RWC physical slot is outside Main Draw")
        template = slots[index]
        if (
            template.player_id
            != wild_card_repair_authority.withdrawn_player_id
            or template.entry_status != "wild_card"
            or template.seed_number is not None
        ):
            raise ValueError("RWC physical slot no longer matches repair authority")
        slots[index] = TournamentDrawSlot(
            slot_index=template.slot_index,
            idealized_slot_number=template.idealized_slot_number,
            entrant_kind="player",
            player_id=wild_card_repair_authority.replacement_player_id,
            entry_status="wild_card",
        )
        main = TournamentDrawBracket(
            draw_type=predecessor.main.draw_type,
            section_id=predecessor.main.section_id,
            bracket_size=predecessor.main.bracket_size,
            seed_positions=predecessor.main.seed_positions,
            slots=tuple(slots),
            nodes=predecessor.main.nodes,
            bye_slot_indexes=predecessor.main.bye_slot_indexes,
            qualifier_placeholder_slots=predecessor.main.qualifier_placeholder_slots,
        )
        qualification = predecessor.qualification
        qualification_sections = predecessor.qualification_sections
        cross_draw = wild_card_repair_authority.replacement_source == "qualification"
        if cross_draw:
            q_slot_index = (
                wild_card_repair_authority.qualification_physical_slot_index
            )
            q_backfill = wild_card_repair_authority.qualification_backfill_player_id
            if q_slot_index is None or q_backfill is None:
                raise ValueError("Qualification RWC repair lacks Q slot/backfill evidence")
            rebuilt = []
            matched = 0
            for bracket in predecessor.qualification_brackets:
                if bracket.section_id != wild_card_repair_authority.qualification_section_id:
                    rebuilt.append(bracket)
                    continue
                if q_slot_index > bracket.bracket_size:
                    raise ValueError("Qualification RWC physical slot is outside Q bracket")
                q_slots = list(bracket.slots)
                q_template = q_slots[q_slot_index - 1]
                if (
                    q_template.player_id
                    != wild_card_repair_authority.replacement_player_id
                    or q_template.seed_number is not None
                ):
                    raise ValueError(
                        "Qualification RWC physical slot no longer matches authority"
                    )
                q_slots[q_slot_index - 1] = TournamentDrawSlot(
                    slot_index=q_template.slot_index,
                    idealized_slot_number=q_template.idealized_slot_number,
                    entrant_kind="player",
                    player_id=q_backfill,
                )
                rebuilt.append(
                    TournamentDrawBracket(
                        draw_type=bracket.draw_type,
                        section_id=bracket.section_id,
                        bracket_size=bracket.bracket_size,
                        seed_positions=tuple(
                            sorted(
                                (item.seed_number, item.slot_index)
                                for item in q_slots
                                if item.seed_number is not None
                            )
                        ),
                        slots=tuple(q_slots),
                        nodes=bracket.nodes,
                        bye_slot_indexes=tuple(
                            item.slot_index
                            for item in q_slots
                            if item.entrant_kind == "bye"
                        ),
                        qualifier_placeholder_slots=tuple(
                            (item.placeholder_id, item.slot_index)
                            for item in q_slots
                            if item.entrant_kind == "qualifier_placeholder"
                            and item.placeholder_id is not None
                        ),
                    )
                )
                matched += 1
            if matched != 1:
                raise ValueError(
                    "Qualification RWC repair did not resolve exactly one Q bracket"
                )
            if predecessor.qualification_sections:
                qualification = None
                qualification_sections = tuple(rebuilt)
            else:
                qualification = rebuilt[0]
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
        return TournamentDrawRevision(
            schema_version=(
                "tournament_draw_revision.v7"
                if cross_draw
                else "tournament_draw_revision.v6"
            ),
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            event_id=predecessor.event_id,
            sequence=sequence,
            command_id=command_id,
            repair_kind="frozen_wild_card_repair",
            affected_draw_types=(
                ("main", "qualification") if cross_draw else ("main",)
            ),
            main_process_window_ordinal=main_process_window_ordinal,
            qualification_process_window_ordinal=(
                qualification_process_window_ordinal if cross_draw else None
            ),
            main_repair_action="frozen_wild_card_fill",
            qualification_repair_action=(
                "frozen_rwc_q_backfill" if cross_draw else None
            ),
            withdrawn_player_ids=(
                wild_card_repair_authority.withdrawn_player_id,
            ),
            replacement_cutoff_authorities=(
                wild_card_repair_authority.replacement_cutoff_authority,
            ),
            wild_card_repair_authority=wild_card_repair_authority,
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


def _repair_frozen_bracket_family(
    *,
    brackets: tuple[TournamentDrawBracket, ...],
    target_player_ids: tuple[str, ...],
) -> tuple[TournamentDrawBracket, ...]:
    templates: dict[tuple[int, int], TournamentDrawSlot] = {}
    mutable: dict[tuple[int, int], TournamentDrawSlot] = {}
    player_ref: dict[str, tuple[int, int]] = {}
    for bracket_index, bracket in enumerate(brackets):
        for slot in bracket.slots:
            ref = (bracket_index, slot.slot_index)
            templates[ref] = slot
            mutable[ref] = slot
            if slot.player_id is not None:
                if slot.player_id in player_ref:
                    raise ValueError(
                        "Draw-Freeze repair contains duplicate predecessor player"
                    )
                player_ref[slot.player_id] = ref

    predecessor_players = set(player_ref)
    target_set = set(target_player_ids)
    if len(target_set) != len(target_player_ids):
        raise ValueError("Draw-Freeze repair target contains duplicate players")

    removed = predecessor_players - target_set
    incoming = tuple(
        player_id
        for player_id in target_player_ids
        if player_id not in predecessor_players
    )
    if not removed:
        raise ValueError(
            "Draw-Freeze repair component has no removed predecessor player"
        )
    if len(incoming) > len(removed):
        raise ValueError(
            "Draw-Freeze repair has more incoming players than physical vacancies"
        )

    ordered_vacancies = sorted(
        (player_ref[player_id] for player_id in removed),
        key=lambda ref: _ordinary_vacancy_priority(ref, templates),
    )
    replacement_count = len(incoming)
    for destination, player_id in zip(
        ordered_vacancies[:replacement_count],
        incoming,
        strict=True,
    ):
        template = templates[destination]
        mutable[destination] = TournamentDrawSlot(
            slot_index=template.slot_index,
            idealized_slot_number=template.idealized_slot_number,
            entrant_kind="player",
            player_id=player_id,
        )

    for destination in ordered_vacancies[replacement_count:]:
        template = templates[destination]
        mutable[destination] = TournamentDrawSlot(
            slot_index=template.slot_index,
            idealized_slot_number=template.idealized_slot_number,
            entrant_kind="bye",
        )

    rebuilt = []
    for bracket_index, bracket in enumerate(brackets):
        slots = tuple(
            mutable[(bracket_index, index)]
            for index in range(1, bracket.bracket_size + 1)
        )
        players = {
            slot.player_id
            for slot in slots
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
                        for slot in slots
                        if slot.seed_number is not None
                    )
                ),
                slots=slots,
                nodes=bracket.nodes,
                bye_slot_indexes=tuple(
                    slot.slot_index
                    for slot in slots
                    if slot.entrant_kind == "bye"
                ),
                qualifier_placeholder_slots=tuple(
                    (slot.placeholder_id, slot.slot_index)
                    for slot in slots
                    if slot.entrant_kind == "qualifier_placeholder"
                    and slot.placeholder_id is not None
                ),
            )
        )
        if not players <= target_set:
            raise ValueError(
                "Draw-Freeze repair retained a player outside successor field"
            )

    actual_players = {
        slot.player_id
        for bracket in rebuilt
        for slot in bracket.slots
        if slot.player_id is not None
    }
    if actual_players != target_set:
        raise ValueError(
            "Draw-Freeze repair physical player set differs from successor field"
        )
    return tuple(rebuilt)


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

