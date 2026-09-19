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
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
)


class TournamentDrawRevision(FrozenInput):
    schema_version: Literal["tournament_draw_revision.v1"] = "tournament_draw_revision.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    command_id: str = Field(min_length=1, max_length=128)
    repair_kind: Literal["full_redraw"]
    draw_type: TournamentDrawType
    process_window_ordinal: int = Field(ge=1)
    repair_draw_seed: int
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    process_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_draw: TournamentDrawAuthority

    @model_validator(mode="after")
    def validate_scope(self):
        if (
            self.successor_draw.run_id,
            self.successor_draw.branch_id,
            self.successor_draw.event_id,
        ) != (self.run_id, self.branch_id, self.event_id):
            raise ValueError("Draw revision successor scope mismatch")
        if self.successor_draw.fingerprint == self.predecessor_draw_fingerprint:
            raise ValueError("Full redraw must produce a new Draw fingerprint")
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
        draw_input: TournamentDrawInputAuthority,
        process_authority: TournamentDrawProcessAuthority,
        draw_type: TournamentDrawType,
        process_window_ordinal: int,
        repair_draw_seed: int,
        sequence: int,
        command_id: str,
    ) -> TournamentDrawRevision:
        if predecessor.draw_input_fingerprint != draw_input.fingerprint:
            raise ValueError("Active Draw and frozen Draw Input dependency differ")
        if process_authority.phase_for(
            draw_type=draw_type,
            process_window_ordinal=process_window_ordinal,
        ) != "full_redraw":
            raise ValueError("Full redraw is only legal before Redraw Cutoff")

        regenerated = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input,
            command_id=command_id,
            algorithm_version=predecessor.algorithm_version,
            draw_seed_override=repair_draw_seed,
        )

        if draw_type == "main":
            successor = regenerated.model_copy(
                update={
                    "qualification": predecessor.qualification,
                    "qualification_sections": predecessor.qualification_sections,
                }
            )
        else:
            successor = regenerated.model_copy(
                update={
                    "main": predecessor.main,
                }
            )

        if draw_type == "qualification":
            before_ids = tuple(
                bracket.section_id for bracket in predecessor.qualification_brackets
            )
            after_ids = tuple(
                bracket.section_id for bracket in successor.qualification_brackets
            )
            if before_ids != after_ids:
                raise ValueError("Qualification redraw changed Q1..Qn linkage identities")
        else:
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
            draw_type=draw_type,
            process_window_ordinal=process_window_ordinal,
            repair_draw_seed=repair_draw_seed,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            process_authority_fingerprint=process_authority.fingerprint,
            successor_draw=successor,
        )