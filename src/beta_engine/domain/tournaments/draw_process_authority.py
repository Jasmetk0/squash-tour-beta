"""Canonical Qualification/Main Draw process-window phase authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawType,
)


TournamentDrawRepairPhase = Literal[
    "full_redraw",
    "seed_cascade",
    "draw_frozen",
]


class TournamentDrawProcessWindowPolicy(FrozenInput):
    """Configured post-draw process windows for one draw component.

    Master §15.10 fixes the last two window roles:
    - penultimate window begins Redraw Cutoff / seed-cascade phase;
    - final window begins Draw Freeze.

    Earlier windows, if configured, remain the complete-redraw phase.
    """

    process_window_count: int = Field(ge=2)
    redraw_cutoff_window_ordinal: int = Field(ge=1)
    draw_freeze_window_ordinal: int = Field(ge=2)

    @model_validator(mode="after")
    def validate_boundaries(self):
        if self.redraw_cutoff_window_ordinal != self.process_window_count - 1:
            raise ValueError(
                "Redraw Cutoff must begin at the penultimate process window"
            )
        if self.draw_freeze_window_ordinal != self.process_window_count:
            raise ValueError("Draw Freeze must begin at the final process window")
        return self

    @classmethod
    def from_window_count(cls, process_window_count: int):
        if process_window_count < 2:
            raise ValueError(
                "Draw process requires at least Redraw Cutoff and Draw Freeze windows"
            )
        return cls(
            process_window_count=process_window_count,
            redraw_cutoff_window_ordinal=process_window_count - 1,
            draw_freeze_window_ordinal=process_window_count,
        )

    def phase_at(self, process_window_ordinal: int) -> TournamentDrawRepairPhase:
        if process_window_ordinal < 1 or process_window_ordinal > self.process_window_count:
            raise ValueError("Process window ordinal is outside configured Draw process")
        if process_window_ordinal >= self.draw_freeze_window_ordinal:
            return "draw_frozen"
        if process_window_ordinal >= self.redraw_cutoff_window_ordinal:
            return "seed_cascade"
        return "full_redraw"


class TournamentDrawProcessAuthority(FrozenInput):
    """Immutable process-window authority bound to one canonical Draw version."""

    schema_version: Literal["tournament_draw_process_authority.v1"] = (
        "tournament_draw_process_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    configured_by_command_id: str = Field(min_length=1, max_length=128)
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification: TournamentDrawProcessWindowPolicy | None = None
    main: TournamentDrawProcessWindowPolicy

    def policy_for(self, draw_type: TournamentDrawType) -> TournamentDrawProcessWindowPolicy:
        if draw_type == "main":
            return self.main
        if self.qualification is None:
            raise ValueError("Tournament has no Qualification Draw process")
        return self.qualification

    def phase_for(
        self,
        *,
        draw_type: TournamentDrawType,
        process_window_ordinal: int,
    ) -> TournamentDrawRepairPhase:
        return self.policy_for(draw_type).phase_at(process_window_ordinal)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentDrawProcessAuthorityBuilder:
    @staticmethod
    def build(
        *,
        draw: TournamentDrawAuthority,
        command_id: str,
        main_process_window_count: int,
        qualification_process_window_count: int | None = None,
    ) -> TournamentDrawProcessAuthority:
        has_qualification = bool(draw.qualification_brackets)
        if has_qualification and qualification_process_window_count is None:
            raise ValueError(
                "Qualification Draw requires its own configured process-window count"
            )
        if not has_qualification and qualification_process_window_count is not None:
            raise ValueError(
                "Qualification process windows supplied for tournament without Qualification Draw"
            )

        return TournamentDrawProcessAuthority(
            run_id=draw.run_id,
            branch_id=draw.branch_id,
            event_id=draw.event_id,
            configured_by_command_id=command_id,
            draw_authority_fingerprint=draw.fingerprint,
            qualification=(
                TournamentDrawProcessWindowPolicy.from_window_count(
                    qualification_process_window_count
                )
                if qualification_process_window_count is not None
                else None
            ),
            main=TournamentDrawProcessWindowPolicy.from_window_count(
                main_process_window_count
            ),
        )
