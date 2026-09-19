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
    TournamentDrawType,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
)
from beta_engine.domain.tournaments.entry_field import TournamentEntryField
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
)


class TournamentDrawRevision(FrozenInput):
    schema_version: Literal["tournament_draw_revision.v2"] = "tournament_draw_revision.v2"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    command_id: str = Field(min_length=1, max_length=128)
    repair_kind: Literal["full_redraw"]
    affected_draw_types: tuple[TournamentDrawType, ...]
    main_process_window_ordinal: int | None = Field(default=None, ge=1)
    qualification_process_window_ordinal: int | None = Field(default=None, ge=1)
    repair_draw_seed: int
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
            raise ValueError("Full redraw must produce a new Draw fingerprint")
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
                "Qualification redraw requires Qualification process-window evidence"
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